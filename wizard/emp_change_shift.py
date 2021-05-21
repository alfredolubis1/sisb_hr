from openerp import models, fields, api, _
from openerp.exceptions import ValidationError, AccessError

class EmpChangeSchedule(models.TransientModel):
    _name = "change.schedule"

    name = fields.Char(string="Description")
    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    prev_shift_id = fields.Many2one('working.time.conf', string="Current Shift", readonly=True)
    new_shift_id = fields.Many2one('working.time.conf', string="New Shift")
    start_hour = fields.Float(string="Start Hour", digits=(16,11))
    end_hour = fields.Float(string="End Hour", digits=(16,11))
    late_tolerance = fields.Float(string="Late Tolerance", digits=(16,11))
    start_break = fields.Float(string="Start Break", digits=(16,11))
    end_break = fields.Float(string="End Break", digits=(16,11))

    # @api.onchange('new_shift_id')
    # def change_time_conf(self):
    #     if self.new_shift_id == self.prev_shift_id:
    #         warning = {'title': 'User Alert!',
    #                     'message': 'You cannot change Schedule with the Current Schedule!!'}
    #         return {'value': {'new_shift_id':False}, 'warning': warning}
    #     if self.new_shift_id:
    #         res = {}
    #         for rec in self.new_shift_id:
    #             res = {
    #             'start_hour': rec.start_hour,
    #             'end_hour': rec.end_hour,
    #             'late_tolerance': rec.late_tolerance,
    #             'start_break': rec.start_break,
    #             'end_break': rec.end_break,
    #             }
    #             print('res = ', res)
    #         return {'value': res}
    @api.onchange('new_shift_id')
    def change_time_conf(self):
        if self.new_shift_id == self.prev_shift_id:
            warning = {'title': 'User Alert!',
                        'message': 'You cannot change Schedule with the Current Schedule!!'}
            return {'value': {'new_shift_id': 0}, 'warning': warning}
        if self.new_shift_id:
            for rec in self.new_shift_id:
                self.start_hour = rec.start_hour
                self.end_hour = rec.end_hour
                self.late_tolerance = rec.late_tolerance
                self.start_break = rec.start_break
                self.end_break = rec.end_break

    @api.multi
    def apply_shift(self):
        if not self.new_shift_id:
            raise ValidationError(_('Please Set The New Shift to Apply'))
        for rec in self:
            prev_shift = rec.prev_shift_id
            prev_shift.employee_ids = [(3, self.employee_id.id,0)]
            new_shift = rec.new_shift_id
            new_shift.employee_ids = [(4,self.employee_id.id,0)]
            for emp in rec.employee_id:
                pass
                # emp.update({
                #     'working_time_id': rec.new_shift_id,
                # })
                # emp.working_time_id = rec.new_shift_id 
            rec.employee_id._onchange_schedule(self.new_shift_id)
        