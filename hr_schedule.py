from openerp import api, models, fields, _
from datetime import date, datetime
from openerp.exceptions import ValidationError, Warning, RedirectWarning
from .utility.count_date import date_range
from .utility.utils import hour_float_to_time as hftt
import pytz


DAYOFWEEK_SELECTION = [('0','Monday'),
                       ('1','Tuesday'),
                       ('2','Wednesday'),
                       ('3','Thursday'),
                       ('4','Friday'),
                       ('5','Saturday'),
                       ('6','Sunday'),
]

class hr_schedule_allocation(models.Model):
    _name = "hr.schedule.allocation"
    _inherit = ['mail.thread']
    _order = "date_from desc"

    name            = fields.Char(string="Name", default="/", track_visibility="onchange")
    responsible_id  = fields.Many2one('hr.employee', string="Responsible", track_visibility="onchange")
    employee_ids    = fields.Many2many('hr.employee', string="Employee List")
    company_id      = fields.Many2one('res.company', string="Company", track_visibility="onchange")
    date_from       = fields.Date(string="From", track_visibility="onchange")
    date_to         = fields.Date(string="To", track_visibility="onchange")
    department_id   = fields.Many2one('hr.department', string="Department")
    shift_id        = fields.Many2one('work.time.structure', string="Shift", track_visibility="onchange")
    employee_shift_ids  = fields.One2many('hr.schedule.running.shift', 'reference_id', string="Employee Shift")
    cancel_before   = fields.Boolean('Cancelled')
    count_gener_shift   = fields.Integer(string="Generated Shift", compute='_count_gener_shift')
    count_shift_list    = fields.Integer(string="Shift List", compute='_count_shift_list')
    state           = fields.Selection([
                                        ('draft','Draft'),
                                        ('cancel','Cancelled'),
                                        ('submitted','Submitted'),
                                        ], string="State", default="draft", track_visibility="onchange")
    rel_company_id  = fields.Many2one('res.company', string="Company", related="company_id")   
    rel_department_id   = fields.Many2one('hr.department', string="Department", related="department_id")


    @api.one
    def _count_gener_shift(self):
        self.count_gener_shift = len(self.employee_shift_ids.filtered(lambda x: x.state == 'submitted'))

    @api.one
    def _count_shift_list(self):
        shift = 0
        if self.employee_shift_ids:
            for rec in self.employee_shift_ids.filtered(lambda x: x.state == 'submitted'):
                for l in rec.shift_list_ids:
                    shift += 1
        self.count_shift_list = shift
    
    @api.multi
    def group_generated_shift(self):
        print('self = ', self)
        return {'name'      : _('Change Shift'),
                'type'      : 'ir.actions.act_window',
                'res_model' : 'hr.schedule.running.shift',
                # 'view_id'   : self.env.ref('sisb_hr.hr_schedule_running_shift_tree_view').id,
                # 'res_id'    : late_wizard,
                'view_type' : 'form',
                'view_mode' : 'tree,form',
                'nodestroy' : True,
                'context'   : {'search_default_reference_id': self.id},
                # 'domain'    : {'reference_id': [('id','=',self.id)]},
                'target'    : 'current',
                }
    
    @api.multi
    def group_shift_list(self):
        return {'name'      : _('Change Shift'),
                'type'      : 'ir.actions.act_window',
                'res_model' : 'hr.schedule.shift.list',
                # 'view_id'   : self.env.ref('sisb_hr.hr_schedule_shift_list_view').id,
                # 'res_id'    : late_wizard,
                'view_type' : 'form',
                'view_mode' : 'tree,form',
                'nodestroy' : True,
                'context'   : {'search_default_source_shift_id': self.id},
                # 'domain'    : {'source_shift_id': [('id','=',self.id)]},
                'target'    : 'current',
                }

    @api.onchange('responsible_id')
    def onchange_responsible(self):
        if self.responsible_id:
            self.company_id = self.responsible_id.company_id
            self.department_id = self.responsible_id.department_id


    @api.model
    def create(self, vals):
        company_id = self.env['res.company'].search([('id','=',vals.get('company_id'))])
        code = ''
        if company_id.name == "SISB Public Company Limited":
            code = 'HQ'
        elif company_id.name == "Singapore International School Chiangmai":
            code = 'CH'
        elif company_id.name == "Singapore International School Ekkamai":
            code = 'EK'
        elif company_id.name == "Singapore International School of Bangkok":
            code = 'PU'
        elif company_id.name == "Singapore International School Suvarnabhumi":
            code = 'SV'
        elif company_id.name == "Singapore International School Thonburi":
            code = 'TH'  
        elif company_id.name == "SISB SIRI Company Limited":
            code = 'SIRI'

        print('code = ', code)
        default_seq = self.env['ir.sequence'].sudo().search([('code','=', self._name)], limit=1)
        if default_seq:
            default_seq.update({'prefix': 'SHIFT/' + code + '/'})
        if vals.get('name', '/') == '/' or False:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.schedule.allocation') or '/'
        res = super(hr_schedule_allocation, self).create(vals)
        print('vals2 = ', vals)
        return res


    @api.model
    def default_get(self, fields):
        res = super(hr_schedule_allocation, self).default_get(fields)
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if 'employee_id' in fields:
            res.update({'employee_id': employee_rec.id})
        return res


    @api.one
    def reassign(self):
        self.write({'state': 'draft'})

    @api.multi
    def avoid_overlap(self, employee, date):
        overlap = False
        shift_list_obj = self.env['hr.schedule.shift.list']
        check_schedule = shift_list_obj.search([('employee_id', '=', employee.id),('name','=', date)])
        if check_schedule:
            return check_schedule.running_shift_id
        elif not check_schedule:
            return overlap
    
    @api.multi
    def create_shift(self, employee_id, shift_id):
        running_shift_obj = self.env['hr.schedule.running.shift']
        shift_list_obj = self.env['hr.schedule.shift.list']
        vals = {}
        for i in employee_id:
            vals['employee_id'] = i.id
            vals['company_id'] = i.company_id.id
            vals['department_id'] = i.department_id.id
        for k in shift_id:
            vals['date_from']   = k.date_from
            vals['date_to']     = k.date_to
            vals['shift_id']    = k.shift_id.id
            vals['responsible_id']  = k.responsible_id.id
            vals['reference_id']    = k.id
            vals['state']           = 'submitted'
        shift_assign = running_shift_obj.create(vals)
        for date in date_range(vals['date_from'], vals['date_to'], step=1):
            shift_list_obj.create({
                'name': date,
                'employee_id': vals['employee_id'],
                'notes': 'Allocated Shift',
                'running_shift_id': shift_assign.id,
                'shift_id':  vals['shift_id'],
            })
        return True


    @api.multi
    def check_employee_shift(self, employee, date_from, date_to, alloc_obj):
        overlap = False
        for date in date_range(date_from, date_to, step=1):
            self._cr.execute("SELECT id FROM hr_schedule_running_shift WHERE employee_id = %s AND state = %s AND reference_id != %s AND %s BETWEEN date_from AND date_to",(employee.id, 'submitted', alloc_obj.id, date,))
            check_overlap = self._cr.fetchall()
            if check_overlap:
                overlap = True
                break
        return check_overlap



    @api.multi
    def assign_shift(self):
        if self.employee_ids:
            for rec in self.employee_ids:
                overlap = self.check_employee_shift(rec, self.date_from, self.date_to, self)
                if overlap:
                    exist_shift = self.env['hr.schedule.running.shift'].search([('id','=',overlap[0][0])])
                    raise ValidationError(_("You try to Overlap an Exist Shift for Employee {}. Shift for Employee {} from {} to {} is already Generated From {}").format(exist_shift.employee_id.name, exist_shift.employee_id.name, exist_shift.date_from, exist_shift.date_to, exist_shift.reference_id.name))

        elif not self.employee_ids:
            raise ValidationError(_("You must Fill at least 1 Employee to Employee list to Generate Shift"))
        if self.cancel_before:
            employee_list = []
            shift_to_delete = []
            assigned_shift = []
            for rec in self.employee_ids:
                employee_list.append(rec.id)
            for r in self.employee_shift_ids:
                if r.employee_id.id in employee_list:
                    r.state = 'submitted'
                    assigned_shift.append(r.employee_id.id)
                else:
                    shift_to_delete.append(r.id)
            unassign_shift = [i for i in employee_list if i not in assigned_shift]
            if unassign_shift:
                employee_ids = self.env['hr.employee'].search([('id','in',unassign_shift)])
                for employ in employee_ids:
                    self.create_shift(employ, self)
            if shift_to_delete:
                self._cr.execute("DELETE FROM hr_schedule_running_shift WHERE id in %s",(tuple(shift_to_delete),))
        else:
            assign_shift = []
            employee_list = []
            if self.employee_shift_ids:
                shifted_employee = self.employee_shift_ids.filtered(lambda x: x.state in ['submitted','cancel'])
                for emp_id in shifted_employee:
                    assign_shift.append(emp_id.employee_id.id)
            for rec in self.employee_ids:
                employee_list.append(rec.id)
            running_shift_obj = self.env['hr.schedule.running.shift']
            shift_list_obj = self.env['hr.schedule.shift.list']
            if assign_shift:
                if set(assign_shift) == set(employee_list):
                    for rec in self.employee_shift_ids:
                        rec.state == 'submitted'
                    return self.write({'state': 'submitted'})
                elif set(assign_shift) != set(employee_list):
                    if len(assign_shift) < len(employee_list):
                        for rec in self.employee_ids.filtered(lambda x: x.id not in assign_shift):
                            # self.create_shift(employ, self.id)
                            vals = {}
                            vals['employee_id'] = rec.id
                            vals['date_from']   = self.date_from
                            vals['date_to']     = self.date_to
                            vals['shift_id']    = self.shift_id.id
                            vals['responsible_id']  = self.responsible_id.id
                            vals['reference_id']    = self.id
                            vals['company_id']      = rec.company_id.id
                            vals['department_id']   = rec.department_id.id
                            vals['state']           = 'submitted'
                            shift_assign = running_shift_obj.create(vals)
                            print('shift_assign = ', shift_assign)
                            for date in date_range(self.date_from, self.date_to, step=1):
                                shift_list_obj.create({
                                    'name': date,
                                    'employee_id': rec.id,
                                    'notes': 'Allocated Shift',
                                    'running_shift_id': shift_assign.id,
                                    'shift_id':  self.shift_id.id,
                                    'state': 'submitted'
                                })
                    elif len(assign_shift) > len(employee_list):
                        shift_id = []
                        shift_to_delete = self.employee_shift_ids.filtered(lambda x: x.employee_id.id not in employee_list)
                        for l in shift_to_delete:
                            shift_id.append(l.id)
                        self.cr_execute("DELETE FROM hr_schedule_running_shift WHERE id in %s",(tuple(shift_id),))
            elif not assign_shift:
                print('here')
                for rec in self.employee_ids:
                    vals = {}
                    vals['employee_id'] = rec.id
                    vals['date_from']   = self.date_from
                    vals['date_to']     = self.date_to
                    vals['shift_id']    = self.shift_id.id
                    vals['responsible_id']  = self.responsible_id.id
                    vals['reference_id']    = self.id
                    vals['company_id']      = rec.company_id.id
                    vals['department_id']   = rec.department_id.id
                    vals['state']           = 'submitted'
                    shift_assign = running_shift_obj.create(vals)
                    print('shift_assign = ', shift_assign)
                    for date in date_range(self.date_from, self.date_to, step=1):
                        shift_list_obj.create({
                            'name'          : date,
                            'employee_id'   : rec.id,
                            'notes'         : 'Allocated Shift',
                            'running_shift_id': shift_assign.id,
                            'shift_id'      :  self.shift_id.id,
                            'state'         : 'submitted'
                        })
        return self.write({'state': 'submitted'})
                

    @api.multi
    def cancel_shift(self):
        employee_list = []
        for rec in self.employee_shift_ids.filtered(lambda x: x.state == 'submitted'):
            employee_list.append(rec.id)
        return {
                'name'      : _('Cancel Shift'),
                'type'      : 'ir.actions.act_window',
                'res_model' : 'wiz.cancel.shift',
                # 'view_id'   : view_id,
                # 'res_id'    : late_wizard,
                'view_type' : 'form',
                'view_mode' : 'form',
                'nodestroy' : True,
                'context'   : {'default_shift_source_id': self.id},
                'domain'    : {'employee_shift_ids': [('id','in', employee_list)]},
                'target'    : 'new',
                } 

            


class hr_schedule_running_shift(models.Model):
    _name = "hr.schedule.running.shift"
    _inherit = ['mail.thread']
    _order= "date_from desc"

    name            = fields.Char("Name", default="/", track_visibility="onchange")
    date_from       = fields.Date(string="From", track_visibility="onchange")
    date_to         = fields.Date(string="To", track_visibility="onchange")
    employee_id     = fields.Many2one('hr.employee', string="Employee", track_visibility="onchange")
    shift_id        = fields.Many2one('work.time.structure', string="Shift", track_visibility="onchange")
    responsible_id  = fields.Many2one('hr.employee', string="Responsible", track_visibility="onchange")
    reference_id    = fields.Many2one('hr.schedule.allocation', string="Allocated From", ondelete='cascade', track_visibility="onchange")
    department_id   = fields.Many2one('hr.department', string="Department")
    company_id      = fields.Many2one('res.company', string="Company")
    shift_list_ids  = fields.One2many('hr.schedule.shift.list', 'running_shift_id', string="Shift Detail List")
    state           = fields.Selection([
                                        ('draft','Draft'),
                                        ('cancel','Cancelled'),
                                        ('submitted','Submitted'),
                                        ], string="State", default="draft", track_visibility="onchange")

    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/' or False:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.schedule.running.shift') or '/'
        print('vals2 = ', vals)
        return super(hr_schedule_running_shift, self).create(vals)
    
    @api.multi
    def uncancel_shift(self):
        return self.write({'state':'submitted'})

class hr_schedule_shift_list(models.Model):
    _name = "hr.schedule.shift.list"
    _order= "name desc"

    name                = fields.Date(string="Date")
    employee_id         = fields.Many2one('hr.employee', string="Employee")
    employee_name       = fields.Char("Employee(*)", related="employee_id.name", store=True)
    responsible_id      = fields.Many2one('hr.employee', string="Responsible", related="running_shift_id.responsible_id", store=True)
    responsible_name    = fields.Char("Responsible(*)", related="responsible_id.name", store=True)
    notes               = fields.Text(string="Notes")
    running_shift_id    = fields.Many2one('hr.schedule.running.shift', string="Shift Number", ondelete="cascade", store=True)
    shift_number        = fields.Char("Shift Number(*)", related="running_shift_id.name", store=True)
    source_shift_id     = fields.Many2one('hr.schedule.allocation', string="Source Document", related="running_shift_id.reference_id", store=True)
    source_shift_name   = fields.Char("Source Document", related="source_shift_id.name", store=True)
    shift_id            = fields.Many2one('work.time.structure', string="Shift")
    shift_name          = fields.Char("Shift Name(*)", related="shift_id.name", store=True)
    state               = fields.Selection([
                                            ('draft','Draft'),
                                            ('cancel','Cancelled'),
                                            ('submitted','Submitted'),
                                            ], string="State", default="draft")

    # @api.multi
    # def name_get(self):
    #     res = []
    #     for reg in self:
    #         shift = reg.student_id.name #+"[" + reg.division_id.name + "]" 
    #         res.append((reg.id,shift))
    #     return res


    @api.multi
    def change_shift(self):
        print('test')
        return {
                'name'      : _('Change Shift'),
                'type'      : 'ir.actions.act_window',
                'res_model' : 'wiz.change.shift',
                # 'view_id'   : view_id,
                # 'res_id'    : late_wizard,
                'view_type' : 'form',
                'view_mode' : 'form',
                'nodestroy' : True,
                'context'   : {'default_current_shift_id': self.shift_id.id, 
                                'default_employee_id': self.employee_id.id,
                                'default_date': self.name},
                # 'domain'    : {'new_shift_id': [('self','=',self.shift_id.id)]},
                'target'    : 'new',
                }
    

class hr_schedule_shift_request(models.Model):
    _name       = "hr.schedule.shift.request"
    _inherit    = 'mail.thread'

    name            = fields.Char(string="Number", default="/")
    employee_id     = fields.Many2one('hr.employee', string="Employee", track_visibility="onchange")
    description     = fields.Char('Description', track_visibility="onchange")
    date_from       = fields.Date("From", track_visibility="onchange")
    date_to         = fields.Date("To", track_visibility="onchange")
    shift_id        = fields.Many2one('work.time.structure', string="Shift", track_visibility="onchange")
    shift_list_ids  = fields.One2many('shift.list.request', 'request_id', string="Shift List")
    responsible_id  = fields.Many2one('hr.employee', string="Supervisor", track_visibility="onchange")
    related_responsible_id = fields.Many2one('hr.employee', string="Supervisor", related="responsible_id")
    shift_source_id = fields.Many2one('hr.schedule.allocation', string="Shift Source Number", readonly=True, store=True)
    state           = fields.Selection([
       ('draft','Draft'),
       ('cancel','Cancelled'),
       ('1appv','Wait For Approval'),
       ('appv',' Approved'),
       ('reject','Rejected'),
   ], string="State", default='draft', track_visibility="onchange")

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/' or False:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.schedule.shift.request') or '/'
        return super(hr_schedule_shift_request, self).create(vals)

    @api.one
    def write(self, vals):
        result = super(hr_schedule_shift_request, self).write(vals)
        if vals.get('related_responsible_id'):
            vals['responsible_id'] = vals.get('related_responsible_id')
        return result

   


    @api.onchange('employee_id')
    def onchange_employee(self):
        if self.employee_id:
            if self.employee_id.supervisor_id:
                self.responsible_id = self.employee_id.supervisor_id.id
            elif not self.employee_id.supervisor_id:
                if self.employee_id.supervisor_lvl2_id:
                    self.responsible_id = self.employee_id.supervisor_lvl2_id.id
                else:
                    raise ValidationError("This Employee doesn't have supervisor, please set the Supervisor for this Employee first")
        return {
            'domain':{'shift_id': [('company_id','=',self.employee_id.company_id.id)]}
        }

    @api.constrains('date_from','date_to')
    def date_constraint(self):
        if self.date_from > self.date_to:
            raise ValidationError(_("Date To must be greater than Date From"))


    @api.multi
    def submit_req(self):
        date_from = self.date_from
        date_to = self.date_to
        alloc_schedule = self.env['hr.schedule.allocation']
        req_line_obj = self.env['shift.list.request']
        check_overlap = alloc_schedule.check_employee_shift(self.employee_id, date_from, date_to)
        print('check_overlap = ', check_overlap)
        if check_overlap:
            exist_shift = self.env['hr.schedule.running.shift'].search([('id','=',check_overlap[0][0])])
            # raise ValidationError(_("Shift for Employee {} from {} to {} is already Generated From {}").format(exist_shift.employee_id.name, exist_shift.date_from, exist_shift.date_to, exist_shift.reference_id.name))
            raise ValidationError(_("You try to Overlap an Exist Shift for Employee {}.\n"
                                    "Shift for Employee {} from {} to {} is already Generated From {}").format(exist_shift.employee_id.name, exist_shift.employee_id.name, exist_shift.date_from, exist_shift.date_to, exist_shift.reference_id.name))
        elif not check_overlap:
            self._cr.execute("DELETE FROM shift_list_request WHERE request_id = %s",(self.id,))
            for date in date_range(date_from, date_to, step=1):
                req_line_obj.create({
                    'name': date,
                    'employee_id': self.employee_id.id,
                    'shift_id': self.shift_id.id,
                    'state': '1appv',
                    'request_id': self.id
                })
        # if self.responsible_id:
        #     self.write({'responsible_id': self.responsible_id.id})
        return self.write({'state': '1appv'})
    

    @api.multi
    def cancel_req(self):
        for rec in self.shift_list_ids:
            rec.state = 'cancel'
        return self.write({'state': 'cancel'})

    @api.multi
    def appv_req(self):
        schedule_alloc_obj = self.env['hr.schedule.allocation']
        validated_req = schedule_alloc_obj.create({
            'responsible_id'    : self.responsible_id.id,
            'date_from'         : self.date_from,
            'date_to'           : self.date_to,
            'shift_id'          : self.shift_id.id,
            'company_id'        : self.responsible_id.company_id.id,
            'employee_ids'      : [(4, self.employee_id.id, 0)],
        })
        self.shift_source_id = validated_req
        validated_req.assign_shift()
        for rec in self.shift_list_ids:
            rec.state = 'appv'
        return self.write({'state': 'appv'})

    @api.one
    def set_draft(self):
        return self.write({'state': 'draft'})
    @api.multi
    def reject_req(self):
        for rec in self.shift_list_ids:
            rec.state = 'reject'
        return self.write({'state': 'reject'})


class shift_list_request(models.Model):
    _name = "shift.list.request"

    name        = fields.Date("Date")
    employee_id = fields.Many2one('hr.employee','Employee')
    shift_id    = fields.Many2one('work.time.structure', string="Shift")
    request_id  = fields.Many2one('hr.schedule.shift.request', string="Request", ondelete='cascade')
    state       = fields.Selection([
       ('draft','Draft'),
       ('cancel','Cancelled'),
       ('1appv','Wait For Approval'),
       ('appv',' Approved'),
       ('reject','Rejected')
   ], string="State", default='draft')

    # @api.one
    # def write(self, vals):
    #     result = super(hr_schedule_shift_request, self).write(vals)
    #     if vals.get('related_responsible_id'):
    #         vals['responsible_id'] = vals.get('related_responsible_id')
    #     return result
   

class hr_schedule_change_request(models.Model):
    _name = "hr.schedule.change.request"
    _inherit = 'mail.thread'
    _order = 'date desc'

    name                = fields.Char("Reason", required="1", track_visibility="onchange")
    date                = fields.Date("Date", default=datetime.today(), readonly="1", track_visibility="onchange")
    employee_id         = fields.Many2one('hr.employee', string="Employee", track_visibility="onchange")
    responsible_id      = fields.Many2one('hr.employee', string="Responsible", track_visibility="onchange")
    related_responsible_id = fields.Many2one('hr.employee', string="Responsible(*)", related="responsible_id")
    change_shift_ids    = fields.One2many('hr.schedule.change.shift.line', 'change_req_id', string="Change Request List")
    state               = fields.Selection([
                            ('draft','Draft'),
                            ('cancel','Cancel'),
                            ('reject','Rejected'),
                            ('1appv','Wait For Approval'),
                            ('appv','Approved')
                        ], default='draft', string="State", track_visibility="onchange")


    @api.onchange('employee_id')
    def onchange_employee(self):
        if self.employee_id:
            if self.employee_id.supervisor_id:
                self.responsible_id = self.employee_id.supervisor_id.id
            elif not self.employee_id.supervisor_id:
                if self.employee_id.supervisor_lvl2_id:
                    self.responsible_id = self.employee_id.supervisor_lvl2_id.id
                else:
                    raise ValidationError("This Employee doesn't have supervisor, please set the Supervisor for this Employee first")
        # return {
        #     'domain':{'shift_id': [('company_id','=',self.employee_id.company_id.id)]}
        # }
    
    @api.one
    def write(self, vals):
        result = super(hr_schedule_change_request, self).write(vals)
        if vals.get('related_responsible_id'):
            vals['responsible_id'] = vals.get('related_responsible_id')
        return result

    @api.multi
    def submit_change_req(self):
        overtime_list_obj = self.env['overtime.list.line']
        overtime_request = []
        if not self.change_shift_ids:
            raise ValidationError(_("You Don't Fill the Change Shift List, kindly to filled it with the shift you want to change"))
        for rec in self.change_shift_ids:
            # ot_req = overtime_list_obj.search([('date_overtime', '=', rec.name),('')])
            rec.state = '1appv'
        return self.write({'state':'1appv'})

    @api.multi
    def approve_change_req(self):
        running_shift_obj = self.env['hr.schedule.shift.list']
        for rec in self.change_shift_ids:
            rec.running_shift_id.update({
                'shift_id': rec.new_shift_id.id,
                'notes': self.name,
            })
            rec.state = 'appv'
        return self.write({'state': 'appv'})



    
class hr_schedule_change_shift_line(models.Model):
    _name = "hr.schedule.change.shift.line"

    name                = fields.Date('Date')
    running_shift_id    = fields.Many2one('hr.schedule.shift.list', string="Current Shift")
    change_req_id       = fields.Many2one('hr.schedule.change.request', string="Change Shift Parent", ondelete='cascade')
    current_shift_id    = fields.Many2one('work.time.structure', string="Current shift")
    related_current_shift = fields.Many2one('work.time.structure', string="Related Current Shift", related="current_shift_id")
    employee_id         = fields.Many2one('hr.employee', string="Employee")
    new_shift_id        = fields.Many2one('work.time.structure', string="New shift")
    state               = fields.Selection([
                            ('draft','Draft'),
                            ('cancel','Cancel'),
                            ('reject','Rejected'),
                            ('1appv','Wait For Approval'),
                            ('appv','Approved')
                        ], default='draft', string="State")

    
    @api.one
    def write(self, vals):
        result = super(hr_schedule_change_shift_line, self).write(vals)
        if vals.get('related_current_shift'):
            vals['current_shift_id'] = vals.get('related_current_shift')
        return result
   

    @api.onchange('name')
    def get_current_running_shift(self):
        print('employee_id = ', self.employee_id)
        running_shift_obj = self.env['hr.schedule.shift.list']
        if self.name:
            self._cr.execute("SELECT id FROM hr_schedule_shift_list WHERE name = %s AND state = %s AND employee_id = %s",(self.name, 'submitted', self.employee_id.id))
            curr_shift = self._cr.fetchall()
            print('curr_shift = ', curr_shift)
            if not curr_shift:
                raise ValidationError(_("You Don't Have Shift at {}").format(self.name))
            else:
                shift = running_shift_obj.search([('id','=',curr_shift[0][0])])
                self.running_shift_id = shift.id
                self.current_shift_id = shift.shift_id.id



    @api.onchange('employee_id')
    def onchange_employee(self):
        company = ''
        if self.employee_id:
            company = self.employee_id.company_id
        print('company = ', company)
        return {'domain': {
                'new_shift_id' : [('company_id', '=', company.id)]
            }
        }

    @api.onchange('current_shift_id')
    def onchange_new_shift(self):
        if self.current_shift_id:
            return {'domain': 
                {'new_shift_id': [('id','!=',self.current_shift_id.id)]}
            }


class SISBWorkTimeStructure(models.Model):
    _name = "work.time.structure"

    name                = fields.Char(string="Name")
    shift_code          = fields.Char(string="Shift Code")
    punch_in            = fields.Float(string="Punch In")
    punch_out           = fields.Float(string="Punch Out")
    start_hour          = fields.Float(string="Start")
    end_hour            = fields.Float(string="End")
    start_break_hour    = fields.Float(string="Start Break")
    end_break_hour      = fields.Float(string="End Break")
    total_break         = fields.Float(string="Total Break")
    total_wk_hour       = fields.Float(string="Total Work Hours")
    late_tolerance      = fields.Float(string="Late Tolerance")
    company_id          = fields.Many2one('res.company', string="Company")
    default_timezone    = fields.Selection('_tz_get', string='Timezone')
    shift_option        = fields.Selection([
                                           ('normal','Normal'),
                                           ('night','Night Shift'),
                                           ('half','Half Day')
                                            ], string="Type", default='normal')
                                            

    notes = fields.Text(string="Notes")
    ## Day Name
    day_of_wewks_ids = fields.One2many('day.of.week', 'work_time_id', string="Day of Week")
    # monday = fields.Boolean(string="Monday")
    # tuesday = fields.Boolean(string="Tuesday")
    # wednesday = fields.Boolean(string="Wednesday")
    # thursday = fields.Boolean(string="Thursday")
    # friday = fields.Boolean(string="Friday")
    # saturday = fields.Boolean(string="Saturday")
    # sunday = fields.Boolean(string="Sunday")
    

    @api.model
    def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
        return [(tz,tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

    @api.model
    def default_get(self, fields):
        res = super(SISBWorkTimeStructure, self).default_get(fields)
        # emp_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        work_day_obj = self.env['day.of.week']
        wk_day = []
        if 'notes' in fields:
            res.update({'notes': "N =  Normal work Day, H = Holiday. if there's day not appear in the above list, system will set it as a Holiday in this Schedule"})
        if 'day_of_wewks_ids' in fields:
            # default_day = ''
            # for day in DAYOFWEEK_SELECTION:
            #     if int(day[0]) <= 4:
            #         default_day = work_day_obj.create({
            #             'day_of_week': unicode(day[0]),
            #             'options': unicode('normal'),
            #             'work_time_id': self.id,
            #         })
            #     else:
            #         default_day = work_day_obj.create({
            #             'day_of_week': unicode(day[0]),
            #             'options': unicode('holiday'),
            #             'work_time_id': self.id,
            #         })
            #     wk_day.append(default_day.id)
            # print('wk_day = ', wk_day)
            # res.update({'day_of_wewks_ids': [(6, 0, wk_day)]})
            for day in DAYOFWEEK_SELECTION:
                print('day = ', day[0], 'type = ', type(day[0]))
                if int(day[0]) <= 4:
                    print('here1')
                    line = (0, 0, {
                        'day_of_week': unicode(day[0]),
                        'options': unicode('normal')
                    })
                    wk_day.append(line)
                else:
                    print('here2')
                    line = (0, 0, {
                        'day_of_week': unicode(day[0]),
                        'options': unicode('holiday')
                    })
                    wk_day.append(line)
            res.update({'day_of_wewks_ids': wk_day} )
            
        return res

    @api.constrains('start_hour','end_hour','start_break_hour','end_break_hour','shift_option')
    def hour_rule(self):
        if self.shift_option != 'night':
            if self.start_hour >= self.end_hour:
                raise ValidationError(_("Start Hour cannot be greater than End Hour"))
        # if self.start_break_hour >= self.end_break_hour:
        #     raise ValidationError(_("Start Break Hour cannot be greater than End Break Hour"))

    @api.one
    def test_function(self):
        day = 1

        for rec in self.day_of_wewks_ids:
            print('all_day = ', rec.day_of_week, 'Type = ', type(rec.day_of_week))
            print('option = ', rec.options , 'Type = ', type(rec.options))
            if int(rec.day_of_week) == 0:
                print('Monday')
            else:
                print('Just Test')

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = rec.name
            start = hftt(rec.start_hour)
            end = hftt(rec.end_hour)
            res.append((rec.id, "%s [%s - %s]" %(name, start,end)))
        return res

class day_of_week(models.Model):
    _name = "day.of.week"

    day_of_week = fields.Selection(DAYOFWEEK_SELECTION, 'Day of Week')
    options = fields.Selection([
        ('normal','N'),
        ('holiday','H')
    ], string="Options", required=True)
    work_time_id = fields.Many2one('work.time.structure', string="Work Time")