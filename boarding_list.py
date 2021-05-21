from openerp import models, fields, api, _
from datetime import datetime, date


class SISBHRBoardingList(models.Model):
    _name = "hr.boarding.list"
    _description = "HR Boarding List"

    sequence = fields.Integer(string="Sequence")
    category = fields.Char('Categ')
    name = fields.Char(string="Item")
    parent_item = fields.Many2one('hr.boarding.list', string="Parent Item")
    code = fields.Char(string="Code")
    responsible = fields.Selection([
                                        ('department','Department'),
                                        ('dept_mgr','Department Manager')
                                    ], string="Responsible")
    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string="Company")
    note = fields.Text("Note")
    

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            if rec.parent_item:
                result.append((rec.id, "{}/{}".format(rec.parent_item.name, rec.name)))
            else:
                result.append((rec.id, "{}".format(rec.name)))
        return result

    @api.onchange('parent_item','responsible')
    def get_dept(self):
        if self.parent_item:
            dept_id = self.parent_item.department_id
            print('dept_id = ', dept_id)
            self.department_id = self.parent_item.department_id
            # self.department_id = self.parent_item.department_id
            return {'domain': {
                'department_id': [('id','=', dept_id.id)]
                }
            }
        if not self.parent_item:
            all_dept = self.env['hr.department'].search([])
            all_id = []
            for id in all_dept:
                all_id.append(id.id)
            return {'domain': {
                'department_id': [('id','in', all_id)]
                }
            }
        if self.responsible == 'dept_mgr':
            self.department_id = False
        


    @api.model
    def create(self, vals):
        res = super(SISBHRBoardingList, self).create(vals)
        if 'department_id' in vals:
            vals.update({'department_id': vals.get('department_id')})
        return res
    
    @api.multi
    def write(self, vals):
        res = super(SISBHRBoardingList, self).write(vals)
        if 'department_id' in vals:
            vals.update({'department_id': vals.get('department_id')})
        return res


class SISBHRBoardingListLine(models.Model):
    _name = "hr.boarding.list.line"
    _description = "HR Boarding List"

    name = fields.Char(string="Description")
    req = fields.Boolean(string="Request", store=True)
    # requested = fields.Boolean(string="Requested", store=True)
    req_date = fields.Date(string="Request Date")
    sequence = fields.Integer(string="Sequence")
    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string="Company")
    note = fields.Text("Note")
    visa_no = fields.Char(string="Visa No")
    teaching_license = fields.Char(string="Teaching License")
    visa_exp_date = fields.Date(string="Exp Date")
    teaching_license_exp_date = fields.Date(string="Exp Date")
    passport_id_exp_date = fields.Date(string="Exp Date")
    boarding_list_id = fields.Many2one('hr.employee', string="ON Boarding Item")
    off_boarding_list_id = fields.Many2one('hr.employee', string="OFF Borading Item")
    amount = fields.Integer(string="Amount")
    transfer_emp_id = fields.Many2one('hr.employee.transfer', "Employee Transfer")
    resign_boarding_list_id = fields.Many2one('hr.resignation', string="Boardig List Off")
    code = fields.Char(string="Code")
    is_received = fields.Boolean("Received")
    date_is_received = fields.Date(string="Received Date")
    is_returned = fields.Boolean("Returned")
    date_is_returned = fields.Date(string="Return Date")
    boarding_id = fields.Many2one('hr.boarding.list', string="Name")

    @api.onchange('code')
    def set_boarding_list_code(self):
        if self.name:
            self.code = self.boarding_id.code

    @api.onchange('is_received','is_returned')
    def toggle_item(self):
        if not self.is_received:
            self.date_is_received = False
        if not self.is_returned:
            self.date_is_returned = False


    @api.multi
    def get_emp(self):
        emp = self.env['hr.employee'].search([('user_id','=', self._uid)])
        name = ''
        for rec in emp:
            name = rec.name
        print('name = ', name)
        return name

    @api.one
    def send_board_email(self):
        template = self.env['ir.model.data'].get_object('sisb_hr', 'email_request_for_boarding_list')
        print('template = ', template)
        if template:
            mail_id = template.send_mail(self.id)
            mail = self.env['mail.mail'].sudo().browse(mail_id)
            print('mail = ', mail)
            if mail:
                mail.send()


    @api.multi
    def get_url(self):
        print('self = ', self)
        emp = self.env['hr.employee'].search([('user_id','=', self._uid)])
        print('emp = ', emp)
        emp_id = False
        part_obj = self.env['res.partner']
        url = part_obj.get_url(emp_id, emp)
        print('url = ', url)
        return url

    @api.model
    def get_email_to(self):
        user_group = self.env['res.users'].has_group('base.group_hr_user')
        user_groups = self.env.ref('v8_website_support.hide_menus_hr')
        partner_list = [usr.partner_id.name for usr in user_groups.users if usr.partner_id.email]
        email_list = [usr.partner_id.email for usr in user_groups.users if usr.partner_id.email]
        emails = ", ".join(email_list)
        print('emails = ', emails)
        email_to = 'alfredolubis5@gmail.com'
        # for email in email_list:
        #     if 'alfredolubis5@gmail.com' in email:
        #         email_to = 'alfredolubis5@gmail.com'
        # print('email_to = ', email_to)
        return email_to
    