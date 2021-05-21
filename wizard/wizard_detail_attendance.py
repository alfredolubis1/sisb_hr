from openerp import api, fields, models, _
from datetime import date, datetime
from openerp.exceptions import ValidationError, AccessError, AccessDenied

class summary_detail_report(models.TransientModel):
    _name = "summary.detail.report"

    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    academic_year_id = fields.Many2one('academic.year', string="Academic Year")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string="Department")


    @api.constrains('date_from','date_to')
    def date_constrains(self):
        if self.date_from >= self.date_to:
            raise ValidationError(_("Date From cannot Greater than or Equal with Date To"))


    def print_detail_attendance_report(self, cr, uid, ids, context=None):
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        datas = {
                'ids': [],
                'model': 'hr.attendance',
                'form': data
                }
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.sisb_employee_detail_summary_attendance_report', data=datas, context=context)