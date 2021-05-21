from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar
import random
from ...utility.utils import hour_float_to_time as hftt
from ...utility.utils import float_to_day_time as ftdt

class report_accumulative_leave(report_sxw.rml_parse):
    _name = 'report.sisb_hr.leave_accumulative_per_allocated'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(report_accumulative_leave, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'get_employee': self._get_employee,
            'get_leave_to_display': self._get_leave_to_display,
            'get_emp_detail_leave': self._get_emp_detail_leave,
            'check_emp_hd': self._check_emp_hd,
            'check_hd_ev_month': self._check_hd_ev_month,
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


    def _get_emp_detail_leave(self, employ, all_holiday):
        data = []
        employ_obj = self.pool.get('hr.employee').search(self.cr, self.uid, [('id', '=', employ)])
        employee_id = self.pool.get('hr.employee').browse(self.cr, self.uid, employ_obj)
        holiday = self.pool.get('hr.holidays.status').search(self.cr, self.uid, [('id','in', all_holiday)], order="name ASC")
        all_hd = self.pool.get('hr.holidays.status').browse(self.cr, self.uid, holiday)
        for hd in all_hd:
            lv_amount = ''
            lv_used = ''
            lv_remain = ''
            lv_over = ''
            emp_hd = employee_id.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == hd)
            if emp_hd:
                lv_amount = ftdt(emp_hd.total_curr_leave)
                lv_used = ftdt(emp_hd.total_taken_leave)
                lv_remain = ftdt(emp_hd.current_leave)
            result = {
                'leave_total': lv_amount,
                'leave_used': lv_used,
                'leave_remain': lv_remain,
                'leave_over': lv_over,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}


    def _check_hd_ev_month(self, start_date, end_date, employee_id, all_hd):
        data = []
        employee_obj = employ_obj = self.pool.get('hr.employee').search(self.cr, self.uid, [('id', '=', employee_id)])
        days_holidays = self.pool.get('days.holidays.days')
        employee_id = self.pool.get('hr.employee').browse(self.cr, self.uid, employee_obj)
        holiday = self.pool.get('hr.holidays.status').search(self.cr, self.uid, [('id','in', all_hd)], order="name ASC")
        all_hd = self.pool.get('hr.holidays.status').browse(self.cr, self.uid, holiday)
        holiday_obj = self.pool.get('hr.holidays')
        half = ['first_half','second_half']
        for hd in all_hd:
            lv_days = 0.00
            lv_status = ''
            lv_remain = ''
            lv_over = ''
            self.cr.execute("SELECT dhd.leave_type, dhd.hour_span FROM days_holidays_days dhd, hr_holidays hh \
                            WHERE hh.employee_id = %s\
                            AND dhd.date1 >= %s\
                            AND dhd.date1 <= %s\
                            AND hh.state = 'validate'\
                            AND hh.holiday_status_id = %s\
                            AND hh.id = dhd.holiday_id",(employee_id.id, start_date, end_date, hd.id))
            all_hd = self.cr.fetchall()
            for h in all_hd:
                if h[0] == 'full':
                    lv_days += 1
                elif h[0] in half:
                    lv_days += 4 / 24
                elif h[0] == 'part':
                    print('h1 = ', h[1])
                    lv_days += h[1]/ 24
                    print('lv_days = ',lv_days)
            lv_days = ftdt(lv_days)
            if lv_days == '0 - 00:00':
                lv_days = ''
            result = {
                'status': lv_status,
                'used': lv_days,
                'remain': lv_remain,
                'over': lv_over
            }
            data.append(result)
        if data:
            return data
        else:
            return {}


    def _check_emp_hd(self, leave_reset_month):
        FMT = '%Y-%m-%d'
        data = []
        now = datetime.now()
        end_year = 0
        start_year = 0
        if int(now.month) > int(leave_reset_month):
            start_year = now.year
        elif int(now.month) < int(leave_reset_month):
            start_year = now.year - 1
        # print('alloc_template = ', alloc_template)
        start_period = str(start_year) + '-' + str(leave_reset_month) + '-' + '01'
        date_start = datetime.strptime(start_period, FMT)
        date_end = date_start.replace(year= date_start.year + 1, month=date_start.month - 1)
        date_end2 = date_end.replace(day=calendar.monthrange(date_end.year, date_end.month)[1])
        next_year_month = date_start.month - 1
        # som stands for Start Of Month
        # eom stands for End Of Month
        step = timedelta(days=1)

        while (date_start < date_end2):
            som = ''
            eom = ''
            if date_start.day == 1:
                som = date_start.strftime(FMT)
                eom = date_start.replace(day = calendar.monthrange(date_start.year, date_start.month)[1]).strftime(FMT)
                result = {
                    'month_year': str(date_start.year) + '      /      ' + str(date_start.month),
                    'start_period': som,
                    'end_period': eom,
                }
                date_start += step
                data.append(result)
            else:
                date_start += step
    
        if data:
            return data
        else:
            return {}



        # alloc_template_obj = self.pool.get('allocate.leaves.run').search(self.cr, self.uid, [('id','=', alloc_template[0])])
        # alloc_template__id = self.pool.get('allocate.leaves.run').browse(self.cr, self.uid, alloc_template_obj)
        # # employee_obj = employ_obj = self.pool.get('hr.employee').search(self.cr, self.uid, [('id', '=', employee)])
        # # employee_id = self.pool.get('hr.employee').browse(self.cr, self.uid, employee_obj)
        # year_obj = alloc_template__id.year_id
        # for year in year_obj.period_ids:
        #     result = {
        #         'month_year': year.name,
        #         'start_period': year.date_start,
        #         'end_period': year.date_stop,
        #     }
        #     data.append(result)
        # if data:
        #     return data
        # else:
        #     return {}


    def _get_employee(self, form):
        data = []
        allocate_template = form['allocated_leave_id']
        all_holiday = form['leave_acc_select']
        allocate = self.pool.get('allocate.leaves.run').search(self.cr, self.uid, [('id', '=', allocate_template[0])])
        allocate_id = self.pool.get('allocate.leaves.run').browse(self.cr, self.uid, allocate)
        all_emp = []
        for emp in allocate_id.allocation_line_ids:
            if emp.employee_id.id not in all_emp:
                all_emp.append(emp.employee_id.id)
        all_employee = self.pool.get('hr.employee').browse(self.cr, self.uid, all_emp)
        for employ in all_employee:
            if not employ.emp_curr_leave_ids:
                continue
            employ_no_name = employ.employee_no + '    ' + employ.name 
            result = {
                'employee_name': employ_no_name,
                'employee_id': employ.id,
                'hd_to_display': all_holiday,
                'allocated_template': allocate_template,
                'leave_reset_month': employ.leave_reset_month,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}




        #     holiday_name_obj = self.pool.get('hr.holidays.status').search(self.cr, self.uid, [('id' ,'in', all_holiday)], order="name ASC")
        #     all_hd = self.pool.get('hr.holidays.status').browse(self.cr, self.uid, holiday_name_obj)all_hd = self.pool.get('hr.holidays.status').browse(self.cr, self.uid, holiday_name_obj)
        #     for holiday in all_hd:
        #         lv_amount = 0
        #         lv_used = 0
        #         lv_remain = 0
        #         lv_over = 0
        #         emp_hd = employ.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == holiday)
        #         if not emp_hd:
        #             lv_amount = 0
        #             lv_used = 0
        #             lv_remain = 0
        #             lv_over = 0
        #         else:
        #             lv_amount = emp_hd.total_curr_leave
        #             lv_used = emp_hd.total_taken_list
        #             lv_remain = emp_hd.current_leave
        #         result = {
        #             'leave_total': lv_amount,
        #             'leave_used': lv_used,
        #             'leave_remain': lv_remain,
        #             'leave_over': lv_over,
        #         }
        #         data.append(result)
        # if data:
        #     return data
        # else:
        #     return {}
                

            
    def _get_leave_to_display(self, form):
        data = []
        all_holiday = form['leave_acc_select']
        holiday_name_obj = self.pool.get('hr.holidays.status').search(self.cr, self.uid, [('id' ,'in', all_holiday)], order="name ASC")
        all_hd = self.pool.get('hr.holidays.status').browse(self.cr, self.uid, holiday_name_obj)
        for hd_name in all_hd:
            result = {
                'hd_name': hd_name.name,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}



class report_summary_leave(models.AbstractModel):
    _name = 'report.sisb_hr.leave_accumulative_per_allocated'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.leave_accumulative_per_allocated'
    _wrapped_report_class = report_accumulative_leave