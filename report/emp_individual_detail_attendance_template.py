from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar
from ..utility.utils import hour_float_to_time as hftt

class report_employee_individual_detail_attendance(report_sxw.rml_parse):
    _name = 'report.sisb_hr.employee_individual_attendance_detail_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(report_employee_individual_detail_attendance, self).__init__(cr, uid, name, context = context)
        ids = context.get('active_ids')
        att_obj = self.pool['hr.attendance']
        docs = att_obj.browse(cr, uid, ids, context)
        print('docs =', docs)
        self.localcontext.update({
            'docs': docs,
            'emp_att_detail': self._emp_att_detail,
            'total_all': self._total_all

        })



    def delta_days(self, date_from, date_to):
        FMT = '%Y-%m-%d'
        start   = datetime.strptime(date_from, '%Y-%m-%d')
        end     = datetime.strptime(date_to, '%Y-%m-%d')   
        step    = timedelta(days=1)
        date_list   = []
        weekend     = []
        all_day     = []
        value = {}
        while (start <= end):
            string_date = start.strftime('%Y-%m-%d')
            all_day.append(string_date)
            day = calendar.weekday(int(start.strftime("%Y")),int(start.strftime("%m")),int(start.strftime("%d")))
            if day == 5 or day == 6:
                str_date = start.strftime('%Y-%m-%d')
                weekend.append(str_date)
            else:
                str_date = start.strftime('%Y-%m-%d')
                date_list.append(str_date)
            start += step
        value['date_list'] = date_list
        value['weekend'] = weekend
        value['all_day'] = all_day
        return value

    def get_employee_schedule(self, employee_id, day):
        schedule_name = ''
        sched_obj = self.pool.get('employee.schedule').search(self.cr, self.uid, [
            ('employee_id', '=', employee_id.id),
            ('date_from', '<=', day),
            ('date_to', '>=', day)
        ])
        if sched_obj:
            schedule = self.pool.get('employee.schedule').browse(self.cr, self.uid, sched_obj)
            schedule_name = schedule.schedule_type_id.name
        else:
            schedule_name = '-'
        return schedule_name

    def check_leave(self, employee_id, date):
        hd_name = ''
        if employee_id:
            hd = self.pool.get('hr.holidays').search(self.cr, self.uid, [
                ('employee_id', '=', employee_id.id),
                ('date_from1','<=', date),
                ('date_to1', '>=', date),
                ('type', 'in', ('remove', 'claim'))
            ])
            holiday = self.pool.get('hr.holidays').browse(self.cr, self.uid, hd)
            if holiday:
                hd_name = holiday.holiday_status_id.name
            if not hd:
                hd_name = False
            return hd_name


            # hd = self.pool.get('days.holidays.days').search(self.cr, self.uid,[
            #     ('user_id', '=', employee_id.user_id.id),
            #     ('date1', '=', date)
            # ])
            # if hd:
            #     validate_hd = self.pool.get('hr.holidays').search(self.cr, self.uid,[
            #         ('id', '=', hd[0]),
            #         ('state', '=', 'validate')
            #     ])
            #     if validate_hd:
            #         hd = self.pool.get('hr.holidays').browse(self.cr, self.uid, validate_hd)
            #         hd_name = hd.holiday_status_id.name
            #         print('hd = ', hd)
            #         return hd_name
            #     else:
            #         return False
    
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
                        check = hd.reason
                    else:
                        check = False
            if department_id.public_holiday_type == 'school':
                academic_years_obj = self.pool.get('academic.year').search(self.cr, self.uid, [('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.pool.get('school.holidays').search(self.cr, self.uid, [('year_id','=', academic_years_obj[0])])
                if school_holiday:
                    school_holiday_id = self.pool.get('school.holidays').browse(self.cr, self.uid, school_holiday[0])
                    for rec in school_holiday_id.line_ids:
                        if rec.date == date_att:
                            check = rec.name
                else:
                    return False
            if department_id.public_holiday_type == 'both':
                holiday_obj = self.pool.get('public.holidays.days').search(self.cr, self.uid, [])
                holiday = self.pool.get('public.holidays.days').browse(self.cr, self.uid, holiday_obj)
                for hd in holiday:
                    if hd.name == date_att:
                        check = hd.reason
                    else:
                        check = False
                academic_years_obj = self.pool.get('academic.year').search(self.cr, self.uid, [('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.pool.get('school.holidays').search(self.cr, self.uid, [('year_id','=', academic_years_obj[0])])
                if school_holiday:
                    school_holiday_id = self.pool.get('school.holidays').browse(self.cr, self.uid, school_holiday[0])
                    for rec in school_holiday_id.line_ids:
                        if rec.date == date_att:
                            check = rec.name
                else:
                    if check:
                        return check
                    else:
                        check = False
        return check
    

    def check_late_or_early(self, attendance_id, late=False, early=False):
        late_or_early_duration = ''
        employee_att = self.pool.get('hr.attendance').search(self.cr, self.uid, [
            ('id', '=', attendance_id)
        ])
        if employee_att:
            att_id = self.pool.get('hr.attendance').browse(self.cr, self.uid, employee_att)
            for rec in att_id:
                if late:
                    if rec.attendance_options == 'late':
                        late_or_early_duration =  '{0:02.0f}:{1:02.0f}'.format(*divmod(rec.late_or_leave_early * 60, 60))
                    else:
                        late_or_early_duration = False
                if early:
                    if rec.attendance_options == 'leave_early':
                        late_or_early_duration =  '{0:02.0f}:{1:02.0f}'.format(*divmod(rec.late_or_leave_early * 60, 60))
                    else:
                        late_or_early_duration = False
            return late_or_early_duration

    def _total_all(self, employee, company, start, end):
        data = []
        print('company_id = ', company)
        print('employee = ', employee)
        print('start = ', start)
        print('end = ', end)
        date_from   = start + ' 00:00:00'
        date_to     = end + ' 23:59:59'
        company_obj = self.pool.get('res.company').search(self.cr, self.uid, [('id', '=',company.id)])
        company_id  = self.pool.get('res.company').browse(self.cr, self.uid, company_obj)
        section_code = ''
        for rec in company_id:
            if rec.school_ids:
                for school in rec.school_ids:
                    section_code = '00' + str(school.sequence) + ' :' + ' Section :' + ' SISB-' + str(school.code)
                    break
            if not rec.school_ids:
                section_code = 'Section : SISB'
        late_total = ''
        leave_early_total = ''
        leave_i_total = '0 - 0:0'
        leave_d_total = '0 - 0:0'
        dec_total = '0 - 0:0'
        inc_total = '0 - 0:0'
        ot_one_total = ''
        ot_one_half_total = ''
        ot_two_total = ''
        ot_two_half_total = ''
        ot_three_total = ''
        ot_six_total = ''
        self.cr.execute("SELECT COALESCE(SUM(late_duration), 0)\
                        FROM hr_attendance\
                        WHERE employee_id = %s \
                        AND name + INTERVAL '8 HOURS' >= %s \
                        AND name + INTERVAL '8 HOURS' <= %s \
                        ", (employee.id, date_from, date_to))
        late_duration = self.cr.fetchall()
        print('late_dur = ', late_duration[0][0])
        if late_duration[0][0] > 0:
            late_total = hftt(late_duration[0][0])
        print('late_total = ', late_total)

        self.cr.execute("SELECT COALESCE(SUM(leave_early_duration), 0)\
                        FROM hr_attendance\
                        WHERE employee_id = %s \
                        AND name + INTERVAL '8 HOURS' >= %s \
                        AND name + INTERVAL '8 HOURS' <= %s \
                        ", (employee.id, date_from, date_to))
        early_duration = self.cr.fetchall()
        if early_duration[0][0] > 0:
            leave_early_total = hftt(early_duration[0][0])


        # self.cr.execute("SELECT COALESCE(SUM(daily_ot_total), 0)\
        #                 FROM hr_attendance\
        #                 WHERE employee_id = %s \
        #                 AND name + INTERVAL '8 HOURS' >= %s \
        #                 AND name + INTERVAL '8 HOURS' <= %s \
        #                 ", (employee.id, date_from, date_to))
        # ot_tot = self.cr.fetchall()
        # if ot_tot[0][0] > 0:
        #     ot_one_half_total = hftt(ot_tot[0][0])


        self.cr.execute("SELECT COALESCE(SUM(oll.rate_one), 0), COALESCE(SUM(oll.rate_one_half), 0), COALESCE(SUM(oll.rate_double), 0), COALESCE(SUM(oll.rate_triple), 0)\
                        FROM hr_attendance ha LEFT JOIN overtime_list_line oll ON (ha.id = oll.attendance_id)\
                        WHERE ha.employee_id = %s\
                        AND ha.name + INTERVAL '8 HOURS' >= %s \
                        AND ha.name + INTERVAL '8 HOURS' <= %s \
                        ", (employee.id, date_from, date_to))
        ot_tot = self.cr.fetchall()
        print('ot_tot = ', ot_tot)
        if ot_tot[0][0] > 0.0:
            ot_one_total = hftt(ot_tot[0][0])
        if ot_tot[0][1] > 0.0:
            ot_one_half_total = hftt(ot_tot[0][1])
        if ot_tot[0][2] > 0.0:
            ot_two_total = hftt(ot_tot[0][2])
        if ot_tot[0][3] > 0.0:
            ot_three_total = hftt(ot_tot[0][3])
        
        
        
        result = {
            'section_code': section_code,
            'late_tot': late_total,
            'leave_early_tot': leave_early_total,
            'leave_i_tot': leave_i_total,
            'leave_d_tot': leave_d_total,
            'dec_tot': dec_total,
            'inc_tot': inc_total,
            'ot_one_tot': ot_one_total,
            'ot_one_half_tot': ot_one_half_total,
            'ot_two_tot': ot_two_total,
            'ot_two_half_tot': ot_two_half_total,
            'ot_three_tot': ot_three_total,
            'ot_six_tot': ot_six_total,
        }
        data.append(result)
        if data:
            return data
        else:
            return {}


    def _emp_att_detail(self, form):
        # 01/Nov/2019 [Fri]
        FMT = '%Y-%m-%d'
        data = []
        date_from   = form['date_from']
        date_to     = form['date_to'] 
        employee    = form['employee_id']
        employee_obj= self.pool.get('hr.employee').search(self.cr, self.uid, [('id', '=', employee[0])])
        employee_id  = self.pool.get('hr.employee').browse(self.cr, self.uid, employee_obj)
        company     = form['company_id']
        company_obj = self.pool.get('res.company').search(self.cr, self.uid, [('id', '=', company[0])])
        company_id  = self.pool.get('res.company').browse(self.cr, self.uid, company_obj)
        section_code = ''
        for rec in company_id:
            if rec.school_ids:
                for school in rec.school_ids:
                    section_code = '00' + str(school.sequence) + ' :' + ' Section :' + ' SISB-' + str(school.code)
                    break
            if not rec.school_ids:
                section_code = 'Section : SISB'
        start_date  = date_from + ' 00:00:00'
        end_date    = date_to + ' 23:59:59'
        days = self.delta_days(date_from, date_to)
        print('days = ', days)
        for day in days['all_day']:
            day_date_obj = datetime.strptime(day, FMT)
            date_att = day_date_obj.strftime('%d/%b/%Y')
            day_name = day_date_obj.strftime('%a')
            
            wk_day_type = ''
            if day_name not in ('Sat','Sun'):
                wk_day_type = 'N'
            else:
                wk_day_type = 'H'
            emp_schedule = self.get_employee_schedule(employee_id, day)
            date_name = date_att + ' [' + day_name + ']'
            emp_sign_in_time = ''
            emp_sign_out_time = ''
            emp_late_time = ''
            emp_early_time = ''
            emp_leave_l = 0 
            emp_leave_d = ''
            ot_rate_one = ''
            ot_rate_one_half = ''
            ot_rate_double = ''
            ot_rate_triple = ''
            info = ''
            # self.cr.execute("SELECT name + INTERVAL '8 HOURS', sign_out + INTERVAL '8 HOURS', daily_ot_total, late_duration, leave_early_duration\
            #             FROM hr_attendance \
            #             WHERE employee_id=%s \
            #             AND sign_out IS NOT NULL\
            #             AND name + INTERVAL '8 HOURS' <=  %s \
            #             AND name + INTERVAL '8 HOURS' >= %s \
            #         ", (employee[0], day + ' 23:59:50', day + ' 00:00:00'))
            # attendance = self.cr.fetchall()
            self.cr.execute("SELECT ha.name + INTERVAL '8 HOURS', ha.sign_out + INTERVAL '8 HOURS', ha.late_duration, ha.leave_early_duration, oll.rate_one,\
                        oll.rate_one_half, oll.rate_double, oll.rate_triple, ha.shift_id\
                        FROM hr_attendance ha \
                        LEFT JOIN overtime_list_line oll ON (ha.id = oll.attendance_id)\
                        WHERE ha.employee_id=%s \
                        AND sign_out IS NOT NULL\
                        AND ha.name + INTERVAL '8 HOURS' <=  %s \
                        AND ha.name + INTERVAL '8 HOURS' >= %s \
                    ", (employee[0], day + ' 23:59:50', day + ' 00:00:00'))
            attendance = self.cr.fetchall()
            print('attendance = ', attendance)
            if not attendance:
                print('here1')
                if day_date_obj > datetime.now():
                    continue
                if day_name in ('Sun'):
                    continue
                check_leave = self.check_leave(employee_id, day)
                if check_leave:
                    emp_leave_l +=1
                    info = check_leave
                if not check_leave:
                    check_emp_holiday = self.check_emp_holiday(employee_id.department_id, day)
                    if check_emp_holiday:
                        info = check_emp_holiday
                    else:
                        info = 'Absent'
            else:
                print('here2')
                day = calendar.weekday(int(day_date_obj.strftime("%Y")),int(day_date_obj.strftime("%m")),int(day_date_obj.strftime("%d")))
                if day == 6:
                    info = 'Weekend'
                sign_in_date_obj = datetime.strptime(attendance[0][0], '%Y-%m-%d %H:%M:%S')
                emp_sign_in_time = sign_in_date_obj.strftime('%H:%M')
                sign_out_date_obj = datetime.strptime(attendance[0][1], '%Y-%m-%d %H:%M:%S')
                emp_sign_out_time = sign_out_date_obj.strftime(' %H:%M')
                if attendance[0][2] > 0:
                    emp_late_time = hftt(attendance[0][2])
                if attendance[0][3] > 0:
                    emp_early_time = hftt(attendance[0][3])
                if attendance[0][4]:
                    ot_rate_one = hftt(attendance[0][4])
                print('ot_rate_one = ', ot_rate_one)
                if attendance[0][5]:
                    ot_rate_one_half= hftt(attendance[0][5])
                if attendance[0][6]:
                    ot_rate_double  = hftt(attendance[0][6])
                if attendance[0][7]:
                    ot_rate_triple  = hftt(attendance[0][7])


            result = {
                'section_code': section_code,
                'date': date_name,
                'schedule': emp_schedule,
                'type': wk_day_type,
                'sign_in': emp_sign_in_time,
                'sign_out': emp_sign_out_time,
                'late': emp_late_time,
                'early': emp_early_time,
                'leave_l': emp_leave_l,
                'leave_d': emp_leave_d,
                'rate_one': ot_rate_one,
                'rate_one_half': ot_rate_one_half,
                'rate_double': ot_rate_double,
                'rate_triple': ot_rate_triple,
                'info': info

            }
            data.append(result)
        if data:
            return data
        else:
            return {}
    



class report_individual_detail_summary_emp_att(models.AbstractModel):
    _name = 'report.sisb_hr.employee_individual_attendance_detail_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.employee_individual_attendance_detail_report'
    _wrapped_report_class = report_employee_individual_detail_attendance