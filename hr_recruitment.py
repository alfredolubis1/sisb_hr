from openerp import models, fields, api, _
from datetime import datetime, date
from openerp import http
from openerp.http import request
from lxml import etree
from openerp.exceptions import ValidationError
from openerp.addons.mail import mail_thread
class SISBHRApplicant(models.Model):
    _inherit = "hr.applicant"



    # partner_name = fields.Char("Applicant's Name")
    is_existing_employee = fields.Boolean("Is Existing Employee")
    apply_notes = fields.Text("Notes")
    employee_no = fields.Char("Employee ID")
    detect_transfer = fields.Boolean("Transfer")
    existing_employee_id = fields.Many2one("hr.employee", string="Employee")
    transfer_state = fields.Char(string="Transfer History", compute="_get_transfer_state", default="-")
    job_title_id = fields.Many2one('hr.position', string="Job Title")
    state = fields.Selection([
                             ('draft','Draft'),
                             ('process','Procces'),
                             ('refuse','Rejected'),
                             ('confirmed','Confirmed'),
                             ('transferred','Transferred'), 
                            ], "State", default="draft")




    # @api.multi
    # @api.onchange('existing_empoyee_id')
    def on_change_participant(self, cr, uid, ids,existing_employee_id, context=None):
        email_from = False
        nationality_id = False
        name = False
        company = False
        phone = False
        part_media_type_id = False
        part_media_no = False
        department_id = False
        job_id = False
        employee_no = False
        if existing_employee_id:
            emp_data = self.pool.get('hr.employee').browse(cr, uid, existing_employee_id, context=context)
            name = emp_data.name
            employee_no = emp_data.employee_no
            email_from = emp_data.work_email
            nationality_id = emp_data.country_id
            company = emp_data.company_id
            phone = emp_data.work_phone
            part_media_type_id = emp_data.part_media_type_id
            part_media_no = emp_data.part_media_no
            department_id = emp_data.department_id
            job_id = emp_data.job_id
            name = emp_data.name + "'s Application"
        return  {'value':{  'email_from': email_from,
                            'partner_name': name,
                            # 'nationality_id': nationality_id,
                            'name': name,
                            'employee_no': employee_no,
                            # 'company_id': company,
                            # 'partner_phone': phone,
                            # 'part_media_type_id': part_media_type_id,
                            # 'part_media_no': part_media_no,
                            # 'department_id': department_id,
                            # 'job_id': job_id,
                         }
                }
    @api.one
    def _get_transfer_state(self):
        default = "-"
        transfer_menu = self.env['hr.employee.transfer'].search([('application_source_id','=',self.id)])
        print('transfer_menu = ', transfer_menu.state)
        state = dict(transfer_menu._fields['state'].selection).get(transfer_menu.state)
        print('state = ', state)
        ids = self.ids
        print('ids = ', ids)
        if state:
            self.transfer_state = state
        else:
            self.transfer_state = state

    def default_get(self, cr, uid, fields, context=None):
        res = super(SISBHRApplicant, self).default_get(cr, uid, fields, context=None)
        print('res1 = ', res)
        print('context = ', context)
        print('field = ', fields)
        selfobj = self.browse(cr, uid, context)
        if 'agreement_notes' in fields:
            res.update({'agreement_notes': "By checking this box, you agree that SISB. may collect, use and disclose your personal data as provided in this application form, or (if applicable) as obtained by our organisation as a result of your application, for the following purposes in accordance with the Personal Data Protection Act 2012 (Revised on 15 July 2019):\n"
                                            "(a) the processing of this application; and\n"
                                            "(b) the administration of the application with our organisation.\n"
                                            "I declare that the particulars and information provided in this form are true and correct to the best of my belief and knowledge and that I have not wilfully suppressed any information."})
        if 'is_existing_employee' in fields:
            if context.get('default_is_existing_employee'):
                if context['default_is_existing_employee'] == True:
                    res.update({'is_existing_employee': True})
        return res

    @api.constrains('effective_date')   
    def forbid_without_eff_date(self):
        if not self.effective_date:
            raise ValidationError(_("Please Set the Effective Date"))


    @api.multi
    def go_to_transfer_menu(self):
        act_window = self.env['ir.actions.act_window']
        ir_model_data = self.env['ir.model.data']
        transfer_menu_xml_id = ir_model_data.get_object('sisb_hr', 'hr_employee_all_transfer_action')
        form_view = ir_model_data.get_object('sisb_hr', 'hr_all_employee_transfer_form_view')
        transfer_id = self.env['hr.employee.transfer'].search([('application_source_id', '=', self.id)])
        return {
            'name': _("All Transfer"),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.employee.transfer',
            'views': [(form_view.id, 'form')],
            'res_id': transfer_id.id,
            'type': 'ir.actions.act_window'
        }

    @api.multi
    def submit_transfer(self):
        print('disini')
        transfer_obj = self.env['hr.employee.transfer']
        vals = {}
        self._cr.execute("SELECT existing_employee_id, company_id, department_id, job_title_id, job_id FROM hr_applicant WHERE id=%s",(self.id, ))
        destination = self._cr.fetchall()
        print('destination = ', destination)
        for rec in destination:
            vals['company_destination_id'] = rec[1]
            vals['department_destination_id'] = rec[2]
            vals['new_position_id'] = rec[3]
            vals['new_job_id'] = rec[4]
        """Current Position and Company"""
        for l in self.existing_employee_id:
            vals['employee_id'] = l.id
            vals['company_id'] = l.company_id.id
            vals['department_id'] = l.department_id.id
            vals['job_id'] = l.job_id
            vals['position_id'] = l.employee_position_id.id 
        vals['application_source_id'] = self.id
        vals['tf_date'] = datetime.now()
        vals['state'] = 'submit'
        transfer_obj.create(vals)
        # self.sudo().notif_for_new_applicant()
        template = self.env['ir.model.data'].get_object('sisb_hr', 'email_notification_from_employee_applicant')
        if template:
            mail_id = template.send_mail(self.id)
            mail = self.env['mail.mail'].sudo().browse(mail_id)
            if mail:
                mail.send()
        return self.write({'state': 'process', 'detect_transfer': True})
        
    @api.model
    def get_email_to(self):
        user_group = self.env['res.groups'].search([('category_id.name','=','Human Resources'),('name','=','Manager')])
        email_list = [usr.email for usr in user_group.users if usr.email]
        emails = ", ".join(email_list)
        print('emails = ', emails)
        email_to = 'alfredolubis5@gmail.com'
        print('email_to = ', email_to)
        return email_to

    # @api.multi ## This Function Already Moved to sisb_project module
    # def notif_for_new_applicant(self):
    #     for rec in self:
    #         # template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'email_notification_from_job_applicant')
    #         template = self.env['ir.model.data'].get_object('sisb_hr', 'email_notification_from_job_applicant')
    #         if template:
    #             mail_id = template.send_mail(rec.id)
    #             print('mail_id = ', mail_id)
    #             # mail = self.env['mail.mail'].browse(mail_id)
    #             mail = self.env['mail.mail'].browse(mail_id)
    #             print('mail = ', mail)
    #             if mail:
    #                 mail.send()
    #     return True


    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     print('self = ', self)
    #     menu_id = self._context.get('view_id', False)
    #     print('menu_id = ', menu_id)
    #     action = self._context.get('action', False)
    #     print('action = ', action)
    #     res = super(SISBHRApplicant, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,submenu=submenu)
    #     menu_id1 = self._context.get('view_id', False)
    #     print('menu_id1 = ', menu_id1)
    #     action1 = self._context.get('action', False)
    #     print('view_id = ', view_id)
    #     view_name = self.env['ir.ui.view'].search([('id','=',view_id)])
    #     print('view_name = ', view_name.name)
    #     doc = etree.XML(res['arch'])
    #     if view_name == 'Jobs - Recruitment Form':
    #         for node in doc.xpath("//field[@name='is_existing_employee']"):
    #             node.set('context', "{'is_existing_employee': True}")
    #     res['arch'] = etree.tostring(doc)
    #     print('action1 = ', action1)
    #     return res


    # @api.multi
    # def get_url(self, object):
    #     print('object =', object)
    #     current_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #     print('current_url = ', current_url)
    #     http = request.httprequest.environ['HTTP_ORIGIN']
    #     http2 = request.httprequest.environ
    #     print('http2 = ', http2)
    #     url = ''
    #     action = self.env.ref(self.env.context.get('action', 'hr_recruitment.crm_case_categ0_act_job'))
    #     dict_act_window = action.read()[0]
    #     dict_act_window['res_id'] = self.id
    #     print('dict_act_window = ', dict_act_window)
    #     # model_id = request.params['args'][1]['params']['id']
    #     # model_id = request.params['args'][0][0]
    #     # view_type = request.params['args'][1]['params']['view_type']
    #     # model = request.params['args'][1]['params']['model']
    #     # action = request.params['args'][1]['params']['action']
    #     url = str(http) + '/web#id=' + str(dict_act_window['res_id']) + '&view_type=form' + '&model=' + str(self._name) + '&menu_id=1080' + '&action=' + str(dict_act_window['id'])
    #     # print('url = ', url)
    #     return url



    @api.multi
    def update_existing_employee(self):
        """This Function is For Update Existing Employee in case they are apply for a job,to avoid duplicate data"""
        model_data = self.env['ir.model.data']
        act_window = self.env['ir.actions.act_window']
        emp = self.existing_employee_id
        print ('company = ', self.company_id)
        print ('job = ', self.job_id)
        if emp:
            for rec in emp:
                rec.update({
                    'work_email': self.email_from,
                    'work_phone': self.partner_phone,
                    'company_id': self.company_id,
                    'job_id': self.job_id,
                    'department_id': self.department_id,
                    'country_id': self.nationality_id,
                    'join_date': datetime.now(),
                    'mobile_phone': self.partner_mobile,
                    'part_media_type_id': self.part_media_type_id,
                    'part_media_no': self.part_media_no

                })
        # action_model, action_id = model_data.get_object_reference('hr', 'open_view_employee_list')
        body = "Employee " + str(emp.name) + ' Updated From ' + str(self.name)
        self.message_post(body=body)
        action = self.env.ref(self.env.context.get('action', 'hr.open_view_employee_list'))
        dict_act_window = action.read()[0]
        dict_act_window['res_id'] = emp.id
        dict_act_window['view_mode'] = 'form,tree'
        return dict_act_window
                # return {'type': 'ir.actions.act_window_close'}
    
    def create(self, cr, uid, vals, context=None):
        cand_sequence = False
        cand_sequence = self.pool.get('ir.sequence').get(cr, uid, 'app')
        vals['candidate_no'] = cand_sequence
        
        context = dict(context or {})
        context['mail_create_nolog'] = True
        if vals.get('department_id') and not context.get('default_department_id'):
            context['default_department_id'] = vals.get('department_id')
        if vals.get('job_id') or context.get('default_job_id'):
            job_id = vals.get('job_id') or context.get('default_job_id')
            vals.update(self.onchange_job(cr, uid, [], job_id, context=context)['value'])
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        if 'stage_id' in vals:
            vals.update(self.onchange_stage_id(cr, uid, None, vals.get('stage_id'), context=context)['value'])
        obj_id = mail_thread.mail_thread.create(self, cr, uid, vals, context=context) #to create logs
#        obj_id = models.BaseModel.create(self, cr, uid, vals)
#        obj_id = super(hr_applicant, self).create(cr, uid, vals, context=context)
        applicant = self.browse(cr, uid, obj_id, context=context)
        if applicant.job_id:
            name = applicant.partner_name or applicant.existing_employee_id.name if applicant.is_existing_employee else applicant.name
            candidate_no = applicant.candidate_no if applicant.candidate_no else applicant.candidate_no
            self.pool['hr.job'].message_post(
                cr, uid, [applicant.job_id.id],
                body=("""New application from """+name+"""
                         <p>Candidate No """+candidate_no+"""</p>
                    """),
                
                subtype="hr_recruitment.mt_job_applicant_new", context=context)
                
            self.message_post(
                cr, uid, [applicant.id],
                body=("""New application from """+name+"""
                         <p>Candidate No """+candidate_no+"""</p>
                    """),
                
                subtype="hr_recruitment.mt_job_applicant_new", context=context)
        return obj_id 

class sisb_hr_job(models.Model):
    _inherit = 'hr.job'


class sisb_hr_recruitment_stage(models.Model):
    _inherit = 'hr.recruitment.stage'