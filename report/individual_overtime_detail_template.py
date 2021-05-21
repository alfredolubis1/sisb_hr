from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar
from ..utility.utils import hour_float_to_time as hftt
from time import gmtime, strftime

class employee_individu_ot_detail_report(report_sxw.rml_parse):
    _name = 'report.sisb_hr.employee_individual_detail_ot'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(employee_individu_ot_detail_report, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'individual_employee_ot_det': self._individual_employee_ot_det,
            'get_ot_total': self._get_ot_total,
            'get_section_code': self._get_section_code,
            'tot_all': self._tot_all,
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
    

    def _tot_all(self, company_id, employee_id, date_from, date_to):
        data = []
        start = date_from + ' 00:00:00'
        end = date_to + ' 23:59:59'
        total_ot_one = ''
        total_ot_one_half = ''
        total_ot_two = ''
        total_ot_two_half = ''
        total_ot_three = ''
        total_ot_six = ''
        self.cr.execute("SELECT COALESCE(SUM(daily_ot_total), 0)\
                        FROM hr_attendance \
                        WHERE employee_id=%s \
                        AND name + INTERVAL '8 HOURS' >= %s\
                        AND name + INTERVAL '8 HOURS' <= %s\
                        AND overtime = true\
                        ",(employee_id.id, start, end))
        ot_one_half_obj = self.cr.fetchall()
        print('ot_one_half_obj = ', ot_one_half_obj)
        total_ot_one_half = hftt(ot_one_half_obj[0][0])
        result = {
            'total_ot_one': total_ot_one,
            'total_ot_one_half': total_ot_one_half,
            'total_ot_two': total_ot_two,
            'total_ot_two_half': total_ot_two_half,
            'total_ot_three': total_ot_three,
            'total_ot_six': total_ot_six,
        }
        data.append(result)
        if data:
            return data
        else: 
            return {}
        


    def get_employee_schedule(self, employee_id, day):
        schedule_name = ''
        sched_obj = self.pool.get('employee.schedule').search(self.cr, self.uid, [
            ('employee_id', '=', employee_id[0]),
            ('date_from', '<=', day),
            ('date_to', '>=', day)
        ])
        if sched_obj:
            schedule = self.pool.get('employee.schedule').browse(self.cr, self.uid, sched_obj)
            schedule_name = schedule.schedule_type_id.name
        else:
            schedule_name = '-'
        return schedule_name
    
    def _get_ot_total(self, ot_total):
        print('total = ', ot_total)
        ot = float(ot_total)
        print('ot = ', ot)
        ot_hour = int(ot) * 3600
        left_hour = ((ot % 1) * 60) * 60
        second = ot_hour + int(left_hour)
        ot_minute = int(left_hour)
        hour_minute = '{}:{}'.format(ot_hour, ot_minute)
        return strftime('%H:%M', gmtime(second))

    def _individual_employee_ot_det(self, form):
        data = []
        FMT = '%Y-%m-%d'
        emp_obj = self.pool.get('hr.employee')
        date_from = form['date_from']
        date_to = form['date_to']
        employee = form['employee_id']
        print('employee = ', employee)
        employee_id = emp_obj.browse(self.cr, self.uid, employee)
        print('employee_id = ', employee_id)
        all_day = emp_obj.delta_days(self.cr, self.uid, date_from, date_to)
        ot_total = 0.0
        for day in all_day['all_day']:
            emp_sign_in_time = ''
            emp_sign_out_time = ''
            day_date_obj = datetime.strptime(day, FMT)
            date_att = day_date_obj.strftime('%d/%b/%Y')
            day_name = day_date_obj.strftime('%a')
            date_name = date_att + ' [' + day_name + ']'
            ot_rounded = 0.0
            schedule = self.get_employee_schedule(employee, day)
            self.cr.execute("SELECT name + INTERVAL '8 HOURS', sign_out + INTERVAL '8 HOURS', id \
                FROM hr_attendance \
                WHERE employee_id=%s \
                AND sign_out IS NOT NULL\
                AND name + INTERVAL '8 HOURS' <=  %s \
                AND name + INTERVAL '8 HOURS' >= %s \
                AND overtime = true \
            ", (employee[0], day + ' 23:59:50', day + ' 00:00:00'))
            overtime = self.cr.fetchall()
            if not overtime:
                continue
            overtime_id = self.pool.get('hr.attendance').browse(self.cr, self.uid, overtime[0][2])
            ot_round = 0.0
            for ot_list in overtime_id.overtime_ids:
                print('ot = ', ot_list.ot_rounded, 'type = ', type(ot_list.ot_rounded))
                ot_round += ot_list.ot_rounded
            ot_total += ot_round
            print('ot_total = ', ot_total)
            p_in_obj = datetime.strptime(overtime[0][0], '%Y-%m-%d %H:%M:%S')
            punch_in = p_in_obj.strftime('%d/%b/%Y %H:%M')
            p_out_obj = datetime.strptime(overtime[0][1], '%Y-%m-%d %H:%M:%S')
            punch_out = p_out_obj.strftime('%d/%b/%Y %H:%M')
            ot_round = hftt(ot_round)
            result = {
                'date': date_name,
                'schedule': schedule,
                'punch_in': punch_in,
                'punch_out': punch_out,
                'ot_rounded': ot_round,
                'ot_length': ot_total,
            }
            data.append(result)
        if data:
            print('data= ', data)
            return data
        else:
            return {}
            
            
            

        

class report_emp_ot_detail(models.AbstractModel):
    _name = 'report.sisb_hr.employee_individual_detail_ot'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.employee_individual_detail_ot'
    _wrapped_report_class = employee_individu_ot_detail_report