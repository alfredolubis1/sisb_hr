import time
import calendar
from datetime import datetime, date, timedelta
import pytz
from tzlocal import get_localzone
from openerp.osv import fields, osv
from openerp.tools.translate import _
from .utility.utils import hour_float_to_time as hftt
from tzlocal import get_localzone
from pytz import timezone
from openerp.exceptions import ValidationError


class hr_action_reason_late(osv.osv):
    _name = "hr.action.reason.late"
    _description = "Action Reason Late"
    _columns = {
        'name': fields.char('Late Reason', required=True, help='Specifies the reason for Signing In/Signing Out.'),
        'other': fields.boolean("Ask for Other Reason", help="When this box ticked, it will ask the Employee to describe their reason of Late"),
    }


class hr_action_reason_leave_early(osv.osv):
    _name = "hr.action.reason.leave.early"
    _description = "Action Reason Leave Early"
    _columns = {
        'name': fields.char('Leave Early Reason', required=True, help='Specifies the reason for Signing In/Signing Out.'),
        'other': fields.boolean("Ask for Other Reason", help="When this box ticked, it will ask the Employee to describe their reason of Leave Early"),
    }

def _employee_get(obj, cr, uid, context=None):
    ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
    return ids and ids[0] or False

class hr_attendance(osv.osv):
    _name = 'hr.attendance'
    _inherit = ['mail.thread','hr.attendance']
    _description = "Attendance"

    def _worked_hours_compute(self, cr, uid, ids, fieldnames, args, context=None):
        """For each hr.attendance record of action sign-in: assign 0.
        For each hr.attendance record of action sign-out: assign number of hours since last sign-in.
        """
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.action == 'sign_in':
                res[obj.id] = 0
            elif obj.action == 'sign_out':
                # Get the associated sign-in

                # last_signin_id = self.search(cr, uid, [
                #     ('employee_id', '=', obj.employee_id.id),
                #     ('name', '<', obj.name), ('action', '=', 'sign_in')
                # ], limit=1, order='name DESC')
                # if last_signin_id:
                #     last_signin = self.browse(cr, uid, last_signin_id, context=context)[0]

                    # Compute time elapsed between sign-in and sign-out
                # last_signin_datetime = datetime.strptime(last_signin.name, '%Y-%m-%d %H:%M:%S')
                signin_datetime = datetime.strptime(obj.name, '%Y-%m-%d %H:%M:%S')
                signout_datetime = datetime.now()
                workedhours_datetime = (signout_datetime - signin_datetime)
                res[obj.id] = ((workedhours_datetime.seconds) / 60) / 60.0
                # else:
                #     res[obj.id] = False
        return res


    def get_todays_attendance(self, cr, uid, ids, context=None):
        now = date.today()
        dt_now = now.strftime('%Y-%m-%d')
        FMT = '%H:%M:%S'
        employee_obj = self.pool.get('hr.employee')
        if context is None:
            context = {}
        detail = {}
        # employee_id = _employee_get(self, cr, uid, context=None)
        employee_id = employee_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        emp_obj = employee_obj.browse(cr, uid, employee_id, context=context)
        sched = self.pool.get('employee.schedule.line').search(cr, uid, [('employee_id', '=', employee_id[0]), ('date', '=', dt_now)])
        shift_obj = self.pool.get('hr.schedule.shift.list').search(cr, uid, [('employee_id', '=', employee_id[0]), ('name', '=', dt_now)])
        shift_id = self.pool.get('hr.schedule.shift.list').browse(cr, uid, shift_obj)
        total_duration = 0
        for att in emp_obj:
            if att.state == 'absent':
                for schedule in shift_id.shift_id:
                    timezone = pytz.timezone(schedule.default_timezone)
                    tmz_curr_time = datetime.now(timezone)
                    tmz_curr_hour = str(tmz_curr_time.hour) + ':' + str(tmz_curr_time.minute)
                    start_time = hftt(schedule.start_hour)
                    if tmz_curr_time.hour > schedule.start_hour:
                        time_now = str(tmz_curr_time.hour) + ':' + str(tmz_curr_time.minute) + ':' + str(tmz_curr_time.second)
                        sched = str(int(schedule.start_hour)) + ':' + str(int(float((schedule.late_tolerance * 60) + (schedule.start_hour%1 * 60)))) + ':00'
                        tdelta = datetime.strptime(time_now, FMT) - datetime.strptime(sched, FMT)
                        total_duration = (float(tdelta.seconds) / 60) / 60.0
                        detail['duration'] = total_duration
                        detail['attendance_options'] = 'late'

                    elif tmz_curr_time.hour == int(schedule.start_hour) and tmz_curr_time.minute > int(float(schedule.late_tolerance * 60) + (schedule.start_hour%1 * 60)):
                        dt_now = str(tmz_curr_time.hour) + ':' + str(tmz_curr_time.minute) + ':' + str(tmz_curr_time.second)
                        sched = str(int(schedule.start_hour)) + ':' + str(int(float((schedule.late_tolerance * 60) + (schedule.start_hour%1 * 60)))) + ':00'
                        tdelta = datetime.strptime(dt_now, FMT) - datetime.strptime(sched, FMT)
                        total_duration = (float(tdelta.seconds) / 60) / 60.0
                        detail['duration'] = total_duration
                        detail['attendance_options'] = 'late'
                    else:
                        total_duration = 0
                        detail = False
            return detail

    def onchange_late_action_desc(self, cr, uid, ids, late_action_desc, context=None):
        values = {}
        if late_action_desc:
            action = self.pool.get('hr.action.reason.late').browse(cr, uid, late_action_desc, context=context)
            values = {'get_reason_late': action.other,}
        return {'value': values}

    def onchange_leave_early_action_desc(self, cr, uid, ids, leave_early_duration, context=None):
        values = {}
        if leave_early_duration:
            action = self.pool.get('hr.action.reason.leave.early').browse(cr, uid, leave_early_duration, context=context)
            values = {'get_reason_leave_early': action.other,}
        return {'value': values}

    def default_get(self, cr, uid, fields, context=None):
        res = super(hr_attendance, self).default_get(cr, uid, fields, context=context)
        late_duration = self.get_todays_attendance(cr, uid, context)
        print('late_today = ', late_duration)
        # check_employee = self.check_employee(cr, uid, context)
        if 'late_duration' in fields:
            if late_duration:
                res.update({'late_duration': late_duration['duration']})
                res.update({'attendance_options': late_duration['attendance_options']})
        return res


    _columns = {
        'name'                      : fields.datetime('Sign In', required=True, select=1, track_visibility="onchange"),
        'shift_id'                  : fields.many2one('work.time.structure', "Shift", required=True, track_visibility='onchange'),
        'sign_out'                  : fields.datetime('Sign Out', select=1, track_visibility="onchange"),
        'other_reason_late'         : fields.char(string="Other Reason", track_visibility="onchange"),
        'other_reason_leave_early'  : fields.char(string="Other Reason", track_visibility="onchange"),
        'action'                    : fields.selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('action','Action')], 'Action', required=True),
        'late_action_desc_id'       : fields.many2one("hr.action.reason.late", "Late Reason", help='Specifies the reason for Signing In/Signing Out in case of extra hours.', track_visibility="onchange"),
        'leave_early_action_desc_id': fields.many2one("hr.action.reason.leave.early", "Leave Early Reason", help='Specifies the reason for Signing In/Signing Out in case of extra hours.', track_visibility="onchange"),
        'employee_id'               : fields.many2one('hr.employee', "Employee", required=True, select=True, track_visibility="onchange"),
        'late_duration'             : fields.float("Late Duration", type="float", digits=(16,11), track_visibility="onchange"),
        'leave_early_duration'      : fields.float("Early Duration", type="float", digits=(16,11), track_visibility="onchange"),
        'worked_hours'              : fields.function(_worked_hours_compute, type='float', string='Worked Hours', store=True),
        'compensated_days'          : fields.boolean('Compensated Days', track_visibility="onchange"),
        'overtime'                  : fields.boolean('Overtime', track_visibility="onchange"),
        'overtime_ids'              : fields.one2many('overtime.list.line', 'attendance_id', string="Overtime Detail"),
        'get_reason_late'           : fields.boolean(string="Reason"),
        'get_reason_leave_early'    : fields.boolean(string="Reason"),
        'attendance_options'        : fields.selection([
                                                ('late','Late'),
                                                ('leave_early','Leave Early'),
                                                ('both','Late & Leave Early'),
                                                ], string="Options"),
    }
    _defaults = {
        'name'                  : lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), #please don't remove the lambda, if you remove it then the current time will not change
        'employee_id'           : _employee_get,
        'compensated_days'      : lambda *a: False,
    }


    def on_change_employee(self, cr, uid, ids, employee_id, context=None):
        values = {}
        now = date.today()
        dt_now = now.strftime('%Y-%m-%d')
        print('disini')
        print('employee_id = ', employee_id)
        if employee_id:
            shift_obj = self.pool.get('hr.schedule.shift.list').search(cr, uid, [('employee_id', '=', employee_id), ('name', '=', dt_now)])
            shift_id = self.pool.get('hr.schedule.shift.list').browse(cr, uid, shift_obj)
            values = {'shift_id': shift_id.shift_id.id}
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
            if employee.state == 'present':
                values.update({'action' : 'sign_out',})
            elif employee.state == 'absent':
                values.update({'action' : 'sign_in',})

            
        return {'value' : values}

    def _altern_si_so(self, cr, uid, ids):
        """ Alternance sign_in/sign_out check.
            Previous (if exists) must be of opposite action.
            Next (if exists) must be of opposite action.
        """

        """ Implementing this logic at the attendance level doesn't work, so
        we skip it, and check at the whole time sheet level. 's all good!"""
        # for att in self.browse(cr, uid, ids, context=context):
        #     # search and browse for first previous and first next records
        #     prev_att_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '<', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name DESC')
        #     next_add_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '>', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name ASC')
        #     prev_atts = self.browse(cr, uid, prev_att_ids, context=context)
        #     next_atts = self.browse(cr, uid, next_add_ids, context=context)
        #     # check for alternance, return False if at least one condition is not satisfied
        #     # if prev_atts and prev_atts[0].action == att.action: # previous exists and is same action
        #     #     return False
        #     # if next_atts and next_atts[0].action == att.action: # next exists and is same action
        #     #     return False
        #     if (not prev_atts) and (not next_atts) and att.action != 'sign_in': # first attendance must be sign_in
        #         return False
        return True

    # _constraints = [(_altern_si_so, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    _constraints = [(_altern_si_so, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    _order = 'name desc'



    def attendance_save(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }

    def confirm_save(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }
hr_attendance()


class hr_employee(osv.osv):
    _inherit = "hr.employee"
    _description = "Employee"

    def _state(self, cr, uid, ids, name, args, context=None):
        result = {}
        if not ids:
            return result
        for id in ids:
            result[id] = 'absent'
        cr.execute('SELECT hr_attendance.action, hr_attendance.employee_id \
                FROM ( \
                    SELECT MAX(name) AS name, employee_id \
                    FROM hr_attendance \
                    WHERE action in (\'sign_in\', \'sign_out\') \
                    GROUP BY employee_id \
                ) AS foo \
                LEFT JOIN hr_attendance \
                    ON (hr_attendance.employee_id = foo.employee_id \
                        AND hr_attendance.name = foo.name) \
                WHERE hr_attendance.employee_id IN %s',(tuple(ids),))
        for res in cr.fetchall():
            result[res[1]] = res[0] == 'sign_in' and 'present' or 'absent'
        return result

    def _last_sign(self, cr, uid, ids, name, args, context=None):
        result = {}
        if not ids:
            return result
        for id in ids:
            result[id] = False
            cr.execute("""select max(name) as name
                        from hr_attendance
                        where action in ('sign_in', 'sign_out') and employee_id = %s""",(id,))
            for res in cr.fetchall():
                result[id] = res[0]
        return result

    def _attendance_access(self, cr, uid, ids, name, args, context=None):
        # this function field use to hide attendance button to singin/singout from menu
        visible = self.pool.get("res.users").has_group(cr, uid, "base.group_hr_attendance")
        return dict([(x, visible) for x in ids])

    _columns = {
       'state': fields.function(_state, type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Attendance'),
       'last_sign': fields.function(_last_sign, type='datetime', string='Last Sign'),
       'attendance_access': fields.function(_attendance_access, string='Attendance Access', type='boolean'),
    }

    def _action_check(self, cr, uid, emp_id, dt=False, context=None):
        cr.execute('SELECT MAX(name) FROM hr_attendance WHERE employee_id=%s', (emp_id,))
        res = cr.fetchone()
        return not (res and (res[0]>=(dt or time.strftime('%Y-%m-%d %H:%M:%S'))))


    def check_holiday(self, cr, uid, employee, tz_time, context=None):
        holiday = False
        for rec in employee:
            if rec.holiday_type_id:
                for h in rec.holiday_type_id:
                    l = h.holiday_type_line_ids.filtered(lambda x: x.date_hd == tz_time)
                    if l:
                        holiday = True
            elif not rec.holiday_type_id:
                for l in rec.department_id:
                    if l.public_holiday_type == 'public' or 'both':
                        public_hd_obj = self.pool.get('public.holidays.days')
                        check_hd = public_hd_obj.search(cr, uid, [('name', '=', tz_time)], context=context)
                        print('check_hd = ', check_hd)
                        if check_hd:
                            holiday = True
                    elif l.public_holiday_type == 'school' or ' both':
                        academic_year = self.pool.get('academic.year').search(cr, uid, [('date_start', '<=', tz_time),('date_stop', '>=', tz_time)], context=context)
                        school_hd_obj = self.pool.get('school.holidays').search(cr, uid, [('year_id', '=', academic_year[0])])
                        if school_hd_obj:
                            school_hd = self.pool.get('school.holidays').browse(cr, uid, school_hd_obj)
                            check_hd = school_hd.line_ids.filtered(lambda x:x.date == tz_time)
                            if check_hd:
                                holiday =  True
        return holiday
                        




    # def calculate_overtime(self, cr, uid, employee, schedule, ot_obj, type, context=None):
    #     k = {}
    #     FMT = "%H:%M"
    #     ot_detail = {}
    #     minute_rounded = 0
    #     ot_length = ''
    #     tz = pytz.timezone(schedule.default_timezone)
    #     tz_time = datetime.now(tz)
    #     print('tz_time = ', tz_time)
    #     overtime_id = self.pool.get('hr.overtime.request.line').browse(cr, uid, ot_obj)
    #     for rec in overtime_id:
    #         k['start_hour'] = rec.start_hour
    #         k['end_hour'] = rec.end_hour
    #         k['ot_type'] = rec.overtime_type_id and rec.overtime_type_id.id
    #     log_in_out = datetime.strftime(tz_time, FMT)
    #     year = int(datetime.strftime(tz_time, '%Y'))
    #     month = int(datetime.strftime(tz_time, '%m'))
    #     day = int(datetime.strftime(tz_time, '%d'))
    #     print('log_in =', log_in_out)
    #     start_ot = '{0:02.0f}:{1:02.0f}'.format(*divmod(k['start_hour'] * 60, 60))
    #     end_ot = '{0:02.0f}:{1:02.0f}'.format(*divmod(k['end_hour'] * 60, 60))
    #     print('end_ot = ', end_ot)
    #     frequently = ''
    #     for r in employee:
    #         for l in r.allowance_type_ids.filtered(lambda x: x.allow_type_id.salary == True):
    #             frequently = l.frequently
    #     today = calendar.weekday(year, month, day)
    #     weekend = today if today > 4 else False
    #     check_shift =  [r.options for r in schedule.day_of_wewks_ids.filtered(lambda x: int(x.day_of_week) == today)]
    #     if check_shift[0] == False:
    #         raise ValidationError(_("The Shift has no Work Day Configuration, Please ask your Supervisor or Manager to Configure it"))
    #     print('check_shift = ', check_shift)
    #     holiday_shift = True if check_shift[0] == 'holiday' else False
    #     print('holiday_shift = ', holiday_shift)
    #     holiday_year = self.check_holiday(cr, uid, employee, tz_time)
    #     # if holiday_shift or holiday_year:
    #     #     if type == 'sign_in':
    #     #         if datetime.strptime(log_in_out, FMT) <= datetime.strptime(start_ot, FMT):
    #     #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
    #     #         else:
    #     #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
    #     # if not holiday_year:
    #     #     if today == 6:
    #     #         ot_detail['overtime_rate'] = 'triple'
    #     #     elif today != 6:
    #     #         ot_detail['overtime_rate'] = 'one_half'
    #     # elif holiday_year:
    #     #     ot_detail['overtime_rate'] = 'triple'
    #     if type == 'sign_in':
    #         if datetime.strptime(log_in_out, FMT) <= datetime.strptime(start_ot, FMT):
    #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
    #         else:
    #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
    #     if type == 'sign_out':
    #         if datetime.strptime(log_in_out, FMT) >= datetime.strptime(end_ot, FMT):
    #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
    #         else:
    #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
    #     seconds = ot_length.seconds
    #     hour_length = seconds / 3600.0
    #     if hour_length > (k['end_hour'] - k['start_hour']):
    #         hour_length = k['end_hour'] - k['start_hour']
    #     hour = seconds//3600
    #     minute = (seconds % 3600) // 60
    #     if minute <= 14:
    #         minute_rounded = 0
    #     elif 15 <= minute <= 29:
    #         minute_rounded = 15
    #     elif 30 <= minute <= 44:
    #         minute_rounded = 30
    #     elif 45 <= minute <= 59:
    #         minute_rounded = 45
    #     ot_rounded = ((hour * 3600.0) + (minute_rounded * 60.0)) / 3600.0
    #     print('type = ', k['ot_type'])
    #     if holiday_year or holiday_shift:
    #         ot_detail['rate_triple']  = ot_rounded
    #     ot_detail['start_ot']   = k['start_hour']
    #     ot_detail['end_ot']     = k['end_hour']
    #     ot_detail['ot_type']    = k['ot_type']
    #     ot_detail['ot_length']  = hour_length
    #     ot_detail['ot_rounded'] = ot_rounded
    #     return ot_detail
    
    def rounded_overtime(self, cr, uid, ot_hour, context=None):
        """Overtime Hour Rounded 15 minutes below 
           e.g : 1. 10:50 -> 10:45 
                 2. 10:03 -> 10:00 (rounded the minute to 0 if minute less than 15)
        """
        minute_rounded = 0
        hour    = ot_hour.seconds // 3600
        minutes = (ot_hour.seconds % 3600.0) // 60
        if minutes <= 14:
            minute_rounded = 0
        elif 15 <= minutes <= 29:
            minute_rounded = 15
        elif 30 <= minutes <= 44:
            minute_rounded = 30
        elif 45 <= minutes <= 59:
            minute_rounded = 45
        ot_rate_holiday = ((hour * 3600.0) + (minute_rounded * 60.0)) / 3600.0

        return ot_rate_holiday


    def calculate_overtime(self, cr, uid, employee, schedule, ot_obj, type, context=None):
        k               = {}
        FMT             = "%H:%M"
        ot_detail       = {}
        minute_rounded  = 0
        start_ot        = 0.00
        end_ot          = 0.00 
        ot_length       = ''
        frequently      = '' # Use for to clarify the employee overtime rate 
        tz              = pytz.timezone(schedule.default_timezone)
        tz_time         = datetime.now(tz)
        
        # Time In and Out
        hour_time_in_out, minute_time_in_out = tz_time.hour, tz_time.minute
        float_time_in_out = ((hour_time_in_out * 3600.0) + (minute_time_in_out * 60.0)) / 3600.00


        overtime_id     = self.pool.get('hr.overtime.request.line').browse(cr, uid, ot_obj) #Check Overtime
        for rec in overtime_id:
            k['start_hour'] = rec.start_hour
            k['end_hour'] = rec.end_hour
            k['ot_type'] = rec.overtime_type_id and rec.overtime_type_id.id
        log_in_out = datetime.strftime(tz_time, FMT)
        year = int(datetime.strftime(tz_time, '%Y'))
        month = int(datetime.strftime(tz_time, '%m'))
        day = int(datetime.strftime(tz_time, '%d'))
        start_ot = '{0:02.0f}:{1:02.0f}'.format(*divmod(k['start_hour'] * 60, 60))
        end_ot = '{0:02.0f}:{1:02.0f}'.format(*divmod(k['end_hour'] * 60, 60))
        for r in employee:
            for l in r.allowance_type_ids.filtered(lambda x: x.allow_type_id.salary == True):
                frequently = l.frequently
        today = calendar.weekday(year, month, day)
        weekend = today if today > 4 else False
        check_shift =  [r.options for r in schedule.day_of_wewks_ids.filtered(lambda x: int(x.day_of_week) == today)]
        if check_shift[0] == False:
            raise ValidationError(_("The Shift has no Work Day Configuration, Please ask your Supervisor or Manager to Configure it"))
        holiday_shift = True if check_shift[0] == 'holiday' else False
        holiday_year = self.check_holiday(cr, uid, employee, tz_time)
        if holiday_shift or holiday_year:
            """Calculate OT Rate When the day is Holiday"""
            ot_rate_holiday = ''
            if type == 'sign_in':
                start_work  = schedule.start_hour
                end_hd_ot   = '{0:02.0f}:{1:02.0f}'.format(*divmod(start_work * 60, 60))

                end_work    = schedule.end_hour
                end_wk_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(end_work * 60, 60))

                if datetime.strptime(log_in_out, FMT) <= datetime.strptime(start_ot, FMT):
                    ot_rate_holiday = datetime.strptime(end_hd_ot, FMT) - datetime.strptime(start_ot, FMT)
                elif (datetime.strptime(log_in_out, FMT) > datetime.strptime(start_ot, FMT)) and (datetime.strptime(log_in_out, FMT) <= datetime.strptime(end_hd_ot, FMT)):
                    ot_rate_holiday = datetime.strptime(end_hd_ot, FMT) - datetime.strptime(log_in_out, FMT)
                # elif datetime.strptime(log_in_out, FMT) > datetime.strptime(end_hd_ot, FMT):
                #     ot_rate_holiday = datetime.strptime('00:00', FMT)

                calculate_overtime = self.rounded_overtime(cd, uid, ot_rate_holiday)
                if frequently == 'monthly':
                    ot_detail['rate_triple'] = calculate_overtime
                else:
                    ot_detail['rate_double'] = calculate_overtime

                ot_detail['ot_time_in'] = float_time_in_out
                hour_length = datetime.strptime(end_wk_time, FMT) - datetime.strptime(log_in_out, FMT)
                ot_detail['rate_one']   = schedule.total_wk_hour
            if type == 'sign_out':
                pass
        elif not holiday_shift and not holiday_year:
            if type == 'sign_in':
                ot_rate_regular = ''
                if datetime.strptime(log_in_out, FMT) <= datetime.strptime(start_ot, FMT):
                    ot_rate_regular = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
                else:
                    ot_rate_regular = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
                calculate_overtime = self.rounded_overtime(cr, uid, ot_rate_regular)
                ot_detail['rate_one_half'] = calculate_overtime
                ot_detail['ot_time_in'] = float_time_in_out
            if type == 'sign_out':
                ot_rate_regular = ''
                if datetime.strptime(log_in_out, FMT) >= datetime.strptime(end_ot, FMT):
                    ot_rate_regular = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
                else:
                    ot_rate_regular = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
                calculate_overtime = self.rounded_overtime(cr, uid, ot_rate_regular)
                ot_detail['rate_one_half'] = calculate_overtime
                ot_detail['ot_time_out'] = float_time_in_out
        ot_detail['start_ot']   = k['start_hour']
        ot_detail['end_ot']     = k['end_hour']
        ot_detail['ot_type']    = k['ot_type']  
        return ot_detail

        # if holiday_shift or holiday_year:
        #     if type == 'sign_in':
        #         if datetime.strptime(log_in_out, FMT) <= datetime.strptime(start_ot, FMT):
        #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
        #         else:
        #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
        # if not holiday_year:
        #     if today == 6:
        #         ot_detail['overtime_rate'] = 'triple'
        #     elif today != 6:
        #         ot_detail['overtime_rate'] = 'one_half'
        # elif holiday_year:
        #     ot_detail['overtime_rate'] = 'triple'
        # if type == 'sign_in':
        #     if datetime.strptime(log_in_out, FMT) <= datetime.strptime(start_ot, FMT):
        #         ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
        #     else:
        #         ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
        # if type == 'sign_out':
        #     if datetime.strptime(log_in_out, FMT) >= datetime.strptime(end_ot, FMT):
        #         ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
        #     else:
        #         ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
        # seconds = ot_length.seconds
        # hour_length = seconds / 3600.0
        # if hour_length > (k['end_hour'] - k['start_hour']):
        #     hour_length = k['end_hour'] - k['start_hour']
        # hour = seconds//3600
        # minute = (seconds % 3600) // 60
        # if minute <= 14:
        #     minute_rounded = 0
        # elif 15 <= minute <= 29:
        #     minute_rounded = 15
        # elif 30 <= minute <= 44:
        #     minute_rounded = 30
        # elif 45 <= minute <= 59:
        #     minute_rounded = 45
        # ot_rounded = ((hour * 3600.0) + (minute_rounded * 60.0)) / 3600.0
        # print('type = ', k['ot_type'])
        # if holiday_year or holiday_shift:
        #     ot_detail['rate_triple']  = ot_rounded
        # ot_detail['start_ot']   = k['start_hour']
        # ot_detail['end_ot']     = k['end_hour']
        # ot_detail['ot_type']    = k['ot_type']
        # ot_detail['ot_length']  = hour_length
        # ot_detail['ot_rounded'] = ot_rounded
        # return ot_detail


    def attendance_ask_shift(self, cr, uid, ids, context=None):
        raise ValidationError("You Try to Login with no have Shift for Today, try to contact your Spervisor or Manager to Generate Your Shift")


    def employee_current_shift(self, cr, uid, shift_id, context=None):
        wk_time_obj = self.pool.get('work.time.structure')
        print('shift_id = ', shift_id)
        shift = wk_time_obj.search(cr, uid, [('id', '=', shift_id)])
        current_shift = wk_time_obj.browse(cr, uid, shift)
        print('current_shift = ', current_shift)
        value = {}
        for rec in current_shift:
            value['start_hour'] = rec.start_hour
            value['end_hour'] = rec.end_hour
            value['late_tolerance'] = rec.late_tolerance
        print('value = ', value)
        return value

    def check_schedule(self, cr, uid, employee_id, context=None):
        now = datetime.now()
        dt_now = now.strftime('%Y-%m-%d')
        sched_obj = self.pool.get('hr.schedule.shift.list').search(cr, uid, [('name', '=', dt_now), ('employee_id', '=', employee_id.id),('state','=','submitted')], limit=1)
        print('sched_obj = ', sched_obj)
        sched_id = self.pool.get('hr.schedule.shift.list').browse(cr, uid, sched_obj)
        if not sched_id:
            return False
        else:
            return sched_id.shift_id



    def attendance_action_change(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        action_date = context.get('action_date', False)
        now = datetime.now()
        dt_now = now.strftime('%Y-%m-%d')
        action = context.get('action', False)
        hr_attendance = self.pool.get('hr.attendance')
        warning_sign = {'sign_in': _('Sign In'), 'sign_out': _('Sign Out')}
        for employee in self.browse(cr, uid, ids, context=context):
            # schedule = self.check_schedule(cr, uid, employee, context=context)
            schedule = ''
            if not action:
                if employee.state == 'present': action = 'sign_out'
                if employee.state == 'absent': action = 'sign_in'

            # if not self._action_check(cr, uid, employee.id, action_date, context):
            #     raise osv.except_osv(_('Warning'), _('You tried to %s with a date anterior to another event !\nTry to contact the HR Manager to correct attendances.')%(warning_sign[action],))
            
            vals = {'action': action, 'employee_id': employee.id}

            if action == 'sign_in':
                shift_obj = self.pool.get('hr.schedule.shift.list').search(cr, uid, [('employee_id','=',employee.id), ('name', '=', dt_now), ('state','=', 'submitted')])
                if shift_obj:
                    shift_id = self.pool.get('hr.schedule.shift.list').browse(cr, uid, shift_obj)
                    for rec in shift_id:
                        schedule = rec.shift_id
                        vals['shift_id'] = schedule.id
                ot_obj  = self.pool.get('hr.overtime.request.line').search(cr, uid, [('date_overtime','=',dt_now), ('employee_id', '=', employee.id),('state', '=', 'approved')])
                ot_id   = self.pool.get('hr.overtime.request.line').browse(cr, uid, ot_obj)
                ot_sign_in = [l for l in ot_id if l.overtime_type_id.start_type == 'before_start_wktime']
                print('ot_sign_in = ', ot_sign_in)
                if ot_sign_in:
                    print('here')
                    vals['overtime'] = True
                    ot_detail = self.calculate_overtime(cr, uid, employee, schedule, ot_sign_in[0].id, action)
                    vals['overtime_ids'] = [(0, 0, {
                        'name': date.today(),
                        'start_ot': ot_detail['start_ot'],
                        'end_ot': ot_detail['end_ot'],
                        'ot_time_in': ot_detail['ot_time_in'],
                        'ot_type_id': ot_detail['ot_type'],
                        'rate_one': ot_detail.get('rate_one', False),
                        'rate_one_half': ot_detail.get('rate_one_half', False),
                        'rate_double': ot_detail.get('rate_double', False),
                        'rate_triple': ot_detail.get('rate_triple', False)
                    })]
                # if ot_obj:
                #     print('here')
                #     ot_obj_id = self.pool.get('hr.overtime.request.line').browse(cr, uid, ot_obj)
                #     vals['overtime'] = True
                #     ot_detail = self.calculate_overtime(cr, uid, employee, schedule, ot_obj, action)
                #     vals['overtime_ids'] = [(0, 0, {
                #         'name': date.today(),
                #         'start_ot': ot_detail['start_ot'],
                #         'end_ot': ot_detail['end_ot'],
                #         'ot_length': ot_detail['ot_length'],
                #         'ot_rounded': ot_detail['ot_rounded'],
                #         'ot_type_id': ot_detail['ot_type'],
                #         'rate_one': ot_detail['rate_one'] or False,
                #         'rate_one_half': ot_detail['rate_one_half'] or False,
                #         'rate_double': ot_detail['rate_double'] or False,
                #         'rate_triple': ot_detail['rate_triple'] or False
                #     })]
                if not ot_obj:
                    vals['overtime'] = False
                if action_date:
                    vals['name'] = action_date
                hr_attendance.create(cr, uid, vals, context=context)
            elif action == 'sign_out':
                last_sign_obj = hr_attendance.search(cr, uid, [('employee_id', '=', employee.id), ('action','=','sign_in')], limit=1, order="name DESC")
                last_att = hr_attendance.browse(cr, uid, last_sign_obj)
                date_sign_in = last_att.name
                print('date_sign_in = ', date_sign_in)
                sign_in_obj = datetime.strptime(date_sign_in, '%Y-%m-%d %H:%M:%S')
                hours_diff = 7 #Hour diff from Bangkok Timezone to System Timezone is 7 Hours
                hours_added = timedelta(hours=hours_diff)
                real_time = sign_in_obj + hours_added
                sign_in = real_time.strftime('%Y-%m-%d')
                ot_obj  = self.pool.get('hr.overtime.request.line').search(cr, uid, [('date_overtime','=',sign_in), ('employee_id', '=', employee.id),('state', '=', 'approved')])
                ot_id   = self.pool.get('hr.overtime.request.line').browse(cr, uid, ot_obj)
                ot_sign_out = [l for l in ot_id if l.overtime_type_id.start_type == 'after_end_wktime']
                ot = {}
                if ot_sign_out:
                    print('here1')
                    ot_detail = self.calculate_overtime(cr, uid, employee, last_att.shift_id, ot_sign_out[0].id, action)
                    ot_time_in = ''
                    if last_att.overtime:
                        for rec in last_att.overtime_ids.filtered(lambda x: x.ot_type_id.start_type == 'before_start_wktime'):
                            rec.ot_time_out = ot_detail['ot_time_out']
                            ot_time_in = rec.ot_time_in
                    elif not last_att.overtime:
                        hour, minute = real_time.hour, real_time.minute
                        ot_time_in = ((hour * 3600.0) + (minute * 60.0)) / 3600.00
                        print('hour , minute = ', hour, ',', minute)
                    ot.update({
                        'name': date.today(),
                        'start_ot': ot_detail['start_ot'],
                        'end_ot': ot_detail['end_ot'],
                        'ot_time_in': ot_time_in,
                        'ot_time_out': ot_detail['ot_time_out'],
                        'ot_type_id': ot_detail['ot_type'],
                        'rate_one': ot_detail.get('rate_one', False),
                        'rate_one_half': ot_detail.get('rate_one_half', False),
                        'rate_double': ot_detail.get('rate_double', False),
                        'rate_triple': ot_detail.get('rate_triple', False)
                    })
                    last_att.update({
                        'action': 'sign_out',
                        'overtime': True,
                        'sign_out': datetime.now(),
                        'overtime_ids': [(0, 0, ot)]
                    })
                else:
                    print('here2')
                    last_att.update({
                        'action': 'sign_out',
                        'sign_out': datetime.now()
                    })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
