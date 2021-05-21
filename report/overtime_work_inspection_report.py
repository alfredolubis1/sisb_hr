from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar
from ..utility.utils import hour_float_to_time as hftt
from time import gmtime, strftime
import pytz


class employee_overtime_work_inspection_report(report_sxw.rml_parse):
    _name = 'report.sisb_hr.employee_overtime_work_inspection'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(employee_overtime_work_inspection_report, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'get_employee_ot': self._get_employee_ot,
            'get_daily_overtime': self._get_daily_overtime,
            'get_section_code': self._get_section_code,
        })

    def _get_section_code(self, company):
        section_code = ''
        if company.school_ids:
            for rec in company.school_ids:
                section_code = '00' + str(rec.sequence) + ' :Section : SISB-' + rec.code
                break
        else:
            section_code = 'Section: SISB'  
        return section_code


    def _get_daily_overtime(self, employee_id, date_from , date_to, attendance_id):
        data = []
        print('attendance_id = ', attendance_id)
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(self.cr, self.uid, [('id', '=', employee_id)])
        employee = emp_obj.browse(self.cr, self.uid, emp_id)
        all_day = emp_obj.delta_days(self.cr, self.uid, date_from, date_to)
        for att_id in attendance_id:
            print('att_id = ', att_id)
            self.cr.execute("SELECT name + INTERVAL '8 HOURS', sign_out + INTERVAL '8 HOURS' \
                            FROM hr_attendance \
                            WHERE id = %s \
                            ",(att_id,))
            ot_att = self.cr.fetchall()
            att_obj = self.pool.get('hr.attendance').browse(self.cr, self.uid, att_id)
            sign_in_obj = datetime.strptime(ot_att[0][0], '%Y-%m-%d %H:%M:%S')
            sign_out_obj = datetime.strptime(ot_att[0][1], '%Y-%m-%d %H:%M:%S')
            sign_in = sign_in_obj.strftime('%d/%b/%Y %H:%M')
            sign_out = sign_out_obj.strftime('%d/%b/%Y %H:%M')
            date_sign_in = datetime.strptime(ot_att[0][0], '%Y-%m-%d %H:%M:%S')
            day_name = date_sign_in.strftime('%d/%b/%Y') + ' [' + date_sign_in.strftime('%a') + ']'
            att_obj = self.pool.get('hr.attendance').browse(self.cr, self.uid, att_id)
            schedule = att_obj.shift_id
            tz  = pytz.timezone(schedule.default_timezone)
            tz_time = datetime.now(tz)
            year = date_sign_in.year
            month = date_sign_in.month
            day = date_sign_in.day
            # year = int(datetime.strftime(tz_time, '%Y'))
            # month = int(datetime.strftime(tz_time, '%m'))
            # day = int(datetime.strftime(tz_time, '%d'))
            today = calendar.weekday(year, month, day)
            check_shift =  [r.options for r in schedule.day_of_wewks_ids.filtered(lambda x: int(x.day_of_week) == today)]
            holiday_shift = True if check_shift[0] == 'holiday' else False
            holiday_year = emp_obj.check_holiday(self.cr, self.uid, employee, tz_time)
            day_option = 'N'
            if holiday_shift and not holiday_year:
                day_option = 'H'
            elif (holiday_shift and holiday_year) or (not holiday_shift and holiday_year):
                day_option = 'HD'
            for ot in att_obj.overtime_ids:
                print('ot_end = ', ot.end_ot)
                ot_day = hftt(ot.ot_rounded)
                ot_type = ot.ot_type_id.name
                ot_start = hftt(ot.start_ot)
                ot_end = hftt(ot.end_ot)
                ot_len = hftt(ot.end_ot - ot.start_ot)
                ot_one = hftt(ot.rate_one) if ot.rate_one > 0.00 else ''
                ot_one_half = hftt(ot.rate_one_half) if ot.rate_one_half > 0.00 else ''
                ot_double = hftt(ot.rate_double) if ot.rate_double > 0.00 else ''
                ot_triple = hftt(ot.rate_triple) if ot.rate_triple > 0.00 else ''
                # ot_length = hftt(ot.ot_length)
                result = {
                    'type': ot_type,
                    'date': day_name,
                    'schedule': att_obj.shift_id.name,
                    'day': day_option,
                    'sign_in': sign_in,
                    'sign_out': sign_out,
                    'one': ot_one,
                    'one_half': ot_one_half,
                    'double': ot_double,
                    'triple': ot_triple,
                    'ot_start': ot_start,
                    'ot_end': ot_end,
                    'ot_one': hftt(ot.rate_one),
                    'ot_one_half': hftt(ot.rate_one_half),
                    'ot_double': hftt(ot.rate_double),
                    'ot_triple': hftt(ot.rate_triple),
                    'ot_total': ot_len
                    # 'ot_length': ot_length

                }
                data.append(result)
        if data:
            return data
        else:
            return {}


        # for day in all_day['all_day']:
        #     self.cr.execute("SELECT name + INTERVAL '8 HOURS', sign_out + INTERVAL '8 HOURS' \
        #                     FROM sisb_attendance \
        #                     WHERE name + INTERVAL '8 HOURS' >= %s \
        #                     AND name + INTERVAL '8 HOURS' <= %s \
        #                     AND employee_id = %s\
        #                     AND overtime = true\
        #                     ",(day + ' 00:00:00', day + ' 23:59:59', employee_id))



    def _get_employee_ot(self, form):
        data = []
        emp_obj = self.pool.get('hr.employee')
        date_from = form['date_from']
        print('date_from = ', date_from)
        date_to = form['date_to']
        company = form['company_id']
        all_employee = self.pool.get('hr.employee').search(self.cr, self.uid, [('company_id', '=', company[0]),('active','=', True)])
        all_employee_id = self.pool.get('hr.employee').browse(self.cr, self.uid, all_employee)
        all_day = emp_obj.delta_days(self.cr, self.uid, date_from, date_to)
        for employee in all_employee_id:
            name = ''
            if employee.gender == 'male':
                name = employee.employee_no + ' ' + 'Mr.' + employee.name
            if employee.gender == 'female':
                name = employee.employee_no + ' ' + 'Mrs.' + employee.name
            if not employee.gender:
                name = employee.employee_no + ' ' + employee.name
            print('employee_id = ', employee.id)
            self.cr.execute("SELECT id FROM hr_attendance\
                            WHERE name + INTERVAL '8 HOURS' >= %s\
                            AND name + INTERVAL '8 HOURS' <= %s\
                            AND sign_out IS NOT NULL \
                            AND employee_id = %s \
                            AND overtime = true \
                            ORDER BY name ASC \
                            ",(date_from + ' 00:00:00', date_to + ' 23:59:59', employee.id))
            emp_ot = self.cr.fetchall()
            if not emp_ot:
                continue
            emp_ot_id = []
            total_one = total_one_half = total_double = total_triple = 0.00
            one = one_half = double = triple = ''
            for ot_id in emp_ot:
                if ot_id not in emp_ot_id:
                    emp_ot_id.append(ot_id[0])
            emp_att_id = self.pool.get('hr.attendance').browse(self.cr, self.uid, emp_ot_id)
            for ot_list in emp_att_id:
                for ot in ot_list.overtime_ids:
                    total_one += ot.rate_one
                    total_one_half += ot.rate_one_half
                    total_double += ot.rate_double
                    total_triple += ot.rate_triple
            if total_one > 0.00:
                one = hftt(total_one)
            if total_one_half > 0.00:
                one_half = hftt(total_one_half)
            if total_double > 0.00:
                double = hftt(total_double)
            if total_triple > 0.00:
                triple = hftt(total_triple)

            result = {
                'name': name,
                'ot_one': one,
                'ot_one_half': one_half,
                'ot_double': double,
                'ot_triple': triple,
                'employee_id': employee.id,
                'date_from': date_from,
                'date_to': date_to,
                'attendance_id': emp_ot_id
            }
            data.append(result)
        if data:
            return data
        else:
            return {}
                    
                


class report_overtime_work_inspection(models.AbstractModel):
    _name = 'report.sisb_hr.employee_overtime_work_inspection'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.employee_overtime_work_inspection'
    _wrapped_report_class = employee_overtime_work_inspection_report