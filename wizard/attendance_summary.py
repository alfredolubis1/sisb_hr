# -*- coding: utf-8 -*-
import time
import base64
import re
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _

class employee_summary_attendance_reports(osv.osv_memory):
    _name = 'attend.summary.report.all.employee'
    _inherit = 'mail.thread'
    _description = 'Print Daily Attendance Report By All Employee'
    
    def onchange_date_from(self, cr, uid, ids, start_date, end_date):
        if (start_date and end_date) and (start_date > end_date):
            raise osv.except_osv(_('Warning!'),_('The start date must be anterior to the end date.'))
        return True
    
    def onchange_date_to(self, cr, uid, ids, start_date, end_date):
        if (start_date and end_date) and (start_date > end_date):
            raise osv.except_osv(_('Warning!'),_('The start date must be anterior to the end date.'))
        return True
    
    
    _columns = {
        'start_date': fields.date('Starting Date',required=False),
        'end_date': fields.date('Ending Date',required=False),
        'action': fields.selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'),('sign_in_and_sign_out','Sign In and Sign Out')], 'Sign Type'),
        'employee_s': fields.many2many('hr.employee', 'employee_attend_rel', 'attend_id', 'emp_id', 'Employee List', domain="[('user_id.login', '!=', 'admin')]"),
        'employee_name': fields.char('Employee Name'),
        'start_date_display': fields.char('Starting Date'),
        'end_date_display': fields.char('Ending Date')
    }
    _defaults = {
        'start_date': fields.date.context_today,
        'end_date': fields.date.context_today,
        'action':'sign_in_and_sign_out',
    }
    
    def print_attendance_all_employee(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, ['start_date', 'end_date', 'employee_s','action'], context=context)
        res = res and res[0] or {}
        datas['form'] = res
        datas['form']['employee_name_s'] = []
        
        
        if (res.get('start_date') and res.get('end_date')) and (res.get('start_date') > res.get('end_date')):
            raise osv.except_osv(_('Warning!'),_('The start date must be anterior to the end date.'))   
            
        if res.get('id',False):
            datas['ids']=[res['id']]        
        if not datas['form']['employee_s']:
            raise osv.except_osv(_('No Data Available!'), _('Please select at least one employee!')) 
        
        attend_obj = self.pool.get('hr.attendance') 
        attend_ids = attend_obj.search(cr,uid,
        [('name','>=',datas['form']['start_date'] + ' 00:00:00'),
        ('name','<=',datas['form']['end_date'] + ' 23:59:59'),
        ('employee_id','in',datas['form']['employee_s']),
        ('action','=','sign_in')],
        order='name ASC')
        if not attend_ids:
            raise osv.except_osv(_('No Data Available!'), _('No records are found for your selection!'))
        
        count = 0
        count_emp = 0;
        employee_obj = self.pool.get('hr.employee')
        employee = employee_obj.browse(cr, uid,datas['form']['employee_s'],context=context) 
        for emp in employee:
            datas['form']['employee_name_s'].insert(count,emp.name.capitalize())
            count += 1
            count_emp +=1
            if count_emp < len(employee):
                datas['form']['employee_name_s'].insert(count,',')     
                count += 1
                
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.employee_attendance_summary_report', data=datas, 
        context=context)
        
        

    
    # def create_attachment(self, cr, uid, ids, context=None):
    #     attachment_obj = self.pool.get('ir.attachment')
    #     attachment_id = False
    #     id = str(context['data']['ids'][0])
    #     ir_actions_report = self.pool.get('ir.actions.report.xml')
    #     matching_reports = ir_actions_report.search(cr, uid, [('report_name','=',context['report_name'])])
    #     if matching_reports:
    #             report = ir_actions_report.browse(cr, uid, matching_reports[0], context=context)
    #             (result, format) = report.render_report(id, report.report_name,context['data'], context=context)
    #             result1 = result
    #             eval_context = {'time': fields.datetime.now(), 'object': context['data']}
    #             if not report.attachment or not eval(report.attachment, eval_context):
    #                 # no auto-saving of report as attachment, need to do it manually
    #                 result = base64.b64encode(result)
    #                 file_name = re.sub(r'[^a-zA-Z0-9_-]','_','Attendance Report')
    #                 file_name += ".pdf"
    #                 attachment_id = attachment_obj.create(cr, uid,
    #                     {
    #                         'name': file_name,
    #                         'datas': result,
    #                         'datas_fname': file_name,
    #                         'res_model': context['attachment_model'],
    #                         'res_id': id,
    #                         'type': 'binary'
    #                     }, context=context)
    #     return attachment_id

    # def send_report_emp(self, cr, uid, ids, context=None):
    #     if not context:
    #         context={}
    #     datas = {'ids': context.get('active_ids', [])} 
    #     res = self.read(cr, uid, ids, ['start_date', 'end_date', 'employee_s','action','date_or_period','period_id'], context=context)
    #     res = res and res[0] or {}
    #     datas['form'] = res
    #     datas['form']['employee_name_s'] = []       
    #     if res.get('date_or_period',False) == 'period':
    #         period_id = res.get('period_id',False)
    #         if period_id:
    #             period = self.pool.get('ik.account.period').browse(cr, uid, period_id[0], context=context)
    #             start_period = period.date_start
    #             end_period = period.date_stop
    #             datas['form']['start_date'] = start_period
    #             datas['form']['end_date'] = end_period
    #     if res.get('id',False):
    #         datas['ids']=[res['id']] 
    #     if not datas['form']['employee_s']:
    #         raise osv.except_osv(_('No Data Available!'), _('Please select at least one employee!'))
    #     count = 0
    #     count_emp = 0;
    #     employee_name = ''
    #     employee_obj = self.pool.get('hr.employee')
    #     employee = employee_obj.browse(cr, uid,datas['form']['employee_s'],context=context) 
    #     for emp in employee:
    #         datas['form']['employee_name_s'].insert(count,emp.name.capitalize())
    #         employee_name += emp.name.capitalize()
    #         count += 1
    #         count_emp +=1
    #         if count_emp < len(employee):
    #             datas['form']['employee_name_s'].insert(count,',')
    #             employee_name += ','
    #             count += 1
                
    #     ir_model_data = self.pool.get('ir.model.data')
    #     try:
    #         template_id = ir_model_data.get_object_reference(cr, uid, 'ik_hrms_custom', 'ik_hrms_custom_template_email_daily_report')[1]
    #     except ValueError:
    #         template_id = False
    #     try:
    #         compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
    #     except ValueError:
    #         compose_form_id = False

        
    #     start_date = self.browse(cr, uid, ids, context=context).start_date
    #     end_date = self.browse(cr, uid, ids, context=context).end_date
    #     start_date_display = datetime.strptime(str(start_date), '%Y-%m-%d')
    #     start_date_display = datetime.strftime(start_date_display, '%d-%m-%Y')
    #     end_date_display = datetime.strptime(str(end_date), '%Y-%m-%d')
    #     end_date_display = datetime.strftime(end_date_display, '%d-%m-%Y')
    #     for att in self.browse(cr, uid, ids, context=context):
    #         att.employee_name =  employee_name
    #         att.start_date_display = start_date_display
    #         att.end_date_display = end_date_display
           
    #     context['order_ids'] = ids[0]
    #     context['data'] = datas
    #     context['attachment_model'] ='attend.report.all.employee'
    #     context['report_name'] = 'ik_hrms_custom.report_daily_attend_all_employee'
    #     attachment_id = self.create_attachment(cr, uid, ids, context=context)
        
    #     result_partner_ids = []
    #     count_partner = 0
    #     partner_ids = self.pool.get('res.users').search(cr, uid,[('groups_id.name','=','Manager')],context=context)
    #     partner = self.pool.get('res.users').browse(cr, uid, partner_ids, context)
        
    #     for item in partner:
    #         if item.active == True:
    #             result_partner_ids.insert(count_partner,item.partner_id.id)

    #     ctx = dict(context)
    #     ctx.update({
    #         'default_model': 'attend.report.all.employee',
    #         'default_res_id': ids[0],
    #         'default_attachment_ids' :[(6, 0, [attachment_id])],
    #         'default_partner_ids': result_partner_ids,
    #         'mail_log_sender_id':uid,
    #         'mail_log_model': 'attend.report.all.employee',
    #         'mail_log_res_id': ids[0],
    #         'default_use_template': bool(template_id),
    #         'default_template_id': template_id,
    #         'default_composition_mode': 'comment',
    #         'mail_force_notify': True,
    #         'from_render_report': True,
    #         'mail_auto_delete': False,
    #     })
    #     return {
    #         'name': _('Compose Email'),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'mail.compose.message',
    #         'views': [(compose_form_id, 'form')],
    #         'view_id': compose_form_id,
    #         'target': 'new',
    #         'context': ctx,
    #     }


