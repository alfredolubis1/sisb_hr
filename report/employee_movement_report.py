from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar
from openerp.exceptions import ValidationError






class employee_individual_movement_report(report_sxw.rml_parse):
    _name = 'report.sisb_hr.employee_individual_detailed_movement_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(employee_individual_movement_report, self).__init__(cr, uid, name, context = context)
        print('context = ', context)
        self.localcontext.update({
            'get_section_code': self._get_section_code,
            'get_history_data': self._get_history_data,
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


    def _get_history_data(self, form):
        data = []
        date_from = form['date_from']
        date_to = form['date_to']
        employee = form['employee_id']
        self.cr.execute("SELECT id FROM hr_employee_transfer\
                        WHERE effective_date >= %s\
                        AND effective_date <= %s\
                        AND employee_id = %s\
                        AND state = %s\
                        ORDER BY id ",(date_from, date_to, employee[0], 'transferred'))
        all_history_tf = self.cr.fetchall()
        print('all_history_tf = ', all_history_tf)
        if not all_history_tf:
            raise ValidationError('There is no Transfer Data for this')
        all_ht_id = self.pool.get('hr.employee.transfer').browse(self.cr, self.uid, all_history_tf[0])
        print('all_ht_id = ', all_ht_id)
        for ht in all_ht_id:
            effective_date = datetime.strptime(ht.effective_date, '%Y-%m-%d')
            result = {
                'name': str(ht.employee_id.employee_no) + ' ' + str(ht.employee_id.name),
                'effective_date': effective_date.strftime('%d/%b/%Y'),
                '1st_company': ht.company_id.name,
                '1st_department': ht.department_id.name,
                '1st_position': ht.position_id.name,
                '2nd_company': ht.company_destination_id.name,
                '2nd_department': ht.department_destination_id.name,
                '2nd_position': ht.new_position_id.name,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}


class report_individual_emp_movement(models.AbstractModel):
    _name = 'report.sisb_hr.employee_individual_detailed_movement_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.employee_individual_detailed_movement_report'
    _wrapped_report_class = employee_individual_movement_report




    
class detail_summary_employee_movement_report(report_sxw.rml_parse):
    _name = 'report.sisb_hr.summary_employee_movement_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(detail_summary_employee_movement_report, self).__init__(cr, uid, name, context = context)
        print('context = ', context)
        self.localcontext.update({
            'get_section_code': self._get_section_code,
            'get_transfer_summary_data': self._get_transfer_summary_data_by_employee,
            'get_transfer': self._get_transfer,
            # 'get_history_data': self._get_history_data,
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


    def _get_transfer_summary_data_by_employee(self, form):
        data = []
        date_from = form['date_from']
        date_to = form['date_to']
        employee_obj = self.pool.get('hr.employee').search(self.cr, self.uid, [])
        employee_id = self.pool.get('hr.employee').browse(self.cr, self.uid, employee_obj)
        for rec in employee_id:
            self.cr.execute("SELECT id FROM hr_employee_transfer\
                             WHERE employee_id = %s\
                             AND effective_date <= %s\
                             AND effective_date >= %s \
                             AND state = %s \
                             ORDER BY effective_date", (rec.id, date_to, date_from, 'transferred'))
            employee = self.cr.fetchall()
            print('Employee = ', employee)
            if employee:
                name = str(rec.employee_no) + ' ' + str(rec.name)
                result = {
                    'name': name,
                    'employee_id': rec.id,
                    'transfer_obj': employee[0],
                }
                data.append(result)
            if not employee:
                continue
        if data:
            return data
        else:
            return {}

    def _get_transfer(self, transfer_obj):
        data = []
        print('transfer_obj = ', transfer_obj)
        transfer_obj = self.pool.get('hr.employee.transfer').search(self.cr, self.uid, [('id', 'in', transfer_obj)])
        all_transfer_id = self.pool.get('hr.employee.transfer').browse(self.cr, self.uid, transfer_obj)
        for tf in all_transfer_id:
            effective_date = datetime.strptime(tf.effective_date, '%Y-%m-%d')
            result = {
                'name': str(tf.employee_id.employee_no) + ' ' + str(tf.employee_id.name),
                'effective_date': effective_date.strftime('%d/%b/%Y'),
                '1st_company': tf.company_id.name,
                '1st_department': tf.department_id.name,
                '1st_position': tf.position_id.name,
                '2nd_company': tf.company_destination_id.name,
                '2nd_department': tf.department_destination_id.name,
                '2nd_position': tf.new_position_id.name,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}


class report_summary_emp_movement(models.AbstractModel):
    _name = 'report.sisb_hr.summary_employee_movement_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.summary_employee_movement_report'
    _wrapped_report_class = detail_summary_employee_movement_report