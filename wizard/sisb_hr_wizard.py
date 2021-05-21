# -*- coding: utf-8 -*-
##############################################################################
#
#    TigernixERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, models, api, _
from openerp import SUPERUSER_ID
from openerp.exceptions import ValidationError
from datetime import date, datetime
import xlwt
import io
import base64
from cStringIO import StringIO
import calendar

class SISBRefusedRequest(models.TransientModel):
    _name = "hr.refused.request"

    name = fields.Text(string="Refused Reason", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")

    @api.multi
    def confirm_refused(self):
        print(self._uid)
        print('context = ', self._context)
        context = self._context
        ot_req_obj = self.env['hr.overtime.request'].search([('id','=', context['active_id'])])
        for rec in ot_req_obj:
            rec.refused_by_id = self._uid
            rec.refuse_reason = self.name
            rec.state = 'refuse'
            rec.total_overtime = 0.00
            for state in rec.request_line_ids:
                state.state = 'refuse'



class employee_timesheet_report_wiz(models.TransientModel):
    _name = "employee.timesheet.report"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    name = fields.Char(string="Employee")
    option = fields.Selection([
        ('blank','Blank Timesheet'),
        ('data','With Attendance Data'),
    ], string="Option")
    month = fields.Selection([
        ('1','January'),
        ('2','February'),
        ('3','March'),
        ('4','April'),
        ('5','May'),
        ('6','June'),
        ('7','July'),
        ('8','August'),
        ('9','September'),
        ('10','October'),
        ('11','November'),
        ('12','December')
    ], string="Month")
    month_in_str = fields.Char("Month")

    @api.onchange('month')
    def get_month(self):
        res = ''
        for item in self:
            res = dict(item._fields['month'].selection).get(item.month)
        self.month_in_str = res

    @api.onchange('employee_id')
    def set_name(self):
        if self.employee_id:
            self.name = self.employee_id.name

    @api.multi
    def generate_timesheet(self):
        data = self.read()[0]
        print('data = ', data)
        datas = {
                'ids': [],
                'model': 'employee.timesheet.report',
                'form': data
                }
        return self.pool['report'].get_action(self._cr, self._uid, [], 'sisb_hr.generate_timesheet_report', data=datas, context=self._context)





class req_onboard_wiz(models.TransientModel):
    _name = "req.onboard.wiz"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string="Department", select=True)
    on_boarding_list_ids = fields.Many2many('hr.boarding.list.line', string="ON Boarding List", store=True)

    @api.model
    def default_get(self, fields):
        res = super(req_onboard_wiz, self).default_get(fields)
        employee_id = self._context.get('active_id')
        if 'employee_id' in fields:
            res.update({'employee_id': employee_id})
        return res

    @api.onchange('employee_id')
    def get_department(self):
        dept_id = []
        if self.employee_id:
            for rec in self.employee_id:
                for board in rec.boarding_list_ids:
                    if board.department_id.id not in dept_id:
                        dept_id.append(board.department_id.id)
        print('dept_id = ', dept_id)
        return {
            'domain': {'department_id': [('id', 'in', dept_id)]}
        }


    @api.onchange('department_id')
    def get_onboard_item(self):
        all_items = []
        if self.department_id:
            self.on_boarding_list_ids = [(5,0,0)]
            for rec in self.employee_id:
                for l in rec.boarding_list_ids.filtered(lambda x: x.is_received == False and x.req == False and x.department_id == self.department_id):
                    all_items.append(l.id)
            return {
                'domain': {'on_boarding_list_ids': [('id', 'in', all_items)]}
                }
        if not self.department_id:
            return {
                'domain': {'on_boarding_list_ids': [('id', 'in', all_items)]}
            }
            # self.on_boarding_list_ids = [(4,item) for item in all_items]

    @api.multi
    def write(self, vals):
        res = super(req_onboard_wiz, self).write(vals)
        return res

    @api.multi
    def send_request(self):
        self.ensure_one()
        context = self._context.copy()
        all_item = []
        for l in self.on_boarding_list_ids:
            all_item.append(l.boarding_id.name)
            l.req = True
            l.req_date = datetime.now()
        print('all_item = ', all_item)
        if not all_item:
            raise ValidationError(_("You Don't Request anything, please tick the item you want to request"))
        if not self.on_boarding_list_ids:
            raise ValidationError(_("The ON Boarding List is not generated"))
        context['request_list'] = all_item
        self = self.with_context(context)
        template = self.env['ir.model.data'].get_object('sisb_hr', 'email_request_for_boarding_list')
        mail = ''
        if template:
            mail_id = template.send_mail(self.id)
            mail = self.env['mail.mail'].sudo().browse(mail_id)
            print('mail = ', mail)
            if mail:
                mail.send()


    # @api.one
    # def send_request(self):
    #     template = self.env['ir.model.data'].get_object('sisb_hr', 'email_request_for_boarding_list')
    #     print('template = ', template)
    #     if template:
    #         mail_id = template.send_mail(self.id)
    #         mail = self.env['mail.mail'].sudo().browse(mail_id)
    #         print('mail = ', mail)
    #         if mail:
    #             mail.send()

class onboard_item_excel_wizard(models.TransientModel):
    _name = "onboard.item.excel.wizard"


    name = fields.Char(string="File Name")
    file = fields.Binary(string="Onboarding Item Excel Report", readonly=True)

class on_board_wizard(models.TransientModel):
    _name = "onboard.item.wizard"

    options = fields.Selection([
        ('pdf','PDF'),
        ('excel','Excel')
    ], string="Report Type", default="pdf")

    excel_option = fields.Selection([
        ('received','Received Item Only'),
        ('requested','Requested Item Only'),
        ('both', 'Both')
    ], string="Excel Options")



    @api.multi
    def print_report(self):
        print('context = ', self._context)
        employee_id = self.env['hr.employee'].search([('id','=', self._context.get('active_id'))])
        if self.options == 'pdf':
            return self.env['report'].get_action(employee_id, 'sisb_hr.generate_on_board_item')
        elif self.options == 'excel':
            self.ensure_one()
            print('sss = ', self.ensure_one())
            name = ''
            position = ''
            campus = ''
            join_date = ''
            employee_no = ''

            for rec in employee_id:
                name = rec.name
                position = rec.employee_position_id.name
                campus = rec.company_id.name
                join_date = rec.join_date
                employee_no = rec.employee_no

            workbook = xlwt.Workbook()
            header1 = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, ,vert bottom ,horz centre')
            title1 = xlwt.easyxf('font: color black, name Arial; align: wrap yes, vert centre ,horz centre') 
            title_total = xlwt.easyxf('font: color black, name Arial; align: wrap yes, horz centre; pattern: pattern solid, fore_color gray40')
            name_style = xlwt.easyxf('font: color black, name Arial; align: wrap yes, ,vert centre ,horz left')

            worksheet = workbook.add_sheet('Sheet 1')            
            worksheet.write_merge(1, 2, 0, 7, "Staff Onboarding Checklist", header1)
            worksheet.write_merge(3, 3, 0, 1, "Name :", name_style) 
            worksheet.write(3, 2, name, name_style)
            worksheet.write_merge(3, 3, 5, 6, "Campus/Corporate :", name_style) 
            worksheet.write(3, 7, campus, name_style)
            worksheet.write_merge(4, 4, 0, 7, '', name_style)
            worksheet.write_merge(5, 5, 0, 1, "Position :", name_style)
            worksheet.write(5, 2, position, name_style)
            worksheet.write_merge(5, 5, 5, 6, "First day of employment :", name_style) 
            worksheet.write(5, 7, join_date, name_style)
            worksheet.write_merge(6, 6, 0, 7, '', name_style)
            worksheet.write_merge(7, 7, 0, 1, "Staff ID :", name_style)
            worksheet.write(7, 2, employee_no, name_style)

            worksheet.write(9, 0, "Item", title1)
            worksheet.write(9, 1, "Department", title1)
            worksheet.write(9, 2, "Note", title1)
            worksheet.write(9, 3, "Requested", title1)
            worksheet.write(9, 4, "Request Date", title1)
            worksheet.write(9, 5, "Received", title1)
            worksheet.write(9, 6, "Received Date", title1)

            i = 10
            for rec in employee_id.boarding_list_ids:
                if self.excel_option == 'both':
                    worksheet.write(i, 0, rec.boarding_id.name, name_style)
                    worksheet.write(i, 1, rec.department_id.name if rec.department_id else "Department Manager", name_style)
                    worksheet.write(i, 2, rec.note if rec.note else "-", name_style)
                    if rec.req == True:
                        worksheet.write(i, 3, "Yes", name_style)
                    elif rec.req == False:
                        worksheet.write(i, 3, "No", name_style)
                    worksheet.write(i, 4, rec.req_date if rec.req else "-", name_style)
                    if rec.is_received == True:
                        worksheet.write(i, 5, "Yes", name_style)
                    elif rec.is_received == False:
                        worksheet.write(i, 5, "No", name_style)
                    worksheet.write(i, 6, rec.date_is_received if rec.is_received else "-", name_style)
                elif self.excel_option == 'received':
                    if not rec.is_received:
                        continue
                    else:
                        worksheet.write(i, 0, rec.boarding_id.name, name_style)
                        worksheet.write(i, 1, rec.department_id.name if rec.department_id else "Department Manager", name_style)
                        worksheet.write(i, 2, rec.note if rec.note else "-", name_style)
                        if rec.req == True:
                            worksheet.write(i, 3, "Yes", name_style)
                        elif rec.req == False:
                            worksheet.write(i, 3, "No", name_style)
                        worksheet.write(i, 4, rec.req_date if rec.req else "-", name_style)
                        if rec.is_received == True:
                            worksheet.write(i, 5, "Yes", name_style)
                        elif rec.is_received == False:
                            worksheet.write(i, 5, "No", name_style)
                        worksheet.write(i, 6, rec.date_is_received if rec.is_received else "-", name_style)
                elif self.excel_option == 'requested':
                    if not rec.req:
                        continue
                    else:
                        worksheet.write(i, 0, rec.boarding_id.name, name_style)
                        worksheet.write(i, 1, rec.department_id.name if rec.department_id else "Department Manager", name_style)
                        worksheet.write(i, 2, rec.note if rec.note else "-", name_style)
                        if rec.req == True:
                            worksheet.write(i, 3, "Yes", name_style)
                        elif rec.req == False:
                            worksheet.write(i, 3, "No", name_style)
                        worksheet.write(i, 4, rec.req_date if rec.req else "-", name_style)
                        if rec.is_received == True:
                            worksheet.write(i, 5, "Yes", name_style)
                        elif rec.is_received == False:
                            worksheet.write(i, 5, "No", name_style)
                        worksheet.write(i, 6, rec.date_is_received if rec.is_received else "-", name_style)
                i += 1
            fp = StringIO()
            workbook.save(fp)
            fp.seek(0)
            excel_data = fp.read()
            fp.close()
            excel_data = base64.encodestring(excel_data)
            filename = 'Employee Onboarding Checklist.xls'

            # self.write({'data': excel_data, 'filename': filename})
            excel_wizard = self.env['onboard.item.excel.wizard'].create({'name': filename, 'file': excel_data})
            return {
            'name': _('Onboarding Excel Report'),
            'res_id' : excel_wizard.id,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'onboard.item.excel.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            }


class cancel_resign_wizard(models.TransientModel):
    _name = "cancel.resign.wizard"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    resign_id = fields.Many2one('hr.resignation', string="Resign Form")
    notes = fields.Text('Notes')
    item_exist = fields.Boolean(string="Check Item", help="If True, mean there are returned item Else the returned item is null")
    boarding_to_reallocated_ids = fields.Many2many('hr.boarding.list.line', string="Boarding Item")


    @api.onchange('item_exist')
    def get_boarding_domain(self):
        item_to_re_allocated = []
        if self.item_exist:
            for rec in self.resign_id:
                for line in rec.off_boarding_list_ids:
                    if line.is_returned:
                        item_to_re_allocated.append(line.id)

            return {
                'domain': {
                    'boarding_to_reallocated_ids': [('id', 'in', item_to_re_allocated)]
                }
            }

    @api.multi
    def cancel_resign(self):
        item_to_reback = []
        last_state = ''
        for rec in self:
            for r in rec.resign_id:
                last_state = r.employee_last_state
                r.state = 'cancel'
            for l in rec.boarding_to_reallocated_ids:
                l.is_returned = False
                l.is_received = True
                l.date_is_returned = False
                item_to_reback.append(l.id)
            rec.employee_id.update({
                'off_boarding_list_ids': [(3, item, 0)for item in item_to_reback],
                'boarding_list_ids': [(4, item, 0)for item in item_to_reback],
                'active': True,
                'employee_state': last_state,
            })


class survey_result_wizard(models.TransientModel):
    _name = "survey.result.wizard"


    name = fields.Char(string="File Name")
    file = fields.Binary(string="Survey Result Excel Report", readonly=True)


#REFERENCE LETTER
class employee_reference_letter(models.TransientModel):
    _name = "employee.reference.letter"

    indicate_salary = fields.Boolean('Indicate Salary')
    employee_id     = fields.Many2one('hr.employee', string="Employee")

    @api.model
    def default_get(self, fields):
        res = super(employee_reference_letter, self).default_get(fields)
        if 'employee_id' in fields:
            res.update({'employee_id': self._context.get('active_id')})
        return res



    @api.multi
    def print_report(self):
        context = self._context
        pdf = ''
        employee_id = self.env['hr.employee'].search([('id','=', self._context.get('active_id'))])
        if self.indicate_salary:
            pdf = self.env['report'].get_pdf(employee_id, 'sisb_hr.generate_reference_letter_with_salary')
        else:
            pdf = self.env['report'].get_pdf(employee_id, 'sisb_hr.generate_reference_letter')
        pdf_file = base64.encodestring(pdf)
        filename = "Reference Letter.pdf"
        reference_letter = self.env['reference.letter'].create({'name': filename, 'file': pdf_file})

        return {
        'name': _('Reference Letter'),
        'res_id' : reference_letter.id,
        'view_type': 'form',                                    
        "view_mode": 'form',
        'res_model': 'reference.letter',
        'type': 'ir.actions.act_window',
        'target': 'new',
        'context': context,
        }


class survey_result_wizard(models.TransientModel):
    _name = "reference.letter.wizard"

    name = fields.Char(string="File Name")
    file = fields.Binary(string="Reference Letter", readonly=True)
#####################


class alloc_leave_structure(models.TransientModel):
    _name = "alloc.leave.structure"

    employee_ids            = fields.Many2many('hr.employee', string="Employee's")
    leave_structure_id      = fields.Many2one('hr.holidays.structure', string="Leave Structure")
    company_id              = fields.Many2one('res.company', string="Company")
    leave_structure_type    = fields.Selection([
                            ('new','New'),
                            ('probation','Probation'),
                            ('contract','Contract'),
                            ('permanent','Permanent'),
                            ], string="Employee Type")

    @api.onchange('leave_structure_type')
    def got_employee(self):
        exist_employee = []
        if self.leave_structure_type:
            for rec in self.leave_structure_id:
                for emp in rec.employee_ids:
                    exist_employee.append(emp.id)
            print('exist_employee = ', exist_employee)
            return {
                'domain': {'employee_ids': [('id', 'not in', exist_employee), ('employee_state', '=', self.leave_structure_type), ('company_id', '=', self.company_id.id)]}
            }

    @api.multi
    def passing_employee(self):
        all_selected_employee = []
        for emp in self.employee_ids:
            emp.leave_structure_id = self.leave_structure_id
        for l in self.leave_structure_id:
            l.state = 'allocated'




# class employee_add_schedule(models.TransientModel):
#     _name = "employee.add.schedule"

#     sched_id = fields.Many2one('employee.schedule', string="Schedule")
#     employee_id = fields.Many2one('hr.employee', string="Employee")
#     sched_line_ids = fields.Many2many('employee.schedule.line', string="Schedule List")


#     @api.multi
#     def create_new_sched(self):
#         last_employee_sched = self.env['employee.schedule.line'].search([('employee_id', '=', self.employee_id.id)], limit=1, order="date DESC")
#         print('last_employee_sched = ', last_employee_sched)
#         for sched in self.sched_line_ids:
#             if sched.date < last_employee_sched.date:
#                 raise ValidationError("You cannot Add new Schedule with date overlaps the exist date")
#             else:
#                 sched.schedule_id = self.sched_id
#                 sched.employee_id = self.employee_id



class probation_compleion_letter_wizard(models.TransientModel):
    _name = 'probation.completion.letter.wizard'

    name = fields.Char(string="File Name")
    file = fields.Binary(string="Probation Completion Letter", readonly=True)

    @api.multi
    def send_to_employee(self):
        context = self._context
        print('context = ', self._context)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        attachment_obj = self.env['ir.attachment']
        attachment_id = ''
        for rec in self:
            attachment_data = {
                'name': 'Probation Completion Report',
                'datas_fname': rec.name,
                'datas': rec.file,
            }
            attachment_id = attachment_obj.create(attachment_data)
            print('attachment_id = ', attachment_id)
        self._cr.execute("SELECT rp.id FROM res_partner rp, res_users ru LEFT JOIN hr_employee he ON (he.user_id=ru.id) WHERE rp.id = ru.partner_id AND he.id=%s",(self._context.get('active_id'), ))
        partner_id = self._cr.fetchall()
        print('partner_id = ', partner_id)
        print('partner_id2 = ', partner_id[0])
        partner_ids = [pid for pid in partner_id[0]]
        ctx = dict(
            default_model = 'probation.completion.letter.wizard',
            default_res_id = context.get('active_id'),
            default_composition_mode = 'comment',
            default_attachment_ids = [(6, 0, [attach.id for attach in attachment_id])],
            default_partner_ids = partner_ids,
            default_recipient_ids = partner_ids,
            # mail_force_notify = True,
            from_render_report = True,
            mail_auto_delete = True,
        )
        print('ctx = ', ctx)
        return {
            'name': _('Send Probation Completion Report'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }


class inherit_mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'


    # def _notify(self, cr, uid, newid, context=None, force_send=False, user_signature=True):
    #     """ Override specific notify method of mail.message, because we do
    #         not want that feature in the wizard. """
    #     return

    def send_mail(self, cr, uid, ids, context=None):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        context = dict(context or {})
        print('ajgaaadada')
        # clean the context (hint: mass mailing sets some default values that
        # could be wrongly interpreted by mail_mail)
        context.pop('default_email_to', None)
        context.pop('default_partner_ids', None)

        for wizard in self.browse(cr, uid, ids, context=context):
            mass_mode = wizard.composition_mode in ('mass_mail', 'mass_post')
            active_model_pool = self.pool[wizard.model if wizard.model else 'mail.thread']
            print ('active_model_pool=', active_model_pool)
            if not hasattr(active_model_pool, 'message_post'):
                context['thread_model'] = wizard.model
                active_model_pool = self.pool['mail.thread']

            # wizard works in batch mode: [res_id] or active_ids or active_domain
            if mass_mode and wizard.use_active_domain and wizard.model:
                res_ids = self.pool[wizard.model].search(cr, uid, eval(wizard.active_domain), context=context)
            elif mass_mode and wizard.model and context.get('active_ids'):
                res_ids = context['active_ids']
            else:
                res_ids = [wizard.res_id]

            batch_size = int(self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'mail.batch_size')) or self._batch_size

            sliced_res_ids = [res_ids[i:i + batch_size] for i in range(0, len(res_ids), batch_size)]
            for res_ids in sliced_res_ids:
                all_mail_values = self.get_mail_values(cr, uid, wizard, res_ids, context=context)
                for res_id, mail_values in all_mail_values.iteritems():
                    if wizard.composition_mode == 'mass_mail':
                        self.pool['mail.mail'].create(cr, uid, mail_values, context=context)
                    else:
                        subtype = 'mail.mt_comment'
                        if wizard.is_log or (wizard.composition_mode == 'mass_post' and not wizard.notify):  # log a note: subtype is False
                            print('here1')
                            subtype = False
                        if wizard.composition_mode == 'mass_post':
                            print('here2')
                            context = dict(context,
                                           mail_notify_force_send=False,  # do not send emails directly but use the queue instead
                                           mail_create_nosubscribe=True)  # add context key to avoid subscribing the author
                        print('here3')
                        active_model_pool.message_post(cr, uid, [res_id], type='comment', subtype=subtype, context=context, **mail_values)

        return {'type': 'ir.actions.act_window_close'}






class performance_appraisals_report_wizard(models.TransientModel):
    _name = "performance.appraisals.report.wizard"


    employee_id = fields.Many2one('hr.employee', string="Employee")
    academic_year_id = fields.Many2one('academic.year', string="Academic Year")
    company_id = fields.Many2one('res.company', string="Company")
    staff_type = fields.Selection([
        ('general','General Staff'),
        ('spv','Supervisor'),
        ('manager','Manager')
    ], string="Staff Type")


    @api.onchange('employee_id')
    def onchange_employee(self):
        if self.employee_id:
            for rec in self.employee_id:
                self.company_id = rec.company_id
                if not rec.supervisor and not rec.manager:
                    self.staff_type = 'general'
                elif rec.supervisor and not rec.manager:
                    self.staff_type = 'spv'
                elif rec.manager or (rec.manager and rec.supervisor):
                    self.staff_type = 'manager'
    


    @api.multi
    def print_report(self):
        company = ''
        department = ''
        position = ''
        spv_manager_level = ('spv','manager')
        for r in self.employee_id:
            company = r.company_id.name or ''
            department = r.department_id.name or ''
            position = r.employee_position_id.name or ''
        workbook = xlwt.Workbook()

        header1 = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, ,vert bottom ,horz centre')
        title1 = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, vert centre ,horz centre; borders: top thin, right thin, bottom thin, left thin;')
        title1_left = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, vert centre ,horz left; borders: top thin, right thin, bottom thin, left thin;')
        title1_right = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, vert centre ,horz right; borders: top thin, right thin, bottom thin, left thin;')
        title1_vertical = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, vert centre ,horz centre, rotation 90; borders: top thin, right thin, bottom thin, left thin;')
        title1_vertical_green = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, vert centre ,horz centre, rotation 90; borders: top thin, right thin, bottom thin, left thin; pattern: pattern solid, fore_colour lime')
        title1_red = xlwt.easyxf('font: bold on, color red, name Arial; align: wrap yes, vert centre ,horz centre; borders: top thin, right thin, bottom thin, left thin;') 
        title_total = xlwt.easyxf('font: color black, name Arial; align: wrap yes, horz centre; pattern: pattern solid, fore_color gray40')
        name_style = xlwt.easyxf('font: color black, name Arial; align: wrap yes, ,vert centre ,horz left')
        content_left = xlwt.easyxf('font: color black, name Arial; align: wrap yes, ,vert centre ,horz left; borders: top thin, right thin, bottom thin, left thin;')
        content_light_lime = xlwt.easyxf('font: color black, name Arial; align: wrap yes, ,vert centre ,horz left; borders: top thin, right thin, bottom thin, left thin; pattern: pattern solid, fore_colour light_green')
        content_right = xlwt.easyxf('font: color black, name Arial; align: wrap yes, ,vert centre ,horz right; borders: top thin, right thin, bottom thin, left thin;')
        content_center = xlwt.easyxf('font: color black, name Arial; align: wrap yes, ,vert centre ,horz center; borders: top thin, right thin, bottom thin, left thin;')

        manager_work_sheet = workbook.add_sheet("Manager's Assesment", )
        self_work_sheet = workbook.add_sheet("Self's Assesment")
        criteria_work_sheet = ''
        if self.staff_type in spv_manager_level:
            criteria_work_sheet = workbook.add_sheet("Explanations")
        elif self.staff_type == 'general':
            criteria_work_sheet = workbook.add_sheet("Criteria")
        development_work_sheet = workbook.add_sheet("Development Plan")
        goal_work_sheet = workbook.add_sheet("Goal Setting")

        manager_work_sheet.col(0).width = 5000
        manager_work_sheet.col(1).width = 6000
        manager_work_sheet.col(2).width = 5000
        manager_work_sheet.col(3).width = 5000
        manager_work_sheet.row(2).height = 500
        manager_work_sheet.row(3).height = 500
        manager_work_sheet.row(4).height = 500
        manager_work_sheet.row(5).height = 500

        manager_work_sheet.row(13).height = 1500
        if self.staff_type in spv_manager_level:
            manager_work_sheet.write_merge(0, 0, 0, 3, "Performance evaluation form for Supervisor & Manager", header1)
        elif self.staff_type == 'general':
            manager_work_sheet.write_merge(0, 0, 0, 3, "Performance Appraisals for General Staff", header1)
        manager_work_sheet.write(2, 0, "Academic Year", name_style)
        manager_work_sheet.write(2, 1, self.academic_year_id.name, name_style)
        manager_work_sheet.write(2, 2, "Campus", name_style)
        manager_work_sheet.write(2, 3, company, name_style)
        manager_work_sheet.write(3, 0, "Name-Surname", name_style)
        manager_work_sheet.write(3, 1, self.employee_id.name, name_style)
        manager_work_sheet.write(3, 2, "ID-Number", name_style)
        manager_work_sheet.write(3, 3, self.employee_id.employee_no, name_style)
        manager_work_sheet.write(4, 0, "Position", name_style)
        manager_work_sheet.write(4, 1, position, name_style)
        manager_work_sheet.write(4, 2, "Dept", name_style)
        manager_work_sheet.write(4, 3, department, name_style)
        manager_work_sheet.write(5, 0, "Join Date", name_style)
        manager_work_sheet.write(5, 1, self.employee_id.join_date, name_style)


        #Table Header
        manager_work_sheet.write_merge(7, 13, 0, 1, "Competency", title1)
        manager_work_sheet.write_merge(7, 9, 2, 4, "Manager's Assesment", title1_red)
        if self.staff_type in spv_manager_level:
            manager_work_sheet.write_merge(10, 13, 2, 2, "Weighted (a)", title1_vertical)
            manager_work_sheet.write_merge(10, 13, 3, 3, "Rating (b) \n (to be completed)", title1_vertical_green)
            manager_work_sheet.write_merge(10, 13, 4, 4, "Rating against \n weight \n c = (a x b)", title1_vertical)
        elif self.staff_type == 'general':
            manager_work_sheet.write_merge(10, 13, 2, 2, "Weighted by \n Importance(a)", title1_vertical)
            manager_work_sheet.write_merge(10, 13, 3, 3, "Points(b)", title1_vertical_green)
            manager_work_sheet.write_merge(10, 13, 4, 4, "Points earned \n c = (a x b)", title1_vertical)

        # Table Content Competency

        general_staff_structure = self.env['appraisals.structure.general.staff'].search([], order="sequence asc")
        nongeneral_staff_structure = self.env['appraisals.structure.nongeneral.staff'].search([], order="sequence asc")
        i = 0
        if self.staff_type in spv_manager_level:
            for record in nongeneral_staff_structure:
                manager_work_sheet.write_merge(14 + i , 14 + i, 0, 1, record.name + ' (' + str(record.points) + ')', content_left)
                manager_work_sheet.write(14 + i, 2, str(record.importance), content_center)
                manager_work_sheet.write(14 + i, 3, '', content_light_lime)
                manager_work_sheet.write(14 + i, 4, '', content_center)
                manager_work_sheet.row(14 + i).height = 450
                i += 1
        elif self.staff_type == 'general':
            for record in general_staff_structure:
                manager_work_sheet.write_merge(14 + i , 14 + i, 0, 1, record.name + ' (' + str(record.points) + ')', content_left)
                manager_work_sheet.write(14 + i, 2, str(record.importance), content_center)
                manager_work_sheet.write(14 + i, 3, '', content_light_lime)
                manager_work_sheet.write(14 + i, 4, '', content_center)
                manager_work_sheet.row(14 + i).height = 450
                i += 1
        
        y = i + 14
        manager_work_sheet.write_merge(y, y, 0, 1, "Full Score 200 Points", title1_right)
        manager_work_sheet.write_merge(y, y, 2, 3, "Total", title1_right)
        manager_work_sheet.write(y, 4, '', title1_right)

        z = y + 2
        manager_work_sheet.write_merge(z, z, 0, 1, "Points refer to (b)", content_right)
        manager_work_sheet.write(z, 2, "4 = Very Good", content_left)
        manager_work_sheet.write(z, 3, "3 = Good", content_left)
        manager_work_sheet.write(z + 1, 2, "2 = Fair", content_left)
        manager_work_sheet.write(z + 1, 3, "1 = Need Development", content_left)

        manager_work_sheet.write_merge(z + 3, z + 3, 0, 1, "Grade Level", content_right)
        manager_work_sheet.write(z + 3, 2, "A = 190 - 200 Points", content_left)
        manager_work_sheet.write(z + 3 , 3, "B = 170 - 189 Points", content_left)
        manager_work_sheet.write(z + 4, 2, "C = 130 - 169 Points", content_left)
        manager_work_sheet.write(z + 4, 3, "D = 90 - 129 Points", content_left)
        manager_work_sheet.write(z + 5, 2, "E = Below 90 Points", content_left)

        manager_work_sheet.write_merge(z + 7, z + 7, 0, 4, "Employee / Comments", content_left)
        manager_work_sheet.write_merge(z + 8, z + 8, 0, 4, "", content_left)
        manager_work_sheet.write_merge(z + 9, z + 9, 0, 4, "", content_left)
        manager_work_sheet.write_merge(z + 10, z + 10, 0, 1, "Signed", content_left)
        manager_work_sheet.write(z + 10, 2, "...................", content_left)
        manager_work_sheet.write(z + 10, 3, "Date", content_left)
        manager_work_sheet.write(z + 10, 4, "...................", content_left)

        manager_work_sheet.write_merge(z + 12, z + 12, 0, 4, "Evaluator's Comments", content_left)
        manager_work_sheet.write_merge(z + 13, z + 13, 0, 4, "", content_left)
        manager_work_sheet.write_merge(z + 14, z + 14, 0, 4, "", content_left)
        manager_work_sheet.write_merge(z + 15, z + 15, 0, 1, "Signed", content_left)
        manager_work_sheet.write(z + 15, 2, "...................", content_left)
        manager_work_sheet.write(z + 15, 3, "Date", content_left)
        manager_work_sheet.write(z + 15, 4, "...................", content_left)

        manager_work_sheet.write_merge(z + 17, z + 17, 0, 4, "Dept. Manager Acknowledged / Comments", content_left)
        manager_work_sheet.write_merge(z + 18, z + 18, 0, 4, "", content_left)
        manager_work_sheet.write_merge(z + 19, z + 19, 0, 4, "", content_left)
        manager_work_sheet.write_merge(z + 20, z + 20, 0, 1, "Signed", content_left)
        manager_work_sheet.write(z + 20, 2, "...................", content_left)
        manager_work_sheet.write(z + 20, 3, "Date", content_left)
        manager_work_sheet.write(z + 20, 4, "...................", content_left)

        manager_work_sheet.write_merge(z + 22, z + 22, 0, 4, "Dept. Manager Acknowledged / Comments", content_left)
        manager_work_sheet.write_merge(z + 23, z + 23, 0, 4, "", content_left)
        manager_work_sheet.write_merge(z + 24, z + 24, 0, 4, "", content_left)
        manager_work_sheet.write_merge(z + 25, z + 25, 0, 1, "Signed", content_left)
        manager_work_sheet.write(z + 25, 2, "...................", content_left)
        manager_work_sheet.write(z + 25, 3, "Date", content_left)
        manager_work_sheet.write(z + 25, 4, "...................", content_left)



        self_work_sheet.col(0).width = 5000
        self_work_sheet.col(1).width = 6000
        self_work_sheet.col(2).width = 5000
        self_work_sheet.col(3).width = 5000
        self_work_sheet.row(2).height = 500
        self_work_sheet.row(3).height = 500
        self_work_sheet.row(4).height = 500
        self_work_sheet.row(5).height = 500

        self_work_sheet.row(13).height = 1500
        if self.staff_type in spv_manager_level:
            self_work_sheet.write_merge(0, 0, 0, 3, "Performance evaluation form for Supervisor & Manager", header1)
        elif self.staff_type == 'general':
            self_work_sheet.write_merge(0, 0, 0, 3, "Performance Appraisals for General Staff", header1)
        self_work_sheet.write(2, 0, "Academic Year", name_style)
        self_work_sheet.write(2, 1, self.academic_year_id.name, name_style)
        self_work_sheet.write(2, 2, "Campus", name_style)
        self_work_sheet.write(2, 3, company, name_style)
        self_work_sheet.write(3, 0, "Name-Surname", name_style)
        self_work_sheet.write(3, 1, self.employee_id.name, name_style)
        self_work_sheet.write(3, 2, "ID-Number", name_style)
        self_work_sheet.write(3, 3, self.employee_id.employee_no, name_style)
        self_work_sheet.write(4, 0, "Position", name_style)
        self_work_sheet.write(4, 1, position, name_style)
        self_work_sheet.write(4, 2, "Dept", name_style)
        self_work_sheet.write(4, 3, department, name_style)
        self_work_sheet.write(5, 0, "Join Date", name_style)
        self_work_sheet.write(5, 1, self.employee_id.join_date, name_style)


        #Table Header
        self_work_sheet.write_merge(7, 13, 0, 1, "Competency", title1)
        self_work_sheet.write_merge(7, 9, 2, 4, "Self's Assesment", title1_red)
        if self.staff_type in spv_manager_level:
            self_work_sheet.write_merge(10, 13, 2, 2, "Weighted (a)", title1_vertical)
            self_work_sheet.write_merge(10, 13, 3, 3, "Rating (b) \n (to be completed)", title1_vertical_green)
            self_work_sheet.write_merge(10, 13, 4, 4, "Rating against \n weigth \n c = (a x b)", title1_vertical)
        elif self.staff_type == 'general':
            self_work_sheet.write_merge(10, 13, 2, 2, "Weighted by \n Importance(a)", title1_vertical)
            self_work_sheet.write_merge(10, 13, 3, 3, "Points(b)", title1_vertical_green)
            self_work_sheet.write_merge(10, 13, 4, 4, "Points earned \n c = (a x b)", title1_vertical)

        # Table Content Competency

        general_staff_structure = self.env['appraisals.structure.general.staff'].search([], order="sequence asc")
        nongeneral_staff_structure = self.env['appraisals.structure.nongeneral.staff'].search([], order="sequence asc")
        i = 0
        if self.staff_type in spv_manager_level:
            for record in nongeneral_staff_structure:
                self_work_sheet.write_merge(14 + i , 14 + i, 0, 1, record.name + ' (' + str(record.points) + ')', content_left)
                self_work_sheet.write(14 + i, 2, str(record.importance), content_center)
                self_work_sheet.write(14 + i, 3, '', content_light_lime)
                self_work_sheet.write(14 + i, 4, '', content_center)
                self_work_sheet.row(14 + i).height = 450
                i += 1
        elif self.staff_type == 'general':
            for record in general_staff_structure:
                self_work_sheet.write_merge(14 + i , 14 + i, 0, 1, record.name + ' (' + str(record.points) + ')', content_left)
                self_work_sheet.write(14 + i, 2, str(record.importance), content_center)
                self_work_sheet.write(14 + i, 3, '', content_light_lime)
                self_work_sheet.write(14 + i, 4, '', content_center)
                self_work_sheet.row(14 + i).height = 450
                i += 1
        
        y = i + 14
        self_work_sheet.write_merge(y, y, 0, 1, "Full Score 200 Points", title1_right)
        self_work_sheet.write_merge(y, y, 2, 3, "Total", title1_right)
        self_work_sheet.write(y, 4, '', title1_right)

        z = y + 2
        self_work_sheet.write_merge(z, z, 0, 1, "Points refer to (b)", content_right)
        self_work_sheet.write(z, 2, "4 = Very Good", content_left)
        self_work_sheet.write(z, 3, "3 = Good", content_left)
        self_work_sheet.write(z + 1, 2, "2 = Fair", content_left)
        self_work_sheet.write(z + 1, 3, "1 = Need Development", content_left)

        self_work_sheet.write_merge(z + 3, z + 3, 0, 1, "Grade Level", content_right)
        self_work_sheet.write(z + 3, 2, "A = 190 - 200 Points", content_left)
        self_work_sheet.write(z + 3 , 3, "B = 170 - 189 Points", content_left)
        self_work_sheet.write(z + 4, 2, "C = 130 - 169 Points", content_left)
        self_work_sheet.write(z + 4, 3, "D = 90 - 129 Points", content_left)
        self_work_sheet.write(z + 5, 2, "E = Below 90 Points", content_left)

        self_work_sheet.write_merge(z + 7, z + 7, 0, 4, "Employee / Comments", content_left)
        self_work_sheet.write_merge(z + 8, z + 8, 0, 4, "", content_left)
        self_work_sheet.write_merge(z + 9, z + 9, 0, 4, "", content_left)
        self_work_sheet.write_merge(z + 10, z + 10, 0, 1, "Signed", content_left)
        self_work_sheet.write(z + 10, 2, "...................", content_left)
        self_work_sheet.write(z + 10, 3, "Date", content_left)
        self_work_sheet.write(z + 10, 4, "...................", content_left)

        self_work_sheet.write_merge(z + 12, z + 12, 0, 4, "Evaluator's Comments", content_left)
        self_work_sheet.write_merge(z + 13, z + 13, 0, 4, "", content_left)
        self_work_sheet.write_merge(z + 14, z + 14, 0, 4, "", content_left)
        self_work_sheet.write_merge(z + 15, z + 15, 0, 1, "Signed", content_left)
        self_work_sheet.write(z + 15, 2, "...................", content_left)
        self_work_sheet.write(z + 15, 3, "Date", content_left)
        self_work_sheet.write(z + 15, 4, "...................", content_left)

        self_work_sheet.write_merge(z + 17, z + 17, 0, 4, "Dept. Manager Acknowledged / Comments", content_left)
        self_work_sheet.write_merge(z + 18, z + 18, 0, 4, "", content_left)
        self_work_sheet.write_merge(z + 19, z + 19, 0, 4, "", content_left)
        self_work_sheet.write_merge(z + 20, z + 20, 0, 1, "Signed", content_left)
        self_work_sheet.write(z + 20, 2, "...................", content_left)
        self_work_sheet.write(z + 20, 3, "Date", content_left)
        self_work_sheet.write(z + 20, 4, "...................", content_left)

        self_work_sheet.write_merge(z + 22, z + 22, 0, 4, "Dept. Manager Acknowledged / Comments", content_left)
        self_work_sheet.write_merge(z + 23, z + 23, 0, 4, "", content_left)
        self_work_sheet.write_merge(z + 24, z + 24, 0, 4, "", content_left)
        self_work_sheet.write_merge(z + 25, z + 25, 0, 1, "Signed", content_left)
        self_work_sheet.write(z + 25, 2, "...................", content_left)
        self_work_sheet.write(z + 25, 3, "Date", content_left)
        self_work_sheet.write(z + 25, 4, "...................", content_left)

        
        header1_criteria = xlwt.easyxf('font: bold on, height 280, color black, name Arial; align: wrap yes, ,vert bottom ,horz centre')


        if self.staff_type in spv_manager_level:
            criteria_work_sheet.write_merge(0, 0, 0, 3, "Performance Evaluation Form for Supervisor/Manager", header1_criteria)
            criteria_work_sheet.write_merge(1, 1, 0, 3, "The Evaluation form is to assess work performance (1-12) and attendance (13-15)", content_left)
            criteria_work_sheet.write_merge(2, 2, 0, 3, "Leave Cycle is From", content_left)
        elif self.staff_type == 'general':
            criteria_work_sheet.write_merge(0, 0, 0, 3, "Performance Appraisal for General Staff", header1_criteria)
            criteria_work_sheet.write_merge(1, 1, 0, 3, "There are 16 assessment criterias of which No. 1-13 refers to performance and No. 14-16 refers to attendance.", content_left)
            criteria_work_sheet.write_merge(2, 2, 0, 3, "Leave Cycle is From", content_left)
        criteria_work_sheet.write(3, 0, "Name", name_style)
        criteria_work_sheet.write(3, 1, self.employee_id.name, name_style)
        criteria_work_sheet.write(3, 2, "ID", name_style)
        criteria_work_sheet.write(3, 3, self.employee_id.employee_no, name_style)
        criteria_work_sheet.write(4, 0, "Position", name_style)
        criteria_work_sheet.write(4, 1, position, name_style)
        criteria_work_sheet.write(4, 2, "Department", name_style)
        criteria_work_sheet.write(4, 3, department, name_style)


        criteria_work_sheet.write(6, 0, "Competency", title1_left)
        if self.staff_type in spv_manager_level:
            criteria_work_sheet.write_merge(6, 6, 1, 3, "Evaluation Criteria", title1)
        elif self.staff_type == 'general':
            criteria_work_sheet.write_merge(6, 6, 1, 3, "", title1)


        criteria_work_sheet.row(0).height = 600
        criteria_work_sheet.row(1).height = 500
        criteria_work_sheet.row(2).height = 500
        criteria_work_sheet.row(3).height = 500
        criteria_work_sheet.row(4).height = 500

        criteria_work_sheet.col(0).width = 7000
        criteria_work_sheet.col(1).width = 7000
        criteria_work_sheet.col(2).width = 7000
        criteria_work_sheet.col(3).width = 7000
        #Content
        i = 0
        general_criteria = self.env['appraisals.structure.general.staff'].search([])
        nongeneral_staff_structure = self.env['appraisals.structure.nongeneral.staff'].search([], order="sequence asc")
        if self.staff_type in spv_manager_level:
            for r in nongeneral_staff_structure:
                criteria_work_sheet.write(7 + i, 0, str(r.sequence) + '. ' + r.name, content_left)
                criteria_work_sheet.row(7 + i).height = 450
                if r.non_general_kpi_line_ids:
                    criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, "Key Performance Indicator (KPI) :", content_left)
                    for l in r.non_general_kpi_line_ids:
                        i += 1
                        criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, str(l.sequence) + '. ' + l.name, content_left)
                if r.non_general_evaluation_line_ids:
                    i += 1
                    criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, "Evaluation :", content_left)
                    criteria_work_sheet.row(7 + i).height = 450
                    for l in sorted(r.non_general_evaluation_line_ids, key=lambda x: x.sequence):
                        i += 1
                        criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, 'Level ' + str(l.sequence) + ': ' + l.name, content_left)
                if r.non_general_criteria_line_ids:
                    criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, "Evaluation from following criteria :", content_left)
                    criteria_work_sheet.row(7 + i).height = 450
                    for l in sorted(r.non_general_criteria_line_ids, key=lambda x: x.sequence):
                        i += 1
                        criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, 'Level ' + str(l.sequence) + ': ' + l.name, content_left)
                i += 1
            criteria_work_sheet.write(6 + i, 0, '', content_left)
        elif self.staff_type == 'general':
            for r in general_criteria:
                criteria_work_sheet.write(7 + i, 0, str(r.sequence) + '. ' + r.name, content_left)
                criteria_work_sheet.row(7 + i).height = 450
                if r.general_kpi_line_ids:
                    criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, "Key Performance Indicator (KPI) :", content_left)
                    for l in r.general_kpi_line_ids:
                        i += 1
                        criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, str(l.sequence) + '. ' + l.name, content_left)
                if r.general_evaluation_line_ids:
                    i += 1
                    criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, "Evaluation :", content_left)
                    criteria_work_sheet.row(7 + i).height = 450
                    for l in sorted(r.general_evaluation_line_ids, key=lambda x: x.sequence):
                        i += 1
                        criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, 'Level ' + str(l.sequence) + ': ' + l.name, content_left)
                if r.general_criteria_line_ids:
                    criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, "Criteria :", content_left)
                    criteria_work_sheet.row(7 + i).height = 450
                    for l in sorted(r.general_criteria_line_ids, key=lambda x: x.sequence):
                        i += 1
                        criteria_work_sheet.write_merge(7 + i, 7 + i, 1, 3, 'Level ' + str(l.sequence) + ': ' + l.name, content_left)
                i += 1
            criteria_work_sheet.write(6 + i, 0, '', content_left)



        #Development

        development_work_sheet.write_merge(0, 0, 0, 3, "Development Plan", header1)
        development_work_sheet.write(1, 0, "Name", title1_left)
        development_work_sheet.write(1, 1, self.employee_id.name, title1_left)
        development_work_sheet.write(1, 2, "Employee ID", title1_left)
        development_work_sheet.write(1, 3, self.employee_id.employee_no, title1_left)
        development_work_sheet.write(2, 0, "Position", title1_left)
        development_work_sheet.write(2, 1, position, title1_left)
        development_work_sheet.write(2, 2, "Dept", title1_left)
        development_work_sheet.write(2, 3, department, title1_left)

        development_work_sheet.col(0).width = 6000
        development_work_sheet.col(1).width = 6000
        development_work_sheet.col(2).width = 6000
        development_work_sheet.col(3).width = 6000


        development_work_sheet.write_merge(4, 4, 0, 1, "Strength", title1)
        development_work_sheet.write_merge(4, 4, 2, 3, "Area of Development", title1)
        
        for i in range(5, 20):
            development_work_sheet.write_merge(i, i, 0, 1, "", content_center)
            development_work_sheet.write_merge(i, i, 2, 3, "", content_center)
        

        development_work_sheet.write_merge(21, 21, 0, 1, "Knowledge/Skill that needs development", title1)
        development_work_sheet.write(21, 2, "Method", title1)
        development_work_sheet.write(21, 3, "When", title1)
        for i in range(22, 38):
            development_work_sheet.write_merge(i, i, 0, 1, "", content_center)
            development_work_sheet.write(i, 2, "", content_center)
            development_work_sheet.write(i, 3, "", content_center)
        
        #Goal Setting Tab

        goal_work_sheet.write_merge(0, 0, 0, 5, "Goal Setting For A/Y" + self.academic_year_id.name, header1)
        goal_work_sheet.write(1, 0, "Name", title1_left)
        goal_work_sheet.write(1, 1, self.employee_id.name, title1_left)
        goal_work_sheet.write(2, 0, "Emp ID", title1_left)
        goal_work_sheet.write(2, 1, self.employee_id.employee_no, title1_left)
        goal_work_sheet.write(3, 0, "Position", title1_left)
        goal_work_sheet.write(3, 1, position, title1_left)
        goal_work_sheet.write(4, 0, "Dept", title1_left)
        goal_work_sheet.write(4, 1, department, title1_left)

        goal_work_sheet.col(0).width = 2500
        goal_work_sheet.col(1).width = 10000
        goal_work_sheet.col(2).width = 5000
        goal_work_sheet.col(3).width = 5000
        goal_work_sheet.col(4).width = 5000
        goal_work_sheet.col(5).width = 5000

        
        goal_work_sheet.write_merge(6, 7, 0, 0, "No.", title1)
        goal_work_sheet.write_merge(6, 7, 1, 1, "Key Performance Indicator(KPI)", title1)
        goal_work_sheet.write_merge(6, 6, 2, 3, "Working Target", title1)
        goal_work_sheet.write_merge(6, 6, 4, 5, "Work Outcome", title1)
        goal_work_sheet.write(7, 2, "Goal", title1)
        goal_work_sheet.write(7, 3, "Full Score (50)", title1)
        goal_work_sheet.write(7, 4, "Goals Met", title1)
        goal_work_sheet.write(7, 5, "Score Gained", title1)
        i = 1
        for k in range(8, 18):
            goal_work_sheet.write(k, 0, i, content_center)
            goal_work_sheet.write(k, 1, "", content_center)
            goal_work_sheet.write(k, 2, "", content_center)
            goal_work_sheet.write(k, 3, "", content_center)
            goal_work_sheet.write(k, 4, "", content_center)
            goal_work_sheet.write(k, 5, "", content_center)
            i += 1
            k += 1
        


        goal_work_sheet.write(21, 1, "KPI Set Manager Signed", content_left)
        goal_work_sheet.write(21, 3, "Date", content_left)
        goal_work_sheet.write(24, 1, "Acknowledged by Employee Signed", content_left)
        goal_work_sheet.write(24, 3, "Date", content_left)
        goal_work_sheet.write(27, 1, "Acknowledged by HR Signed", content_left)
        goal_work_sheet.write(27, 3, "Date", content_left)

        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        excel_data = fp.read()
        fp.close()
        excel_data = base64.encodestring(excel_data)
        filename = 'Probation Appraisals Form.xls'

        # self.write({'data': excel_data, 'filename': filename})
        excel_wizard = self.env['probation.appraisals.form.result.wizard'].create({'name': filename, 'file': excel_data})
        return {
            'name': _('Probation Appraisals Excel Report'),
            'res_id' : excel_wizard.id,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'probation.appraisals.form.result.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }



class onboard_item_excel_wizard(models.TransientModel):
    _name = "probation.appraisals.form.result.wizard"


    name = fields.Char(string="File Name")
    file = fields.Binary(string="Onboarding Item Excel Report", readonly=True)



class wiz_cancel_shift(models.TransientModel):
    _name = "wiz.cancel.shift"

    cancel_options      = fields.Selection([
        ('cs','Cancel Shift'),
        ('ce','Cancel Employee Shift')
    ], string="Cancel Options", default="cs", required=True)
    shift_source_id = fields.Many2one('hr.schedule.allocation', string="Shift Allocation")
    employee_shift_ids  = fields.Many2many('hr.schedule.running.shift', string="Employee Shift")
    
    @api.multi
    def cancel_shift(self):
        if self.cancel_options == 'cs':
            running_shift_id = self.env['hr.schedule.running.shift'].search([('reference_id','=',self.shift_source_id.id)])
            for rec in self.shift_source_id:
                rec.state = 'cancel'
                rec.cancel_before = True
            for running_shift in running_shift_id:
                running_shift.state = 'cancel'
        else:
            if not self.employee_shift_ids:
                raise ValidationError(_("You must Selec at least 1 Employee Shift"))
            else:
                for s in self.employee_shift_ids:
                    s.state = 'cancel'


class wiz_change_shift(models.TransientModel):
    _name = "wiz.change.shift"

    employee_id         = fields.Many2one('hr.employee', string="Employee")
    date                = fields.Date(string="Date")
    current_shift_id    = fields.Many2one('work.time.structure', string="Current Shift")
    new_shift_id        = fields.Many2one('work.time.structure', string="New Shift")
    description         = fields.Text(string="Description")


    @api.multi
    def change_shift(self):
        print(self._context)  
        shift_id = self.env[self._context.get('active_model')].search([('id','=',self._context.get('active_id'))])
        if shift_id:
            shift_id.shift_id = self.new_shift_id.id
            shift_id.notes = self.description

    @api.onchange('current_shift_id')
    def onchange_curr_shift(self):
        if self.current_shift_id:
            company_id = self.employee_id.company_id
            print('company_id = ', company_id)
            return {'domain': {
                    'new_shift_id': [('id','!=',self.current_shift_id.id),('company_id','=',company_id.id)]
                }
            }
