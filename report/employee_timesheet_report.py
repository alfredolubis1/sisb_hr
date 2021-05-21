from openerp import models
from openerp.report import report_sxw
import datetime
from datetime import date, datetime, timedelta
import dateutil.parser
import time
import calendar


class employee_timesheet_report(report_sxw.rml_parse):
    _name = 'report.sisb_hr.generate_timesheet_report'
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(employee_timesheet_report, self).__init__(cr, uid, name, context = context)
        self.localcontext.update({
            'get_data': self._get_data,
            'generate_date': self._generate_date,
        })

    def _get_data(self, form):
        data = []
        FMT = '%Y-%m-%d'
        year = datetime.now().year
        month = form['month']
        employee = form['employee_id']
        print('year = ', year)
        start = str(year) + '-' + str(month) + '-' + '01'
        start_date = datetime.strptime(start, FMT)
        start = start_date.strftime(FMT)
        print('start_date = ', start_date)
        end_date = start_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        print('end_date = ', end_date)
        end = end_date.strftime(FMT)
        step = timedelta(days=1)
        while (start_date <= end_date):
            sign_in = ''
            sign_out = ''
            start = start_date.strftime(FMT)
            self.cr.execute("SELECT name, sign_out FROM hr_attendance\
                            WHERE employee_id = %s\
                            AND name + INTERVAL '8 HOURS' >= %s\
                            AND name + INTERVAL '8 HOURS' <= %s\
                            ORDER BY id ASC\
                            ",(employee[0], start + ' 00:00:00', start + ' 23:59:59'))
            all_attendance = self.cr.fetchall()
            print('all_attendance = ', all_attendance)
            for att in all_attendance:
                sign_in = att[0]
                sign_out = att[1]
            result = {
                'date': start,
                'sign_in': sign_in or '',
                'sign_out': sign_out or '',
            }
            data.append(result)
            start_date += step
        if data:
            return data
        else:
            return {}

    def _generate_date(self, form):
        data = []
        FMT = '%Y-%m-%d'
        year = datetime.now().year
        month = form['month']
        employee = form['employee_id']
        print('year = ', year)
        start = str(year) + '-' + str(month) + '-' + '01'
        start_date = datetime.strptime(start, FMT)
        step = timedelta(days=1)
        print('start_date = ', start_date)
        end_date = start_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        print('end_date = ', end_date)
        while (start_date <= end_date):
            start = start_date.strftime(FMT)
            print('start_date = ', start_date)
            result = {
                'date': start
            }
            start_date += step
            data.append(result)
        if data:
            return data
        else:
            return {}
        

    # def _all_employee(self, form):
    #     data = []
    #     FMT = '%Y-%m-%d'
    #     company_id = form['company_id']
    #     self.cr.execute("""SELECT he.employee_no || ' ' || rr.name, hp.name, rco.name, he.join_date, he.gender, he.marital, rc.name, 
    #                         (SELECT DATE_PART('year', AGE((SELECT CURRENT_DATE::date), he.join_date))) || ' Years '|| 
    #                         CONCAT((SELECT DATE_PART('month', AGE((SELECT CURRENT_DATE::date), he.join_date))), ' Months') as "Year Of Service" FROM hr_employee he
    #                         LEFT JOIN resource_resource rr ON (rr.id = he.id)
    #                         LEFT JOIN res_company rc ON (rc.id = rr.company_id)
    #                         LEFT JOIN res_country rco ON (rco.id = he.country_id)
    #                         LEFT JOIN hr_position hp ON (hp.id = he.employee_position_id)
    #                         WHERE rr.active = true
    #                         AND rr.company_id = 1
    #                         ORDER BY rr.name;  
    #                     """,('true', company_id[0]))
    #     all_employee = self.cr.fetchall()
    #     print('all_employee =', all_employee)
    #     for emp in all_employee:
    #         join_date = ''
    #         if emp[3]:
    #             join_date_obj = datetime.strptime(emp[3], FMT)
    #             join_date = join_date_obj.strftime('%d/%b/%Y')

    #         gender = ''
    #         if emp[4] == 'male':
    #             gender = 'Male'
    #         elif emp[4] == 'female':
    #             gender = 'Female'

    #         marital = ''
    #         if emp[5] == 'single':
    #             marital = "Single"
    #         elif emp[5] == 'married':
    #             marital = 'Married'
    #         elif emp[5] == 'widower':
    #             marital = 'Widow'
    #         elif emp[5] == 'divorced':
    #             marital = 'Divorced'
    #         result = {
    #             'name': emp[0],
    #             'position': emp[1],
    #             'country': emp[2],
    #             'join_date': join_date,
    #             'gender': gender,
    #             'marital': marital,
    #             'company': emp[6],
    #             'yof': emp[7],
    #         }
    #         data.append(result)
    #     if data:
    #         return data
    #     else:
    #         return {}

class report_employee_timesheet(models.AbstractModel):
    _name = 'report.sisb_hr.generate_timesheet_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.generate_timesheet_report'
    _wrapped_report_class = employee_timesheet_report