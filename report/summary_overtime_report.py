from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar
from .. utility.utils import hour_float_to_time as hftt

class employee_summary_overtime_report(report_sxw.rml_parse):
    _name = 'report.sisb_hr.employee_summary_overtime'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(employee_summary_overtime_report, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'get_emp_overtime': self._get_emp_overtime,
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

    def _get_emp_overtime(self, form):
        data = []
        emp_obj = self.pool.get('hr.employee')
        date_from = form['date_from']
        print('date_from')
        date_to = form['date_to']
        company_id = form['company_id']
        all_day = emp_obj.delta_days(self.cr, self.uid, date_from, date_to)
        all_emp_obj = self.pool.get('hr.employee').search(self.cr, self.uid, [('company_id', '=', company_id[0]),('active','=','True')], order="name ASC")
        print('all_emp_obj =', all_emp_obj)
        all_emp_id = self.pool.get('hr.employee').browse(self.cr, self.uid, all_emp_obj)
        for emp in all_emp_id:
            ot_total = one = one_half = double = two_half = triple = ''
            emp_name = emp.employee_no + ' ' + emp.name
            self.cr.execute("SELECT id FROM hr_attendance\
                        WHERE overtime = true\
                        AND employee_id = %s \
                        AND name + INTERVAL '8 HOURS' >= %s \
                        AND name + INTERVAL '8 HOURS' <= %s \
                        AND sign_out IS NOT NULL\
                        ", (emp.id, date_from + ' 00:00:00', date_to + ' 23:59:59'))
            overtime = self.cr.fetchall()
            total_ot = 0.00
            rate_one = 0.00
            rate_one_half = 0.00
            rate_double = 0.00
            rate_two_half = 0.00
            rate_triple = 0.00
            if overtime:
                emp_ot = []
                for ot_id in overtime:
                    emp_ot.append(ot_id[0])
                print('emp_ot = ', emp_ot)
                emp_ot = self.pool.get('hr.attendance').browse(self.cr, self.uid, emp_ot)
                for ots in emp_ot:
                    for ot in ots.overtime_ids:
                        rate_one += ot.rate_one
                        rate_one_half += ot.rate_one_half
                        rate_double += ot.rate_double
                        rate_triple += ot.rate_triple
            total_ot  = rate_one + rate_one_half + rate_double + rate_two_half + rate_triple
            if total_ot > 0:
                ot_total = hftt(total_ot)
            if rate_one > 0:
                one = hftt(rate_one)
            if rate_one_half > 0:
                one_half = hftt(rate_one_half)
            if rate_double > 0:
                double = hftt(rate_double)
            if rate_two_half > 0:
                two_half = hftt(rate_two_half)
            if rate_triple > 0:
                triple = hftt(rate_triple)
            result = {
                'name': emp_name,
                'rate_one': one,
                'rate_one_half': one_half,
                'rate_double': double,
                'rate_two_half': two_half,
                'rate_triple': triple,
                'ot_total': ot_total
            }
            data.append(result)
        if data:
            return data
        else:
            return {}




class summary_overtime_report(models.AbstractModel):
    _name = 'report.sisb_hr.employee_summary_overtime'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.employee_summary_overtime'
    _wrapped_report_class = employee_summary_overtime_report