from odoo import _, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    onedrive_folder_id = fields.Char(string='OneDrive Folder ID', readonly=True, copy=False)
    onedrive_folder_url = fields.Char(string='OneDrive Folder URL', readonly=True, copy=False)
    onedrive_folder_name = fields.Char(string='OneDrive Folder Name', readonly=True, copy=False)

    def action_generate_deal_number(self):
        for record in self:
            if not record.series_sequence_id:
                raise UserError("Please select a Sequence Number before generating the sale order number.")
            series_record = record.series_sequence_id
            series_starting_value = series_record.starting_value
            series_ending_value = series_record.ending_value
            if series_starting_value > series_ending_value:
                raise UserError("Sale Order Series has Ended.")
            while record._check_duplicate_deal_number(series_starting_value):
                series_starting_value += 1
                if series_starting_value > series_ending_value:
                    raise UserError("No available numbers in this series range.")
            record.odoo_deal_number_6digit = series_starting_value
            # record.name = series_starting_value This field is computed.
            series_record.starting_value = series_starting_value + 1
            # create OneDrive Folder
            service = self.env['onedrive.service']
            if not self.onedrive_folder_id:
                info = service.create_lead_folder(self)

            # EXPORT CRM RECORD TO HUBSPOT DEAL
            record.export_deal_in_hubspot()


    def action_open_onedrive_folder(self):
        self.ensure_one()
        if not self.onedrive_folder_url:
            raise UserError(_('No OneDrive folder is linked to this lead yet.'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.onedrive_folder_url,
            'target': 'new',
        }

    def action_create_onedrive_folder(self):
        self.ensure_one()
        service = self.env['onedrive.service']
        info = service.create_lead_folder(self)


    def fix_previous_crm_lead_folder_url(self):
        service = self.env['onedrive.service']
        token = service._get_access_token()
        site_id = service._get_site_id(token, service._get_settings()['sharepoint_site_url'])

        leads = self.env['crm.lead'].search([('onedrive_folder_id', '!=', False)])
        fixed, failed = 0, 0
        for lead in leads:
            link = service._create_share_link(token, site_id, lead.onedrive_folder_id)
            if link:
                lead.onedrive_folder_url = link
                fixed += 1
            else:
                failed += 1
        self.env.cr.commit()
        raise Warning('Fixed %s, failed %s' % (fixed, failed))



