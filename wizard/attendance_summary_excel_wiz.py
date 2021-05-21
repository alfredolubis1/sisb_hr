from openerp import models, fields, api, _
from datetime import date, datetime, timedelta
import xlwt
import io
import base64
from cStringIO import StringIO
import calendar
from ..utility.utils import hour_float_to_time as hftt
from ..utility.utils import float_to_day_time as ftdt


class summary_attendance_excel_report(models.TransientModel):
    _name = "sum.att.xls.report"



    file = fields.Binary(string="Summary Attendance Report", readonly=True)
    name = fields.Char("File Name", readonly=True)




class summary_attendance_excel_report_wiz(models.TransientModel):
    _name = "summary.attendance.excel.report"

    name = fields.Char("Name")
    company_id = fields.Many2one('res.company', "Company", required=True)
    date_from = fields.Date("From", required=True)
    date_to = fields.Date("To", required=True)
    dept_ids = fields.Many2many('hr.department', string="Department", required=True)
    holiday_status_ids = fields.Many2many('hr.holidays.status', string="Holiday Type", required=True)
    



    @api.multi
    def check_holiday(self, department_id, day):
        now = date.today()
        dt_now = now.strftime('%Y-%m-%d')
        check = False
        if department_id:
            if department_id.public_holiday_type == ('public' or False):
                print('public_holiday')
                holiday = self.env['public.holidays.days'].search([])
                for hd in holiday:
                    if hd.name == day:
                        check = True
                    else:
                        check = False
            if department_id.public_holiday_type == 'school':
                academic_years_obj = self.env['academic.year'].search([('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.env['school.holidays'].search([('year_id','=', academic_years_obj.id)])
                if school_holiday:
                    for rec in school_holiday.line_ids:
                        if rec.date == day:
                            check = True
                else:
                    return False
            if department_id.public_holiday_type == 'both':
                holiday = self.env['public.holidays.days'].search([])
                for hd in holiday:
                    if hd.name == day:
                        check = True
                    else:
                        check = False
                academic_years_obj = self.env['academic.year'].search([('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.env['school.holidays'].search([('year_id','=', academic_years_obj.id)])
                if school_holiday:
                    for rec in school_holiday.line_ids:
                        if rec.date == day:
                            check = True
                else:
                    if check == True:
                        return check
                    else:
                        check = False
        return check
        
        

    @api.multi
    def check_leave(self, employee_id, day):
        self._cr.execute(""" SELECT id FROM hr_holidays 
                            WHERE employee_id = %s
                            AND date_from1 <= %s
                            AND date_to1 >= %s 
                            AND type = %s
                            """, (employee_id.id, day, day, 'remove'))
        leave_id = self._cr.fetchall()
        if leave_id:
            return True
        else:
            return False


    @api.multi
    def check_attendance(self, employee_id, day):
        att = False
        date_to_check = day.strftime('%Y-%m-%d')
        self._cr.execute(""" SELECT id FROM hr_attendance 
                        WHERE employee_id = %s 
                        AND name + INTERVAL '8 HOURS' >= %s
                        AND name + INTERVAL '8 HOURS' <= %s 
                        """, (employee_id.id, date_to_check + ' 00:00:00', date_to_check + ' 23:59:59'))
        att_id  = self._cr.fetchall()
        print('att_id = ', att_id)
        if att_id:
            att = True
        return att


    @api.multi
    def count_employee_absent(self, employee_id, date_from, date_to):
        FMT     = '%Y-%m-%d'
        start   = datetime.strptime(date_from, FMT)
        end     = datetime.strptime(date_to, FMT)
        step    = timedelta(days=1)
        now     = datetime.now()
        absent  = 0
        while (start <= end):
            day     = calendar.weekday(int(start.strftime("%Y")),int(start.strftime("%m")),int(start.strftime("%d")))
            str_date = start.strftime(FMT)
            if day == 6:
                start += step
                continue
            if start >= now:
                start += step
                continue
            check_attendance = self.check_attendance(employee_id, start)
            print('check_attendance = ', check_attendance)
            if check_attendance:
                print('21312')
                start += step
                continue
            if not check_attendance:
                print('alpha att')
                check_holiday = self.check_holiday(employee_id.department_id, day)
                if check_holiday:
                    start += step
                    continue
                if not check_holiday:
                    check_leave = self.check_leave(employee_id, start)
                    if check_leave:
                        start += step
                        continue
                    if not check_leave:
                        absent += 1
            start += step
        return absent


    @api.multi
    def count_emp_late_early(self, employee_id, date_from, date_to):
        late_early_dict = {}
        self._cr.execute("""SELECT COALESCE(SUM(late_duration), 0), count(*) 
                            FROM hr_attendance
                            WHERE employee_id = %s
                            AND name + INTERVAL'8 HOURS' >= %s
                            AND name + INTERVAL'8 HOURS' <= %s
                            AND late_duration > 0.0
                            """, (employee_id.id, date_from + ' 00:00:000', date_to + ' 23:59:59'))
        late_result = self._cr.fetchall()
        print('late_result = ', late_result)
        late_to_display = str(late_result[0][1]) + ' - ' + hftt(late_result[0][0])
        if late_to_display == '0 - 00:00':
            late_early_dict['late'] = ''
        else:
            late_early_dict['late'] = late_to_display
        late_early_dict['total_late'] = late_result[0][1]
        late_early_dict['length_late'] = late_result[0][0]
        self._cr.execute("""SELECT COALESCE(SUM(leave_early_duration), 0), count(*) 
                            FROM hr_attendance
                            WHERE employee_id = %s
                            AND name + INTERVAL'8 HOURS' >= %s
                            AND name + INTERVAL'8 HOURS' <= %s
                            AND leave_early_duration > 0.0
                            """, (employee_id.id, date_from + ' 00:00:000', date_to + ' 23:59:59'))
        leave_early_result = self._cr.fetchall()
        leave_early_to_display = str(leave_early_result[0][1]) + ' - ' + hftt(leave_early_result[0][0])
        if leave_early_to_display == '0 - 00:00':
            late_early_dict['leave_early'] = ''
        else:
            late_early_dict['leave_early'] = leave_early_to_display
        late_early_dict['total_leave_early'] = leave_early_result[0][1]
        late_early_dict['length_leave_early'] = leave_early_result[0][0]

        return late_early_dict


    @api.multi
    def count_leave(self, employee_id, date_from, date_to, leave_type_id):
        self._cr.execute(""" SELECT COALESCE(SUM(number_of_days), 0) FROM hr_holidays
                            WHERE holiday_status_id = %s
                            AND employee_id = %s
                            AND date_from1 >= %s
                            AND date_from1 <= %s
                            AND type = %s
                            """, (leave_type_id, employee_id.id, date_from, date_to, 'remove'))
        all_leave = self._cr.fetchall()
        print('all_leave = ', all_leave)
        res = ftdt(all_leave[0][0])
        if res == '0 - 00:00':
            res = ''
        return res

    @api.one
    def converse_late_early(self, total, length):
        res = ''
        total_string = str(total)
        result = '{0:02.0f}:{1:02.0f}'.format(*divmod(length * 60, 60))
        res = total_string + ' - ' + result
        return res


    @api.multi
    def print_report(self):
        self.ensure_one()
        print('ensure_one = ', self.ensure_one())
        context = dict(self._context or {})
        # Header Section
        date_from = self.date_from
        date_to = self.date_to
        now = datetime.now()
        date_now = now.strftime('%d/%b/%Y')
        time_now = now.strftime('%H:%M')
        year = now.strftime('%Y')
        company_name = self.company_id.name
        all_employee = self.env['hr.employee'].search([('company_id','=',self.company_id.id)])
        print('all_employee = ', all_employee)
        company_name = company_name.upper()
        dhm = 'Day - Hour:Minute'
        chm = 'Count - Hour:Minute'
        ##########################

        # Leave Section
        all_leave = self.env['hr.holidays.status'].search([])
        all_leave_name = []
        for leave in self.holiday_status_ids:
            if leave.name not in all_leave_name:
                all_leave_name.append(leave.name)
        
        # ########################3333 
        
        workbook = xlwt.Workbook()
        header1 = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, ,vert bottom ,horz centre')
        title1 = xlwt.easyxf('font: color black, name Arial; align: wrap yes, vert centre ,horz centre') 
        title_total = xlwt.easyxf('font: color black, name Arial; align: wrap yes, horz centre; pattern: pattern solid, fore_color gray40')
        name = xlwt.easyxf('font: color black, name Arial; align: wrap yes, ,vert centre ,horz left') 
        for dept in self.dept_ids:
            j = 0
            i = 0
            worksheet = workbook.add_sheet(dept.name)
            worksheet.write(0, j + 5, company_name, header1)
            worksheet.write(0, j + 10, date_now, title1)
            worksheet.write(1, j + 10, time_now, title1)
            worksheet.write(2, j + 5, str(date_from) + ' - ' + str(date_to) + ' Year ' + str(year), title1)
            worksheet.write(4, j + 2, dhm, title1)
            worksheet.write(4, j + 3, chm, title1)
            worksheet.write(4, j + 4, chm, title1)

            
            worksheet.col(0+j).width = 11000
            worksheet.col(1+j).width = 8000
            worksheet.col(2+j).width = 8000
            worksheet.col(3+j).width = 8000
            worksheet.col(4+j).width = 8000
            

            worksheet.row(5).height = 600
            worksheet.write(5, j + 1, 'Join Date', title1)
            worksheet.write(5, j + 2, 'Absent/Not Clock', title1)
            worksheet.write(5, j + 3, 'Late', title1)
            worksheet.write(5, j + 4, 'Leave Early', title1)
            j = 5
            all_leave_name.sort()
            print('all_leave_name = ', all_leave_name)
            for l in all_leave_name:
                if j == 5:
                    worksheet.col(j).width = 11000
                else:
                    worksheet.col(j).width = 8000
                worksheet.write(4, j, dhm, title1)
                worksheet.write(5, j, l, title1)
                j += 1
            worksheet.col(j+0).width = 8000
            worksheet.col(j+1).width = 10000
            worksheet.col(j+2).width = 8000
            worksheet.col(j+3).width = 8000
            worksheet.write(4, j + 0, 'Hour', title1)
            worksheet.write(4, j + 1, 'Hours', title1)
            worksheet.write(5, j + 0, 'Working Hours', title1)
            worksheet.write(5, j + 1, 'Absent + late + leave early + all leaves excl. annual leave', title1)
            worksheet.write(5, j + 2, '% Loss of worktime', title1)
            worksheet.write(5, j + 3, '% Remaining of worktime', title1)
            i = 7
            k = 0
            print('j = ', j)
            # Count Section
            absent = 0
            late_total = 0
            late_length_total = 0.00
            early_total = 0
            early_length_total = 0.00
            for employee in all_employee.filtered(lambda x: x.department_id == dept):
                count_employee_absent = self.count_employee_absent(employee, date_from, date_to)
                absent += count_employee_absent

                emp_late_early = self.count_emp_late_early(employee, date_from, date_to)
                late_total += emp_late_early['total_late']
                late_length_total += emp_late_early['length_late']
                early_total += emp_late_early['total_leave_early']
                early_length_total += emp_late_early['length_leave_early']



                late = emp_late_early['late']
                early = emp_late_early['leave_early']
                worksheet.write(i, k + 0, employee.employee_no + ' ' + employee.name, name)
                worksheet.write(i, k + 1, employee.join_date, title1)
                worksheet.write(i, k + 2, str(count_employee_absent) + ' - 00:00', title1)
                worksheet.write(i, k + 3, late, title1)
                worksheet.write(i, k + 4, early, title1)
                all_leave_name.sort()
                ls = 5
                for p in all_leave_name:
                    holiday_type_id = self.env['hr.holidays.status'].search([('name', '=', p)])
                    count_holiday = self.count_leave(employee, date_from, date_to, holiday_type_id.id)
                    worksheet.write(i, ls, count_holiday, title1)
                    ls += 1
                i += 1


            absent_to_display = str(absent) + ' - 00:00'
            late_to_display = self.converse_late_early(late_total, late_length_total)
            leave_early_to_display = self.converse_late_early(early_total, early_length_total)

            for t in range(0, (j + 4), 1):
                if t == 2:
                    worksheet.write(6, t, absent_to_display, title_total)
                elif t == 3:
                    worksheet.write(6, t, late_to_display, title_total)
                elif t == 4:
                    worksheet.write(6, t, leave_early_to_display, title_total)
                else:
                    worksheet.write(6, t, None, title_total)
                
        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        res = base64.encodestring(data)
        mod_rec = self.env['sum.att.xls.report'].create({'name': 'Summary Attendance Report.xls', 'file': res})
        return {
            'name': _('Summary Attendance Report'),
            'res_id' : mod_rec.id,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'sum.att.xls.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }



    