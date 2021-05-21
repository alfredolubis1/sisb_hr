from openerp.exceptions import Warning
from openerp import tools
from openerp import SUPERUSER_ID, models
from openerp.osv import fields, osv
from lxml import etree
from openerp.tools.translate import _

class res_users(osv.osv):
    _inherit = 'res.users'
    
    def _get_group(self,cr, uid, context=None):
        dataobj = self.pool.get('ir.model.data')
        result = []
        try:
          
            dummy,group_id = dataobj.get_object_reference(cr, SUPERUSER_ID, 'base', 'group_user')
            result.append(group_id)
#            dummy,group_id = dataobj.get_object_reference(cr, SUPERUSER_ID, 'account', 'group_account_invoice')
            result.append(group_id)
        except ValueError:
            # If these groups does not exists anymore
            pass
        return result
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False, submenu=False):
        
        res = super(res_users, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        ir_model_data = self.pool.get('ir.model.data')
        groups = {}
        if  view_type == 'form':
            
            first_node = doc.xpath("//field[@name='groups_id']")
            if first_node:
                root = first_node[0].getparent()
                groups_ref = [  
                                # ('sisb_hr_new','group_hr'),
                                # ('sisb_hr_new','group_project_manager'),
#                                ('ik_hrms_custom','group_administrator'),
                                ('base','group_user'),
                                # ('ik_hrms_custom','group_director'),
                                ('base','group_hr_manager')]
                
              
                for obj,group_ref in groups_ref:
                   
                    try:
                        group_id = ir_model_data.get_object_reference(cr, uid, obj, group_ref)[1]
                    except ValueError:
                        group_id = False
                   
                    group_field_name = 'in_group_%s'%str(group_id)
                    fields_get = self.fields_get(cr, SUPERUSER_ID, [group_field_name], context)
                 
                    if group_id and fields_get.get(group_field_name, False):
                        groups[group_field_name] = etree.Element("field")
                        groups[group_field_name].set('name',group_field_name)
                        root.append(groups[group_field_name])
                       
                        res['fields'][group_field_name] = fields_get.get(group_field_name, False)
        res['arch'] = etree.tostring(doc)   
        return res
    
    _columns = {
#        'work_email' :fields.char('Email',related='partner_id.email')
#        'employee_creation' : fields.boolean('Employee Creation' ,default=True)
    }
    def create(self, cr, uid, vals,context=None):
        user_id = super(res_users, self).create(cr, uid, vals, context=context)
        user = self.browse(cr, uid, user_id, context=context)
        if user.partner_id.company_id: 
            user.partner_id.write({'company_id': user.company_id.id})
#        if user.employee_creation == True:
            employee_obj = self.pool.get('hr.employee')
            employee_obj.create(cr, uid,{'name': user.name,'user_id': user.id, 'company_id': user.company_id.id, 'work_email': user.email}, context=context)
        return user_id
    
#    def _get_group(self,cr, uid, context=None):
#        dataobj = self.pool.get('ir.model.data')
#        result = []
#        try:
#            print'dwiaa'
#            dummy,group_id = dataobj.get_object_reference(cr, SUPERUSER_ID, 'base', 'group_user')
#            result.append(group_id)
#            dummy,group_id = dataobj.get_object_reference(cr, SUPERUSER_ID, 'base', 'group_partner_manager')
#            result.append(group_id)
#        except ValueError:
#            # If these groups does not exists anymore
#            pass
#        return result
    _defaults = {
      
        'groups_id': _get_group,

    }
