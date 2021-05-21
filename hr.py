
from openerp import models, fields, api, _
from openerp import tools
from datetime import datetime, time, date
# import datetime
from dateutil.relativedelta import relativedelta
import calendar
from openerp.exceptions import ValidationError
from tzlocal import get_localzone
import pytz
from pytz import timezone
from openerp import SUPERUSER_ID
from .utility.utils import hour_float_to_time as hftt



class SISBHRDept(models.Model):
    _inherit = "hr.department"


    section = fields.Char("Section Name")
    email = fields.Char(string="Email")
    section_code = fields.Char("Section Code")
    department_code = fields.Char("Department Code")
    public_holiday_type = fields.Selection([
        ('public','Public Holiday'),
        ('school','School Holiday'),
        ('both','Both'),
    ], string="Holiday Type")
    leave_month_reset = fields.Selection([
        (1, 'January'), 
        (2, 'February'), 
        (3, 'March'), 
        (4, 'April'),
        (5, 'May'), 
        (6, 'June'), 
        (7, 'July'), 
        (8, 'August'),
        (9, 'September'), 
        (10, 'October'), 
        (11, 'November'), 
        (12, 'December')
    ], string="Leave Reset Month")

    @api.onchange('parent_id')
    def set_reset_leave_month(self):
        if self.parent_id:
            self.leave_month_reset = self.parent_id.leave_month_reset

        
                

class AllowanceType(models.Model):
    _name = "allowance.type"

    name = fields.Char("Name", required=True)
    salary = fields.Boolean("Salary", help="Tick this checkbox if this record use to indicate Salary")
    description = fields.Char("Description")


class AllowanceTypeLine(models.Model):
    _name = "allowance.type.line"

    employee_id = fields.Many2one('hr.employee', string="Employee", invisible="True")
    allow_type_id = fields.Many2one('allowance.type', string="Name")
    amount = fields.Integer("Amount")
    frequently = fields.Selection([
        ('daily','Daily'),
        ('one_time','One Time'),
        ('weekly','Weekly'),
        ('monthly','Monthly')
    ], string="Payment Frequently")
    gross_net = fields.Selection([
        ('gross','Gross'),
        ('net','Net'),
        ('basic','Basic')
    ], string="Type", required=True)    


class SISBOvertimeConfRequest(models.Model):
    _name = "hr.overtime.request"
    _inherit = 'mail.thread'
    _order = 'date desc'
    _description = "Overtime"

    name = fields.Char(string="Overtime Number", default="/", track_visibility="onchange")
    date = fields.Date("Date", default=date.today())
    employee_id = fields.Many2one('hr.employee', string="Employee")
    company_id = fields.Many2one('res.company', string="Company")
    rel_comp_id = fields.Many2one('res.company', related="company_id", string="Company")
    canceled_reason = fields.Char(string="Cancelled Reason")
    department_id = fields.Many2one('hr.department', string="Department")
    rel_dept_id = fields.Many2one('hr.department', related="department_id", string="Department")
    position_id = fields.Many2one('hr.position', string="Position")
    rel_position_id = fields.Many2one('hr.position', related="position_id",string="Position")
    refused_by_id = fields.Many2one('res.users', string="Refused By", readonly=True, track_visibility="onchange")
    refuse_reason = fields.Text(string="Refused Reason", readonly=True)
    request_line_ids = fields.One2many('hr.overtime.request.line','overtime_request_id', string="Request Line")
    notes = fields.Text(string="Notes")
    state = fields.Selection([
        ('draft','Draft'),
        ('cancel','Cancel'),
        ('refuse','Rejected'),
        ('to_approve','Waiting For Approval'),
        ('approved','Approved'),
    ],string="State", default="draft", track_visibility="onchange")
    approved = fields.Boolean("Approved")
    refused = fields.Boolean("Rejected")
    type = fields.Selection([
        ('add','Request'),
        ('allocated','Allocated')
    ], string="Overtime Type", invisible="1", default="add")
    approved_by_id = fields.Many2one('res.users', string="Approved By", readonly=True, track_visibility="onchange") 
    approved_date = fields.Date("Approved Date", readonly=True, track_visibility="onchange")
    total_overtime = fields.Float("Total Overtime", readonly=True, digits=(4,3))

    @api.model
    def create(self, vals):
        print('test = ',vals)
        seq_obj = self.env['ir.sequence']
        current_emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        # emp_prefix = self.env['hr.contract'].search([('employee_id', '=', vals.get('employee_id'))])
        # prefix = ''
        # if emp_prefix:
        #     for rec in emp_prefix:
        #         prefix = rec.name
        # if not prefix:
        default_seq = self.env['ir.sequence'].sudo().search([('code','=', self._name)], limit=1)
        if default_seq:
            default_seq.update({'prefix': 'OT/'})
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('hr.overtime.request') or '/'   
        # else:
        #     new_seq = self.env['ir.sequence'].search([('code','=', self._name)], limit=1)
        #     if new_seq:
        #         new_seq.update({'prefix': 'OT/'+ prefix + '/'})
        #     if vals.get('name', '/') == '/':
        #         vals['name'] = self.env['ir.sequence'].next_by_code('hr.overtime.request') or '/'
        print('sudo = ', SUPERUSER_ID)
        print('disnin')
        res = super(SISBOvertimeConfRequest, self).create(vals)
        return res
    
    @api.constrains('employee_id', 'request_line_ids')
    def forbis_non_eligible_emp(self):
        if self.employee_id:
            if self.employee_id.overtime == False:
                raise ValidationError(_("Cannot Request Overtime as Employee %s is not Eligible For Request Overtime")%(self.employee_id.name))
        if not self.request_line_ids:
            raise ValidationError(_("You must set at Least 1 Overtime Request"))

        
    @api.onchange('employee_id')
    def get_emp_dept_and_post(self):
        if self.employee_id:
            rec = {}
            schedule_domain = []
            for record in self.employee_id:
                self.department_id = record.department_id
                self.company_id = record.company_id
                self.position_id = record.employee_position_id
            for line in self.request_line_ids:
                # line.start_hour = self.employee_id.end_hour
                # line.schedule_id = self.employee_id.working_time_id.id
                line.employee_id = self.employee_id.id
                line.overtime_type_id = False
        if not self.employee_id:
            self.department_id  = False
            self.company_id     = False
            self.position_id    = False
            
            

    @api.model
    def default_get(self, fields):
        res = super(SISBOvertimeConfRequest, self).default_get(fields)
        vals = []
        now = datetime.now()
        dt_now = now.strftime('%Y-%m-%d')
        start_hour = 0
        end_hour = 0
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if 'employee_id' in fields:
            res.update({'employee_id': employee_id.id})
        if 'company_id' in fields:
            res.update({'company_id': employee_id.company_id.id})
        if 'department_id' in fields:
            res.update({'department_id': employee_id.department_id.id})
        if 'position_id' in fields:
            res.update({'position_id': employee_id.employee_position_id.id})
        if 'notes' in fields:
            res.update({'notes': 'S = OT Before, E = OT After, N = Normal, H = Holiday Shift, HD = Holiday Year'})
        return res


    @api.multi
    def check_holiday(self, employee_id):
        print('employee = ', employee_id)
        for rec in employee_id:
            pass

    @api.multi
    def compute_ot_hour(self):
        total_overtime = 0
        wk_time = {}
        ot_history_obj = self.env['hr.overtime.history'].search([('employee_id','=', self.employee_id.id)])
        all_req = []
        for rec in self.request_line_ids:
            for sched in rec.schedule_id:
                wk_time['punch_in'] = sched.punch_in
                wk_time['start_hour'] = sched.start_hour
                wk_time['end_hour'] = sched.end_hour
                wk_time['punch_out'] = sched.punch_out
            date_ot = rec.date_overtime
            date_ots = date_ot.split('-')
            date_ots[2] = date_ots[2].split(' ')
            a=date(int(date_ots[0]),int(date_ots[1]),int(date_ots[2][0]))
            if (wk_time['start_hour'] < rec.start_hour and wk_time['end_hour'] > rec.start_hour):
                raise ValidationError(_("Cannot generate OT with start Hour in range between Working Hour"))
            if rec.start_hour == rec.end_hour:
                raise ValidationError(_("You cannot request Overtime with start hour equal to end hour"))
            if rec.day_type != 'normal':
                for l in rec.overtime_type_id:
                    if l.start_type == 'before_start_wktime':
                        if rec.end_hour != wk_time['end_hour']:
                            raise ValidationError(_("You Set Overtime Type to S(OT Before)\n"
                                                    "Your End Hour must be {} according to the Schedule".format(hftt(wk_time['end_hour']))))
                        if rec.start_hour < wk_time['punch_in']:
                            max_ot = wk_time['start_hour'] - wk_time['punch_in']
                            raise ValidationError(_("Maximum for this overtime is {} Hour's\n"
                                                    "you set more than {} Hour's\n"
                                                    "From {} to {}".format(max_ot, max_ot, hftt(rec.start_hour), hftt(rec.end_hour))))
                        if rec.start_hour > wk_time['start_hour']:
                            raise ValidationError(_("You cannot Start OT after Schedule Start Hour"))
                    if l.start_type == 'after_end_wktime':
                        if rec.start_hour != wk_time['end_hour']:
                            raise ValidationError(_("Please Set the time According to your Work Time\n"
                                                    "({} - {})".format(hftt(wk_time['start_hour']), hftt(wk_time['end_hour']))))
                        if rec.end_hour > wk_time['punch_out']:
                            max_ot = wk_time['punch_out'] - wk_time['end_hour']
                            raise ValidationError(_("Maximum for this overtime is {} Hour's\n"
                                                    "you set more than {} Hour's\n"
                                                    "From {} to {}".format(max_ot, max_ot, hftt(rec.start_hour), hftt(rec.end_hour))))                               
            else:
                for max_amt in rec.overtime_type_id:
                    if max_amt.start_type == 'before_start_wktime':
                        if rec.start_hour > wk_time['start_hour']:
                            raise ValidationError(_("You cannot Start OT after Schedule Start Hour"))
                        if rec.end_hour != wk_time['start_hour']:
                            raise ValidationError(_("You Set Overtime Type to S(OT Before)\n"
                                                    "your End Hour must be {}".format(hftt(wk_time['start_hour']))))
                        if rec.start_hour < wk_time['punch_in']:
                            max_ot = wk_time['start_hour'] - wk_time['punch_in']
                            raise ValidationError(_("Maximum for this overtime is {} Hour's\n"
                                                    "you set more than {} Hour's\n"
                                                    "From {} to {}".format(max_ot, max_ot, hftt(rec.start_hour), hftt(rec.end_hour))))                            
                    if max_amt.start_type == 'after_end_wktime':
                        if rec.start_hour != wk_time['end_hour']:
                            raise ValidationError(_("Please Set the time According to your Work Time\n"
                                                    "({} - {})".format(hftt(wk_time['start_hour']), hftt(wk_time['end_hour']))))
                        if rec.end_hour > wk_time['punch_out']:
                            max_ot = wk_time['punch_out'] - wk_time['end_hour']
                            raise ValidationError(_("Maximum for this overtime is {} Hour's\n"
                                                    "you set more than {} Hour's\n"
                                                    "From {} to {}".format(max_ot, max_ot, hftt(rec.start_hour), hftt(rec.end_hour))))
            if rec not in all_req:
                all_req.append(rec)
            rec.hour_span = rec.end_hour - rec.start_hour
        y = 1
        for line in range(len(all_req)):
            for ot in self.request_line_ids.filtered(lambda x: x.id != all_req[line].id):
                if ot.date_overtime == all_req[line].date_overtime:
                    if ot.overtime_type_id == all_req[line].overtime_type_id:
                        raise ValidationError(_("You cannot have Overtime with same type in the same date"))
            same_ot = self.env['hr.overtime.request.line'].search([('date_overtime', '=', all_req[line].date_overtime),('overtime_type_id', '=', all_req[line].overtime_type_id.id),('id', '!=', all_req[line].id),('overtime_request_id','=',self.id)])
            print('same_ot = ', same_ot)
            if same_ot:
                raise ValidationError(_("Seem like you already take the same Time or Type in another Overtime Request Form\n Please Check Again"))
        
        return self.write({'state':'draft'})

    @api.multi
    def check_ot_form(self):
        if not self.request_line_ids:
            raise ValidationError(_("Please Set The Overtime Configuration First"))
        if self.request_line_ids:
            for rec in self.request_line_ids:
                if rec.start_hour == rec.end_hour:
                    raise ValidationError(_("OT Configuration is incorrect Start Hour Cannot be equal to End Hour"))


    @api.multi
    def check_supervisor(self):
        for rec in self.employee_id:
            if rec.supervisor_id:
                return rec.supervisor_id.work_email
            elif not rec.supervisor_id:
                if rec.supervisor_lvl2_id:
                    return rec.supervisor_lvl2_id.work_email
                elif not rec.supervisor_lvl2_id:
                    raise ValidationError ("This Employee Don't Have a Supervisor to send Overtime Request for Confirmation, Please ask you HR Managar to Set you Superisor")
    
    @api.multi
    def cancel_request(self):
        for rec in self.request_line_ids:
            rec.state = 'cancel'
        return self.write({'state': 'cancel'})


    @api.multi
    def confirm_request(self):
        self.check_ot_form()
        self.compute_ot_hour()
        self.check_supervisor()
        template = self.env['ir.model.data'].get_object('sisb_hr', 'request_overtime_from_employee')
        if template:
            mail_id = template.send_mail(self.id)
            mail = self.env['mail.mail'].browse(mail_id)
            if mail:
                mail.send()
        for rec in self.request_line_ids:
            rec.state = 'to_approve'
        return self.write({'state': 'to_approve'})

    @api.model
    def get_receiver(self, employee_id):
        for rec in employee_id:
            if rec.supervisor_id:
                return rec.supervisor_id.name
            elif not rec.supervisor_id:
                return rec.supervisor_lvl2_id.name
            else:
                return False

    @api.multi
    def approve_request(self): 
        history_obj = self.env['hr.overtime.history']
        curr_emp_ot_obj = self.env['employee.curr.overtime'] 
        employee_obj = self.env['hr.employee'].search([('id','=',self.employee_id.id)])
        self.check_ot_form()
        emp_ot = []
        for rec in self:
            for ot in rec.request_line_ids:
                ot.state = 'approved'
                history_obj.create({
                    'name': rec.name,
                    'desc': ot.name,
                    'employee_id': rec.employee_id.id,
                    'date_overtime': ot.date_overtime,
                    'start_hour': ot.start_hour,
                    'end_hour': ot.end_hour,
                    'ot_type_id': ot.overtime_type_id.id,
                    'ot_hour': ot.hour_span,
                    'type' : rec.type,
                    'state': ot.state,
                })
            rec.update({
                'approved_by_id': self._uid,
                'approved_date': date.today()
            })  

            
        template = self.env['ir.model.data'].get_object('sisb_hr', 'approved_request_overtime_from_employee')
        if template:
            print('self_id = ', self.id)
            mail_id = template.send_mail(self.id)
            print('mail_id 11 = ', mail_id)
            mail = self.env['mail.mail'].browse(mail_id)
            if mail:
                mail.send() 
                
        return self.write({'state': 'approved'})

    @api.multi
    def refuse_request(self):
        for rec in self:
            return {
                    'name'      : _('Set Employee Stage'),
                    'type'      : 'ir.actions.act_window',
                    'res_model' : 'hr.refused.request',
                    'view_type' : 'form',
                    'view_mode' : 'form',
                    'nodestroy' : True,
                    'context'   : {'default_employee_id': rec.employee_id.id},
                    'target'    : 'new',
                } 


    @api.multi
    def set_draft_button(self):
        return self.write({'state': 'draft'})


    @api.multi
    def get_url(self, emp_id, object):
        url_source = self.env['res.partner']
        url = url_source.get_url(emp_id, object)
        return url      




class SISBOvertimeLine(models.Model):
    _name = "hr.overtime.request.line"

    name = fields.Char(string="Description")
    start_hour = fields.Float(string="Start Hour")
    start_hour_display = fields.Float(string="Start Hour", related='start_hour')
    end_hour = fields.Float(string="End Hour")
    end_hour_display = fields.Float(string="End Hour", related='end_hour')
    date_overtime = fields.Date(string="Date")
    schedule_id = fields.Many2one('work.time.structure', string="Schedule")
    related_schedule_id = fields.Many2one('work.time.structure', string="Schedule", related="schedule_id")
    hour_span = fields.Float(string="OT Hours", readonly=True)
    overtime_request_id = fields.Many2one('hr.overtime.request', string='Overtime', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    start_type = fields.Selection([
        ('before_start_wktime','Before Start Work'),
        ('after_end_wktime','After End Work'),
        ('all_day','All Day')
    ], string="Type", help="E is the total overtime counted before you punch in, S is total overtime counted after the end of your working Schedule")
    overtime_type_id = fields.Many2one('overtime.type', string="Type", required=True)
    day = fields.Char("Day")
    day_related = fields.Char("Day", related="day")
    day_type = fields.Selection([
        ('normal','N'),
        ('weekend','H'),
        ('holiday','HD')
    ], string="OT Type", default='normal', required="1")
    # state = fields.Selection([
    #     ('draft','Draft'),
    #     ('cancel','Cancel')
    #     ('wait','Wait'),
    #     ('approved','Approved'),
    #     ('refused','Rejected')
    # ], string="State", default="draft")

    state = fields.Selection([
        ('draft','Draft'),
        ('cancel','Cancel'),
        ('refuse','Rejected'),
        ('to_approve','Waiting For Approval'),
        ('approved','Approved'),
    ],string="State", default="draft")

    @api.onchange('date_overtime')
    def get_emp_sched(self):
        hr_employee_obj = self.env['hr.employee']
        if self.date_overtime:
            date_to_take = datetime.strptime(self.date_overtime, '%Y-%m-%d')
            day = calendar.weekday(date_to_take.year, date_to_take.month, date_to_take.day)
            weekend = day if day > 4 else False
            holiday_shift = False
            sched_obj = self.env['hr.schedule.shift.list'].search([('employee_id', '=', self.employee_id.id), ('name', '=', self.date_overtime),('state', '=', 'submitted')])
            if not sched_obj:
                self.schedule_id = False
                raise ValidationError(_("Employee {} Has no Schedule For date {}".format(self.employee_id.name, self.date_overtime)))
            elif sched_obj:
                self.schedule_id = sched_obj.shift_id
            for rec in sched_obj.shift_id:
                for d in rec.day_of_wewks_ids.filtered(lambda x: int(x.day_of_week) == day):
                    holiday_shift = True if d.options == 'holiday' else False
            tz = sched_obj.shift_id.default_timezone
            curr_tz = pytz.timezone(tz)
            tz_time = datetime.now(curr_tz)
            check_hd = hr_employee_obj.check_holiday(self.employee_id, self.date_overtime)
            if holiday_shift and not check_hd:
                self.day = date_to_take.strftime('%A') + ' [H]'
                self.day_type = 'weekend'
            elif (not holiday_shift and check_hd) or (holiday_shift and check_hd):
                self.day = date_to_take.strftime('%A') + ' [HD]'
                self.day_type = 'holiday'
            elif not holiday_shift and not check_hd:
                self.day = date_to_take.strftime('%A') + ' [N]'
                self.day_type = 'normal'

            

    @api.constrains('start_hour','end_hour')
    def hour_rule(self):
        if self.end_hour < self.start_hour:
            raise ValidationError(_("End Hour must be greater than Start Hour"))
    
    @api.onchange('overtime_type_id', 'day_type')
    def ot_rule_onchange(self):
        if self.day_type != 'normal':
            if self.overtime_type_id.start_type == 'before_start_wktime':
                self.end_hour = self.schedule_id.end_hour
                self.start_hour = self.schedule_id.start_hour
            elif self.overtime_type_id.start_type == 'after_end_wktime':
                self.start_hour = self.schedule_id.end_hour
                self.end_hour = 0.00
            if not self.overtime_type_id:
                self.end_hour = 0.00
                self.start_hour = 0.00
                self.start_type = False
        else:
            if self.overtime_type_id.start_type == 'before_start_wktime':
                self.end_hour = self.schedule_id.start_hour
                self.start_hour = 0.00
            elif self.overtime_type_id.start_type == 'after_end_wktime':
                self.start_hour = self.schedule_id.end_hour
                self.end_hour = 0.00
            if not self.overtime_type_id:
                self.end_hour = 0.00
                self.start_hour = 0.00
                self.start_type = False






class overtime_history(models.Model):
    _name = "hr.overtime.history"
    _order = "date_overtime desc"
     
    name = fields.Char('Reference', readonly=True)
    desc = fields.Text('Description', readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    date_overtime = fields.Date(string="Date", readonly=True)
    ot_type_id = fields.Many2one('overtime.type', string="Overtime Type")
    start_hour = fields.Float(string="From", readonly=True)
    end_hour = fields.Float(string="To", readonly=True)
    ot_hour = fields.Float(string="OT Hours(Rounded)", readonly=True)
    state = fields.Selection([
        ('draft','Draft'),
        ('refuse','Rejected'),
        ('to_approve','Waiting For Approved'),
        ('approved','Approved'),
    ],string="State", default="draft", readonly=True)

class overtime_type(models.Model):
    _name = "overtime.type"

    name = fields.Char(string="Name")
    desc = fields.Text(string="Description")
    start_type = fields.Selection([
        ('before_start_wktime','OT Before'),
        ('after_end_wktime','OT After'),
        ('all_day','All Day')
    ], string="Type", help="E is the total overtime counted before you punch in, S is total overtime counted after the end of your working Schedule")


    

class employee_curr_ot(models.Model):
    _name = "employee.curr.overtime"
    _order = "name desc"

    name = fields.Date(string="Date")
    start_hour = fields.Float("Start")
    end_hour = fields.Float("End")
    desc = fields.Text(string="OT Description")
    hour_span = fields.Float("Total Overtime")
    ot_type_id = fields.Char(string="Type")
    employee_id = fields.Many2one(string="Employee")

class employee_job_line(models.Model):
    _name = "employee.job.detail.line"
    _order = "effective_date desc"

    name = fields.Char(string='Description')
    position_id = fields.Many2one('hr.position', string="Position")
    job_id = fields.Many2one('hr.job', string="Job")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    effective_date = fields.Date("Effective Date")
    type = fields.Selection([
        ('promotion',"Job Promotion"),
        ('reassign','Job Re-assignment'),
        ('transfer','Job Transfer')
    ], string="Type")

class sisb_employee_transfer(models.Model):
    _name = "hr.employee.transfer"
    _order = "tf_date desc"

    name = fields.Char(string="Transfer No")
    company_code = fields.Char("Company Code")
    tf_date = fields.Date(string="Date", default=date.today())
    job_id = fields.Many2one('hr.job', string="Job")
    related_job_id = fields.Many2one('hr.job', string="Job", related='job_id', readonly="True")
    position_id = fields.Many2one('hr.position', string="Position")
    related_position_id = fields.Many2one('hr.position', string="Position", related="position_id" ,readonly="True")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    related_employee_id = fields.Many2one('hr.employee', string="Employee", related='employee_id')
    department_id = fields.Many2one('hr.department', string="Department")
    related_department_id = fields.Many2one('hr.department', string="Department", related="department_id" ,readonly="True")
    company_id = fields.Many2one('res.company', string="Company/Campus")
    related_company_id = fields.Many2one('res.company', string="Company", related="company_id" ,readonly="True")
    company_destination_id = fields.Many2one('res.company', string="To Company")
    department_destination_id = fields.Many2one('hr.department', string="To Department")
    new_position_id = fields.Many2one('hr.position', string="To Position")
    new_job_id = fields.Many2one('hr.job', string="To Job")
    effective_date = fields.Date(string="Effective Date")
    notes = fields.Text(string="Notes")
    tf_boarding_list_ids = fields.One2many('hr.boarding.list.line', 'transfer_emp_id', string="Boarding List")
    application_source_id = fields.Many2one('hr.applicant', string="Applicant Source")
    generated = fields.Boolean(string="Board Item Generated")
    transfer_reason = fields.Many2one('hr.transfer.reason', string="Transfer Reason")
    state = fields.Selection([
        ('draft','Draft'),
        ('cancel','Cancelled'),
        ('submit','Submitted'),
        ('accept','Accept Transfer'),
        ('transferred','Transferred'),
    ], string="State", default='draft')
    

    @api.model
    def create(self, vals):
        print('vals = ', vals)
        if vals.get('name', '/') == '/' or False:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.transfer') or '/'
        res = super(sisb_employee_transfer, self).create(vals)
        print('vals2 = ', vals)
        return res

    @api.constrains('effective_date', 'state')   
    def forbid_without_eff_date(self):
        FMT = '%Y-%m-%d'
        now = datetime.now().date()
        print("now = ", now)
        string_now = now.strftime('%Y-%m-%d')
        print("string_now = ", string_now)
        effective_date = self.effective_date
        print('effective_date = ', effective_date)
        if self.effective_date:
            if datetime.strptime(effective_date, FMT) < datetime.now():
                raise ValidationError("Effective date must greater than Today")
            ed = self.effective_date
            ed_date = datetime.strptime(ed, FMT)
            if ed_date.day != 1:
                raise ValidationError(_("Effective Date must be in first date of the month"))


    @api.model
    def default_get(self, fields):
        res = super(sisb_employee_transfer, self).default_get(fields)
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if 'employee_id' in fields:
            res.update({'employee_id': employee_rec.id})
        return res

    @api.onchange('employee_id')
    def onchange_employee(self):
        if self.employee_id:
            self.position_id = self.employee_id.employee_position_id
            self.department_id = self.employee_id.department_id
            self.company_id = self.employee_id.company_id
            self.job_id = self.employee_id.job_id
            self.tf_boarding_list_ids = [(5,0,0)]

    @api.onchange('company_destination_id')
    def get_company_code(self):
        if self.company_destination_id:
            if self.company_destination_id.name == "SISB Public Company Limited":
                self.company_code = 'HQ'
            elif self.company_destination_id.name == "Singapore International School Thonburi":
                self.company_code = 'TH'
            elif self.company_destination_id.name == "Singapore International School Suvarnabhumi":
                self.company_code = 'SV'
            elif self.company_destination_id.name == "Singapore International School Bangkok":
                self.company_code = 'PU'
            elif self.company_destination_id.name == "Singapore International School Ekkamai":
                self.company_code = 'EK'
            elif self.company_destination_id.name == "Singapore International School Chiangmai":
                self.company_code = 'CH'


    @api.multi
    def generate_board_item(self):
        items = []
        for rec in self.employee_id:
            item = rec.boarding_list_ids
            if item:
                for i in item:
                    if i.id not in items:
                        items.append(i.id)
        if not items:
            print('disini')
            raise ValidationError(_("This Employee has no boarding item"))
        if self.tf_boarding_list_ids:
            print('disini1')
            return self.write({'tf_boarding_list_ids': [(6, 0, items)], 'generated': True})
        if not self.tf_boarding_list_ids:
            print('disini2')
            return self.write({'tf_boarding_list_ids': [(4, i, 0) for i in items], 'generated': True})

    @api.multi
    def print_tf_notif_form(self):
        data = self.read([])[0]
        datas = {
            'ids': [data['id']],
            'form': data,
            'model': 'hr.employee.transfer',
        }
        print('datas = ', data)
        return {'type': 'ir.actions.report.xml',
                'report_name': 'sisb_hr.personel_tf_notification_form',
                'datas': datas}

    

    @api.multi
    def staff_tf_checklist_form(self):
        data = self.read([])[0]
        datas = {
            'ids': [data['id']],
            'form': data,
            'model': 'hr.employee.transfer',
        }
        print('datas = ', data)
        return {'type': 'ir.actions.report.xml',
                'report_name': 'sisb_hr.staff_tf_checklist_form',
                'datas': datas}



    @api.multi
    def submit_tf(self):
        return self.write({'state':'submit'})
    
    @api.multi
    def cancel_tf(self):
        return self.write({'state':'cancel'})

    @api.multi
    def set_draft(self):
        return self.write({'state':'draft'})


    @api.multi
    def check_employee(self):
        for rec in self.employee_id:
            line = rec.boarding_list_ids.filtered(lambda x: x.is_received == True)
            if line:
                raise ValidationError(_("This Employee has boarding item, kindly to see it by click Generate Boarding Item button"))
            

    @api.model
    def cnfrmtion_wizard(self, no_boarding=False, no_change=False):
        print('no_boarding = ', no_boarding)
        print('self = ', self)
        return ({
            'name': 'Transfer Confirmation',
            'type'      : 'ir.actions.act_window',
            'res_model' : 'employee.transfer.confirmation',
            'view_mode': 'form',
            'context'   : {'default_name': self.employee_id.name},
            'view_type': 'form',
            'target': 'new'
        })

    @api.multi
    def tf_employee(self):
        job_obj = self.env['employee.job.detail.line']
        curr_job = job_obj.create({
                                'position_id': self.new_position_id.id,
                                'effective_date': datetime.now(),
                                'job_id': self.new_job_id.id,
                            })
        for rec in self.employee_id:
            rec.update({
                'employee_position_id': self.new_position_id.id,
                'department_id': self.department_destination_id.id,
                'company_id': self.company_destination_id.id,
                'job_hstry_ids': [(4, curr_job.id, 0)]
            })
        return self.write({'state':'transferred', 'notes': 'This Transfer is already Updated'})


    def update_employee_tf(self, cr, uid, ids, context=None):
        all_tf = self.pool.get('hr.employee.transfer').search(cr, uid, [('state','=','accept')], context=context)
        all_emp_tf = self.pool.get('hr.employee.transfer').browse(cr, uid, all_tf)
        job_obj = self.pool.get('employee.job.detail.line')
        now =datetime.now()
        now1 = pytz.timezone('Asia/Singapore')
        dt_now = now.strftime('%Y-%m-%d')
        items = []
        for rec in all_emp_tf:
            if rec:
                if rec.effective_date >= dt_now:
                    curr_job = job_obj.create(cr, uid, {
                                'position_id': rec.new_position_id.id,
                                'effective_date': datetime.now(),
                                'job_id': rec.new_job_id.id,
                                'employee_id': rec.employee_id.id,
                                }, context=context)
                    check_emp_company = rec.employee_id.user_id.company_ids
                    cmp_list = list(company.id for company in check_emp_company)
                    if rec.company_destination_id.id not in cmp_list:
                        rec.employee_id.user_id.company_ids = [(4, rec.company_destination_id.id, 0)]
                    rec.employee_id.update({
                                'employee_position_id': rec.new_position_id.id,
                                'department_id': rec.department_destination_id.id,
                                'company_id': rec.company_destination_id.id,
                                'job_hstry_ids': [(4, curr_job, 0)]
                                # 'boarding_list_ids': [(3, k , 0)for k in items]
                                })
                    return rec.write({'state': 'transferred', 'notes': 'This Transfer is already Updated'})
            




    @api.multi
    def accept_tf(self):
        items = []
        returned = []
        for rec in self:
            if not rec.tf_boarding_list_ids:
                print('sas')
                self.check_employee()
                return self.write({'state':'accept'})
            if rec.tf_boarding_list_ids:
                print('dasda')
                all_received_item = rec.tf_boarding_list_ids.filtered(lambda x: x.is_received == True)
                all_returned_item = rec.tf_boarding_list_ids.filtered(lambda x: x.is_returned == True)
                if len(all_received_item) != len(all_returned_item):
                    return self.cnfrmtion_wizard()
                elif len(all_received_item) == len(all_returned_item):
                    for employee in rec.employee_id:
                        employee.boarding_list_ids = [(3, k.id , 0)for k in all_returned_item]
                        employee.off_boarding_list_ids = [(4, i.id, 0)for i in all_returned_item]
                    return self.write({'state':'accept','notes': 'All the changes for this employee will be updated on the Effective Date'})
            #     items = rec.tf_boarding_list_ids.filtered(lambda x: x.is_returned == False and x.is_received == True)
            #     returned = rec.tf_boarding_list_ids.filtered(lambda x: x.is_returned == True)
            #     if items:
            #         self.cnfrmtion_wizard()
            #     if not items:
            #         self.write({'state':'accept'})
            # for employee in rec.employee_id:
            #     employee.boarding_list_ids = [(3, k.id , 0)for k in returned]
            #     employee.off_boarding_list_ids = [(4, i.id, 0)for i in returned]
            # if rec.application_source_id:
            #     for l in rec.application_source_id:
            #         l.write({'state': 'confirmed'})


class hr_transfer_reason(models.Model):
    _name = "hr.transfer.reason"

    name = fields.Char(string="Reason")

class overtime_list_line(models.Model):
    _name = "overtime.list.line"

    name            = fields.Date("Date")
    attendance_id   = fields.Many2one('hr.attendance', string="Attendance", ondelete='cascade')
    ot_time_in      = fields.Float('Time In')
    ot_time_out     = fields.Float('Time Out')
    ot_length       = fields.Float('OT Length')
    ot_rounded      = fields.Float('OT Rounded')
    start_ot        = fields.Float('Start')
    end_ot          = fields.Float('End')
    ot_type_id      = fields.Many2one('overtime.type', "Type")
    rate_one        = fields.Float(string="1")
    rate_one_half   = fields.Float(string="1.5")
    rate_double     = fields.Float(string="2")
    rate_triple     = fields.Float(string="3")
    overtime_rate = fields.Selection([
        ('one','1'),
        ('one_half','1.5'),
        ('double','2'),
        ('triple','3')
    ], string="Overtime Rate")


class inherit_mail_message(models.Model):
    _inherit = 'mail.message'
    _order = 'id asc'



class hr_contract_history(models.Model):
    _name = "hr.contract.history"
    _order = 'end_date desc'

    name = fields.Char("Contract Reference")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    contract_id = fields.Many2one('hr.contract', string="Contract")




class hr_information(models.Model):
    _name = "hr.information"

    name = fields.Char(string="Name", required=True)
    exp_notif = fields.Integer(string="Expired Notification", required=True, default=1)
    notes = fields.Text(string="Notes")


    @api.constrains('exp_notif')
    def forbid_zero_days(self):
        if self.exp_notif:
            if self.exp_notif <= 0:
                raise ValidationError("Expired Notification must be greater than 0")

    @api.model
    def default_get(self, fields):
        res = super(hr_information, self).default_get(fields)
        if 'notes' in fields:
            res.update({'notes': 'System Will send notification Email to employee based on Expired Notification days before Expired'})
        return res
    

class hr_information_line(models.Model):
    _name = 'hr.information.line'

    name = fields.Many2one('hr.information', string="Name")
    number = fields.Char(string="Number")
    exp_date = fields.Date(string="Expired Date")
    employee_id = fields.Many2one('hr.employee')

class inherit_hr_contract(models.Model):
    _inherit = 'hr.contract'

    contract_history_ids = fields.One2many('hr.contract.history', 'contract_id', string="Contract History")


    @api.one
    def check_prev_contract(self):
        self._cr.execute('SELECT id, date_start FROM hr_contract_history\
                          WHERE contract_id = %s\
                          ORDER BY date_start DESC',(self.id,))
        history_id = self._cr.fetchone()
        history_contract = self.env['hr.contract.history'].search([('id', '=', history_id[0])])
        return history_contract





    @api.one
    def renew_contract(self):
        for rec in self:
            if self.contract_history_ids:
                check_prev_contract = self.check_prev_contract()[0]
                print('check_prev_contract = ', check_prev_contract)
                if check_prev_contract.date_end > rec.date_start:
                    raise ValidationError(_("The date you set is less than the End Date Previous Contract For this Employee"))
                else:
                    self._cr.execute('INSERT INTO hr_contract_history (name, date_start, date_end, contract_id, employee_id)\
                                  VALUES (%s, %s, %s, %s, %s) RETURNING id',(rec.name, rec.date_start, rec.date_end, rec.id, rec.employee_id.id))
                    new_contract_id = self.self._cr.fetchall()
                    self.contract_history_ids = [(4, id, 0 ) for id in new_contract_id[0]]
            if not self.contract_history_ids:
                self._cr.execute('INSERT INTO hr_contract_history (name, date_start, date_end, contract_id, employee_id)\
                                  VALUES (%s, %s, %s, %s, %s) RETURNING id',(rec.name, rec.date_start, rec.date_end, rec.id, rec.employee_id.id))
                new_contract_id = self._cr.fetchall()
                print('new_contract_id = ', new_contract_id)
                self.contract_history_ids = [(4, id, 0 ) for id in new_contract_id[0]]
            return True



#Appraisals Structure For General Staff
class appraisals_form_structure_general(models.Model):
    _name = "appraisals.structure.general.staff"
    _order = "sequence asc"


    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Number in Report")
    points = fields.Integer(string="Points")
    importance = fields.Integer(string="Weighted by importance")
    general_kpi_line_ids = fields.One2many('general.staff.appraisals.kpi.line', 'general_appraisals_id', string="Key Performance Indicator") #kpi stands for Key Performance Indicator
    general_evaluation_line_ids = fields.One2many('general.staff.appraisals.evaluation.line', 'general_appraisals_id', string="Evaluation")
    general_criteria_line_ids = fields.One2many('general.staff.appraisals.criteria.line', 'general_appraisals_id', string="Criteria")

class general_staff_appraisals_kpi_line(models.Model):
    _name = "general.staff.appraisals.kpi.line"
    _order = "sequence asc" 

    name = fields.Char("Name")
    sequence = fields.Integer("Number in Report")
    general_appraisals_id = fields.Many2one('appraisals.structure.general.staff', string="Appraisals Structure")

class general_staff_appraisals_evaluation_line(models.Model):
    _name = "general.staff.appraisals.evaluation.line"
    _order = "sequence asc" 

    name = fields.Char("Name")
    sequence = fields.Integer("Level")
    general_appraisals_id = fields.Many2one('appraisals.structure.general.staff', string="Appraisals Structure")


class general_staff_appraisals_criteria_line(models.Model):
    _name = "general.staff.appraisals.criteria.line"
    _order = "sequence asc" 

    name = fields.Char("Name")
    sequence = fields.Integer("Level")
    general_appraisals_id = fields.Many2one('appraisals.structure.general.staff', string="Appraisals Structure")



###################################################

#Appraisals Structure For Non-General Staff
class appraisals_form_structure_non_general(models.Model):
    _name = "appraisals.structure.nongeneral.staff"
    _order = "sequence asc"


    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Number in Report")
    points = fields.Integer(string="Points")
    importance = fields.Integer(string="Weighted by importance")
    non_general_kpi_line_ids = fields.One2many('nongeneral.staff.appraisals.kpi.line', 'nongeneral_appraisals_id', string="Key Performance Indicator") #kpi stands for Key Performance Indicator
    non_general_evaluation_line_ids = fields.One2many('nongeneral.staff.appraisals.evaluation.line', 'nongeneral_appraisals_id', string="Evaluation")
    non_general_criteria_line_ids = fields.One2many('nongeneral.staff.appraisals.criteria.line', 'nongeneral_appraisals_id', string="Criteria")

class nongeneral_staff_appraisals_kpi_line(models.Model):
    _name = "nongeneral.staff.appraisals.kpi.line"
    _order = "sequence asc" 

    name = fields.Char("Name")
    sequence = fields.Integer("Number in Report")
    nongeneral_appraisals_id = fields.Many2one('appraisals.structure.nongeneral.staff', string="Appraisals Structure")

class nongeneral_staff_appraisals_evaluation_line(models.Model):
    _name = "nongeneral.staff.appraisals.evaluation.line"
    _order = "sequence asc" 

    name = fields.Char("Name")
    sequence = fields.Integer("Level")
    nongeneral_appraisals_id = fields.Many2one('appraisals.structure.nongeneral.staff', string="Appraisals Structure")


class nongeneral_staff_appraisals_criteria_line(models.Model):
    _name = "nongeneral.staff.appraisals.criteria.line"
    _order = "sequence asc" 

    name = fields.Char("Name")
    sequence = fields.Integer("Level")
    nongeneral_appraisals_id = fields.Many2one('appraisals.structure.nongeneral.staff', string="Appraisals Structure")
###################################################

class inherit_hr_position(models.Model):
    _inherit = 'hr.position'

    # job_position_id = fields.Many2one('hr.job', 'Job Parent')

    # @api.onchange('company_id', 'department_id')
    # def set_position(self):
    #     domain = {}
    #     dept = self.department_id.id
    #     comp = self.company_id.id
    #     school_id = 0
    #     for rec in self.company_id:
    #         for school in rec.school_ids.filtered(lambda x: x.name == rec.name):
    #             if school:
    #                 school_id = school.id
    #     all_job = self.env['hr.job'].search([('department_id', '=', dept), ('company_address_id', '=', school_id)])
    #     if all_job:
    #         all_job_id = []
    #         for job_id in all_job:
    #             all_job_id.append(job_id.id)
    #         return {'domain': {
    #                         'job_position_id': [('id','in',all_job_id)]
    #                         }
    #                 }
    #     else:
    #         return {'domain':
    #                 {
    #                     'job_position_id': [('id' ,'=', 0)]
    #                 }
    #                 }


class inherit_hr_authority_matrix(models.Model):
    _inherit = 'hr.authority.matrix'


class inherit_school_holidays_line(models.Model):
    _inherit = 'school.holidays.line'
    


class inherit_sisb_mail_log(models.Model):
    _inherit = 'sisb.mail.log'


class mail_notification(models.Model):
    _inherit = 'mail.notification'


    def get_signature_footer(self, cr, uid, user_id, res_model=None, res_id=None, context=None, user_signature=True):
        """ Format a standard footer for notification emails (such as pushed messages
            notification or invite emails).
            Format:
                <p>--<br />
                    Administrator
                </p>
                <div>
                    <small>Sent from <a ...>Your Company</a> using <a ...>TigernixERP</a>.</small>
                </div>
        """
        footer = ""
        if not user_id:
            return footer

        # add user signature
        user = self.pool.get("res.users").browse(cr, SUPERUSER_ID, [user_id], context=context)[0]
        if user_signature:
            if user.signature:
                signature = user.signature
            else:
                signature = "--<br />%s" % user.name
            footer = tools.append_content_to_html(footer, signature, plaintext=False)

        # add company signature
        if user.company_id.website:
            website_url = ('http://%s' % user.company_id.website) if not user.company_id.website.lower().startswith(('http:', 'https:')) \
                else user.company_id.website
            company = "<a style='color:inherit' href='%s'>%s</a>" % (website_url, user.company_id.name)
        else:
            company = user.company_id.name
        sent_by = _('Sent by %(company)s using %(odoo)s')

        signature_company = '<br /><small>%s</small>' % (sent_by % {
            'company': company,
            'odoo': "<a style='color:inherit' href='https://www.tigernix.com/'>TigernixERP</a>"
        })
        footer = tools.append_content_to_html(footer, signature_company, plaintext=False, container_tag='div')

        return footer