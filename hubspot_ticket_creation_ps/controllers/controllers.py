from odoo import http
from odoo.http import request
import pytz
from pytz import timezone, UTC


def _fmt_ddmmyy(value):
    """Date/Datetime -> 'DD/MM/YY', no time. False/None -> ''."""
    if not value:
        return ''
    user_tz = request.env.user.tz or 'UTC'
    tz = pytz.timezone(user_tz)
    local_dt = UTC.localize(value).astimezone(tz)
    return local_dt.strftime('%d/%m/%y')


class BurgtecTicketData(http.Controller):
    @http.route('/hubspot_ticket_creation_ps/fetch_ticket_data', auth='user', type='json')
    def fetch_hubspot_ticket_data(self, planning_screen_id, **kw):
        planning_screen_data = []
        delivery_screen_data = []
        delivery_stage = False
        delivery_stage_references = []
        delivery_stage_status = False
        delivery_stage_name = {'unscheduled': 'Un-scheduled','on_track':'On Track','caution': 'Caution','off_track': 'Off Track','fully_received': 'Fully Received'}
        if planning_screen_id:
            planning_screen = request.env['planning.screen'].browse(planning_screen_id)
            if planning_screen:

                for i in range(1, planning_screen.stage_count + 1):
                    status = getattr(planning_screen, f"do_{i}_status", False)
                    if status == "planned":
                        quote_ref = f"{planning_screen.order_id.burgtec_quote_reference}-{i:03d}"
                        delivery_stage_references.append(quote_ref)
                for delivery_ref in delivery_stage_references:
                    delivery_stage = request.env['sale.order'].sudo().search(
                        [('burgtec_quote_reference', '=', delivery_ref)],
                        limit=1)
                    stage_num = int(delivery_ref.split('-')[-1])
                    field_name = f"do_stage_{stage_num}"
                    if delivery_stage:
                        delivery_stage_status = delivery_stage.delivery_status_tracking
                        delivery_screen_data.append({
                            'field_name': field_name,
                            'stage': delivery_stage.burgtec_quote_reference,
                            'delivery_stage_status': delivery_stage_name[
                                delivery_stage_status] if delivery_stage_status else '',
                        })

                project_quote_reference = planning_screen.order_id.burgtec_quote_reference
                all_tickets = request.env['hubspot.ticket.data'].search(
                    [('delivery_stage_number', 'ilike', project_quote_reference)]
                )
                for ticket in all_tickets:
                    stage = ticket.delivery_stage_number
                    if stage:
                        delivery_stage = request.env['sale.order'].sudo().search([('burgtec_quote_reference', '=', stage)],
                                                                limit=1)
                        if delivery_stage:
                            delivery_stage_status = delivery_stage.delivery_status_tracking
                    try:
                        stage_num = int(stage.split('-')[-1])
                        field_name = f"do_stage_{stage_num}"
                    except (ValueError, IndexError):
                        field_name = None

                    planning_screen_data.append({
                        'id': ticket.id,
                        'stage': stage,
                        'field_name': field_name,
                        'url': ticket.hubspot_ticket_url or '',
                         'Disp': _fmt_ddmmyy(ticket.scheduled_dispatch),
                        'Deliver': _fmt_ddmmyy(ticket.scheduled_delivers_date),
                        'Inst_St': _fmt_ddmmyy(ticket.scheduled_install_date),
                        'Inst_Cmp': _fmt_ddmmyy(ticket.scheduled_install_complete_date),
                        # 'delivery_stage_status': delivery_stage_name[delivery_stage_status] if delivery_stage_status else '',
                    })
        return planning_screen_data, delivery_screen_data
