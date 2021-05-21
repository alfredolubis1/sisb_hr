from openerp import models, fields, api, _
from openerp.exceptions import ValidationError, AccessError
from datetime import datetime, date
from openerp import http
from openerp.http import request
import xlwt
import io
import base64
from cStringIO import StringIO
import calendar



class SISBHRResign(models.Model):
    _name = "hr.resignation"
    _inherit = 'mail.thread'
    _order = "effective_date desc"



    # def _get_employee_id(self):
    #     # assigning the related employee of the logged in user
    #     employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    #     print('employee_rec = ', employee_rec)
    #     return employee_rec.id
    

    surname                 = fields.Char(string="Surname")
    employee_id             = fields.Many2one("hr.employee", string="Employee")
    employee_no             = fields.Char(string="Employee Number", track_visibility="onchange")
    company_id              = fields.Many2one('res.company', string="Company")
    related_company_id      = fields.Many2one('res.company', related="company_id", string="Company")
    name                    = fields.Char(string="Resign Number", default="/", track_visibility="onchange")
    related_employee_no     = fields.Char(string="Employee Number", related="employee_no", track_visibility="onchange")
    attention               = fields.Char(string="Attention")
    position_id             = fields.Many2one('hr.position', string="Position")
    related_position_id     = fields.Many2one('hr.position', related="position_id", string="Position")
    emp_id                  = fields.Many2one('hr.employee', string="Employee", related='employee_id')
    department_id           = fields.Many2one('hr.department', string="Department")
    related_department_id   = fields.Many2one('hr.department', related="department_id", string="Department")
    date_resign             = fields.Date(string="Date", default=date.today())
    date_join               = fields.Date(string="Date Join")
    survey_id               = fields.Many2one('survey.survey', string="Exit Interview Survey")
    effective_date          = fields.Date("Effective Date")
    reason_id               = fields.Many2one('hr.resign.reason', string="Reason")
    resign_reason           = fields.Char(string="Other Reason")
    reason_related          = fields.Char(string="Reason Related")
    off_boarding_list_ids   = fields.One2many('hr.boarding.list.line', 'resign_boarding_list_id',string="Boarding List Off")
    spv_appv_id             = fields.Many2one('res.users', string="First Approval By")
    spv_appv_date           = fields.Date(string="First Approval Date")
    final_appv_id           = fields.Many2one('res.users', string="Second Approval By")
    final_appv_date         = fields.Date(string="Second Approval Date")
    generated               = fields.Boolean(string="Off Boarding Generated")
    survey_check            = fields.Boolean(compute='_check_survey', string="Survey Done")
    employee_last_state     = fields.Char(string="Employee Last State")
    state                   = fields.Selection([
                                ('draft', 'Draft'),
                                ('refuse', 'Rejected'),
                                ('cancel', 'Cancelled'),
                                ('wait_1st_apprv', 'Waiting For 1st Approval'),
                                ('wait_2nd_apprv', 'Waiting For 2nd Approval'),
                                ('approved', 'Approved'),
                            ], string="State", track_visibility='onchange', default='draft')


    @api.model
    def create(self, vals):
        print('vals = ', vals)
        if vals.get('name', '/') == '/' or False:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.resignation') or '/'
        res = super(SISBHRResign, self).create(vals)
        print('vals2 = ', vals)
        return res

    @api.onchange('employee_id')
    def get_off_borading_list(self):
        if self.employee_id:
            lines = []
            for rec in self.employee_id:
                for line in rec.boarding_list_ids.filtered(lambda item: item.is_received == True):
                    if line.id not in lines:
                        lines.append(line.id)
            self.off_boarding_list_ids = [(5,0,0)]
            self.off_boarding_list_ids = [(4,item,0)for item in lines]
            self.department_id = self.employee_id.department_id
            self.position_id = self.employee_id.employee_position_id
            self.company_id = self.employee_id.company_id
            self.surname = self.employee_id.surname
        if not self.employee_id:
            print('here')
            self.department_id  = False
            self.position_id    = False
            self.company_id     = False

    @api.onchange('reason_id')
    def get_reason_related(self):
        if self.reason_id:
            self.reason_related = self.reason_id.name
    


    @api.multi
    def _check_survey(self):
        # survey_input = self.env['survey.user_input'].search([('state', 'in', ['skip','done']), ('survey_id', '=', self.survey_id.id), ('partner_id', '=', self.employee_id.user_id.partner_id.id)])
        survey_input = self.env['survey.user_input'].search([('state', 'in', ['skip','done']), ('survey_id', '=', self.survey_id.id)], limit=1, order='create_date ASC')
        print('survey_input = ', survey_input)
        if len(survey_input) > 0:
            self.survey_check = True



    @api.model
    def default_get(self, fields):
        res = super(SISBHRResign, self).default_get(fields)
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if 'employee_id' in fields:
            res.update({'employee_id': employee_rec.id})
        if 'position_id' in fields:
            res.update({'position_id': employee_rec.employee_position_id.id})
        if 'department_id' in fields:
            res.update({'department_id': employee_rec.department_id.id})
        if 'date_join' in fields:
            res.update({'date_join': employee_rec.join_date})
        if 'employee_no' in fields:
            res.update({'employee_no': employee_rec.employee_no})
        return res
        

    @api.multi
    def confirm_resign(self):
        """This Function also send Email Resign Request to Linked Supervisor in Employee Data"""
        template = self.env['ir.model.data'].get_object('sisb_hr', 'resign_request')
        sender_id = self.emp_id
        if template:
            mail_id = template.send_mail(self.id)
            print('mail_id = ', mail_id)
            mail = self.env['mail.mail'].browse(mail_id)
            print('mail = ', mail)
            if mail:
                mail.send()
        self.get_url(sender_id, self)
        return self.write({'state': 'wait_1st_apprv'})
        
    @api.multi
    def get_url(self, emp_id, object):
        # print('params = ', request.params)
        # other_url = request.httprequest.environ
        # action = request.params['args'][1]['params']['action']
        # url = emp_id.user_id.partner_id.with_context(signup_force_type_in_url='')._get_signup_url_for_action_id(action=action,view_type='form',model=object, res_id =object.id)[emp_id.user_id.partner_id.id]
        # return url
        print('object =', object)
        current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        print('current_url = ', current_url)
        http = request.httprequest.environ['HTTP_ORIGIN']
        http2 = request.httprequest.environ
        print('http2 = ', http2)
        url = ''
        action = self.env.ref(self.env.context.get('action', 'sisb_hr.all_hr_resignation_action'))
        dict_act_window = action.read()[0]
        dict_act_window['res_id'] = self.id
        print('dict_act_window = ', dict_act_window)
        # model_id = request.params['args'][1]['params']['id']
        # model_id = request.params['args'][0][0]
        # view_type = request.params['args'][1]['params']['view_type']
        # model = request.params['args'][1]['params']['model']
        # action = request.params['args'][1]['params']['action']
        url = str(http) + '/web#id=' + str(dict_act_window['res_id']) + '&view_type=form' + '&model=' + str(self._name) + '&menu_id=1080' + '&action=' + str(dict_act_window['id'])
        # print('url = ', url)
        return url
       

    @api.one
    def confirm_resign_to_hr(self):
        template        = self.env['ir.model.data'].get_object('sisb_hr', 'supervisor_validation_request')
        sender_id       = self.employee_id
        if template:
            mail_id = template.send_mail(self.id)
            mail = self.env['mail.mail'].browse(mail_id)
            if mail:
                mail.send()
        survey_id       = False
        resign_structure_obj    = self.env['hr.resign.structure'].search([('company_id', '=', self.company_id.id)])

        if not resign_structure_obj:
            raise ValidationError(_("You Haven't Set Resign Structure For %s Please Set The Resign Structure First"))
        survey_id       = resign_structure_obj.survey_id
        survey_name     = str(resign_structure_obj.survey_id.title) + ' (' + str(self.name) + ')'
        survey          = survey_id.copy({})
        survey.write({'title': survey_name})
        self.survey_id  = survey
        return self.write({'state': 'wait_2nd_apprv','spv_appv_id': self._uid, 'spv_appv_date':date.today()})

    @api.one
    def refuse_resign(self):
        self.write({'state': 'refuse'})

    @api.multi
    def cancel_resign(self):
        item_to_re_allocated = []
        if self.state == 'approved':
            for rec in self.off_boarding_list_ids:
                if rec.is_returned:
                    item_to_re_allocated.append(rec.id)
            print('item_to_re_allocated = ', item_to_re_allocated, 'length = ', len(item_to_re_allocated))
            if len(item_to_re_allocated) > 0:
                print('sss')
                return {
                    'name'      : _('Cancel Resign Wizard'),
                    'type'      : 'ir.actions.act_window',
                    'res_model' : 'cancel.resign.wizard',
                    # 'res_id' : survey_wivard.id,
                    'view_type' : 'form',
                    "view_mode" : 'form',
                    'nodestroy' : True,
                    'domain'    : {'boarding_to_reallocated_ids': [('id','in', [item_to_re_allocated])]},
                    'context'   : {'default_employee_id': self.employee_id.id, 
                                    'default_resign_id': self.id,
                                    'default_notes': 'Click Cancel Resign Button will bring employee to the last Employment State and the choosen boarding item will be returned back to Employee',
                                    'default_item_exist': True},
                    'target'    : 'new',
                }
            else:
                return {
                    'name'      : _('Cancel Resign Wizard'),
                    # 'res_id' : survey_wivard.id,
                    'view_type' : 'form',
                    "view_mode" : 'form',
                    'context'   : {'default_employee_id': self.employee_id.id, 'default_resign_id': self.id, 'default_item_exist': False},
                    'res_model' : 'cancel.resign.wizard',
                    'type'      : 'ir.actions.act_window',
                    'target'    : 'new',
                }
            # for rec in self.off_boarding_list_ids:
            #     if rec.is_returned == True:
            #         item_to_re_allocated.append(rec.id)
            # f

        else:
            return self.write({'state': 'cancel'})
        

    @api.one
    def reset_draft(self):
        return self.write({'state': 'draft',
                            'spv_appv_id': False,
                            'spv_appv_date': False,
                            'final_appv_id': False,
                            'final_appv_date': False})
    
    @api.multi
    def action_start_survey(self):
        context             = dict(self._context or {})
        survey_obj          = self.env['survey.survey'].search([('id' ,'=' , self.survey_id.id)])
        response_obj        = self.env['survey.user_input']
        # create a response and link it to this resign_applicant
        response_id         = response_obj.create({'survey_id': self.survey_id.id, 'partner_id': self.emp_id.user_id.partner_id.id})
        # grab the token of the response and start surveying
        context.update({'survey_token': response_id.token})
        return survey_obj.action_start_survey()
    


    @api.multi
    def action_view_result(self):
        survey_obj  = self.env['survey.survey'].search([('id' ,'=' , self.survey_id.id)])
        return survey_obj.action_result_survey()


    @api.multi
    def action_send_survey(self):
        mail = False
        template        = self.env['ir.model.data'].get_object('sisb_hr', 'exit_interview_email')
        if template:
            mail_id = template.send_mail(self.id)
            mail = self.env['mail.mail'].browse(mail_id)
            if mail:
                return mail.send()

    @api.multi
    def generate_off_board(self):
        item_to_returned = []
        for rec in self.emp_id:
            for line in rec.boarding_list_ids.filtered(lambda x: x.is_received == True):
                if line.id not in item_to_returned:
                    item_to_returned.append(line.id)
        if not self.off_boarding_list_ids:
            self.off_boarding_list_ids = [(4, item, 0) for item in item_to_returned]
            self.generated = True
        if self.off_boarding_list_ids:
            self.off_boarding_list_ids = [(5, 0, 0)]
            self.off_boarding_list_ids = [(4, item, 0) for item in item_to_returned]
            self.generated = True

    @api.multi
    def check_boarding_list(self):
        for rec in self.emp_id:
            for line in rec.boarding_list_ids.filtered(lambda x: x.is_received == True):
                if line and not self.off_boarding_list_ids:
                    raise ValidationError(_("This Employee has on boarding item to returned\n"
                                            'Please Click Generate Off Boarding Button to see the item'))

    def update_employee_resign(self, cr, uid, context=None):
        FMT = '%Y-%m-%d'
        now = datetime.now()
        last_day = now.strftime(FMT)
        all_approved_resign = self.pool.get('hr.resignation').search(cr, uid, [('state','=','approved'),('effective_date','=',last_day)], context=context)
        print('all_approved_resign = ', all_approved_resign)
        items = []
        if self.browse(cr, uid, all_approved_resign):
            for res in all_approved_resign:
                for recs in res.off_boarding_list_ids:
                    recs.resign_boarding_list_id = res.id
                    if recs.id not in items:
                        items.append(recs.id)
                print('res = ', res)
                for rec in res.employee_id:
                    print('rec = ', rec)
                    # rec.update({
                    # 'active': False,
                    # 'boarding_list_ids': [(3, stuff, 0)for stuff in items],
                    # 'employee_state': 'resign'})
        return True
        # all_tf = self.pool.get('hr.employee.transfer').search(cr, uid, [('state','=','accept')], context=context)
        # all_emp_tf = self.pool.get('hr.employee.transfer').browse(cr, uid, all_tf)
        # now =datetime.now()
        # now1 = pytz.timezone('Asia/Singapore')
        # dt_now = now.strftime('%Y-%m-%d')
        # items = []
        # for rec in all_emp_tf:
        #     if rec:
        #         if rec.effective_date == dt_now:
        #             print('disini = ')
        #             if not rec.tf_boarding_list_ids:
        #                 rec.tf_employee()
        #             if rec.tf_boarding_list_ids:
        #                 for i in rec.tf_boarding_list_ids.filtered(lambda x: x.is_returned == True):
        #                     if i:
        #                         items.append(i.id)
        #                 if items:
        #                     rec.employee_id.update({
        #                         'employee_position_id': rec.new_position_id.id,
        #                         'department_id': rec.department_destination_id.id,
        #                         'company_id': rec.company_destination_id.id,
        #                         'boarding_list_ids': [(3, k , 0)for k in items]
        #                         })
        #                     rec.write({'state': 'transferred', 'notes': 'This Transfer is already Updated'})
        #                 if not items:
        #                     rec.tf_employee()
        #         for app in rec.application_source_id:
        #             app.state = 'transferred'
            
        # return True 

    @api.one
    def validated_resign(self):
        template = self.env['ir.model.data'].get_object('sisb_hr', 'approved_resign_request')
        sender_id = self.emp_id
        self.check_boarding_list()
        for rec in self:
            if rec.off_boarding_list_ids:
                for item in rec.off_boarding_list_ids:
                    print('item1 = ', item)
                    if not item.is_returned:
                        raise ValidationError(_("Please Check the Returned and set the returned date if the item is already returned"))
        if template:
            mail_id = template.send_mail(self.id)
            mail = self.env['mail.mail'].browse(mail_id)
            if mail:
                mail.send()
        items = []
        for recs in self.off_boarding_list_ids:
            recs.is_received = False
            recs.resign_boarding_list_id = self.id
            if recs.id not in items:
                items.append(recs.id)
        for rec in self.emp_id:
            self.employee_last_state = rec.employee_state
            rec.update({
            'active': False,
            'boarding_list_ids': [(3, stuff, 0)for stuff in items],
            'off_boarding_list_ids': [(4, stuff, 0)for stuff in items],
            'employee_state': 'resign'})
        # for item in items:
        #     self._cr.execute('DELETE FROM hr_boarding_list_line WHERE id=%s', (item,))
        return self.write({'state': 'approved','final_appv_id': self._uid, 'final_appv_date':date.today()})

    

    @api.multi
    def print_survey_result(self):
        survey_input = self.env['survey.user_input'].search([('state', 'in', ['skip','done']), ('survey_id', '=', self.survey_id.id), ('partner_id', '=', self.employee_id.user_id.partner_id.id)], limit=1, order='create_date ASC')
        workbook = xlwt.Workbook()
        header1 = xlwt.easyxf('font: bold on, color black, name Arial; align: wrap yes, ,vert bottom ,horz centre')
        title1 = xlwt.easyxf('font: color black, name Arial; align: wrap yes, vert centre ,horz centre') 
        title_total = xlwt.easyxf('font: color black, name Arial; align: wrap yes, horz centre; pattern: pattern solid, fore_color gray40')
        name_style = xlwt.easyxf('font: color black, name Arial; align: wrap yes, ,vert centre ,horz left')

        worksheet = workbook.add_sheet('Sheet 1')
        name = ''
        employee_id = ''
        position = ''
        department = ''
        join_date = ''
        last_date = ''
        for record in survey_input:
            for rec in record.user_input_line_ids:
                if rec.question_id.question == 'Name' and not rec.skipped:
                    name = rec.value_free_text
                elif rec.question_id.question == 'Employee ID' and not rec.skipped:
                    employee_id = rec.value_free_text
                elif rec.question_id.question == 'Position' and not rec.skipped:
                    position = rec.value_free_text
                elif rec.question_id.question == 'Department / Section' and not rec.skipped:
                    department = rec.value_free_text
                elif rec.question_id.question == 'Start Working Date' and not rec.skipped:
                    join_date = rec.value_free_text
                elif rec.question_id.question == 'Last Working Date' and not rec.skipped:
                    last_date = rec.value_free_text
                # # name = [rec.value_free_text if rec.question_id.question == 'Name' and not rec.skipped else '-']
                # employee_id = [rec.value_free_text if rec.question_id.question == 'Employee ID' and not rec.skipped else '-']
                # position = [rec.value_free_text if rec.question_id.question == 'Position' and not rec.skipped else '-']
                # department = [rec.value_free_text if rec.question_id.question == 'Department / Section' and not rec.skipped else '-']
                # join_date = [rec.value_free_text if rec.question_id.question == 'Start Working Date' and not rec.skipped else '-']
                # last_date = [rec.value_free_text if rec.question_id.question == 'Last Working Date' and not rec.skipped else '-']
        print('name = ', name)
        print('employee_id = ', employee_id)
        print('position = ', position)
        print('department = ', department)
        print('join_date = ', join_date)
        print('last_date = ', last_date)
        worksheet.write_merge(1, 1, 0, 5, "Exit Interview Form", header1)
        worksheet.write(2, 4, 'Effective Date', name_style)
        worksheet.write_merge(3, 3, 0, 1, "Name :", title1)
        worksheet.write(3, 2, name, title1)
        worksheet.write_merge(3, 3, 3, 4, "Employee ID :", title1)
        worksheet.write(3, 5, employee_id, title1)
        worksheet.write_merge(4, 4, 0, 1, "Position :", title1)
        worksheet.write(4, 2, position, title1)
        worksheet.write_merge(4, 4, 3, 4, "Department/Section :", title1)
        worksheet.write(4, 5, department, title1)
        worksheet.write_merge(5, 5, 0, 1, "Start Working Date :", title1)
        worksheet.write(5, 2, join_date, title1)
        worksheet.write_merge(5, 5, 3, 4, "Last Working Date :", title1)
        worksheet.write(5, 5, last_date, title1)

        worksheet.write_merge(7, 8, 0, 5, "To continue to improve and make our company a better place to work, we ask you to kindly provide honest and true answers. \n Your answers will be kept confidential. Please select the answer that best applies to you.", title1)

        worksheet.write_merge(9, 10, 0, 3, "Desccription", title1)
        worksheet.write_merge(9, 9, 4, 8, "Satisfaction Level", title1)
        worksheet.write(10, 4, "Very High", title1)
        worksheet.write(10, 5, " High", title1)
        worksheet.write(10, 6, "Neutral", title1)
        worksheet.write(10, 7, "Low", title1)
        worksheet.write(10, 8, "Very Low", title1)
        worksheet.write_merge(11, 11, 0, 3, "Work Condition", title1)

        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        excel_data = fp.read()
        fp.close()
        excel_data = base64.encodestring(excel_data)
        filename = 'Survey Result.xls'
        survey_wivard = self.env['survey.result.wizard'].create({'name': filename, 'file': excel_data})
        return {
            'name': _('Survey Result Report'),
            'res_id' : survey_wivard.id,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.result.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }




class sisb_hr_resign_structure(models.Model):
    _name = "hr.resign.structure"

    name            = fields.Char("Name")
    company_id      = fields.Many2one('res.company', string="Company")
    survey_id       = fields.Many2one('survey.survey', string="Exit Interview Form")




class hr_resign_reason(models.Model):
    _name = "hr.resign.reason"

    name = fields.Char(string="Reason")
    