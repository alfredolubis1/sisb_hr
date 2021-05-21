from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from datetime import date, datetime


class individual_detailed_employee_movement(models.TransientModel):
    _name = "individual.detailed.employee.movement"

    employee_id = fields.Many2one('hr.employee', 'Employee')
    company_id  = fields.Many2one('res.company', 'Company')
    date_from = fields.Date("From")
    date_to = fields.Date("To")



    @api.model
    def check_employee(self, employee_id, date_from, date_to):
        print('here')
        hr_tf_obj = self.env['hr.employee.transfer']
        # self._cr.execute("SELECT ")
        print('here1')
        employee_tf = hr_tf_obj.search([('employee_id', '=', employee_id.id), ('effective_date', '>=', date_from), ('effective_date', '<=', date_to), ('state', '=', 'transferred')])
        if not employee_tf:
            raise ValidationError (_("There is no Movement or Transfer From this Employee From {} To {}").format(date_from, date_to))

    @api.constrains('date_from', 'date_to')
    def date_rule(self):
        if self.date_from > self.date_to:
            raise ValidationError(_("Date From must be greater than Date To"))
    
    def print_report(self, cr, uid, ids, context=None):
        selfobj = self.browse(cr, uid, ids)
        check_employee = self.check_employee(cr, uid, selfobj.employee_id, selfobj.date_from, selfobj.date_to)
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': [],
             'model': 'individual.detailed.employee.movement',
             'form': data
            }
        print('datas = ', datas)
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.employee_individual_detailed_movement_report', data=datas, context=context)


    

class summary_employee_movement(models.TransientModel):
    _name = "summary.employee.movement"

    company_id  = fields.Many2one('res.company', 'Company')
    date_from   = fields.Date("From")
    date_to     = fields.Date("To")


    @api.constrains('date_from', 'date_to')
    def date_rule(self):
        if self.date_from > self.date_to:
            raise ValidationError(_("Date From must be greater than Date To"))
    
    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
             'ids': [],
             'model': 'summary.employee.movement',
             'form': data
            }
        print('datas = ', datas)
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.summary_employee_movement_report', data=datas, context=context)