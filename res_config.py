from openerp.osv import fields, osv

class sisb_att_config(osv.osv_memory):
    _inherit = 'hr.config.settings'
    # _columns = {
    #     'group_track_all_attendances': fields.boolean('Track attendances for all employees (SISB)', 
    #     implied_group='base.group_sisb_attendance', help="Allocates attendance group to all users."),
    # }
    

    # def onchange_hr_timesheet(self, cr, uid, ids, timesheet, context=None):
    #     """ module_hr_timesheet implies module_hr_attendance """
    #     if timesheet:
    #         return {'value': {'module_hr_timesheet': True}}
    #     return {}

    # def onchange_hr_attendance(self, cr, uid, ids, attendance, context=None):
    #     """ module_hr_timesheet implies module_hr_attendance """
    #     if not attendance:
    #         return {'value': {'module_hr_attendance': False}}
    #     return {}
class ir_actions_act_window(osv.osv):
    _inherit = 'ir.actions.act_window'
    
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        """ call the method get_empty_list_help of the model and set the window action help message
        """
        ids_int = isinstance(ids, (int, long))
        if ids_int:
            ids = [ids]
        results = super(ir_actions_act_window, self).read(cr, uid, ids, fields=fields, context=context, load=load)

        if not fields or 'help' in fields:
            for res in results:
                model = res.get('res_model')
                if model and self.pool.get(model):
                    ctx = dict(context or {})
                    res['help'] = self.pool[model].get_empty_list_help(cr, uid, res.get('help', ""), context=ctx)
        if ids_int:
            if results:
                return results[0]
        return results
