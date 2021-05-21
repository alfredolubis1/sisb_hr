from openerp import models, _
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar
from openerp.exceptions import ValidationError


class report_emp_att(report_sxw.rml_parse):
    _name = 'report.sisb_hr.sisb_employee_summary_attendance_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(report_emp_att, self).__init__(cr, uid, name, context = context)
        ids = context.get('active_ids')
        att_obj = self.pool['hr.attendance']
        docs = att_obj.browse(cr, uid, ids, context)
        self.localcontext.update({
            'docs': docs,
            'st_term': self.st_term,

        })

    def delta_days(self, date_from, date_to):
        FMT = '%Y-%m-%d'
        start   = datetime.strptime(date_from, '%Y-%m-%d')
        end     = datetime.strptime(date_to, '%Y-%m-%d')   
        step    = timedelta(days=1)
        date_list   = []
        weekend     = []
        all_day = []
        value = {}
        while (start < end):
            all_date = start.strftime('%Y-%m-%d')
            all_day.append(all_date)
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

    def count_week(self, date_from, date_to):
        FMT = '%Y-%m-%d'
        start   = date_from
        print('start = ', start)
        end     = date_to   
        print('end = ', end)
        step    = timedelta(days=1)
        week    = 0
        while (start <= end):
            day = calendar.weekday(int(start.strftime("%Y")),int(start.strftime("%m")),int(start.strftime("%d")))
            if day == 6:
                week += 1
            start += step
        return week



    def get_employee_holiday(self, department_id):
        now = date.today()
        dt_now = now.strftime('%Y-%m-%d')
        holiday = []
        if department_id:
            if department_id.public_holiday_type == 'public':
                self.cr.execute("select name, date2 from public_holidays_days" )
                holiday=self.cr.fetchall()
            if department_id.public_holiday_type == 'school':
                academic_year_obj = self.pool.get('academic.year').search(self.cr, self.uid, [('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.pool.get('school.holidays').search(self.cr, self.uid, [('year_id', '=', academic_year_obj[0])])
                if school_holiday:
                    self.cr.execute('select date, name from school_holidays_line where holiday_id=%s',(school_holiday[0],))
                    holiday.append(self.cr.fetchall())
            if department_id.public_holiday_type == 'both':
                self.cr.execute("select name, date2 from public_holidays_days" )
                holiday=self.cr.fetchall()
                academic_year_obj = self.pool.get('academic.year').search(self.cr, self.uid, [('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.pool.get('school.holidays').search(self.cr, self.uid, [('year_id', '=', academic_year_obj[0])])
                if school_holiday:
                    self.cr.execute('select date, name from school_holidays_line where holiday_id=%s',(school_holiday[0],))
                    school_holidays = self.cr.fetchall()
                    for holidays in school_holidays: 
                        holiday.append(holidays)
        else:
            self.cr.execute("select name, date2 from public_holidays_days" )
            holiday = self.cr.fetchall()
        return holiday


    def get_emp_late_early(self, employee_id, date_from, date_to):
        emp_late_early = {}
        self.cr.execute("SELECT COUNT(*) FROM hr_attendance\
                        WHERE employee_id = %s\
                        AND name + INTERVAL '8 HOURS' >= %s\
                        AND name + INTERVAL '8 HOURS' <= %s\
                        AND late_duration >= %s",(employee_id, date_from + ' 00:00:00', date_to + ' 23:59:59', 0.25))
        total_late = self.cr.fetchall()
        emp_late_early['total_late'] = int(total_late[0][0])
        self.cr.execute("SELECT COUNT (*) FROM hr_attendance\
                        WHERE employee_id = %s\
                        AND name + INTERVAL '8 HOURS' <= %s\
                        AND name + INTERVAL '8 HOURS' >= %s\
                        AND leave_early_duration >= 0.25\
                        ",(employee_id, date_to + ' 23:59:59', date_from + ' 00:00:00'))
        total_leave_early = self.cr.fetchall()
        emp_late_early['total_leave_early'] = int(total_leave_early[0][0])
        return emp_late_early


    def absent_check(self, employee_id, day):
        self.cr.execute("SELECT id FROM hr_attendance\
                        WHERE employee_id = %s\
                        AND name + INTERVAL '8 HOURS' >= %s\
                        AND name + INTERVAL '8 HOURS' <= %s\
                        ",(employee_id, day + ' 00:00:00', day + ' 23:59:59'))
        att = self.cr.fetchall()
        if att:
            return True
        else: 
            return False


    def holiday_check(self, employee, day):
        employee_id = self.pool.get('hr.employee').search(self.cr, self.uid, [('id','=',employee)])
        employee = self.pool.get('hr.employee').browse(self.cr, self.uid, employee_id)
        holiday_obj = self.pool.get('hr.holidays')
        days_holidays_day_obj = self.pool.get('days.holidays.days').search(self.cr, self.uid, [('date1', '=', day),('user_id', '=', employee.user_id.id)])
        if not days_holidays_day_obj:
            return False
        else:
            holiday_day = self.pool.get('days.holidays.days').browse(self.cr, self.uid, days_holidays_day_obj)
            days_holiday = holiday_obj.search(self.cr, self.uid, [('employee_id', '=', employee.id),('id', '=', holiday_day.holiday_id.id), ('type', '=', 'remove'), ('state', '=', 'validate')])
            if days_holiday:
                return True
            if not days_holiday:
                return False
        return True

    def sorted_list(self, list_obj):
        return list_obj[0]

    def st_term(self, form):
        FMT = '%Y-%m-%d'
        data = []
        academic_year = form['academic_year_id']
        date_from   = form['date_from']
        date_to     = form['date_to']
        employee    = form['employee_id']
        academic_year_obj = self.pool.get('academic.year').search(self.cr, self.uid, [('id', '=', academic_year[0])])
        academic_year_id = self.pool.get('academic.year').browse(self.cr, self.uid, academic_year_obj)
        academic_term_obj = self.pool.get('academic.term').search(self.cr, self.uid, [])
        academic_term_id = self.pool.get('academic.term').browse(self.cr, self.uid, academic_term_obj)
        len_of_term = len(academic_term_obj)
        academic_year = academic_year_id.name.split("-")

        st_year = int(academic_year[0]) #First Year of Academic e.g (2020-2021) first year is 2020
        nd_year = int(academic_year[1]) #Second Year of Academic e.g (2020-2021) second year is 2021


        # First Term
        st_term_start_date  = ''
        st_term_start_month = ''
        st_term_start_year  = ''
        st_term_start       = ''
        st_term_start_str   = ''
        st_term_end_date    = ''
        st_term_end_month   = ''
        st_term_end_year    = ''
        st_term_end         = ''
        st_term_end_str     = ''
        st_term_date_range  = ''
        fisrt_term_late_and_early = ''
        # ###################

        # Second Term
        nd_term_start_date  = ''
        nd_term_start_month = ''
        nd_term_start_year  = ''
        nd_term_start       = ''
        nd_term_start_str   = ''
        nd_term_end_date    = ''
        nd_term_end_month   = ''
        nd_term_end_year    = ''
        nd_term_end         = ''
        nd_term_end_str     = ''
        nd_term_date_range  = ''
        second_term_late_and_early = ''
        # ##################

        # Third Term
        rd_term_start_date  = ''
        rd_term_start_month = ''
        rd_term_start_year  = ''
        rd_term_start       = ''
        rd_term_start_str   = ''
        rd_term_end_date    = ''
        rd_term_end_month   = ''
        rd_term_end_year    = ''
        rd_term_end         = ''
        rd_term_end_str     = ''
        rd_term_date_range  = ''
        third_term_late_and_early = ''
        # #################
        date_from_obj   = datetime.strptime(date_from, FMT)
        date_to_obj     = datetime.strptime(date_to, FMT)
        week_term1 = 0
        week_term2 = 0
        week_term3 = 0
        week_to_display_in_term1 = ''
        week_to_display_in_term2 = ''
        week_to_display_in_term3 = ''
        date_range_term1 = ''
        date_range_term2 = ''
        date_range_term3 = ''

        # Date Range
        term1_date_range = ''
        term2_date_range = ''
        term3_date_range = ''
        for academic in academic_term_id.sorted(lambda x: x.sequence):
            if academic.sequence == 1:
                st_term_start_date  = academic.date_from
                st_term_start_month = academic.month_from
                st_term_start_year  = st_year
                st_term_start       = datetime(year=int(st_term_start_year), month=int(st_term_start_month), day=int(st_term_start_date)) # First Term Start
                st_term_start_str   = str(st_term_start_year) + '-' + st_term_start_month + '-' + st_term_start_date

                st_term_end_date    = academic.date_to
                st_term_end_month   = academic.month_to
                st_term_end_year = ''
                if int(st_term_end_month) < int(st_term_start_month):
                    st_term_end_year = nd_year
                elif int(st_term_end_month) > int(st_term_start_month):
                    st_term_end_year = st_year
                st_term_end         = datetime(year=int(st_term_end_year), month=int(st_term_end_month), day=int(st_term_end_date)) # First Term End
                st_term_end_str     =  str(st_term_end_year) + '-' + st_term_end_month + '-' + st_term_end_date

                st_term_date_range = self.delta_days(st_term_start_str, st_term_end_str)

                fisrt_term_late_and_early = self.get_emp_late_early(employee[0], st_term_start_str, st_term_end_str)
                if date_from_obj > st_term_end:
                    week_term1 = 0
                elif (date_from_obj <= st_term_end) and (date_from_obj >= st_term_start):
                    if date_to_obj <= st_term_end:
                        date_range_term1 = date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                        week_term1 = self.count_week(date_from_obj, date_to_obj)
                    elif date_to_obj >= st_term_end:
                        date_range_term1 = date_from_obj.strftime('%d %B') + ' - ' + st_term_end.strftime('%d %B %Y')
                        week_term1 = self.count_week(date_from_obj, st_term_end)
                else:
                    week_term1 = 0

                if week_term1:
                    week_to_display_in_term1 = 'Week 1 - ' + str(week_term1)
                    term1_date_range = week_to_display_in_term1 + ' Since ' + date_range_term1

            elif academic.sequence == 2:
                nd_term_start_date  = academic.date_from
                nd_term_start_month = academic.month_from
                if int(nd_term_start_month) < int(st_term_end_month):
                    nd_term_start_year = nd_year
                elif int(nd_term_start_month) > int(st_term_end_month):
                    nd_term_start_year = st_year
                nd_term_start       = datetime(year=int(nd_term_start_year), month=int(nd_term_start_month), day=(int(nd_term_start_date))) # Second Term Start
                nd_term_start_str   = str(nd_term_start_year) + '-' + nd_term_start_month + '-' + nd_term_start_date

                nd_term_end_date    = academic.date_to
                nd_term_end_month   = academic.month_to
                if int(nd_term_end_month) > int(nd_term_start_month):
                    nd_term_end_year = nd_term_start_year
                elif int(nd_term_end_month) < int(nd_term_start_month):
                    nd_term_end_year = nd_year
                nd_term_end         = datetime(year=int(nd_term_end_year), month=int(nd_term_end_month), day=int(nd_term_end_date)) # Second Term End
                nd_term_end_str     =  str(nd_term_end_year) + '-' + nd_term_end_month + '-' + nd_term_end_date
                
                nd_term_date_range  = self.delta_days(nd_term_start_str, nd_term_end_str)
                second_term_late_and_early = self.get_emp_late_early(employee[0], nd_term_start_str, nd_term_end_str)
                if date_from_obj > nd_term_end:
                    week_term2 = 0
                elif date_from_obj < nd_term_end:
                    if date_from_obj <= nd_term_start:
                        if date_to_obj < nd_term_end:
                            date_range_term2= date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                            week_term2 = self.count_week(nd_term_start, date_to_obj)
                        elif date_to_obj >= nd_term_end:
                            date_range_term2 = date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                            week_term2 = self.count_week(nd_term_start, nd_term_end)
                    elif date_from_obj > nd_term_start:
                        if date_to_obj <= nd_term_end:
                            date_range_term2 = date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                            week_term2 = self.count_week(date_from_obj, date_to_obj)
                        elif date_to_obj >= nd_term_end:
                            date_range_term2 = date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                            week_term2 = self.count_week(date_from_obj, nd_term_end)

                if week_term2:
                    week_to_display_in_term2 = 'Week 1 - ' + str(week_term2)
                    term2_date_range = week_to_display_in_term2 + ' Since ' + date_range_term2

            elif academic.sequence == 3:
                rd_term_start_date  = academic.date_from
                rd_term_start_month = academic.month_from
                rd_term_start_year  = nd_year
                rd_term_start       = datetime(year=int(rd_term_start_year), month=int(rd_term_start_month), day=int(rd_term_start_date)) # Third Term Start
                rd_term_start_str   = str(rd_term_start_year) + '-' + rd_term_start_month + '-' + rd_term_start_date

                rd_term_end_date    = academic.date_to
                rd_term_end_month   = academic.month_to
                rd_term_end_year    = nd_year
                rd_term_end         = datetime(year=int(rd_term_end_year), month=int(rd_term_end_month), day=int(rd_term_start_date)) # Third Term End
                rd_term_end_str     = str(rd_term_end_year) + '-' + rd_term_end_month + '-' + rd_term_end_date

                rd_term_date_range  = self.delta_days(rd_term_start_str, rd_term_end_str)
                third_term_late_and_early = self.get_emp_late_early(employee[0], rd_term_start_str, rd_term_end_str)
                if date_from_obj >= rd_term_end:
                    week_term3 = 0
                elif date_from_obj <= rd_term_end and date_from_obj >= rd_term_start:
                    if date_from_obj <= rd_term_start:
                        if date_to_obj < rd_term_end:
                            date_range_term3 = date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                            week_term3 = self.count_week(rd_term_start, date_to_obj)
                        elif date_to_obj >= rd_term_start:
                            date_range_term3 = date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                            week_term3 = self.count_week(rd_term_start, rd_term_end)
                    if date_from_obj >= rd_term_start:
                        if date_to_obj >= rd_term_end:
                            date_range_term3 = date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                            week_term3 = self.count_week(date_from_obj, rd_term_end)
                        elif date_to_obj <= rd_term_end:
                            date_range_term3 = date_from_obj.strftime('%d %B') + ' - ' + date_to_obj.strftime('%d %B %Y')
                            week_term3 = self.count_week(date_from_obj, date_to_obj)
                
                if week_term3:
                    week_to_display_in_term3 = 'Week 1 - ' + str(week_term3)
                    term3_date_range = week_to_display_in_term3 + ' Since ' + date_range_term3


        employee_obj = self.pool.get('hr.employee').search(self.cr, self.uid, [('id', '=', employee[0])])
        employee_id = self.pool.get('hr.employee').browse(self.cr, self.uid, employee_obj)
        self.cr.execute("SELECT id FROM hr_attendance\
                                WHERE name + INTERVAL '8 HOURS' >= %s\
                                AND name + INTERVAL '8 HOURS' <= %s\
                                AND employee_id = %s\
                                ORDER BY name ASC",(date_from + ' 00:00:00', date_to + ' 23:59:59', employee[0]))
        atts = self.cr.fetchall()
        if not atts:
            raise ValidationError(_("There is no Employee Attendance Data"))
        employee_late_and_leave = self.get_emp_late_early(employee[0], date_from, date_to)
        
        all_att = self.pool.get('hr.attendance').browse(self.cr, self.uid, atts[0])
        holiday_name = []
        all_type    = ['Absent', 'Late (More than 15 Minutes)', 'Leave early (More than 15 Minutes)', 'Not Clock-In', 'Not Clock-Out', 'On duty outside']
        term1_dict = {}
        term2_dict = {}
        term3_dict = {}
        emp_holiday = self.get_employee_holiday(employee_id.department_id)
        days_holidays = []
        for t1 in emp_holiday:
            days_holidays.append(t1[0])
        absent_total = 0
        absent_term1 = 0
        absent_term2 = 0
        absent_term3 = 0
        all_day = self.delta_days(date_from, date_to)
        for day in all_day['all_day']:
            each_day = datetime.strptime(day, '%Y-%m-%d')
            if each_day > datetime.now():
                continue
            absent_check = self.absent_check(employee[0], day)
            if absent_check:
                continue
            if not absent_check:
                if day in all_day['weekend']:
                    continue
                if day in days_holidays:
                    continue
                holiday_check = self.holiday_check(employee[0], day) 
                if holiday_check:
                    continue
                else:
                    absent_total += 1
                    if day in st_term_date_range['all_day']:
                        absent_term1 += 1
                    elif day in nd_term_date_range['all_day']:
                        absent_term2 += 1
                    elif day in nd_term_date_range['all_day']:
                        absent_term3 += 1


        term1_dict['Absent'] = absent_term1
        term1_dict['Late (More than 15 Minutes)'] = fisrt_term_late_and_early['total_late']
        term1_dict['Leave early (More than 15 Minutes)'] = fisrt_term_late_and_early['total_leave_early']
        term1_dict['Not Clock-In'] = 0
        term1_dict['Not Clock-Out'] = 0
        term1_dict['On duty outside'] = 0
        term1_list = [[k, v] for k, v in term1_dict.items()]
        term1_list.sort(key=self.sorted_list)

        term2_dict['Absent'] = absent_term2
        term2_dict['Late (More than 15 Minutes)'] = second_term_late_and_early['total_late']
        term2_dict['Leave early (More than 15 Minutes)'] = second_term_late_and_early['total_leave_early']
        term2_dict['Not Clock-In'] = 0
        term2_dict['Not Clock-Out'] = 0
        term2_dict['On duty outside'] = 0
        term2_list = [[k, v] for k, v in term2_dict.items()]
        term2_list.sort(key=self.sorted_list)

        term3_dict['Absent'] = absent_term3
        term3_dict['Late (More than 15 Minutes)'] = third_term_late_and_early['total_late']
        term3_dict['Leave early (More than 15 Minutes)'] = third_term_late_and_early['total_leave_early']
        term3_dict['Not Clock-In'] = 0
        term3_dict['Not Clock-Out'] = 0
        term3_dict['On duty outside'] = 0
        term3_list = [[k, v] for k, v in term3_dict.items()]
        term3_list.sort(key=self.sorted_list)
        print('term3_list = ', term3_list)

        leave_type_obj = self.pool.get('hr.holidays.status').search(self.cr, self.uid, [])
        first_leave_dict = {}
        second_leave_dict = {}
        third_leave_dict = {}
        all_leave_type = self.pool.get('hr.holidays.status').browse(self.cr, self.uid, leave_type_obj)
        all_leave_type_name = []
        for l in all_leave_type:
            if l.name not in all_leave_type_name:
                all_leave_type_name.append(l.name)
            self.cr.execute("SELECT COUNT(*) FROM hr_holidays\
                            WHERE holiday_status_id = %s\
                            AND employee_id = %s\
                            AND date_from1 >= %s\
                            AND date_from1 <= %s\
                            AND type = %s \
                            AND state = %s\
                            ",(l.id, employee[0], st_term_start_str, st_term_end_str, 'remove', 'validate'))
            fisrt_term_hd = self.cr.fetchall()
            if fisrt_term_hd:
                first_leave_dict[l.name] = int(fisrt_term_hd[0][0])
            else:
                first_leave_dict[l.name] = 0
            
            self.cr.execute("SELECT COUNT(*) FROM hr_holidays\
                            WHERE holiday_status_id = %s\
                            AND employee_id = %s\
                            AND date_from1 >= %s\
                            AND date_from1 <= %s\
                            AND type = %s \
                            AND state = %s\
                            ",(l.id, employee[0], nd_term_start_str, nd_term_end_str, 'remove', 'validate'))
            second_term_hd = self.cr.fetchall()
            if second_term_hd:
                second_leave_dict[l.name] = int(second_term_hd[0][0])
            else:
                second_leave_dict[l.name] = 0
            
            self.cr.execute("SELECT COUNT(*) FROM hr_holidays\
                            WHERE holiday_status_id = %s\
                            AND employee_id = %s\
                            AND date_from1 >= %s\
                            AND date_from1 <= %s\
                            AND type = %s \
                            AND state = %s\
                            ",(l.id, employee[0], rd_term_start_str, rd_term_end_str, 'remove', 'validate'))
            third_term_hd = self.cr.fetchall()
            if third_term_hd:
                third_leave_dict[l.name] = int(third_term_hd[0][0])
            else:
                third_leave_dict[l.name] = 0

        all_leave_type_name.sort()
        all_term_dict = {}
        all_term_dict[1] = term1_list
        all_term_dict[2] = term2_list
        all_term_dict[3] = term3_list
        all_term_list    = [[a, b] for a, b in all_term_dict.items()]
        all_term_list.sort(key=self.sorted_list)


        first_leave_list = [[a, b] for a, b in first_leave_dict.items()]
        first_leave_list.sort(key=self.sorted_list)

        second_leave_list = [[a, b] for a, b in second_leave_dict.items()]
        second_leave_list.sort(key=self.sorted_list)

        third_leave_list = [[a, b] for a, b in third_leave_dict.items()]
        third_leave_list.sort(key=self.sorted_list)

        all_term_leave_dict = {}
        all_term_leave_dict[1] = first_leave_list
        all_term_leave_dict[2] = second_leave_list
        all_term_leave_dict[3] = third_leave_list
        all_term_leave_list   = [[a, b] for a, b in all_term_leave_dict.items()]
        all_term_leave_list.sort(key=self.sorted_list)
        all_type.sort()
        print('all_term_list = ', all_term_list)

        result = {
            'all_type': all_type,
            'all_term_up': all_term_list,
            'term1_list': term1_list,
            'term2_list': term2_list,
            'term3_list': term3_list,
            'all_leave_type_name': all_leave_type_name,
            'all_term_down': all_term_leave_list,
            'first_term_leave': first_leave_list,
            'second_term_leave': second_leave_list,
            'third_term_leave': third_leave_list,
            'term1_week_range': week_to_display_in_term1,
            'term1_date_range': term1_date_range,
            'term2_week_range': week_to_display_in_term2,
            'term2_date_range': term2_date_range,
            'term3_week_range': week_to_display_in_term3,
            'term3_date_range': term3_date_range,
            'absent': absent_total,
            'late': employee_late_and_leave['total_late'],
            'leave_early': employee_late_and_leave['total_leave_early'],
            'not_c_in': 0,
            'not_c_out': 0,
        }
        data.append(result)
        if data:
            return data
        else:
            return {}

            

  

class report_summary_emp_att(models.AbstractModel):
    _name = 'report.sisb_hr.sisb_employee_summary_attendance_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.sisb_employee_summary_attendance_report'
    _wrapped_report_class = report_emp_att