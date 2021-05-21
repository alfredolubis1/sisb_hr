from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar


class report_years_of_service(report_sxw.rml_parse):
    _name = 'report.sisb_hr.years_of_service_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(report_years_of_service, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'get_section_code': self._get_section_code,
            'all_employee': self._all_employee,
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

    def _all_employee(self, form):
        data = []
        FMT = '%Y-%m-%d'
        company_id = form['company_id']
        company_ids = form['company_ids']
        from_year_th = form['from_year_th']
        to_year_th = form['to_year_th']
        print('form = ', form)
        all_employee = ''
        if form['options'] == 'one_comp':
            self.cr.execute("""SELECT he.employee_no || ' ' || rr.name, hp.name, rco.name, he.join_date, he.gender, he.marital, rc.name, 
                                (SELECT DATE_PART('year', AGE((SELECT CURRENT_DATE::date), he.join_date))) || ' Years '|| 
                                CONCAT((SELECT DATE_PART('month', AGE((SELECT CURRENT_DATE::date), he.join_date))), ' Months') as "Year Of Service" FROM hr_employee he
                                LEFT JOIN resource_resource rr ON (rr.id = he.id)
                                LEFT JOIN res_company rc ON (rc.id = rr.company_id)
                                LEFT JOIN res_country rco ON (rco.id = he.country_id)
                                LEFT JOIN hr_position hp ON (hp.id = he.employee_position_id)
                                WHERE rr.active = %s
                                AND rr.company_id = %s
                                AND DATE_PART('year', AGE((SELECT CURRENT_DATE::date), he.join_date)) >= %s
                                AND DATE_PART('year', AGE((SELECT CURRENT_DATE::date), he.join_date)) <= %s
                                ORDER BY rr.name;  
                            """,('true', company_id[0], from_year_th, to_year_th))
            all_employee = self.cr.fetchall()
        elif form['options'] == 'multi_comp':
            self.cr.execute("""SELECT he.employee_no || ' ' || rr.name, hp.name, rco.name, he.join_date, he.gender, he.marital, rc.name, 
                                (SELECT DATE_PART('year', AGE((SELECT CURRENT_DATE::date), he.join_date))) || ' Years '|| 
                                CONCAT((SELECT DATE_PART('month', AGE((SELECT CURRENT_DATE::date), he.join_date))), ' Months') as "Year Of Service" FROM hr_employee he
                                LEFT JOIN resource_resource rr ON (rr.id = he.id)
                                LEFT JOIN res_company rc ON (rc.id = rr.company_id)
                                LEFT JOIN res_country rco ON (rco.id = he.country_id)
                                LEFT JOIN hr_position hp ON (hp.id = he.employee_position_id)
                                WHERE rr.active = %s
                                AND rr.company_id in %s
                                AND DATE_PART('year', AGE((SELECT CURRENT_DATE::date), he.join_date)) >= %s
                                AND DATE_PART('year', AGE((SELECT CURRENT_DATE::date), he.join_date)) <= %s
                                ORDER BY rr.name;  
                            """,('true', tuple(company_ids), from_year_th, to_year_th))
            all_employee = self.cr.fetchall()
        print('all_employee =', all_employee)
        for emp in all_employee:
            join_date = ''
            if emp[3]:
                join_date_obj = datetime.strptime(emp[3], FMT)
                join_date = join_date_obj.strftime('%d/%b/%Y')

            gender = ''
            if emp[4] == 'male':
                gender = 'Male'
            elif emp[4] == 'female':
                gender = 'Female'

            marital = ''
            if emp[5] == 'single':
                marital = "Single"
            elif emp[5] == 'married':
                marital = 'Married'
            elif emp[5] == 'widower':
                marital = 'Widow'
            elif emp[5] == 'divorced':
                marital = 'Divorced'
            result = {
                'name': emp[0],
                'position': emp[1],
                'country': emp[2],
                'join_date': join_date,
                'gender': gender,
                'marital': marital,
                'company': emp[6],
                'yof': emp[7],
            }
            data.append(result)
        if data:
            return data
        else:
            return {}

class report_employee_years_of_service(models.AbstractModel):
    _name = 'report.sisb_hr.years_of_service_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.years_of_service_report'
    _wrapped_report_class = report_years_of_service