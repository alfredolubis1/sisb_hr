from openerp import api, fields, models, _
from datetime import date, datetime
from openerp.exceptions import ValidationError, AccessDenied, AccessError


class leave_accumulative_wizard(models.TransientModel):
    _name = "leave.accumulative.wizard"

    company_id  = fields.Many2one('res.company', string="Company")
    allocated_leave_id = fields.Many2one('allocate.leaves.run', "Year")
    leave_acc_select = fields.Many2many('hr.holidays.status', string="Leave to Display in Report")



    @api.constrains('leave_acc_select')
    def leave_report_display_rule(self):
        if len(self.leave_acc_select) != 6:
            raise ValidationError(_("Selected Leave must 5"))


    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        print('data = ', data)
        datas = {
             'ids': [],
             'model': 'hr.holidays',
             'form': data
            }
        print('datas = ', datas)
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.leave_accumulative_per_allocated', data=datas, context=context)