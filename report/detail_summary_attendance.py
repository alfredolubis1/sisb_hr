from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar



class report_detail_emp_att_summary(report_sxw.rml_parse):
    _name = 'report.sisb_hr.sisb_employee_detail_summary_attendance_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(report_detail_emp_att_summary, self).__init__(cr, uid, name, context = context)
        ids = context.get('active_ids')
        att_obj = self.pool['hr.attendance']
        docs = att_obj.browse(cr, uid, ids, context)
        print('docs =', docs)
        self.localcontext.update({
            'docs': docs,
            'detail_att': self._detail_att,

        })


    def check_leave(self, employee_id, date):
        if employee_id:
            hd = self.pool.get('days.holidays.days').search(self.cr, self.uid,[
                ('user_id', '=', employee_id.user_id.id),
                ('date1', '=', date)
            ])
            if hd:
                validate_hd = self.pool.get('hr.holidays').search(self.cr, self.uid,[
                    ('id', '=', hd[0]),
                    ('state', '=', 'validate')
                ])
                if validate_hd:
                    return True
                else:
                    return False
    
    def check_emp_holiday(self, department_id, date_att):
        now = date.today()
        dt_now = now.strftime('%Y-%m-%d')
        check = False
        if department_id:
            if department_id.public_holiday_type == 'public':
                holiday_obj = self.pool.get('public.holidays.days').search(self.cr, self.uid, [])
                holiday = self.pool.get('public.holidays.days').browse(self.cr, self.uid, holiday_obj)
                for hd in holiday:
                    if hd.name == date_att:
                        check = True
                    else:
                        check = False
            if department_id.public_holiday_type == 'school':
                academic_years_obj = self.pool.get('academic.year').search(self.cr, self.uid, [('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.pool.get('school.holidays').search(self.cr, self.uid, [('year_id','=', academic_years_obj[0])])
                if school_holiday:
                    school_holiday_id = self.pool.get('school.holidays').browse(self.cr, self.uid, school_holiday[0])
                    for rec in school_holiday_id.line_ids:
                        if rec.date == date_att:
                            check = True
                else:
                    return False
            if department_id.public_holiday_type == 'both':
                holiday_obj = self.pool.get('public.holidays.days').search(self.cr, self.uid, [])
                holiday = self.pool.get('public.holidays.days').browse(self.cr, self.uid, holiday_obj)
                for hd in holiday:
                    if hd.name == date_att:
                        check = True
                    else:
                        check = False
                academic_years_obj = self.pool.get('academic.year').search(self.cr, self.uid, [('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.pool.get('school.holidays').search(self.cr, self.uid, [('year_id','=', academic_years_obj[0])])
                if school_holiday:
                    school_holiday_id = self.pool.get('school.holidays').browse(self.cr, self.uid, school_holiday[0])
                    for rec in school_holiday_id.line_ids:
                        if rec.date == date_att:
                            check = True
                else:
                    if check == True:
                        return check
                    else:
                        check = False
        return check


    def check_weekend(self, date):
        pass

    def delta_days(self, date_from, date_to):
        FMT = '%Y-%m-%d'
        start   = datetime.strptime(date_from, '%Y-%m-%d')
        end     = datetime.strptime(date_to, '%Y-%m-%d')   
        step    = timedelta(days=1)
        date_list   = []
        weekend     = []
        all_day     = []
        value   = {}
        week    = 0

        while (start <= end):
            str_day = start.strftime('%Y-%m-%d') 
            all_day.append(str_day)
            day = calendar.weekday(int(start.strftime("%Y")),int(start.strftime("%m")),int(start.strftime("%d")))
            if day == 5 or day == 6:
                week += 1
                str_date = start.strftime('%Y-%m-%d')
                weekend.append(str_date)
            else:
                str_date = start.strftime('%Y-%m-%d')
                date_list.append(str_date)
            start += step
        value['date_list'] = date_list
        value['all_day'] = all_day
        value['week'] = week
        return value
        


    def _detail_att(self, form):
        FMT = '%Y-%m-%d'
        data = []
        date_from   = form['date_from']
        date_to     = form['date_to']
        employee    = form['employee_id']
        employee_obj = self.pool.get('hr.employee').search(self.cr, self.uid, [('id', '=', employee[0])])
        employee_id = self.pool.get('hr.employee').browse(self.cr, self.uid, employee_obj)
        limit_att = 0.25
        days = self.delta_days(date_from, date_to)
        print('days = ', days)
        week = 0
        for day in days['all_day']:
            print('day = ', day)
            att_type = ''
            time_in = ''
            time_out = ''
            reason = ''
            late_duration = ''
            leave_early_duration = ''
            day_date_obj = datetime.strptime(day, FMT)
            date_att = day_date_obj.strftime('%d-%b-%Y')
            day_name = day_date_obj.strftime('%A')
            wk_day = calendar.weekday(int(day_date_obj.strftime("%Y")),int(day_date_obj.strftime("%m")),int(day_date_obj.strftime("%d")))
            if wk_day == 6:
                week += 1 

            self.cr.execute("SELECT id, name + INTERVAL '8 HOURS', sign_out + INTERVAL '8 HOURS', late_duration, leave_early_duration\
                            FROM hr_attendance \
                            WHERE employee_id = %s \
                            AND name + INTERVAL '8 HOURS' >= %s \
                            AND name + INTERVAL '8 HOURS' <= %s \
                            ", (employee[0], day + ' 00:00:00', day + ' 23:59:59'))
            attendance = self.cr.fetchall()
            print('attendance = ', attendance)
            if not attendance:
                if day_date_obj > datetime.now():
                    continue
                check_leave = self.check_leave(employee_id, day)
                if check_leave:
                    continue
                check_emp_holiday = self.check_emp_holiday(employee_id.department_id, day)
                if check_emp_holiday:
                    continue
                if wk_day == 6:
                    reason = 'Weekend'
                else:
                    print('day1 = ', day)
                    reason = 'Absent'
            
            if attendance:
                self.cr.execute("SELECT id, name + INTERVAL '8 HOURS', sign_out + INTERVAL '8 HOURS', late_duration, leave_early_duration, late_action_desc_id, leave_early_action_desc_id, other_reason_late, other_reason_leave_early\
                                FROM hr_attendance \
                                WHERE employee_id = %s \
                                AND name + INTERVAL '8 HOURS' >= %s \
                                AND name + INTERVAL '8 HOURS' <= %s \
                                AND (late_duration >= %s OR leave_early_duration >= %s)\
                                ", (employee[0], day + ' 00:00:00', day + ' 23:59:59', limit_att, limit_att))
                late_and_early = self.cr.fetchall()
                if late_and_early:
                    if late_and_early[0][3] >= limit_att:
                        late_duration = '{0:02.0f}:{1:02.0f}'.format(*divmod(late_and_early[0][3] * 60, 60))
                        reason_obj = self.pool.get('hr.action.reason.late').search(self.cr, self.uid, [('id', '=', late_and_early[0][5])])
                        reason_id = self.pool.get('hr.action.reason.late').browse(self.cr, self.uid, reason_obj)
                        if not reason_id.other:
                            reason = reason_id.name
                        elif reason_id.other: 
                            reason = late_and_early[0][7]

                    elif late_and_early[0][4] >= limit_att:
                        leave_early_duration = '{0:02.0f}:{1:02.0f}'.format(*divmod(late_and_early[0][4] * 60, 60))
                        reason_obj = self.pool.get('hr.action.reason.leave.early').search(self.cr, self.uid, [('id', '=', late_and_early[0][6])])
                        reason_id = self.pool.get('hr.action.reason.leave.early').browse(self.cr, self.uid, reason_obj)
                        if not reason_id.other:
                            reason = reason_id.name
                        elif reason_id.other:
                            reason = late_and_early[0][8]
                    elif (late_and_early[0][3] and late_and_early[0][4]) >= limit_att:
                        reason = 'Late and Leave Early'
                    sign_in = datetime.strptime(late_and_early[0][1], '%Y-%m-%d %H:%M:%S')
                    time_in = sign_in.strftime('%H:%M')
                    sign_out = datetime.strptime(late_and_early[0][2], '%Y-%m-%d %H:%M:%S')
                    time_out = sign_out.strftime('%H:%M')
                else:
                    continue
            if wk_day == 5 or wk_day == 6:
                continue
            disp_week = ''
            if week == 0:
                disp_week = 'Week 1'
                week += 1
            # else:
            #     disp_week = 'Week ' + str(week)

            disp_week = 'Week ' + str(week)
            result = {
                'week': disp_week,
                'day_name': day_name,
                'date': date_att,
                'type': att_type,
                'time_in': time_in,
                'time_out': time_out,
                'late': late_duration,
                'leave_early': leave_early_duration,
                'reason': reason
            }
            data.append(result)
        if data:
            return data
        else:
            return {}
                

            



        
    
class report_detail_summary_emp_att(models.AbstractModel):
    _name = 'report.sisb_hr.sisb_employee_detail_summary_attendance_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.sisb_employee_detail_summary_attendance_report'
    _wrapped_report_class = report_detail_emp_att_summary