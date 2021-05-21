from openerp import api, fields, models, _
from datetime import date, datetime
from openerp.exceptions import ValidationError, AccessDenied, AccessError

class emp_all_attendance_detail(models.TransientModel):
    _name = "all.attendance.detail"

    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    company_id = fields.Many2one('res.company', string="Company/Campus")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string="Department")


    @api.constrains('date_from','date_to')
    def date_constrains(self):
        if self.date_from >= self.date_to:
            raise ValidationError(_("Date From cannot Greater than or Equal with Date To"))
    


    def print_attendance_detail_report(self, cr, uid, ids, context=None):
        print('Test 11')
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        datas = {
                'ids': [],
                'model': 'hr.attendance',
                'form': data
                }
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.employee_individual_attendance_detail_report', data=datas, context=context)