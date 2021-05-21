from openerp import models, fields, api, _
from datetime import date, datetime
import pytz

class leave_early_wizard(models.TransientModel):
    _name = "leave.early.wizard"

    reason_id = fields.Many2one('hr.action.reason.leave.early', string="Reason")
    other_reason = fields.Char(strong="Describe")
    get_reason = fields.Boolean(string="Asking for other reason")
    total_leave_early = fields.Float("Leave Early Duration", digits=(16,11))

    @api.onchange('reason_id')
    def get_reason_name(self):
        if self.reason_id:
            self.get_reason = self.reason_id.other

    @api.multi
    def passing_value(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        curr_att = self.env['hr.attendance'].search([('employee_id','=', employee_id.id),('action','=','sign_in')], limit=1, order="name DESC")
        att_opt = 'leave_early'
        for rec in curr_att:
            if rec.attendance_options == 'late':
                att_opt = 'both'
            rec.update({
                'action': 'sign_out',
                'sign_out': datetime.now(),
                'leave_early_duration': self.total_leave_early,
                'leave_early_action_desc_id': self.reason_id.id,
                'other_reason_leave_early': self.other_reason,
                'get_reason_leave_early': True,
                'attendance_options': att_opt,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }

    @api.model
    def default_get(self, fields):
        res = super(leave_early_wizard, self).default_get(fields)
        now = date.today()
        dt_now = now.strftime('%Y-%m-%d')
        FMT = '%H:%M:%S'
        sisb_emp = self.env['hr.employee']
        if self._context is None:
            context = {}
        detail = {}
        employee_id = sisb_emp.search([('user_id', '=', self._uid)])
        print('now = ', datetime.now())
        # sched = self.env['employee.schedule.line'].search([('employee_id', '=', employee_id.id), ('date', '=', dt_now)])
        sched = self.env['hr.schedule.shift.list'].search([('employee_id', '=', employee_id.id), ('name', '=', dt_now)])
        total_duration = 0
        for schedule in sched.shift_id:
            curr_tz = pytz.timezone(schedule.default_timezone)
            timzone_time = datetime.now(curr_tz)
            if timzone_time.hour < int(schedule.end_hour):
                dt_now  = str(timzone_time.hour) + ':' + str(timzone_time.minute) + ':' + str(timzone_time.second)
                sched   = str(int(schedule.end_hour)) + ':' + str(int(float(schedule.end_hour%1 * 60))) + ':00'
                tdelta  = datetime.strptime(sched, FMT) - datetime.strptime(dt_now, FMT)
                total_duration = (float(tdelta.seconds) / 60) / 60.0
                detail['duration'] = total_duration
                detail['attendance_options'] = 'leave_early'
            elif timzone_time.hour == int(schedule.end_hour) and timzone_time.minute < int(float(schedule.end_hour%1 * 60)):
                dt_now  = str(timzone_time.hour) + ':' + str(timzone_time.minute) + ':' + str(timzone_time.second)
                sched   = str(int(schedule.end_hour)) + ':' + str(int(float(schedule.end_hour%1 * 60))) + ':00'
                tdelta  = datetime.strptime(sched, FMT) - datetime.strptime(dt_now, FMT)
                total_duration = (float(tdelta.seconds) / 60) / 60.0
                detail['duration'] = total_duration
                detail['attendance_options'] = 'leave_early'
            else:
                total_duration = 0.0
                detail = False
        if 'total_leave_early' in fields:
            res.update({'total_leave_early': detail['duration']})
        return res