from openerp import api, fields, models, _
from datetime import date, datetime
import time
import datetime
import calendar
from openerp.exceptions import ValidationError, AccessError
from openerp.osv import osv

from .utility.utils import hour_float_to_time as hftt
from openerp import SUPERUSER_ID
class sisb_holidays(models.Model):
    _inherit = "hr.holidays"

    # @api.one
    # def _get_can_reset(self):
    #     """User can reset a leave request if it is its own leave request or if
    #     he is an Hr Manager. """
    #     user = self.env['res.users'].search([('id','=',self.env.uid)])
    #     group_hr_manager_id = self.env['ir.model.data'].get_object_reference('base', 'group_hr_manager')[1]
    #     group_hr_officer = self.env['ir.model.data'].get_object_reference('base', 'group_hr_user')[1]
    #     if (group_hr_manager_id in [g.id for g in user.groups_id]) or (group_hr_officer in [g.id for g in user.groups_id]):
    #         return dict.fromkeys(self.ids, True)
    #     result = dict.fromkeys(self.ids, False)
    #     for holiday in self:
    #         if holiday.employee_id and holiday.employee_id.user_id and holiday.employee_id.user_id.id == uid:
    #             result[holiday.id] = True
    #     return result
    name                        = fields.Char(string="Reason", size=64)
    manager_id                  = fields.Many2one('hr.employee', string="Holiday Manager", readonly=True, default=lambda self: False)
    first_approve               = fields.Many2one('res.users', string="First Approved By")
    reset_id                    = fields.Many2one('reset.leaves', string="Reset")
    date_from                   = fields.Datetime("From", default=None)
    date_to                     = fields.Datetime("To", default=None)
    date_from1                  = fields.Date("From", required=True)
    date_to1                    = fields.Date("To", required=True)
    total_part                  = fields.Integer(string="Total Part Leave", readonly="True")
    type                        = fields.Selection([
                                ('remove','Leave Request'),
                                ('add','Allocation Request'),
                                ('allocated','Allocated Leave'),
                                ('claim','Claim Leave'),
                                ('expired','Expired')
                                ], 'Request Type', required=True, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, help="Choose 'Leave Request' if someone wants to take an off-day. \nChoose 'Allocation Request' if you want to increase the number of leaves available for someone", select=True)
    leave_balance_ids           = fields.One2many('hr.holidays.leaves.balance', 'holiday_id', string="Leave Info")
    department_id               = fields.Many2one('hr.department', string="Department", readonly=False)
    supervisor_id               = fields.Many2one('hr.employee', string="Supervisor I", store=True)
    supervisor_lvl2_id          = fields.Many2one('hr.employee', string="Supervisor II", store=True)
    attachment_file             = fields.Binary(string="Attachment")
    first_approve_date          = fields.Date(string="First Approved Date")
    allocation_run_id           = fields.Many2one('allocate.leaves.run', string="Allocated From")
    reason_of_claim             = fields.Selection([
                                ('company_request','Due to Company Request'),
                                ('not_used','Due to it has not been used/will of own accord')
                                ], string="Reason of Claim")
    claim_leave_balance         = fields.Float(related='display_claim_leave_balance', string="Claim Leave Balance")
    display_claim_leave_balance = fields.Float(string="Claim Leave Balance")
    leave_no                    = fields.Char(string="Leave Number", default="/", track_visibility="onchange")
    total_claim                 = fields.Float(string="Total Claim")
    date_allocate               = fields.Date(string="Allocated Date")
    employee_id                 = fields.Many2one("hr.employee", "Employee", required=True, select=True)
    number_of_days              = fields.Float("Number of Day's", digits=(16,11))
    nod                         = fields.Float("Number of Day's", digits=(3,2), compute='get_nod', store=True)
    state                       = fields.Selection([
                                ('draft', 'To Submit'), 
                                ('confirm', 'Waiting For 1st Approval'), 
                                ('refuse', 'Rejected'), 
                                ('validate1', 'Waiting For 2nd Approval'),
                                ('validate', 'Approved'), 
                                ('cancel', 'Cancelled'),
                                ('expired','Expired')], 
                                'State', readonly=True)
    state_display               = fields.Char("State", compute='state_to_display')
    notes_leave_balance         = fields.Text("Other Notes")
    need_attachment             = fields.Boolean("Need Attachment")
    # can_reset                   = fields.Boolean("Can Reset", compute="_get_can_reset")

    @api.one
    @api.depends('number_of_days')
    def get_nod(self):
        if self.number_of_days > 0.00:
            self.nod = self.number_of_days

    @api.onchange('holiday_status_id')
    def onchange_need_attach(self):
        if self.holiday_status_id:
            for rec in self.holiday_status_id:
                if rec.attachment == True:
                    self.need_attachment = True
                else:
                    self.need_attachment = False
                        

    @api.model
    def default_get(self, fields):
        res = super(sisb_holidays, self).default_get(fields)
        if 'notes' in fields:
            res.update({'notes': 'Leave Type Consist of Full-day, First-Half, Seconf-Half and Part-Time. Click Inside Type Column to change the Type of Leave'})
        if 'notes_leave_balance' in fields:
            res.update({'notes_leave_balance': 'Leave Balance will updated according to Total Request When the Request State is "Approved".'})
        return res



    @api.one
    def state_to_display(self):
        result = {}
        for item in self:
            result[item.id] = dict(item._fields['state'].selection).get(item.state)
        print('result = ', result)
        return result
    
    @api.model
    def create(self, vals):
        print('vals = ', vals)
        if vals.get('leave_no', '/') == '/' or False:
            print('disini')
            vals['leave_no'] = self.env['ir.sequence'].sudo().next_by_code('hr.holidays')
            print('vals = ', vals)
        res = super(sisb_holidays, self).create(vals)
        print('res = ', res)
        return res


    def _check_date(self, cr, uid, ids, context=None):
        for holiday in self.browse(cr, uid, ids, context=context):
            print('holiday = ', holiday)
            if holiday.type in ('remove','claim'):
                domain = [
                    ('date_from', '<=', holiday.date_to),
                    ('date_to', '>=', holiday.date_from),
                    ('employee_id', '=', holiday.employee_id.id),
                    ('id', '!=', holiday.id),
                    ('type', 'in', ['remove','claim']),
                    ('state', 'not in', ['cancel', 'refuse']),
                ]
                nholidays = self.search_count(cr, uid, domain, context=context)
                print('nholidays = ', nholidays)
                all_hd  = self.search(cr, uid, domain, context=context)
                print('all_hd = ', all_hd)
                if nholidays:
                    return False
        return True
    
    
    _check_holidays = lambda self, cr, uid, ids, context=None: self.check_holidays(cr, uid, ids, context=context)


    _constraints = [
        (_check_date, 'You can not have 2 leaves that overlaps on same day!', ['date_from','date_to']),
        (_check_holidays, 'The number of remaining leaves is not sufficient for this leave type', ['state','number_of_days_temp'])
    ] 

    # @api.constrains('claim_leave_balance','number_of_days','type')
    @api.one
    def forbid_total_claim(self):
        if self.type == 'claim':
            print('claim = ',self.claim_leave_balance)
            if self.number_of_days > self.claim_leave_balance:
                raise ValidationError(_("Your Total Claim must be less than your Claim Leave Balance"))

    @api.constrains('type')
    def forbid_claim(self):
        if self.type == 'claim':
            if self.holiday_status_id.claim_able != True:
                raise ValidationError(_("This Leave Type is not Claimable"))

    @api.onchange('type','holiday_status_id')
    def claim_type(self):
        if self.type == 'claim':
            all_remain_leave = []
            if self.holiday_status_id:
                for rec in self.employee_id:
                    leave = rec.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == self.holiday_status_id)
                    if leave:
                        self.display_claim_leave_balance = leave.current_leave
                    else:
                        self.display_claim_leave_balance = 0.00              

    @api.onchange('employee_id')
    def set_user_id(self):
        if self.employee_id:
            for rec in self.employee_id:
                self.user_id = rec.user_id
                self.department_id = rec.department_id
                self.supervisor_id = rec.supervisor_id
                self.supervisor_lvl2_id = rec.supervisor_lvl2_id

    @api.multi
    def get_public_and_school_holiday(self, department_id):
        now = date.today()
        dt_now = now.strftime('%Y-%m-%d')
        holiday = []
        if department_id.public_holiday_type == 'public':
            self._cr.execute("select name, date2 from public_holidays_days" )
            holiday = self._cr.fetchall()
        if department_id.public_holiday_type == 'school':
            academic_year_obj = self.env['academic.year'].search([('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
            print(' = ', academic_year_obj)
            school_holiday = self.env['school.holidays'].search([('year_id', '=', academic_year_obj.id)])
            print('school_holiday = ', school_holiday)
            if not school_holiday:
                holiday = []
            else:
                self._cr.execute('select date, name from school_holidays_line where holiday_id=%s',(school_holiday.id,))
                holiday = self._cr.fetchall()
        if department_id.public_holiday_type == 'both':
            self._cr.execute("select name, date2 from public_holidays_days" )
            holiday = self._cr.fetchall()
            print('public_holiday1 =', holiday)
            academic_year_obj = self.env['academic.year'].search([('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
            school_holiday = self.env['school.holidays'].search([('year_id', '=', academic_year_obj.id)])
            if school_holiday:
                self._cr.execute('select date, name from school_holidays_line where holiday_id=%s',(school_holiday.id,))
                school_holidays = self._cr.fetchall()
                for holidays in school_holidays: 
                    holiday.append(holidays)
        return holiday


    @api.multi
    def get_priority_hd(self, holiday_type):
        self._cr.execute("SELECT date_hd FROM hr_holidays_type_line WHERE holiday_type_id=%s",(holiday_type.id,))
        priority_hd = self._cr.fetchall()
        return priority_hd



    @api.multi
    def claim_all_remain_leave(self):
        date_range = 0
        for s in self:
            tot_all = s.display_claim_leave_balance
            if s.claim_leave_balance < 1.00:
                s.date_to1 = s.date_from1
            elif s.claim_leave_balance > 1.00:
                tot_claim = wk_time_detail['work_hour'] * s.claim_leave_balance
                if tot_claim % wk_time_detail['work_hour'] == 0:
                    date_range = s.claim_leave_balance - 1
                elif tot_claim % wk_time_detail['work_hour'] != 0:
                    date_range = int(s.claim_leave_balance)
            d=s.date_from1
            # dd=s.date_to1
            d1=d.split('-')
            # d2=dd.split('-')
            d1[2]=d1[2].split(' ')
            # d2[2]=d2[2].split(' ')
            a=datetime.date(int(d1[0]),int(d1[1]),int(d1[2][0]))
            # b=datetime.date(int(d2[0]),int(d2[1]),int(d2[2][0]))
            b = a + datetime.timedelta(days=date_range)
            print('b = ', b)
            s.date_to1 = b
            temp=a
            if a>b:
                raise ValidationError(_('Date Error !','From date should be smaller than To date'))
            t12=datetime.timedelta(days=1)
            print('t12 = ', t12)
            dobj=self.env['days.holidays.days']
            delobject=dobj.search([('holiday_id', '=', self.ids[0])])
            dd = []
            for day in delobject:
                day.unlink()
            #     if day.id not in dd:
            #         dd.append(day.id)
            # print('dd = ', dd)
            # for d in dd:
            #     print('d = ', d)
            #     dobj.unlink(d)

            # delete all days if holidays is null 
            self._cr.execute("select id from days_holidays_days where holiday_id is null" )
            t1=[]
            t1=self._cr.fetchall()
            days = []
            for dd in t1:	
		        days.append(dd[0])
            if len(days)>0:
		        dobj.unlink(days)
            self._cr.execute("select id,holiday_id,user_id from days_holidays_days where holiday_id is not null and state='draft'" )
            t1=[]
            t1=self._cr.fetchall()
            for dd in t1:
                hd_obj = self.env['hr.holidays'].search([('id', '=', dd[1])])
                if len(hd_obj)==0:
                    dobj.unlink(dd[0]) 

                hd_obj = self.env['hr.holidays'].search([('id', '=', dd[1]),('user_id','!=',dd[2])])
                if len(hd_obj)>0:
                    del_ob = dobj.browse(dd[0])
                    del_ob.unlink()
              
            # self._cr.execute("select name, reason from public_holidays_days" )
            # t=[]
            # t=self._cr.fetchall()
            t = self.get_public_and_school_holiday(s.employee_id.department_id, SUPERUSER_ID)
            print('t = ', t)
            reason = ''
            #print "::::", t
            fd=1
            pd=hd=0 # this variable is added by sunil
            total_days = 0
            while (temp <= b):
                # wk_time_detail = s.get_working_time(s.employee_id, temp)
                holiday_obj = self.env['days.holidays.days'].search([('date1','=', temp.strftime("%Y-%m-%d")),('user_id',"=",s.employee_id.user_id.id)])
                for s1 in holiday_obj:
                    if self.days_chaeck(s1.id):
                        continue
                    else:
                        return False
                # day = calendar.weekday(int(temp.strftime("%Y")),int(temp.strftime("%m")),int(temp.strftime("%d")))
                # reason = ''

                hd=pd=0
                fd=1
                reason = ''
                if s.number_of_days < 1 and s.number_of_days > 0:
                    fd=0
                    hd=1
                for t1 in t:
                    if t1[0] == temp.strftime("%Y-%m-%d"):
                        temp += t12
                        b += t12
                        continue
                day = calendar.weekday(int(temp.strftime("%Y")),int(temp.strftime("%m")),int(temp.strftime("%d")))
                if day == 5 or day == 6:
                    temp += t12
                    b += t12
                    continue
                if fd:
                    total_days = total_days + 1
                if hd:
                    total_days = total_days + 0.5
                #self.write(cr, uid, ids, {'state':'draft1'})
                end_hour = 0  
                if tot_all >= 1:
                    end_hour = wk_time_detail['end_hour']
                elif tot_all < 1 and tot_all != 0:
                    curr_hour = wk_time_detail['start_hour'] + (tot_all * wk_time_detail['work_hour'])
                    if curr_hour >= wk_time_detail['start_break']:
                        end_hour = curr_hour + wk_time_detail['break_len']
                        wk_time_detail['work_hour'] = end_hour - wk_time_detail['start_hour'] - wk_time_detail['break_len']
                    else:
                        end_hour = curr_hour
                        wk_time_detail['work_hour'] = end_hour - wk_time_detail['start_hour']
                    # end_hour = curr_hour
                    hd = 1
                    fd = 0
                tot_all -= 1
                self.env['days.holidays.days'].create({
                      'name':temp,
                      'date1':temp,
                      'half_day':hd,
                      'full_day':fd,
                      'start_hour': wk_time_detail['start_hour'],
                      'end_hour': end_hour,
                      'hour_span': wk_time_detail['work_hour'],
                      'break_len': wk_time_detail['break_len'],
                      'hourly_leave':0,
                      'holiday_id':self.ids[0],
                      'public_h':pd,
                      'type': s.type,
                      'public_holiday_name': reason,
                      'holiday_status_id':s.holiday_status_id and s.holiday_status_id.id or False,
                      'user_id':s.employee_id.user_id.id,
                      'state':'draft',                      
                      })
                temp += t12
                    
            leave_asked = total_days
            print('total_days = ', total_days)
            #holiday_id = self.pool.get('hr.holidays.per.user').search(cr, uid, [('employee_id','=', s.employee_id.id),('holiday_status_id','=',s.holiday_status_id.id)])
            self.write({'number_of_days':self.display_claim_leave_balance, 'date_to1': b})
        return True

    def unlink(self, cr, uid, ids, context={}, check=True):
        for id in ids:
            selfobj=self.browse(cr,uid,id)
            if selfobj.state=="validate" or selfobj.state=="refuse":
                raise osv.except_osv('Data Error !','Can not Delete Validated or Rejected record')
        return super(sisb_holidays, self).unlink(cr, uid, ids, context=context)


    def onchange_employee_id(self, cr, uid, ids, employee):
        res = {}
        if employee:
            employee_id = self.pool.get('hr.employee').search(cr, uid, [('id','=', employee)])
            employ = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            all_hd_id = []
            for rec in employ.emp_curr_leave_ids:
                if rec.leave_type_id.id not in all_hd_id:
                    all_hd_id.append(rec.leave_type_id.id)
            res = {'domain': {'holiday_status_id': [('id','in', all_hd_id)]}}
        return res



    def button_approve(self, cr, uid, ids, item ,context=None):
        selfobj = self.browse(cr, uid, ids, context=context)
        hr_curr_leave_obj = self.pool.get('hr.holidays.curr.leaves')
        reset_year = 0
        alloc_id = []
        conn = False
        if selfobj:
            for emp in selfobj:
                emp.state = 'validate'
                for emp_id in emp.employee_id:
                    print('ss')
                    for l in emp_id.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == emp.holiday_status_id):
                        if l:
                            if l.leave_type_id.limit == False or l.current_leave == 0:
                                cr.execute('DELETE FROM hr_holidays_curr_leaves WHERE id = %s',(l.id, ))
                            if l.leave_type_id.limit == True and l.current_leave > 0:
                                l.current_leave += emp.number_of_days
                                l.total_curr_leave += emp.number_of_days
                                conn = True
                    emp_id.allocated_source_id = item.id
                    if emp_id.department_id:
                        for dept in emp_id.department_id:
                            emp_id.leave_reset_month = dept.leave_month_reset or dept.parent_id.leave_month_reset
                            if int(emp_id.leave_reset_month)  >= int(emp_id.leave_reset_month) and int(emp_id.leave_reset_month) <= 12:
                                emp_id.reset_year = date.today().year
                            elif int(emp_id.leave_reset_month) < int(emp_id.leave_reset_month):
                                emp_id.reset_year = date.today().year + 1
                    if conn:
                        continue
                    alloc_leave = hr_curr_leave_obj.create(cr, uid,{
                    'leave_type_id': selfobj.holiday_status_id.id,
                    'total_curr_leave': selfobj.number_of_days,
                    'total_taken_leave': 0.00,
                    'current_leave': selfobj.number_of_days,
                    'state': selfobj.state
                    })

                    emp_id.emp_curr_leave_ids = [(4, alloc_leave)]

        return self.write(cr,uid,ids,{'state':'validate'})


    def get_working_time(self, cr, uid, emp_id, temp, context=None):
        if type(temp) == str:
            dt_now = temp
        else:
            dt_now = temp.strftime('%Y-%m-%d')
        print('dt_now = ', dt_now)
        sched_obj = self.pool.get('employee.schedule.line').search(cr, uid, [('employee_id', '=', emp_id.id),('date','=',dt_now)])
        sched = self.pool.get('employee.schedule.line').browse(cr, uid, sched_obj)
        if not sched:
            raise ValidationError("This Employee Has No Work Schedule, Please Set up First")
        vals = {}
        for rec in sched:
            vals['start_hour'] = rec.start_hour
            vals['end_hour'] = rec.end_hour
            vals['start_break'] = rec.start_break_hour
            vals['end_break'] = rec.end_break_hour
            vals['work_hour'] = rec.end_hour - rec.start_hour - (rec.end_break_hour - rec.start_break_hour)
            vals['break_len'] = rec.end_break_hour - rec.start_break_hour
        return vals


    def days_chaeck(self,cr,uid,ids,s1):
        seaobj=self.pool.get('days.holidays.days').browse(cr,uid,s1)
        if seaobj.holiday_id.id:
            if not seaobj.holiday_id.id==ids[0]:
                
                if seaobj.holiday_id.state=='refuse':
                    return True
                else:
                    raise osv.except_osv('Day Error !','Can not create more leaves for one day ')
            else:
                return True
        else:
            return True

    def create_leave_days(self, cr, uid, ids, *args):
        print "::system function is calling::"
        print('ids = ', ids)
        selfobj=self.browse(cr, uid, ids, None).sudo()
        department = ''
        for s in selfobj:
            # wk_time_detail = s.get_working_time(s.employee_id)
            d=s.date_from1
            dd=s.date_to1
            d1=d.split('-')
            d2=dd.split('-')
            d1[2]=d1[2].split(' ')
            d2[2]=d2[2].split(' ')
            a=datetime.date(int(d1[0]),int(d1[1]),int(d1[2][0]))
            b=datetime.date(int(d2[0]),int(d2[1]),int(d2[2][0]))
            temp=a
            if a>b:
                raise osv.except_osv('Date Error !','From date should be smaller than To date')
            t12=datetime.timedelta(days=1)
            # print('t12 = ', t12)
            dobj=self.pool.get('days.holidays.days')
            delobject=dobj.search(cr, uid, [('holiday_id', '=', ids[0])])
            print('delobject =',delobject)
            for d in delobject:
                print('d = ', d)
                dobj.unlink(cr, uid,d)
            # delete all days if holidays is null 
            cr.execute("select id from days_holidays_days where holiday_id is null" )
            t1=[]
            t1=cr.fetchall()
            days = []
            for dd in t1:	
		        days.append(dd[0])
            if len(days)>0:
		        dobj.unlink(cr, uid,days)
            cr.execute("select id,holiday_id,user_id,type from days_holidays_days where holiday_id is not null and state='draft'" )
            t1=[]
            t1=cr.fetchall()
            for dd in t1:
		        hd_obj = self.pool.get('hr.holidays').search(cr, uid, [('id', '=', dd[1])])
		        if len(hd_obj)==0:
			        dobj.unlink(cr, uid,dd[0])

		        hd_obj = self.pool.get('hr.holidays').search(cr, uid, [('id', '=', dd[1]),('user_id','!=',dd[2])])
		        if len(hd_obj)>0:
			        dobj.unlink(cr, uid,dd[0])

            # cr.execute("select name, reason, department_id from public_holidays_days" )
            # t=[]
            # t=cr.fetchall()
            t = s.get_public_and_school_holiday(s.employee_id.department_id)
            print('t = ', t)
            priority_hd_check = s.employee_id.holiday_type_id
            print('priority_hd_check = ', priority_hd_check)
            priority_hd = ''
            if priority_hd_check:
                priority_hd = s.get_priority_hd(priority_hd_check)
            print('priority_hd', priority_hd)
            reason = ''
            fd=1
            pd=hd=0 # this variable is added by sunil
            total_days = 0
            while (temp <= b):
                # wk_time_detail = s.get_working_time(s.employee_id, temp)
                holiday_obj = self.pool.get('days.holidays.days').search(cr, uid, [('date1','=', temp.strftime("%Y-%m-%d")),('user_id',"=",s.employee_id.user_id.id)])
                for s1 in holiday_obj:
                    if self.days_chaeck(cr, uid, ids, s1):
                        continue
                    else:
                        return False
                if not priority_hd_check:
                    for t1 in t:
                        if t1[0] == temp.strftime("%Y-%m-%d"):
                            print('hari  = ', t1[0])
                            temp += t12
                            continue
                else:
                    for t1 in priority_hd:
                        if t1[0] == temp.strftime("%Y-%m-%d"):
                            temp += t12
                            continue 
                day = calendar.weekday(int(temp.strftime("%Y")),int(temp.strftime("%m")),int(temp.strftime("%d")))
                reason = ''
                if day == 5 or day == 6:
                    temp += t12
                    continue
                #self.write(cr, uid, ids, {'state':'draft1'})    
                self.pool.get('days.holidays.days').create(cr,uid,{
                      'name':temp,
                      'date1':temp,
                      'day': temp.strftime('%A'),
                      'leave_type': 'full',
                      'holiday_id':ids[0],
                      'type': s.type,
                      'holiday_status_id': s.holiday_status_id.id,
                      'user_id':s.employee_id.user_id.id,
                      'state':'draft',                      
                      })
                temp += t12
        
            # leave_asked = total_days
            # print('total_days = ', total_days)
            #holiday_id = self.pool.get('hr.holidays.per.user').search(cr, uid, [('employee_id','=', s.employee_id.id),('holiday_status_id','=',s.holiday_status_id.id)])
            # self.write(cr, uid, ids, {'number_of_days':total_days})   
                
        return True




    def calculate_days(self, cr, uid, ids, *args):
        for s in self.browse(cr, uid, ids, None):
            # s.create_leave_days()
            s.forbid_total_claim()
            fd=hd=0
            total_days = 0
            start_hour = 0
            end_hour = 0
            start_break = 0
            end_break = 0
            work_hour = 0
            break_len = 0
            half_leave_amt = 0.00
            half_leave = ('first_half','second_half')
            full = 0
            half = 0
            part = 0
            for f in s.holiday_id:
                if f.leave_type == 'full':
                    full += 1
                    total_days = total_days + 1.0
                    if s.type == 'claim':
                        if total_days > s.display_claim_leave_balance:
                            raise ValidationError(_("You cannot claim leave more than your ramaining leaves\n"
                                                    "Your Remaining Leave is {} days\n"
                                                    "Your Request is {} days".format(s.display_claim_leave_balance, total_days)))
                elif f.leave_type in half_leave:
                    # schedule_obj = self.pool.get('employee.schedule').search(cr, uid, [('date_from', '<=', f.date1), ('date_to', '>=', f.date1), ('employee_id', '=', s.employee_id.id)])
                    # schedule_id = self.pool.get('employee.schedule').browse(cr, uid, schedule_obj)
                    # for sched in schedule_id.schedule_type_id:
                    #     wk_time_length = ((sched.end_hour - sched.start_hour - sched.total_break) / 2) / 24
                    #     total_days += wk_time_length
                    half += 1
                    #half_day= 4.0 / 24.0 # Assumption 1 day work is 8 Hours so 1/2 day work is 4 Hours
                elif f.leave_type == 'part':
                    part += 1
                    f.hour_span = f.end_hour - f.start_hour
                    if f.hour_span > 8:
                        raise ValidationError(_("you can't take part time leave more than 8 Hour's"))
                    hour_span = f.hour_span / 24.0
                    total_days = total_days + hour_span
            if half % 2 == 0:
                total_days = total_days + (half / 2)
            else:
                total_days = total_days + (half // 2) + (4.0 / 24) #-> Assumption 1 day work is 8 Hours so 1/2 day work is 4 Hours
            s.write({'number_of_days': total_days})
            if total_days <= 0.00:
                raise ValidationError(_("Your Leave Request is 0"))
            forbid = self.check_leave_taken(cr, uid, ids)
            if not forbid['forbid']:
                raise ValidationError(_("Your Leave Balance For %s is %.2f.\n Your Request %.2f. Please Change Accordingly ")%(forbid['name'], forbid['current_leave'], forbid['request']))
            self.write(cr, uid, ids, {'number_of_days':total_days,'state':'draft', 'total_full': full, 'total_half': half, 'total_part': part})   
        return True 

    def check_leave_taken(self, cr, uid, ids, context=None):
        val = {}
        for rec in self.browse(cr, uid, ids):
            req = rec.number_of_days
            leave_type = rec.holiday_status_id
            leave = rec.employee_id.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == leave_type)
            if leave.current_leave < rec.number_of_days:
                val['name'] = leave_type.name
                val['request'] = rec.number_of_days
                val['current_leave'] = leave.current_leave
                val['forbid'] = False
            else:
                val['forbid'] = True
                #    raise ValidationError(_("Your Leave balance For %s is %.2f.\n Your Request %.2f. Please Change Accordingly ")%(rec.holiday_status_id.name, leave.current_leave, rec.number_of_days))
        return val
    
    def check_leave_type(self, cr, uid,employee_id, leave_type, context=None):
        check = False
        for rec in employee_id:
            for l in rec.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == leave_type):
                print('l = ', l)
                if l:
                    check = True
        return check

            
    def get_leave_balance(self, cr, uid, leave_type, employee_id, number_of_days, holiday_id, context=None):
        employee_obj = self.pool.get('hr.employee').search(cr, uid, [('id', '=', employee_id.id)], context=context)
        employee = self.pool.get('hr.employee').browse(cr, uid, employee_obj)
        leave_balance = {}
        for rec in employee:
            for line in rec.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == leave_type):
                leave_balance['leave_type_id'] = line.leave_type_id.id
                leave_balance['total_leave'] = line.total_curr_leave
                leave_balance['state'] = 'confirm'
                leave_balance['total_used'] = line.total_taken_leave
                leave_balance['leave_balance'] = line.current_leave
                leave_balance['holiday_id'] = holiday_id.id
                leave_balance['total_request'] = number_of_days
        return leave_balance

    def holidays_confirm(self, cr, uid, ids, context=None):
        # self.create_leave_days(cr, uid, ids)
        selfobject=self.browse(cr, uid, ids, None)
        check_leave = self.check_leave_type(cr, uid, selfobject.employee_id, selfobject.holiday_status_id)
        if not check_leave:
            raise ValidationError(_("You don't have this type of Leave"))

        half_leave = ('first_half','second_half')
        full=0.00
        half=0.00
        part = 0.00
        hl=0.00
        hd=0.00 # This line added by sunil
        for selfobj in selfobject:  
            
            recids=self.pool.get('days.holidays.days').search(cr,uid,[('holiday_id','=', selfobj.id)])            
            #if recids==[]:
            #    raise osv.except_osv('Day Error !','Create Day list')
            for rec in recids:
                if self.days_chaeck(cr, uid, ids, rec):
                    recobj=self.pool.get('days.holidays.days').browse(cr,uid,rec)
                    self.pool.get('days.holidays.days').write(cr,uid,rec,{'state':'confirm'})
                    flg=0
                    if recobj.leave_type == 'full':
                        full+=1
                        flg=1
                    if recobj.leave_type in half_leave:
                        half+=1
                        flg=1
                    if recobj.leave_type == 'part':
                        part+=1
                        flg=1
                    if recobj.hourly_leave > 0:
                        hl+=recobj.hourly_leave
                        flg=1
                    if flg==0:
                        raise osv.except_osv('Leave Error !','Select Leave type')
                else:
                    return False
            # total_days = ((full + (half/2))) # this Line Added By sunil
            total_days = selfobj.number_of_days #this Line Added By Alfredo
            self.calculate_days(cr, uid, ids)
            if not selfobj.leave_balance_ids:
                get_leave_balance = self.get_leave_balance(cr, uid, selfobj.holiday_status_id, selfobj.employee_id, selfobj.number_of_days, selfobj,context=context)
                print('get_leave_balance = ', get_leave_balance)
                leave_balance = self.pool.get('hr.holidays.leaves.balance').create(cr, uid, get_leave_balance, context=context)
            if selfobj.leave_balance_ids:
                for l in selfobj.leave_balance_ids:
                    l.state = 'confirm'
            self.write(cr, uid, ids, {
                     'state':'confirm',
                     'total_half':half,
                     'total_full':full,
                     'total_part': part,
                     'total_hour':hl,
                     'supervisor_id': selfobject.employee_id.supervisor_id.id,
                     'supervisor_lvl2_id': selfobject.employee_id.supervisor_lvl2_id.id
                    #  'number_of_days':total_days # this line added by sunil
                     })
    
            # if selfobj.employee_id and selfobj.employee_id.supervisor_id and selfobj.employee_id.supervisor_id.user_id:
            #     self.message_subscribe_users(cr, uid, [selfobj.id], user_ids=[selfobj.employee_id.supervisor_id.user_id.id], context=context)
            # elif selfobj.employee_id and selfobj.employee_id.parent_id and selfobj.employee_id.parent_id.user_id:
            #     self.message_subscribe_users(cr, uid, [selfobj.id], user_ids=[selfobj.employee_id.parent_id.user_id.id], context=context)

            """This Function also send Email Leave Request to Linked Supervisor in Employee Data"""
            template = ''
            if selfobj.employee_id.supervisor_id:
                template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'first_request_leave_to_spv')
            elif not selfobj.employee_id.supervisor_id and selfobj.employee_id.parent_id:
                template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'first_request_leave_to_mgr')
            elif not selfobj.employee_id.supervisor_id and not selfobj.employee_id.parent_id:
                template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'first_request_leave_to_hr_group')
            if template:
                mail_id = template.send_mail(selfobj.id)
                print('mail_id = ', mail_id)
                # mail = self.env['mail.mail'].browse(mail_id)
                mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
                print('mail = ', mail)
                if mail:
                    mail.send()
        return True



    def holidays_first_validate(self, cr, uid, ids, context=None):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        selfobj = self.browse(cr, uid, ids)
        for rec in selfobj:
            if rec.supervisor_lvl2_id:
                """This Function also send Email Leave Request to Linked Supervisor II in Employee Data"""
                for hd in selfobj.holiday_id:
                    hd.write({'state': 'validate1'})
                for lb in selfobj.leave_balance_ids:
                    lb.write({'state': 'validate1'})
                self.holidays_first_validate_notificate(cr, uid, ids, context=context)
                template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'second_request_leave_to_spv_lvl2')
                if template:
                    mail_id = template.send_mail(selfobj.id)
                    print('mail_id2 = ', mail_id)
                    # mail = self.env['mail.mail'].browse(mail_id)
                    mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
                    print('mail2 = ', mail)
                    if mail:
                        mail.send()
                return self.write(cr, uid, ids, {
                    'state':'validate1',
                    'first_approve': uid,
                    'first_approve_date': date.today()})
            else:
                print('disiniaaaa')
                return self.validate_holidays(cr, uid, ids, context=None)

    def holidays_refuse(self, cr, uid, ids, *args):
        holiday = self.browse(cr, uid, ids)
        for r in holiday.holiday_id:
            r.state = 'refuse'
        for l in holiday.leave_balance_ids:
            l.state = 'refuse'    
        self.write(cr, uid, ids, {'state':'refuse'})
        self.write_data(cr, uid, ids)
        return True
    
    def holidays_cancel(self, cr, uid, ids, *args):
        holiday = self.browse(cr, uid, ids)
        print('holiday =', holiday)
        for r in holiday.holiday_id:
            r.state = 'cancel'
        for l in holiday.leave_balance_ids:
            l.state = 'cancel'
        return self.write(cr, uid, ids, {'state':'cancel'})

    def set_to_draft(self, cr, uid, ids, *args):
        holiday = self.browse(cr, uid, ids)
        for r in holiday.holiday_id:
            r.state = 'draft'
        for l in holiday.leave_balance_ids:
            l.state = 'draft'
        self.write(cr, uid, ids, {'state':'draft','approved_by':False,'approved_date': False})
        return True

    def write_data(self,cr,uid,ids,*args):
        selfobj=self.browse(cr, uid, ids, None)
        half_leave = ('first_half','second_half')
        full=0
        half=0
        part=0
        hl=0
        for s in selfobj:
            sid=self.pool.get('hr.holidays.history').create(cr,uid,{'validated_id':uid,'name':s.name,'state':s.state,'date_from1':s.date_from1,'date_to1':s.date_to1,'employee_id':s.employee_id.id,'user_id':s.user_id.id,'manager_id':s.manager_id.id,'notes':s.notes,'contactno':s.contactno,'total_half':s.total_half,'total_full':s.total_half, 'total_part':s.total_part})
            for s1 in s.holiday_id:
                self.pool.get('days.holidays.days').write(cr,uid,s1.id,{'state':s.state})
                ss1=self.pool.get('days.holidays.days').browse(cr,uid,s1.id)
                if ss1.leave_type == 'full':
                    full+=1
                if ss1.leave_type in half_leave:
                    half+=1
                if ss1.leave_type == 'part':
                    part+=1
                if ss1.hourly_leave >0:
                    hl+=ss1.hourly_leave
                holiday_status_id = ss1.holiday_status_id.id
                self.pool.get('days.holidays.days.history').create(cr,uid,{
                                                                'user_id':ss1.user_id.id,
                                                                'day': ss1.day,
                                                                'start_hour': ss1.start_hour,
                                                                'end_hour': ss1.end_hour,
                                                                'hour_span': ss1.hour_span,
                                                                'state':ss1.state,
                                                                'name':ss1.name,
                                                                'date1':ss1.name,
                                                                'leave_type':ss1.leave_type,
                                                                'hourly_leave':ss1.hourly_leave,
                                                                'holiday_id':sid,
                                                                'public_h':ss1.public_h,
                                                                'holiday_type_id': holiday_status_id})

            self.write(cr, uid, ids, {'total_hour':hl})
            self.write(cr, uid, ids, {'total_half':half})
            self.write(cr, uid, ids, {'total_full':full})
            self.write(cr, uid, ids, {'total_part': part})
            self.pool.get('hr.holidays.history').write(cr, uid, sid, {'total_half':half})
            self.pool.get('hr.holidays.history').write(cr, uid, sid, {'total_full':full})
            self.pool.get('hr.holidays.history').write(cr, uid, sid, {'total_part':part})
            self.pool.get('hr.holidays.history').write(cr, uid, sid, {'total_hour':hl})


    def check_holidays(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.holiday_type != 'employee' or record.type != 'remove' or not record.employee_id or record.holiday_status_id.limit:
                continue
            leave_days = self.pool.get('hr.holidays.status').get_days(cr, uid, [record.holiday_status_id.id], record.employee_id.id, context=context)[record.holiday_status_id.id]
            if leave_days['remaining_leaves'] < 0 or leave_days['virtual_remaining_leaves'] < 0:
                # Raising a warning gives a more user-friendly feedback than the default constraint error
                raise Warning(_('The number of remaining leaves is not sufficient for this leave type.\n'
                                'Please verify also the leaves waiting for validation.'))
        return True

            
    def validate_holidays(self, cr, uid, ids, context=None):
        print "::::::::::::::::: hr request validate method call :::::::::"
        # self.check_holidays(cr,uid,ids)      # this line added by sunil
        selfobject=self.browse(cr, uid, ids, None)
        leave_balance_obj = self.pool.get('hr.holidays.leaves.balance').search(cr, uid, [('holiday_id','=', selfobject.id)], context=context)
        leave_balance = self.pool.get('hr.holidays.leaves.balance').browse(cr, uid, leave_balance_obj)
        for hd in selfobject.holiday_id:
            hd.state = 'validate'
        for lb in selfobject.leave_balance_ids:
            lb.state = 'validate'
            lb.total_used += selfobject.number_of_days
        for selfobj in selfobject:
            for emp in selfobj.employee_id:
                for line in emp.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == selfobj.holiday_status_id):
                    taken_leave = selfobj.number_of_days + (16.0 / 24.0) #Assumption 1 day work is 8 hours so 16 is come from 24 - 8
                    x = selfobj.number_of_days % 1
                    print('x = ', x)
                    if selfobj.number_of_days % 1 == 0.0:
                        line.current_leave -= selfobj.number_of_days
                    else:
                        line.current_leave -= taken_leave
                    line.total_taken_leave += selfobj.number_of_days
                    leave_balance.update({'leave_balance': line.current_leave})
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'approved_leave')
        if template:
            mail_id = template.send_mail(selfobj.id)
            print('mail_id4 = ', mail_id)
            # mail = self.env['mail.mail'].browse(mail_id)
            mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
            print('mail4 = ', mail)
            if mail:
                mail.send()
        self.write(cr, uid, ids, {'state':'validate','approved_by':uid,'approved_date': date.today() })
        self.write_data(cr, uid, ids)
        # self._create_holiday(cr, uid, ids)     # this line added by sunil  
        return True
    
    def _create_holiday(self, cr, uid, ids):
        holidays_user_obj = self.pool.get('hr.holidays.per.user')
        holidays_data = self.browse(cr, uid, ids[0])
        list_holiday = []
        ids_user_hdays = holidays_user_obj.search(cr, uid, [('employee_id', '=', holidays_data.employee_id.id),('holiday_status_id', '=', holidays_data.holiday_status_id.id)])
        for hdays in holidays_user_obj.browse(cr, uid, ids_user_hdays):
            for req in hdays.holiday_ids:
                list_holiday.append(req.id)
        list_holiday.append(ids[0])
        holidays_user_obj.write(cr, uid, ids_user_hdays, {'holiday_ids': [(6, 0, list_holiday)]})
        return True
    

    @api.model
    def get_email_to(self):
        user_group = self.env['res.users'].has_group('base.group_hr_manager')
        print('user_group = ', user_group)
        user_groups = self.env.ref('v8_website_support.hide_menus_hr')
        partner_list = [usr.partner_id.name for usr in user_groups.users if usr.partner_id.email]
        email_list = [usr.partner_id.email for usr in user_groups.users if usr.partner_id.email]
        emails = ", ".join(email_list)
        print('emails = ', emails)
        return emails

    @api.model
    def get_email_from(self):
        current_user = self.env['res.users'].search([('id', '=', self.env.uid)])
        sender = ''
        for rec in current_user:
            sender = rec.partner_id.name + '<' + rec.partner_id.email + '>'
        return sender
    
    @api.multi
    def get_url(self, emp_id, object):
        url_source = self.env['res.partner']
        url = url_source.get_url(emp_id, object)
        return url

class hr_holidays_leaves_balance(models.Model):
    _name = "hr.holidays.leaves.balance"
    
    leave_type_id = fields.Many2one('hr.holidays.status', string="Leave Type")
    holiday_id = fields.Many2one('hr.holidays', string="Holiday Parent", ondelete='cascade')
    total_used = fields.Float("Total Used", digits=(16,11))
    total_leave = fields.Float("Total Leave", digits=(16,11))
    total_request = fields.Float("Total Request", digits=(16,11))
    state = fields.Selection([
        ('draft','To Submit'),
        ('confirm','Waiting For 1st Approval'),
        ('refuse', 'Rejected'),
        ('cancel','Cancelled'),
        ('validate1','Waiting For 2nd Approval'),
        ('validate','Approved')
    ], string="Request State")
    leave_balance = fields.Float("Leave Balance", digits=(16,11))



class inherit_holidays_history(models.Model):
    _inherit = 'hr.holidays.history'

    total_part = fields.Integer('Total Part Leave', readonly=True)
    holiday_status_id = fields.Many2one('hr.holidays.status', string="Holiday's Status")
    state = fields.Selection([
        ('draft', 'To Submit'), 
        ('confirm', 'Waiting For 1st Approval'), 
        ('refuse', 'Rejected'), 
        ('validate1', 'Waiting For 2nd Approval'),
        ('validate', 'Approved'), 
        ('cancel', 'Cancelled'),
        ('expired','Expired')], 
        'State', default="draft")

class inherit_holidays_days_history(models.Model):
    _inherit = "days.holidays.days.history"

    day = fields.Char("Day")
    start_hour = fields.Float("Start Hour", digits=(4,3), readonly=True)
    end_hour = fields.Float("End Hour", digits=(4,3), readonly=True)
    hour_span = fields.Float("Hour Span", store=True, readonly=True)
    leave_type = fields.Selection([
        ('first_half','First-half'),
        ('second_half','Second-half'),
        ('part','Part-time'),
        ('full','Full-day'),
        ], string="Leave Type")
    holiday_type_id = fields.Many2one('hr.holidays.status', "Leave Type")
    state = fields.Selection([
        ('draft', 'To Submit'), 
        ('confirm', 'Waiting For 1st Approval'), 
        ('refuse', 'Rejected'), 
        ('validate1', 'Waiting For 2nd Approval'),
        ('validate', 'Approved'), 
        ('cancel', 'Cancelled'),
        ('expired','Expired')], 
        'State', default="draft")


class sisb_holiday_days(models.Model):
    _inherit = "days.holidays.days"

    public_holiday_name = fields.Text("Public Holiday Info")
    date1 = fields.Date(string="Date", required="1")
    day = fields.Char(string="Day")
    hour_span = fields.Float("Hour Span", store=True)
    hour_span_display = fields.Float("Hour Span", related="hour_span")
    start_hour = fields.Float("Start Hour", digits=(4,3))
    end_hour = fields.Float("End Hour", digits=(4,3))
    leave_type = fields.Selection([
        ('first_half','First-half'),
        ('second_half','Second-half'),
        ('part','Part-time'),
        ('full','Full-day'),
        ], string="Leave Type")

    state = fields.Selection([
        ('draft', 'To Submit'), 
        ('confirm', 'Waiting For 1st Approval'), 
        ('refuse', 'Rejected'), 
        ('validate1', 'Waiting For 2nd Approval'),
        ('validate', 'Approved'), 
        ('cancel', 'Cancelled'),
        ('expired','Expired')], 
        'State', default="draft")
    holiday_id = fields.Many2one('hr.holidays', "Holidays Ref", ondelete='cascade')
    type = fields.Selection([
        ('remove','Remove'),
        ('claim','Claim'),
        ('allocated','Allocated'),
        ('add','Add'),
    ], default='claim', string="Type")

    @api.depends('start_hour','end_hour')
    def get_hour_span(self):
        self.hour_span = self.end_hour - self.start_hour   
    
    @api.constrains('start_hour','end_hour')
    def hour_span_constrain(self):
        if self.end_hour <= self.start_hour:
            raise ValidationError(_("End Hour must be greater than Start Hour"))
    
    @api.constrains('leave_type','start_hour','end_hour')
    def leave_type_constraint(self):
        if self.leave_type == 'part':
            print('disini11')
            if self.start_hour < 1 or self.end_hour < 1:
                print('disini')
                raise ValidationError(_("You Must set Start Hour and End Hour For the Part Time Type"))
    
    # @api.onchange('half_day')
    # def toggle_half_day(self):
    #     if self.half_day and self.full_day:
    #         self.full_day = False

    # @api.onchange('full_day', 'holiday_id', 'date1')
    # def toggle_full_day(self):
    #     print('date = ', self.date1)
    #     emp_id = ''
    #     if self.holiday_id:
    #         emp_id = self.holiday_id.employee_id
    #     now = date.today()
    #     dt_now = now.strftime('%Y-%m-%d')
    #     sched = self.env['employee.schedule.line'].search([('employee_id', '=', emp_id.id),('date','=',self.date1)])
    #     if self.full_day and self.half_day:
    #         self.half_day = False
    #     if self.full_day:
    #         work_times = sched
    #         self.start_hour = work_times.start_hour
    #         self.end_hour = work_times.end_hour
    #         self.hour_span = work_times.end_hour - work_times.start_hour - (work_times.end_break_hour - work_times.start_break_hour)
        

    # @api.one
    # @api.constrains('start_hour', 'end_hour', 'holiday_id','date1')
    # def constrain_leave_hours(self):
    #     now = date.today()
    #     dt_now = now.strftime('%Y-%m-%d')
    #     emp_id = ''
    #     if self.holiday_id:
    #         emp_id = self.holiday_id.employee_id
    #         sched = self.env['employee.schedule.line'].search([('employee_id', '=', emp_id.id),('date','=',self.date1)])
    #         work_times = sched
    #         if self.start_hour > self.end_hour:
    #             raise ValueError(_("You cannot set the End Hour earlier than the Start Hour!"))
    #         if self.start_hour < work_times.start_hour or self.end_hour > work_times.end_hour:
    #             raise ValueError(_("You cannot set your leave hours beyond the range of your work hours! ({} - {})"
    #                                .format(hftt(work_times.start_hour), hftt(work_times.end_hour))))

class sisb_leave_structure(models.Model):
    _name = "hr.holidays.structure.line"

    name = fields.Char("Description")
    leave_type = fields.Many2one('hr.holidays.status', string="Leave Type", required=True)
    amount_to_allow = fields.Integer("Allocate Amount(days)")
    holiday_structure_id = fields.Many2one('hr.holidays.structure', string="Structure")
    color_state = fields.Selection([
        ('not_allowed','Not Allowed'),
        ('allowed','Allowed')
    ], string="Info", default="allowed")

    @api.onchange('leave_type')
    def get_employee_type(self):
        if self.leave_type:
            self.amount_to_allow = self.leave_type.max_leaves
            for rec in self.leave_type:
                # self.amount_to_allow = rec.max_leaves
                if self.amount_to_allow > rec.max_leaves:
                    self.color_state = 'not_allowed'
                else:
                    self.color_state = 'allowed'

    @api.constrains('amount_to_allow', 'leave_type', 'employee_type')
    def check_ammount_allow(self):
        warn_amount = 0.00
        if self.leave_type:
            for rec in self.leave_type:
                warn_amount = rec.max_leaves
            if self.amount_to_allow > warn_amount:
                self.color_state == 'not_allowed'
                raise ValidationError(_("The Maximum Allowed amount For %s is %.2f") %(self.leave_type.name, warn_amount))
            

class sisb_leave_structure(models.Model):
    _name = "hr.holidays.structure"

    name                = fields.Char("Name")
    company_id          = fields.Many2one('res.company', string="Company")
    holiday_type_ids    = fields.One2many('hr.holidays.structure.line', 'holiday_structure_id',string="Leave Type Configuration")
    employee_ids        = fields.One2many('hr.employee', 'leave_structure_id', string="Employee")
    state               = fields.Selection([
                            ('draft','Draft'),
                            ('allocated','Allocated')
                        ], string="State", default="draft")
    employee_type       = fields.Selection([
                            ('new','New'),
                            ('probation','Probation'),
                            ('contract','Contract'),
                            ('permanent','Permanent'),
                        ], string="Employee Type")
    
    @api.multi
    def set_leave_structure(self):
        for employee in self.employee_ids:
            if not employee.leave_structure_id:
                employee.leave_structure_id = self.id
        return self.write({'state': 'allocated'})


    @api.one
    def re_allocate(self):
        return self.write({'state': 'draft'})


    @api.multi
    def call_wizard(self):
        company = self.company_id
        state = self.employee_type
        alloc_employee = []
        for rec in self.employee_ids:
            alloc_employee.append(rec.id)
        return {
            'name'      : _("Select Employee"),
            'type'      : 'ir.actions.act_window',
            'res_model' : 'alloc.leave.structure',
            'view_mode' : 'form',
            'view_type' : 'form',
            'context'   : { 'default_leave_structure_id': self.id,
                            'default_company_id': company.id,
                            'default_leave_structure_type': state},
            'target'    : 'new',
            }

    # @api.multi
    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         result.append((rec.id, "{} for {} Employee".format(rec.name, rec.employee_type.capitalize())))
    #     return result


    # exipired_leave = fields.Integer(string="Exipred")
    # expired_options = fields.Selection([
    #     ('days','Days'),
    #     ('month','Month'),
    #     ('year','Year')
    # ], string="Expired Leave Type")
    # reset_on = fields.Selection([
    #     ('1','January'),
    #     ('2','February'),
    #     ('3','March'),
    #     ('4','April'),
    #     ('5','May'),
    #     ('6','June'),
    #     ('7','July'),
    #     ('8','August'),
    #     ('9','September'),
    #     ('10','October'),
    #     ('11','November'),
    #     ('12','December'),
    # ], string="Reset On", required=True)

class sisb_public_holiday_days(models.Model):
    _inherit="public.holidays.days"

    department_id = fields.Many2one('hr.department', string="Department")
    date2 = fields.Date(string="To")
    employee_id = fields.Many2one('hr.employee', string="Responsible User")

    @api.onchange('name')
    def onchange_date2(self):
        if self.name:
            self.date2 = self.name

    @api.constrains('name','date2')
    def forbid_date2(self):
        if self.date2 > self.name:
            raise ValidationError(_('Date To cannot be greater than Date From'))



class reset_leave(models.Model):
    _name = "reset.leaves"

    name = fields.Char(string="Name")
    year = fields.Many2one('sisb.account.fiscalyear')
    department = fields.Selection([
        ('Corporate','Corporate'),
        ('Academic','Academic')
    ], string="Department", required=True)
    company_id = fields.Many2one('res.company', string="Company")
    date_reset = fields.Date(string="Reset Date")
    prev_allocated_ids = fields.One2many('hr.holidays','reset_id', string="Reset Leaves")
    state = fields.Selection([
        ('draft','Draft'),
        ('reset','Reset')
    ], string="State", default='draft')



    @api.multi
    def generate_allocated(self):
        alloc_hr_holidays_obj = self.env['allocate.leaves.run']
        prev_alloc = alloc_hr_holidays_obj.search([('year_id','=', self.year.id)])
        emp_list = []
        for rec in prev_alloc:
            for emp in rec.allocation_line_ids.filtered(lambda x: x.employee_id.department_id.name == self.department or x.employee_id.department_id.parent_id.name == self.department):
                if emp.id not in emp_list:
                    emp_list.append(emp.id)
        all_leaves_to_reset = []
        for rec in self:
            if not rec.prev_allocated_ids:
                return self.write({'prev_allocated_ids': [(6,0,emp_list)], 'state':'draft'})
            if rec.prev_allocated_ids:
                for leaves in rec.prev_allocated_ids:
                    if leaves.id not in all_leaves_to_reset:
                        all_leaves_to_reset.append(leaves.id)
                for ids in emp_list:
                    if ids not in all_leaves_to_reset:
                        return self.write({'prev_allocated_ids': [(4,ids)], 'state':'draft'})
                    else:
                        return self.write({'state':'draft'})


    @api.multi
    def reset_leave(self):
        alloc_hr_holidays_obj = self.env['allocate.leaves.run']
        prev_alloc = alloc_hr_holidays_obj.search([('year_id','=', self.year.id)])
        for rec in prev_alloc:
            rec.state = 'expired'
        for line in self.prev_allocated_ids:
            line.state = 'expired'
            for prev_leave in line.employee_id:
                prev_leave.emp_curr_leave_ids = [(5,0,0)]
        return self.write({'state':'reset'})
    


class hr_holidays_type(models.Model):
    _name = "hr.holidays.type"

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', string="Company")
    holiday_type_line_ids = fields.One2many('hr.holidays.type.line', 'holiday_type_id', string="Holiday's List")


class hr_holidays_type_line(models.Model):
    _name = "hr.holidays.type.line"
    _order = "date_hd desc"

    holiday_type_id = fields.Many2one('hr.holidays.type', string="Holiday Type")
    date_hd = fields.Date(string="Date")
    name = fields.Text(string="Description")





class hr_year(models.Model):
    _name = "hr.year"

    name = fields.Char("Year")