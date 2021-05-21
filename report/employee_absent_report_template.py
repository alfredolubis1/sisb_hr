from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar

class employee_absent_report(report_sxw.rml_parse):
    _name = 'report.sisb_hr.sisb_employee_absent_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(employee_absent_report, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'track_absent': self._track_absent,
            'get_section_code': self._get_section_code,
        })

    

    def _track_absent(self, form):
        FMT = '%Y-%m-%d'
        data = []
        emp_obj     = self.pool.get('hr.employee')
        date_from   = form['date_from']
        date_to     = form['date_to']
        company_id  = form['company_id']
        company_obj = self.pool.get('res.company').search(self.cr, self. uid, [('id', '=', company_id[0])])
        company     = self.pool.get('res.company').browse(self.cr, self.uid, company_obj)
        all_employee_obj = emp_obj.search(self.cr, self.uid, [('company_id', '=', company_id[0]), ('active','=', True)])
        all_employee = emp_obj.browse(self.cr, self.uid, all_employee_obj)
        print('all_emp = ', all_employee_obj)
        all_day = emp_obj.delta_days(self.cr, self.uid, date_from, date_to)
        print('all_day = ', all_day)
        for employee in all_employee:
            absent = 0
            for day in all_day['all_day']:
                self.cr.execute("SELECT name + INTERVAL '8 HOURS' \
                                FROM hr_attendance \
                                WHERE employee_id = %s \
                                AND sign_out IS NOT NULL \
                                AND name + INTERVAL '8 HOURS' >= %s \
                                AND name + INTERVAL '8 HOURS' <= %s \
                                ", (employee.id, day + ' 00:00:00', day + ' 23:59:59'))
                employee_attendance = self.cr.fetchall()
                if employee_attendance:
                    continue
                if not employee_attendance:
                    date_obj = datetime.strptime(day, '%Y-%m-%d')
                    if date_obj > datetime.now():
                        continue
                    if day in all_day['weekend']:
                        continue
                    check_leave_day = emp_obj.check_leave_day(self.cr, self.uid, employee.id, day)
                    if check_leave_day:
                        continue
                    else:
                        check_emp_holiday = emp_obj.check_emp_holiday(self.cr, self.uid, employee, day)
                        if check_emp_holiday:
                            continue
                        else:
                            absent += 1
            if absent == 0:
                continue
                    
            result = {
                'employee_number': employee.employee_no,
                'employee_name': employee.name,
                'absent_amount': absent,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}


    def _get_section_code(self, company):
        section_code = ''
        if company.school_ids:
            for rec in company.school_ids:
                section_code = '00' + str(rec.sequence) + ' :Section : SISB-' + rec.code
                break
        else:
            section_code = 'Section: SISB'  
        return section_code


class report_emp_absent(models.AbstractModel):
    _name = 'report.sisb_hr.sisb_employee_absent_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.sisb_employee_absent_report'
    _wrapped_report_class = employee_absent_report





# Irregular Absent report

class sisb_employee_irregular_absent_report(report_sxw.rml_parse):
    _name = 'report.sisb_hr.employee_irregular_absent_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(sisb_employee_irregular_absent_report, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'track_irregular_absent': self._track_irregular_absent,
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

    def _track_irregular_absent(self, form):
        FMT = '%Y-%m-%d'
        data = []
        emp_obj     = self.pool.get('hr.employee')
        date_from   = form['date_from']
        date_to     = form['date_to']
        company_id  = form['company_id']
        company_obj = self.pool.get('res.company').search(self.cr, self. uid, [('id', '=', company_id[0])])
        company     = self.pool.get('res.company').browse(self.cr, self.uid, company_obj)
        all_employee_obj = emp_obj.search(self.cr, self.uid, [('company_id', '=', company_id[0]), ('active','=', True)])
        all_employee = emp_obj.browse(self.cr, self.uid, all_employee_obj)
        print('all_emp = ', all_employee_obj)
        all_day = emp_obj.delta_days(self.cr, self.uid, date_from, date_to)
        print('all_day = ', all_day)
        for employee in all_employee:
            absent = 0
            date_only = []
            dat = ''
            for day in all_day['all_day']:
                self.cr.execute("SELECT name + INTERVAL '8 HOURS' \
                                FROM hr_attendance \
                                WHERE employee_id = %s \
                                AND sign_out IS NOT NULL \
                                AND name + INTERVAL '8 HOURS' >= %s \
                                AND name + INTERVAL '8 HOURS' <= %s \
                                ", (employee.id, day + ' 00:00:00', day + ' 23:59:59'))
                employee_attendance = self.cr.fetchall()
                if employee_attendance:
                    continue
                if not employee_attendance:
                    date_obj = datetime.strptime(day, '%Y-%m-%d')
                    if date_obj > datetime.now():
                        continue
                    if day in all_day['weekend']:
                        continue
                    check_leave_day = emp_obj.check_leave_day(self.cr, self.uid, employee.id, day)
                    if check_leave_day:
                        continue
                    else:
                        check_emp_holiday = emp_obj.check_emp_holiday(self.cr, self.uid, employee, day)
                        if check_emp_holiday:
                            continue
                        else:
                            absent += 1
                            date_only.append(int(date_obj.strftime('%d')))
            if absent == 0:
                continue
            if date_only:
                for d in date_only:
                    dat += str(d) +','
                    
            result = {
                'employee_number': employee.employee_no,
                'employee_name': employee.name,
                'date_only': dat,
                'absent_amount': absent,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}




class report_emp_irregular_absent(models.AbstractModel):
    _name = 'report.sisb_hr.employee_irregular_absent_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.employee_irregular_absent_report'
    _wrapped_report_class = sisb_employee_irregular_absent_report