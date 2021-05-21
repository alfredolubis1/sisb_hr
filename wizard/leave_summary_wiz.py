from openerp import api, fields, models, _
from datetime import date, datetime
from openerp.exceptions import ValidationError, AccessDenied, AccessError

class leave_summary_wizard(models.TransientModel):
    _name = "leave.summary.wizard"

    company_id  = fields.Many2one('res.company', string="Company")
    date_from   = fields.Date("From")
    date_to     = fields.Date("To")



    

    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': [],
             'model': 'hr.holidays',
             'form': data
            }
        print('datas = ', datas)
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.leave_summary_percompany', data=datas, context=context)



class individual_leave_summary_wizard(models.TransientModel):
    _name = "individual.leave.summary.wizard"

    company_id  = fields.Many2one('res.company', string="Company")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    date_from   = fields.Date("From")
    date_to     = fields.Date("To")


    

    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': [],
             'model': 'hr.holidays',
             'form': data
            }
        print('datas = ', datas)
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.individual_leave_summary', data=datas, context=context)