from openerp.osv import fields, osv
from openerp import _



class sisb_hr_holidays_status(osv.osv):
    _inherit = "hr.holidays.status"
    _columns =  {
           'max_leaves': fields.integer('Maximum Allowed',required=True)
         
    }

