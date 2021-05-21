from openerp import models, fields, api, _
from datetime import datetime, date
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import pytz
from io import BytesIO as StringIO
import csv
import base64
import encodings
from .utility.utils import hour_float_to_time as hftt
from .utility.count_date import date_range


DAYOFWEEK_SELECTION = [('0','Monday'),
                       ('1','Tuesday'),
                       ('2','Wednesday'),
                       ('3','Thursday'),
                       ('4','Friday'),
                       ('5','Saturday'),
                       ('6','Sunday'),
]

class SISBWorkTimeConf(models.Model):
    _name = "working.time.conf"
    _description = "Configure Work Schedule"


    name = fields.Char(string="Group")
    wk_time_structure_ids = fields.One2many('work.time.line','wk_time_conf_id', string="Work Time")
    company_id = fields.Many2one('res.company', string="Company", required=True)
    department_id = fields.Many2one('hr.department', string="Department", required=True)
    default_timezone = fields.Selection(
        '_tz_get', string='Timezone')
    employee_ids = fields.Many2many('hr.employee', 'working_time_id', string="Employee's")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assign', 'Assigned'),
    ], string="State", default='draft')
    


    @api.multi
    def create(self, vals):
        pass

    @api.onchange('company_id')
    def set_employee(self):
        """This Function give domain to employee_ids based on employee company work for"""
        all_employee_with_grp = []
        all_wk_obj = self.env['working.time.conf'].search([('company_id', '=', self.company_id.id)])
        if self.company_id:
            emps = self.env['hr.employee'].search([('company_id', '=', self.company_id.id)])
            if all_wk_obj:
                for rec in all_wk_obj:
                    if rec.employee_ids:
                        for emp in rec.employee_ids:
                            if emp.id not in all_employee_with_grp:
                                all_employee_with_grp.append(emp.id)
            emps_domain = []
            for employee in emps:
                if employee.id not in emps_domain:
                    emps_domain.append(employee.id)

            res = [x for x in all_employee_with_grp + emps_domain if x not in all_employee_with_grp or x not in emps_domain]
            return {'domain': 
                    {'employee_ids': [('id', 'in', res)]}
                    }   

    @api.multi
    def check_all_sched(self):
        for rec in self.wk_time_structure_ids:
            if not rec.wk_time_structure_id:
                raise ValidationError(_("Please Set the Schedule From {} to {}".format(rec.date_from, rec.date_to)))


    @api.multi
    def set_work_schedule(self):
        """Set all the Employee inside employee_ids to have a work schedule based on where Admin/HR set it"""
        if not self.employee_ids:
            raise ValidationError(_("Please Fill The Employee's List First"))
        if not self.wk_time_structure_ids:
            raise ValidationError(_("Please Set Work Time Configuration"))
        self.check_all_sched()
        sched_obj = self.env['employee.schedule']
        for employees in self.employee_ids:
            for wk_time in self.wk_time_structure_ids:
                prev_sched = self.env['employee.schedule'].search([('employee_id','=',employees.id),('date_from','=',wk_time.date_from),('date_to','=',wk_time.date_to)])
                if prev_sched:
                    continue
                cross_check_sched = self.env['employee.schedule'].search([('employee_id','=',employees.id),('date_from','<',wk_time.date_from),('date_to','>',wk_time.date_to)])
                
                sched_id = sched_obj.create({
                    'name': self.name,
                    'company_id': employees.company_id.id,
                    'department_id': employees.department_id.id,
                    'date_from': wk_time.date_from,
                    'date_to': wk_time.date_to,
                    'schedule_type_id': wk_time.wk_time_structure_id.id,
                    'employee_id': employees.id,
                    'default_timezone': self.default_timezone,
                })
                detail_list = sched_id.create_sched_line()
                sched_id.update({'sched_detail_ids': [(6, 0 ,detail_list)]})
            
        return self.write({'state': 'assign'})

    # @api.multi
    # def create_sched_line(self):
    #     sched_line_obj = self.env['employee.schedule.line']
    #     vals = {}
    #     detail_list = []
    #     for rec in self:
    #         vals['employee_id'] = rec.employee_id
    #         for detail in rec.schedule_type_id:
    #             vals['start_hour']  = detail.start_hour
    #             vals['end_hour']    = detail.end_hour
    #             vals['start_break_hour']    = detail.start_break_hour
    #             vals['end_break_hour']  = detail.end_break_hour
    #             vals['late_tolerance']  = detail.late_tolerance
    #         d=rec.date_from
    #         dd=rec.date_to
    #         d1=d.split('-')
    #         d2=dd.split('-')
    #         d1[2]=d1[2].split(' ')
    #         d2[2]=d2[2].split(' ')
    #         a=datetime.date(int(d1[0]),int(d1[1]),int(d1[2][0]))
    #         b=datetime.date(int(d2[0]),int(d2[1]),int(d2[2][0]))
    #         for day in date_range(a, b, step=1):
    #             print('day = ', day)
    #             vals['date'] = day
    #             schd_detail = sched_line_obj.create(vals)
    #             detail_list.append(schd_detail.id)
    #     return detail_list

    @api.onchange('company_id')
    def get_rel_sched(self):
        sched_obj = self.env['work.time.structure']
        sched_list = []
        if self.company_id:
            sched = sched_obj.search([('company_id' ,'=', self.company_id.id)])
            for rec in sched:
                if rec.id not in sched_list:
                    sched_list.append(rec.id)
            for l in self.wk_time_structure_ids:
                return {
                    'domain':{
                        'l.wk_time_structure_id': [('id','in', sched_list)]
                    }
                }
            
            


    @api.multi
    def open_schedule_template_download_wizard(self):
        export_wiz_obj = self.env['export.employee.schedule.template.wiz']
        field_names = ['From', 'To', 'Shift Code']
        # field_names = ['identity_no', 'name', 'race_id', 'nationality_id', 'birthdate', 'gender',
        #                'highest_education_id',
        #                'designation_id', 'salary_range']
        streamfile = StringIO()  # Create a new StringIO object named streamfile
        writer = csv.writer(streamfile, quotechar="'" or '"', delimiter=',')  # Create a csv writer for the streamfile
        writer.writerow(field_names)  # Writes the field_names list as a csv row to the streamfile
        out = base64.b64encode(streamfile.getvalue().encode('UTF-8'))
        # Create a new wizard obj containing the b64-encoded data and it's file name
        new_wiz = export_wiz_obj.create({'data': out, 'filename': 'Employee_Schedule_Template.csv'})

        ir_model_data = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        act_id = False
        try:
            act_id = ir_model_data.get_object_reference('sisb_hr', 'action_view_export_employe_schedule_template_wiz')[1]
        except ValueError:
            act_id = False
        action = act_obj.browse(act_id)
        # print 'action 1:', action
        action = action.read()[0]
        view_id = False
        try:
            view_id = ir_model_data.get_object_reference('sisb_hr', 'export_employee_schedule_template_wiz_form_view')[1]
        except ValueError:
            view_id = False
        action['views'] = [(view_id, 'form')]
        action['res_id'] = new_wiz._ids[0]  # Inject the new wizard's id into the action
        # print 'action 2:', action

        return action


    @api.multi
    def undo_set_schedule(self):
        """This function undo all the employee that has related schedule to related object"""
        for employ in self.employee_ids:
            employ.update({
                'start_hour': 0.00,
                'end_hour': 0.00,
                'start_break_hour':0.00,
                'late_tolerance': 0.00,
                'end_break_hour': 0.00,
                'working_time_id':[(5,0)],
            })

    @api.multi
    def renew_work_schedule(self):
        return self.write({'state':'draft'})

    

    @api.model
    def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
        return [(tz,tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

    # @api.multi
    # def name_get(self):
    #     res = []
    #     for rec in self:
    #         name = "["+rec.code+"] " + rec.name
    #         res.append((rec.id, name))
    #     return res

# class SISBWorkTimeStructure(models.Model):
#     _name = "work.time.structure"

#     name                = fields.Char(string="Name")
#     shift_code          = fields.Char(string="Shift Code")
#     punch_in            = fields.Float(string="Punch In")
#     punch_out           = fields.Float(string="Punch Out")
#     start_hour          = fields.Float(string="Start")
#     end_hour            = fields.Float(string="End")
#     start_break_hour    = fields.Float(string="Start Break")
#     end_break_hour      = fields.Float(string="End Break")
#     total_break         = fields.Float(string="Total Break")
#     total_wk_hour       = fields.Float(string="Total Work Hours")
#     late_tolerance      = fields.Float(string="Late Tolerance")
#     company_id          = fields.Many2one('res.company', string="Company")
#     shift_option        = fields.Selection([
#                                            ('normal','Normal'),
#                                            ('night','Night Shift'),
#                                            ('half','Half Day')
#                                             ], string="Type", default='normal')
                                            

#     notes = fields.Text(string="Notes")
#     ## Day Name
#     day_of_wewks_ids = fields.One2many('day.of.week', 'work_time_id', string="Day of Week")
#     # monday = fields.Boolean(string="Monday")
#     # tuesday = fields.Boolean(string="Tuesday")
#     # wednesday = fields.Boolean(string="Wednesday")
#     # thursday = fields.Boolean(string="Thursday")
#     # friday = fields.Boolean(string="Friday")
#     # saturday = fields.Boolean(string="Saturday")
#     # sunday = fields.Boolean(string="Sunday")



#     @api.model
#     def default_get(self, fields):
#         res = super(SISBWorkTimeStructure, self).default_get(fields)
#         # emp_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
#         if 'notes' in fields:
#             res.update({'notes': "N =  Normal work Day, H = Holiday. if there's day not appear in the above list, system will set it as a Holiday in this Schedule"})
#         return res

#     @api.constrains('start_hour','end_hour','start_break_hour','end_break_hour','shift_option')
#     def hour_rule(self):
#         if self.shift_option != 'night':
#             if self.start_hour >= self.end_hour:
#                 raise ValidationError(_("Start Hour cannot be greater than End Hour"))
#         # if self.start_break_hour >= self.end_break_hour:
#         #     raise ValidationError(_("Start Break Hour cannot be greater than End Break Hour"))



#     @api.multi
#     def name_get(self):
#         res = []
#         for rec in self:
#             name = rec.name
#             start = hftt(rec.start_hour)
#             end = hftt(rec.end_hour)
#             res.append((rec.id, "%s [%s - %s]" %(name, start,end)))
#         return res

# class day_of_week(models.Model):
#     _name = "day.of.week"

#     day_of_week = fields.Selection(DAYOFWEEK_SELECTION, 'Day of Week')
#     options = fields.Selection([
#         ('normal','N'),
#         ('holiday','H')
#     ], string="Options", required=True)
#     work_time_id = fields.Many2one('work.time.structure', string="Work Time")

class sisb_employee_schedule(models.Model):
    _name = "employee.schedule"

    name = fields.Char(string="Schedule Name")
    company_id = fields.Many2one('res.company', string="Company")
    department_id = fields.Many2one('hr.department', string="Department")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    schedule_type_id = fields.Many2one('work.time.structure', string="Schedule Type")
    sched_detail_ids = fields.One2many('employee.schedule.line', 'schedule_id', string="Schedule List")
    default_timezone = fields.Selection(
        '_tz_get', string='Timezone')
    

    @api.model
    def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
        return [(tz,tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

        
    @api.model
    def default_get(self, fields):
        res = super(sisb_employee_schedule, self).default_get(fields)
        emp_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if 'employee_id' in fields:
            res.update({'employee_id': emp_id.id})
        return res

    @api.constrains('date_from','date_to')
    def sched_date_rule(self):
        if self.date_from > self.date_to:
            raise ValidationError(_("Start Date cannnot be greater than End Date"))

    @api.onchange('employee_id')
    def emp_onchange(self):
        if self.employee_id:
            self.company_id = self.employee_id.company_id.id
            self.department_id = self.employee_id.department_id.id
        if self.employee_id == False or None or 0:
            self.company_id = False or 0
            self.department_id = False or 0

    @api.multi
    def call_wizard(self):
        context = self._context
        print('context = ', context)
        return {
            'name'      : ("Add Schedule Manual"),
            'type'      : 'ir.actions.act_window',
            'res_model' : 'employee.add.schedule',
            'view_type' : 'form',
            'view_mode' : 'form',
            'context'   : {'default_employee_id': self.employee_id.id,
                           'default_sched_id': self.id},
            'target'    : 'new',
        }
        
        

    @api.multi
    def create_sched_line(self):
        sched_line_obj = self.env['employee.schedule.line']
        vals = {}
        detail_list = []
        for rec in self:
            vals['employee_id'] = rec.employee_id.id
            vals['default_timezone'] = rec.default_timezone
            for detail in rec.schedule_type_id:
                vals['start_hour']  = detail.start_hour
                vals['end_hour']    = detail.end_hour
                vals['start_break_hour']    = detail.start_break_hour
                vals['end_break_hour']  = detail.end_break_hour
                vals['late_tolerance']  = detail.late_tolerance
            d=rec.date_from
            dd=rec.date_to
            for day in date_range(rec.date_from, rec.date_to, step=1):
                vals['date'] = day
                avoid_override = sched_line_obj.search([('employee_id','=',vals['employee_id']),('date','=', datetime.strftime(vals['date'], '%Y-%m-%d'))])
                if avoid_override:
                    continue
                schd_detail = sched_line_obj.create(vals)
                detail_list.append(schd_detail.id)
        return detail_list


class employee_add_schedule(models.Model):
    _name = "employee.add.schedule"

    sched_id = fields.Many2one('employee.schedule', string="Schedule")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    sched_line_ids = fields.One2many('employee.schedule.line', 'sched_id', string="Schedule List")

    @api.multi
    def button_create_new_sched(self):
        last_employee_sched = self.env['employee.schedule.line'].search([('employee_id', '=', self.employee_id.id)], limit=1, order="date DESC")
        print('all_employee_sched = ', all_employee_sched)
        for sched in self.sched_line_ids:
            if sched.date < last_employee_sched:
                raise ValidationError("You cannot Add new Schedule with date overlaps the exist date")
            else:
                sched.schedule_id = self.sched_id
                sched.employee_id = self.employee_id

class employee_schedule_line(models.Model):
    _name = "employee.schedule.line"

    name = fields.Char("Schedule Name")
    date = fields.Date("Date")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    schedule_id = fields.Many2one('employee.schedule', string="Schedule Parent",  ondelete='cascade')
    sched_id = fields.Many2one('employee.add.schedule', string="Sched", ondelete='cascade')
    start_hour = fields.Float(string="Start Hour")
    end_hour = fields.Float(string="End Hour")
    start_break_hour = fields.Float(string="Start Break Hour")
    end_break_hour = fields.Float(string="End Break Hour")
    late_tolerance = fields.Float(string="Late Tolerance")
    default_timezone = fields.Selection(
        '_tz_get', string='Timezone')


    @api.model
    def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
        return [(tz,tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]



    # @api.multi
    # def button_create_new_sched(self):
    #     last_employee_sched = self.env['employee.schedule.line'].search([('employee_id', '=', self.employee_id.id)], limit=1, order="date DESC")
    #     print('all_employee_sched = ', all_employee_sched)
    #     for sched in self.sched_line_ids:
    #         if sched.date < last_employee_sched:
    #             raise ValidationError("You cannot Add new Schedule with date overlaps the exist date")
    #         else:
    #             sched.schedule_id = self.sched_id
    #             sched.employee_id = self.employee_id

class SISBWorkTimeLine(models.Model):
    _name = "work.time.line"
    _order = "date_from desc"

    
    date_from = fields.Date("From")
    date_to = fields.Date("To")
    wk_time_structure_id = fields.Many2one('work.time.structure', string="Schedule Name")
    wk_time_conf_id = fields.Many2one('working.time.conf', string="Configuration")

    @api.constrains('date_from','date_to')
    def date_constrains(self):
        if self.date_from > self.date_to:
            raise ValidationError(_("Date To must be greater than date From"))

