from openerp import api, fields, models, _
from datetime import date, datetime
from openerp.exceptions import ValidationError, AccessDenied, AccessError

class overtime_work_inspection_wiz(models.TransientModel):
    _name = "overtime.work.inspection.wiz"

    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    company_id = fields.Many2one('res.company', string="Company/Campus")


    @api.constrains('date_from','date_to')
    def date_constrains(self):
        if self.date_from >= self.date_to:
            raise ValidationError(_("Date From cannot Greater than or Equal with Date To"))



    def print_report(self, cr, uid, ids, context=None):
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        datas = {
                'ids': [],
                'model': 'hr.overtime.request',
                'form': data
                }
        print('datas = ', datas)
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.employee_overtime_work_inspection', data=datas, context=context)
