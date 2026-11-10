from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models
import mimetypes
import base64
import email.policy
import email
import email.policy
import subprocess
import re
from odoo.tools.misc import find_in_path
import email.utils
from odoo.tools import html_escape


EML_EXTENSIONS = ('.eml', '.msg')
PDF_OVERRIDE_CSS = """<style>
  html, body { margin:0 !important; padding:0 !important; background:#fff !important; }
  .email-background { padding:0 !important; background:#fff !important; }
  .email-container-responsive { border:0 !important; border-radius:0 !important;
      max-width:none !important; padding:0 !important; }
  .email-inline-wrapper { display:block !important; }
  .footer { margin:16px 0 0 0 !important; max-width:none !important; }
</style>"""


class AttachmentArtworkWizard(models.TransientModel):
    _name = 'attachment.artwork.wizard'
    _description = 'Attachment Artwork Wizard'

    component_id = fields.Many2one('sale.order.bom.component', string='Component', readonly=True)
    bom_line_id = fields.Many2one('sale.order.bom.component.line', readonly=True)
    planning_screen_line_id = fields.Many2one('planning.screen.line', readonly=True)
    sale_quote_planning_screen_line_id = fields.Many2one('sale.quote.planning.screen.line', readonly=True)

    # art_work_image = fields.Image(
    #     string="Artwork Image",
    #     attachment=True,
    #     max_width=1920,
    #     max_height=1920,
    # )
    attachment_file = fields.Binary(
        string="Attachment",
        attachment=True,
    )

    attachment_filename = fields.Char(
        string="Filename",
    )
    preview_image = fields.Image(
        string="Preview",
    )

    @api.onchange("attachment_file", "attachment_filename")
    def _onchange_attachment(self):
        self.preview_image = False

        if self.attachment_file and self.attachment_filename:
            mimetype, _ = mimetypes.guess_type(self.attachment_filename)

            if mimetype and mimetype.startswith("image/"):
                self.preview_image = self.attachment_file

    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'sale.order.bom.component.line':
            active_id = self.env.context.get('active_id')
            if active_id:
                bom_line = self.env['sale.order.bom.component.line'].browse(active_id)
                res.update({
                    'component_id': bom_line.component_id.id if bom_line.component_id else False,
                    'bom_line_id': bom_line.id
                })
        if self.env.context.get('active_model') == 'planning.screen.line':
            active_id = self.env.context.get('active_id')
            if active_id:
                planning_screen_line = self.env['planning.screen.line'].browse(active_id)
                res.update({
                    'planning_screen_line_id': planning_screen_line.id

                })
        if self.env.context.get('active_model') == 'sale.quote.planning.screen.line':
            active_id = self.env.context.get('active_id')
            if active_id:
                sale_quote_planning_screen_line = self.env['sale.quote.planning.screen.line'].browse(active_id)
                res.update({
                    'sale_quote_planning_screen_line_id': sale_quote_planning_screen_line.id

                })
        return res

    def _eml_headers_html(self, msg):
        """From / To / Date, verbatim from the .eml. Never raises."""
        rows = []
        for label in ('From', 'To', 'Date'):
            try:
                value = msg.get(label)
            except Exception:
                value = None
            if value:
                rows.append(
                    '<tr><td style="font-weight:bold;padding-right:8px;vertical-align:top;'
                    'white-space:nowrap">%s</td><td>%s</td></tr>'
                    % (label, html_escape(str(value).strip()))
                )
        if not rows:
            return ''
        return ('<table style="font-size:10px;font-family:Arial,sans-serif;margin:0 0 8px 0">'
                '%s</table><hr style="border:0;border-top:1px solid #ccc;margin:0 0 10px 0">'
                % ''.join(rows))


    def _eml_to_pdf(self, raw):
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        body = msg.get_body(preferencelist=('html', 'plain'))
        content = body.get_content() if body else ''
        if not body or body.get_content_type() == 'text/plain':
            content = '<html><head></head><body><pre style="white-space:pre-wrap">%s</pre></body></html>' % content

        if '</head>' in content:
            html = content.replace('</head>', PDF_OVERRIDE_CSS + '</head>', 1)
        else:
            html = PDF_OVERRIDE_CSS + content

        header = self._eml_headers_html(msg)
        if header:
            header = '<div style="padding:12px 12px 0 12px">%s</div>' % header
            if '<body' in html:
                # lambda form: a literal replacement would eat backslash escapes
                html = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + header, html, count=1)
            else:
                html = header + html

        proc = subprocess.run([
            find_in_path('wkhtmltopdf'), '--quiet',
            '--page-width', '145mm', '--page-height', '297mm',
            '--margin-top', '3', '--margin-bottom', '3',
            '--margin-left', '3', '--margin-right', '3',
            '--encoding', 'utf-8',
            '--disable-local-file-access',
            '--load-error-handling', 'ignore',
            '--load-media-error-handling', 'ignore',
            '-', '-',
        ], input=html.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)

        if not proc.stdout:
            raise UserError(_("PDF conversion failed: %s") % proc.stderr.decode()[:400])
        return proc.stdout

    def _create_artwork_attachment(self):
        self.ensure_one()
        name = self.attachment_filename
        datas = self.attachment_file

        if name and name.lower().endswith('.eml'):
            pdf = self._eml_to_pdf(base64.b64decode(self.attachment_file))
            datas = base64.b64encode(pdf)
            name = '%s.pdf' % name[:-4]

        attachment = self.env['ir.attachment'].create({
            'name': name,
            'datas': datas,
            'res_model': self._name,
            'res_id': self.id,
        })
        return attachment


    def action_add_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if not rec.attachment_file:
                raise UserError(_("You have not added any Artwork!"))
            # delete previous attachment if any
            if rec.bom_line_id.attachment_id:
                rec.bom_line_id.attachment_id.unlink()
            if rec.planning_screen_line_id.attachment_id:
                rec.planning_screen_line_id.attachment_id.unlink()
            if rec.sale_quote_planning_screen_line_id.attachment_id:
                rec.sale_quote_planning_screen_line_id.attachment_id.unlink()
            attachment = rec._create_artwork_attachment()
            if attachment:
                attachment_url = f"{base_url}/web/content/{attachment.id}?download=false"
                if rec.bom_line_id:
                    rec.bom_line_id.write({
                        'artwork_image_url': attachment_url,
                        'attachment_id': attachment.id,
                    })
                if rec.planning_screen_line_id:
                    rec.planning_screen_line_id.write({
                        'artwork_image_url': attachment_url,
                        'attachment_id': attachment.id,
                    })
                if rec.sale_quote_planning_screen_line_id:
                    rec.sale_quote_planning_screen_line_id.write({
                        'artwork_image_url': attachment_url,
                        'attachment_id': attachment.id,
                    })
