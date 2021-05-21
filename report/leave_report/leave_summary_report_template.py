from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar
from ...utility.utils import  hour_float_to_time as hftt
from ...utility.utils import float_to_day_time as ftdt

class report_summary_asking_leave(report_sxw.rml_parse):
    _name = 'report.sisb_hr.leave_summary_percompany'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(report_summary_asking_leave, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'get_leave': self._get_leave,
            'get_employee': self._get_employee_leave,
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



    def _get_employee_leave(self, employee, date_from, date_to):
        data = []
        FMT = '%Y-%m-%d'
        holiday_obj = self.pool.get('hr.holidays')
        employee_holiday_obj = holiday_obj.search(self.cr, self.uid, [
            ('employee_id','=', employee),
            ('date_from1','>=', date_from),
            ('date_to1', '<=', date_to),
            ('state','=','validate'),
            ('type','=','remove')
        ],order="id asc")
        result = {}
        half_leave = ('first_half','second_half')
        employee_holiday_id = holiday_obj.browse(self.cr, self.uid, employee_holiday_obj)
        all_same = False
        all_leave_type = []
        add_hours = timedelta(hours=8)
        for emp_hd in employee_holiday_id:
            full_all = 0
            second_all = 0
            first_all = 0
            part_all = 0
            leave_part_start = 0
            leave_part_end = 0
            hour_span = 0
            leave_type = ''
            leave_start_date_obj = datetime.strptime(emp_hd.date_from1, FMT)
            leave_end_date_obj = datetime.strptime(emp_hd.date_to1, FMT)
            date_create_obj = datetime.strptime(emp_hd.create_date, '%Y-%m-%d %H:%M:%S') + add_hours
            for days in emp_hd.holiday_id:
                if days.leave_type == 'full':
                    full_all += 1
                if days.leave_type == 'first_half':
                    first_all += 1
                if days.leave_type == 'second_half':
                    second_all += 1
                if days.leave_type == 'part':
                    part_all += 1
            if full_all >= 1 and (second_all == first_all == part_all == 0):
                all_same = True
                leave_type = 'Full-day' 
            if second_all >= 1 and (full_all == first_all == part_all == 0):
                all_same = True
                leave_type = 'Seconfd-half'
            if first_all >= 1 and (full_all == second_all == part_all == 0):
                all_same = True
                leave_type = 'First-half'
            if part_all >= 1 and (first_all == second_all == full_all == 0):
                all_same = True
                leave_type = 'Part-time'
            if all_same:
                print('disini')
                if leave_type == 'Part-time':
                    for day in emp_hd.holiday_id:
                        leave_part_start = day.start_hour
                        leave_part_end = day.end_hour
                        hour_span = day.hour_span
                        
                    result = {
                        'leave_name': emp_hd.holiday_status_id.name,
                        'leave_start': leave_start_date_obj.strftime('%d-%b-%Y'),
                        'leave_end': leave_end_date_obj.strftime('%d-%b-%Y'),
                        'leave_part_start': hftt(float(leave_part_start)),
                        'leave_part_end': hftt(float(leave_part_end)),
                        'leave_time': hftt(float(hour_span)),
                        'leave_total': hftt(float(hour_span)),
                        'leave_type': leave_type,
                        'notes': emp_hd.name,
                        'leave_desc': emp_hd.name,
                        'leave_creation_date': date_create_obj.strftime('%d-%b-%Y')
                    }
                else:
                    if leave_type in half_leave:
                        leave_total = '0 - :00'
                    else:
                        leave_total = emp_hd.number_of_days
                        leave_total = str(int(leave_total)) + ' - :00'
                    result = {
                        'leave_name': emp_hd.holiday_status_id.name,
                        'leave_start': leave_start_date_obj.strftime('%d-%b-%Y'),
                        'leave_end': leave_end_date_obj.strftime('%d-%b-%Y'),
                        'leave_part_start': ':',
                        'leave_part_end': ':',
                        'leave_time': ':',
                        'leave_total': leave_total,
                        'leave_type': leave_type,
                        'notes': emp_hd.name,
                        'leave_desc': emp_hd.name,
                        'leave_creation_date': date_create_obj.strftime('%d-%b-%Y %H:%M')
                    }
                data.append(result)
            if not all_same:
                print('disini1', emp_hd.id)
                for hd in emp_hd.holiday_id:
                    date = datetime.strptime(hd.date1, FMT)
                    amt_leave = ''
                    leave_part_start = 0.00
                    leave_part_end = 0.00
                    hour_span = 0.00
                    if hd.leave_type == 'full':
                        amt_leave = '1 - :00'
                        leave_type = 'Full-day'
                    if hd.leave_type == 'first_half':
                        leave_type = 'First-half'
                    if hd.leave_type == 'second_half':
                        leave_type = 'Second-half'
                    if hd.leave_type == 'part':
                        leave_part_start += hd.start_hour
                        leave_part_end += hd.end_hour
                        hour_span += hd.hour_span
                        amt_leave = '0 - ' + hftt(float(hour_span))
                        leave_type = 'Part-time'
                    result = {
                        'leave_name': emp_hd.holiday_status_id.name,
                        'leave_start': date.strftime('%d-%b-%Y'),
                        'leave_end': date.strftime('%d-%b-%Y'),
                        'leave_type': leave_type,
                        'leave_part_start': hftt(float(leave_part_start)),
                        'leave_part_end': hftt(float(leave_part_end)),
                        'leave_total': amt_leave,
                        'leave_time': hftt(float(hour_span)),
                        'notes': emp_hd.name,
                        'leave_desc': emp_hd.name,
                        'leave_creation_date': date_create_obj.strftime('%d-%b-%Y')
                    }
                    data.append(result)
        if data:
            return data
        else:
            return {}



        

    def _get_leave(self, form):
        data        = []
        FMT         = '%Y-%m-%d'
        emp_obj     = self.pool.get('hr.employee')
        date_from   = form['date_from']
        date_to     = form['date_to']
        company_id  = form['company_id']
        all_day     = emp_obj.delta_days(self.cr, self.uid, date_from, date_to)
        holiday_obj = self.pool.get('hr.holidays').search(self.cr, self.uid, [
            ('date_from1', '>=', date_from),
            ('date_to1', '<=', date_to),
            ('state','=','validate'),
            ('type', '=', 'remove')
        ],order="create_date asc")
        all_holiday = self.pool.get('hr.holidays').browse(self.cr, self.uid, holiday_obj)
        print('all_holiday = ', all_holiday)
        all_employee_obj = emp_obj.search(self.cr, self.uid, [('company_id','=',company_id[0]), ('active','=', True)])
        all_employee_id = emp_obj.browse(self.cr, self.uid, all_employee_obj)
        employee_holiday = ''
        for employee in all_employee_id:
            holiday = self.pool.get('hr.holidays').search(self.cr, self.uid, [
                ('employee_id','=', employee.id),
                ('date_from1', '>=', date_from),
                ('date_to1', '<=', date_to),
                ('state','=','validate'),
                ('type', '=', 'remove')])
            if not holiday:
                continue
            # if holiday:
            #     employee_holiday = self.pool.get('hr.holidays').browse(self.cr, self.uid, holiday)
            emp_name = ''
            if employee.gender == 'male':
                emp_name = 'Mr. ' + employee.name
            if employee.gender == 'female':
                emp_name = 'Mrs. ' + employee.name
            if not employee.gender:
                emp_name = employee.name
            name = employee.employee_no + ' ' + emp_name
            date_join_str = ''
            if employee.join_date:
                date_join_obj = datetime.strptime(employee.join_date, '%Y-%m-%d')
                date_join_str = date_join_obj.strftime('%d-%B-%Y')
            result = {
                'employee_name': name,
                'date_join': date_join_str,
                'employee_id': employee.id,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}
            

class report_summary_leave(models.AbstractModel):
    _name = 'report.sisb_hr.leave_summary_percompany'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.leave_summary_percompany'
    _wrapped_report_class = report_summary_asking_leave





class report_individual_leave_history(report_sxw.rml_parse):
    _name = 'report.sisb_hr.individual_leave_summary'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(report_individual_leave_history, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'get_leave': self._get_leave,
            'get_employee': self._get_employee_leave,
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



    def _get_employee_leave(self, employee, date_from, date_to):
        data = []
        FMT = '%Y-%m-%d'
        holiday_obj = self.pool.get('hr.holidays')
        employee_holiday_obj = holiday_obj.search(self.cr, self.uid, [
            ('employee_id','=', employee),
            ('date_from1','>=', date_from),
            ('date_to1', '<=', date_to),
            ('state','=','validate'),
            ('type','=','remove')
        ],order="id asc")
        result = {}
        half_leave = ('first_half','second_half')
        employee_holiday_id = holiday_obj.browse(self.cr, self.uid, employee_holiday_obj)
        all_same = False
        all_leave_type = []
        add_hours = timedelta(hours=8)
        for emp_hd in employee_holiday_id:
            full_all = 0
            second_all = 0
            first_all = 0
            part_all = 0
            leave_part_start = 0
            leave_part_end = 0
            hour_span = 0
            leave_type = ''
            leave_start_date_obj = datetime.strptime(emp_hd.date_from1, FMT)
            leave_end_date_obj = datetime.strptime(emp_hd.date_to1, FMT)
            date_create_obj = datetime.strptime(emp_hd.create_date, '%Y-%m-%d %H:%M:%S') + add_hours
            for days in emp_hd.holiday_id:
                if days.leave_type == 'full':
                    full_all += 1
                if days.leave_type == 'first_half':
                    first_all += 1
                if days.leave_type == 'second_half':
                    second_all += 1
                if days.leave_type == 'part':
                    part_all += 1
            if full_all >= 1 and (second_all == first_all == part_all == 0):
                all_same = True
                leave_type = 'Full-day' 
            if second_all >= 1 and (full_all == first_all == part_all == 0):
                all_same = True
                leave_type = 'Seconfd-half'
            if first_all >= 1 and (full_all == second_all == part_all == 0):
                all_same = True
                leave_type = 'First-half'
            if part_all >= 1 and (first_all == second_all == full_all == 0):
                all_same = True
                leave_type = 'Part-time'
            if all_same:
                print('disini')
                if leave_type == 'Part-time':
                    for day in emp_hd.holiday_id:
                        leave_part_start = day.start_hour
                        leave_part_end = day.end_hour
                        hour_span = day.hour_span
                    result = {
                        'leave_name': emp_hd.holiday_status_id.name,
                        'leave_start': leave_start_date_obj.strftime('%d-%b-%Y'),
                        'leave_end': leave_end_date_obj.strftime('%d-%b-%Y'),
                        'leave_part_start': hftt(float(leave_part_start)),
                        'leave_part_end': hftt(float(leave_part_end)),
                        'leave_time': hftt(float(hour_span)),
                        'leave_total': 0,
                        'leave_type': leave_type,
                        'notes': emp_hd.name,
                        'leave_desc': emp_hd.name,
                        'leave_creation_date': date_create_obj.strftime('%d-%b-%Y')
                    }
                else:
                    if leave_type in half_leave:
                        leave_total = '0 - :00'
                    else:
                        leave_total = emp_hd.number_of_days
                        leave_total = str(leave_total) + ' - :00'
                    result = {
                        'leave_name': emp_hd.holiday_status_id.name,
                        'leave_start': leave_start_date_obj.strftime('%d-%b-%Y'),
                        'leave_end': leave_end_date_obj.strftime('%d-%b-%Y'),
                        'leave_part_start': ':',
                        'leave_part_end': ':',
                        'leave_time': ':',
                        'leave_total': leave_total,
                        'leave_type': leave_type,
                        'notes': emp_hd.name,
                        'leave_desc': emp_hd.name,
                        'leave_creation_date': date_create_obj.strftime('%d-%b-%Y')
                    }
                data.append(result)
            if not all_same:
                print('disini1', emp_hd.id)
                for hd in emp_hd.holiday_id:
                    date = datetime.strptime(hd.date1, FMT)
                    amt_leave = 0
                    leave_part_start = 0.00
                    leave_part_end = 0.00
                    hour_span = 0.00
                    if hd.leave_type == 'full':
                        amt_leave = 1
                        leave_type = 'Full-day'
                    if hd.leave_type == 'first_half':
                        leave_type = 'First-half'
                    if hd.leave_type == 'second_half':
                        leave_type = 'Second-half'
                    if hd.leave_type == 'part':
                        leave_part_start += hd.start_hour
                        leave_part_end += hd.end_hour
                        hour_span += hd.hour_span
                        leave_type = 'Part-time'
                    result = {
                        'leave_name': emp_hd.holiday_status_id.name,
                        'leave_start': date.strftime('%d-%b-%Y'),
                        'leave_end': date.strftime('%d-%b-%Y'),
                        'leave_type': leave_type,
                        'leave_part_start': hftt(float(leave_part_start)),
                        'leave_part_end': hftt(float(leave_part_end)),
                        'leave_total': str(amt_leave) + ' - :00',
                        'leave_time': hftt(float(hour_span)),
                        'notes': emp_hd.name,
                        'leave_desc': emp_hd.name,
                        'leave_creation_date': date_create_obj.strftime('%d-%b-%Y')
                    }
                    data.append(result)
        if data:
            return data
        else:
            return {}



        

    def _get_leave(self, form):
        data        = []
        FMT         = '%Y-%m-%d'
        emp_obj     = self.pool.get('hr.employee')
        date_from   = form['date_from']
        date_to     = form['date_to']
        company_id  = form['company_id']
        employee_id = form['employee_id']
        all_day     = emp_obj.delta_days(self.cr, self.uid, date_from, date_to)
        holiday_obj = self.pool.get('hr.holidays').search(self.cr, self.uid, [
            ('date_from1', '>=', date_from),
            ('date_to1', '<=', date_to),
            ('type', '=', 'remove'),
            ('state', '=', 'validate')
        ],order="create_date asc")
        all_holiday = self.pool.get('hr.holidays').browse(self.cr, self.uid, holiday_obj)
        print('all_holiday = ', all_holiday)
        all_employee_obj = emp_obj.search(self.cr, self.uid, [('company_id','=',company_id[0]), ('id', '=', employee_id[0]), ('active','=', True)])
        all_employee_id = emp_obj.browse(self.cr, self.uid, all_employee_obj)
        employee_holiday = ''
        for employee in all_employee_id:
            holiday = self.pool.get('hr.holidays').search(self.cr, self.uid, [
                ('employee_id','=', employee.id),
                ('date_from1', '>=', date_from),
                ('date_to1', '<=', date_to),
                ('type', '=', 'remove'),
                ('state', '=', 'validate')])
            if not holiday:
                continue
            # if holiday:
            #     employee_holiday = self.pool.get('hr.holidays').browse(self.cr, self.uid, holiday)
            emp_name = ''
            if employee.gender == 'male':
                emp_name = 'Mr. ' + employee.name
            if employee.gender == 'female':
                emp_name = 'Mrs. ' + employee.name
            if not employee.gender:
                emp_name = employee.name
            name = employee.employee_no + ' ' + emp_name
            date_join_str = ''
            if employee.join_date:
                date_join_obj = datetime.strptime(employee.join_date, '%Y-%m-%d')
                date_join_str = date_join_obj.strftime('%d-%B-%Y')
            result = {
                'employee_name': name,
                'date_join': date_join_str,
                'employee_id': employee.id,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}
            

class report_individual_leave(models.AbstractModel):
    _name = 'report.sisb_hr.individual_leave_summary'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.individual_leave_summary'
    _wrapped_report_class = report_individual_leave_history