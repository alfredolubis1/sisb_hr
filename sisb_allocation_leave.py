import itertools
from lxml import etree
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp
from datetime import timedelta,datetime, date


class AllocateLeavesRun(models.Model):
    _name = 'allocate.leaves.run'
    
    name          = fields.Char('Name',states={'draft':[('readonly',False)]})
    state         = fields.Selection([('draft','Draft'),('assign','Allocated'),('expired','Expired')],string="State",default='draft',states={'draft':[('readonly',False)]})
    year_id       = fields.Many2one('hr.year','Year',states={'draft':[('readonly',False)]})
    company_id    = fields.Many2one('res.company', string="Company")
    reset_month   = fields.Selection([(1,'January'),(2,'February'),(3,'March'),(4,'April'),(5,'May'),(6,'June'),(7,'July'),(8,'August'),(9,'September'),(10,'October'),(11,'November'),(12,'December')],string="Reset in Month",states={'draft':[('readonly',False)]})     
    batch_line_ids= fields.One2many('hr.holidays','allocation_run_id','Allocation Leaves',states={'draft':[('readonly',False)]})
    allocation_line_ids = fields.One2many('hr.holidays','allocation_run_id','Allocation Leaves',states={'draft':[('readonly',False)]},domain=[('type','=','allocated')])
    
    @api.multi
    def open_wizard(self):
        cr, uid, context = self.env.args
        if context is None:
            context = {}
        context = dict(context)

        context.update({'default_company_id': self.company_id.id,
                        'default_year_id': self.year_id.id,
                        'default_allocation_run_id':self.id
                       })
        return {'name': ('Allocate Leaves'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'allocate.leaves.employee',
                'type': 'ir.actions.act_window',
                'target': 'new',
        }
    
    @api.multi
    def button_close(self):
        self.state = 'assign'
        
    @api.multi
    def button_draft(self):
        self.state = 'draft'
        
    @api.multi
    def button_confirm(self):
        for item in self:
            for holiday in item.batch_line_ids:
                if holiday.state != 'validate':
                    holiday.button_approve(item)



    
class AllocationLeaveEmployee(models.Model):
    _name       ="allocate.leaves.employee"
    
    reset_month         = fields.Selection([(1,'January'),(2,'February'),(3,'March'),(4,'April'),(5,'May'),(6,'June'),(7,'July'),(8,'August'),(9,'September'),(10,'October'),(11,'November'),(12,'December')],string="Reset in Month")    
    company_id          = fields.Many2one('res.company', string="Company")
    employee_ids        = fields.Many2many('hr.employee', string='Employees')
    year_id             = fields.Many2one('hr.year','Year')
    allocation_run_id   = fields.Many2one('allocate.leaves.run','Allocation')
    

    # @api.multi
    # def check_structure_leave(self, emp_ids):
    #     not_emp_struct = []
    #     for rec in emp_ids:
    #         if not rec.leave_structure_id:
    #             not_emp_struct.append(rec.id)
    #             return not_emp_struct
    #         else:
    
    @api.multi
    def button_generate(self):
        leave_types = self.env['hr.holidays.status'].search([])
        leave_run = self.allocation_run_id
        hr_holiday_obj = self.env['hr.holidays']
        date_now = datetime.today()
        state ='draft'
        leave = []
        for leave_id in leave_types:
            if leave_id.id not in leave:
                leave.append(leave_id.id)
                print('leave = ', leave)
        for employee in self.employee_ids:
            if not employee.leave_structure_id:
                raise ValidationError(_("Please Set the Leave Structure For All Employee with the Red Highlight in Employees Line"))
            remaining_leaves = sum(left.current_leave for left in employee.emp_curr_leave_ids)
            check_prev_allocated = self.env['hr.holidays'].search([
                        ('employee_id','=',employee.id),
                        ('holiday_status_id','in',leave),
                        ('allocation_run_id','=',self.allocation_run_id.id),
                        ('type','=','allocated')
                        ])
            for structure in employee.leave_structure_id:
                for leave_types in structure.holiday_type_ids:
                    if len(check_prev_allocated) == 0:
                        # if leave_types.employee_type == 'female_staff':
                        #     if employee.gender != 'female':
                        #         continue
                        vals = self.generate_val('allocated', leave_types.leave_type.name, self.year_id.name, state, employee.id, leave_types.leave_type.id, 'allocated', leave_types.amount_to_allow)
                        self._cr.execute("INSERT INTO hr_holidays(name, state, employee_id, holiday_status_id, type, holiday_type, number_of_days, date_from1, date_to1, allocation_run_id, approved_by, date_allocate, approved_date)\
                                        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id\
                                        ",(vals['name'], vals['state'], vals['employee_id'], vals['holiday_status_id'], vals['type'], vals['holiday_type'], vals['number_of_days'], datetime.now().date(), datetime.now().date(), leave_run.id, self._uid, datetime.now().date(), datetime.now().date()))
                        all_leave = self._cr.fetchall()
                        print('all = ', all_leave)
                        self._cr.execute("SELECT number_of_days FROM hr_holidays WHERE id =%s",(all_leave[0]))
                        no_of_days = self._cr.fetchall()
                        print('no of days = ', no_of_days)
        
        
            



            # for type in leave_types:
            #     remaining_leaves = 0
            #     # if employee.first_leave_type_id and type.id == employee.first_leave_type_id.id:
            #     #     remaining_leaves = employee.remaining_leaves
            #     # else:
            #     #     if employee.second_leave_type_id and type.id == employee.second_leave_type_id.id:
            #     #         remaining_leaves = employee.remaining_leaves_second_leave_type
                
            #     # check_reset = self.env['hr.holidays'].search([
            #     #             ('employee_id','=',employee.id),
            #     #             ('holiday_status_id','=',type.id),
            #     #             ('allocation_run_id','=',self.allocation_run_id.id),
            #     #             ('type','=','remove')
            #     #             ])
            #     check_prev_allocated = self.env['hr.holidays'].search([
            #             ('employee_id','=',employee.id),
            #             ('holiday_status_id','=',type.id),
            #             # ('request_type','=','a'),
            #             ('allocation_run_id','=',self.allocation_run_id.id),
            #             ('type','=','allocated')
            #             ])            
            #     if type.employee_type ==  'all_staff':
            #         if not type.limit:
            #             if remaining_leaves != 0:
            #                 #reset
            #                 if len(check_reset) == 0:
            #                     vals = self.generate_val(
            #                     'reset',type.name,self.year_id.name,state,employee.id,
            #                     type.id,'remove',remaining_leaves
            #                     )
            #                     hr_holiday_obj.create(vals)
                    
            #             #add
            #             if len(check_allocation) == 0:
            #                 vals = self.generate_val( 'add',type.name,self.year_id.name,state,employee.id,
            #                 type.id,'add',type.max_leaves)
            #                 hr_holiday_obj.create(vals)
            #                 employee.write({'reset_year':date_now.year + 1})
                        
            #     elif type.employee_type ==  'female_staff':
            #         if employee.gender == 'female':
            #             if len(check_reset) == 0:
            #                 vals = self.generate_val(
            #                 'reset',type.name,self.year_id.name,state,employee.id,
            #                 type.id,'remove',remaining_leaves
            #                 )
            #                 hr_holiday_obj.create(vals)
                            
            #             if len(check_allocation) == 0:
            #                 vals = self.generate_val( 'add',type.name,self.year_id.name,state,employee.id,
            #                 type.id,'add',type.max_leaves)
            #                 hr_holiday_obj.create(vals)
            #                 employee.write({'reset_year':date_now.year + 1})
                
            #     elif type.employee_type == 'single':
            #         if employee.marital == 'single':
            #             if len(check_reset) == 0:
            #                 vals = self.generate_val(
            #                 'reset',type.name,self.year_id.name,state,employee.id,
            #                 type.id,'remove',remaining_leaves
            #                 )
            #                 hr_holiday_obj.create(vals)
                            
            #             if len(check_allocation) == 0:
            #                 vals = self.generate_val( 'add',type.name,self.year_id.name,state,employee.id,
            #                 type.id,'add',type.max_leaves)
            #                 hr_holiday_obj.create(vals)
            #                 employee.write({'reset_year':date_now.year + 1})
                            
            #     elif type.employee_type == 'married':
            #         if employee.marital == 'married':
            #             if len(check_reset) == 0:
            #                 vals = self.generate_val(
            #                 'reset',type.name,self.year_id.name,state,employee.id,
            #                 type.id,'remove',remaining_leaves
            #                 )
            #                 hr_holiday_obj.create(vals)
                            
                            
            #             if len(check_allocation) == 0:
            #                 vals = self.generate_val( 'add',type.name,self.year_id.name,state,employee.id,
            #                 type.id,'add',type.max_leaves)
            #                 hr_holiday_obj.create(vals)
            #                 employee.write({'reset_year':date_now.year + 1})
                        

                    
    
    def generate_val(self,type,leave_name,year,state,employee_id,holiday_status_id,leave_type,remaining_leaves,):
        vals = {}
        name = ''
        print('remaining_leaves = ', remaining_leaves, 'abs version = ', float("{:.16f}".format(abs(remaining_leaves))))
        if type == 'reset':
            name = _('Reset %s for year %s') % (leave_name,year)
        else:
            name = _('Assign Default %s for year %s') % (leave_name,year)

        vals = {'name': name,
                'state':state, 
                'employee_id': employee_id, 
                'holiday_status_id':holiday_status_id, 
                'type': leave_type,
                # 'request_type':'allocated',
                'approved_by': self._uid,
                'holiday_type': 'employee', 
                'number_of_days': float("{:.16f}".format(abs(remaining_leaves)))
                }
                # 'request_by_employee': False,
                # 'reset_allocation':True}
        return vals
        
       
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AllocationLeaveEmployee, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        context = self._context
        # reset_month = context.get('default_reset_month',False)
        company_id = context.get('default_company_id',False)
        doc = etree.XML(res['arch'])
        for node in doc.xpath("//field[@name='employee_ids']"):
            # node.set('domain', "[('id', '!=',1),('company_id','=',company_id)]")
            node.set('domain', "[('company_id','=',company_id)]") #For Test
            res['arch'] = etree.tostring(doc)
        return res


class hr_holidays_status(models.Model):
    _inherit = "hr.holidays.status"

    # max_leaves = fields.Float(string='Maximum Allowed', readonly=False)
    legal_leave = fields.Boolean('Legal Leave')
    attachment = fields.Boolean('Attachment File Required')
    claim_able = fields.Boolean('Claimable')
    compensated_days = fields.Boolean('Compensated Day')
    # employee_type = fields.Selection([
    #     ('all_staff','All Staff'),
    #     ('female_staff','Female Staff'),
    #     ('single','Staff with Marital Status Single'),
    #     ('married','Staff with Marital Status Married ')
    #     ],string="Employee Type")
    

class hr_holidays_current_leaves(models.Model):
    _name = "hr.holidays.curr.leaves"

    leave_type_id       = fields.Many2one('hr.holidays.status', string='Leave Type')
    employee_id         = fields.Many2one('hr.employee', string="Employee")
    total_curr_leave    = fields.Float(string='Total Leave')
    total_taken_leave   = fields.Float(string="Total Taken")
    # leave_detail_ids    = fields.One2many('hr.holidays')
    current_leave       = fields.Float(string="Leave Balance")
    holiday_id          = fields.Many2one('hr.holidays', string="Holiday")
    state = fields.Selection([
        ('draft','Draft'),
        ('validate','Approved')
    ], string="State")


class allocate_compensatory_days(models.Model):
    _name = "allocate.compensatory.days"

    name = fields.Char(string="Description")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    leave_type_id = fields.Many2one('hr.holidays.status', string="Leave Type" ,domain="[('compensated_days', '=', True)]", required=True)
    attendance_ids = fields.Many2many('hr.attendance', string="Compensated Day's")
    days_to_alloc = fields.Float("Allocated Days", digits=(16,11))
    state = fields.Selection([
        ('draft','Draft'),
        ('allocated','Allocated'),
    ], string="State", default='draft')

    @api.onchange('attendance_ids')
    def get_day(self):
        if self.attendance_ids:
            self.days_to_alloc = float(len(self.attendance_ids))

    @api.multi
    def confirmation_wizard(self):
        print('dasdads')
        pass

    @api.multi
    def allocate_compensated_days(self):
        emp_curr_leave = self.env['hr.holidays.curr.leaves']
        if not self.attendance_ids:
            raise ValidationError(_("No data to proccess"))
        else:
            for att in self.attendance_ids:
                att.compensated_days = False
            compensated = len(self.attendance_ids)
            for rec in self.employee_id:
                leave_to_allocate = rec.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == self.leave_type_id)
                if leave_to_allocate:
                    leave_to_allocate.total_curr_leave += float(compensated)
                    leave_to_allocate.state = 'validate'
                    return self.write({'state': 'allocated'})
                if not leave_to_allocate:
                    emp_curr_leave.create({
                        'leave_type_id': self.leave_type_id.id,
                        'employee_id': rec.id,
                        'total_curr_leave': float(compensated),
                        'state': 'validate',
                    })
                    return self.write({'state': 'allocated'})