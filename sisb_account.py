import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import time

import openerp
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools.safe_eval import safe_eval as eva
import openerp.addons.decimal_precision as dp

#class account_fiscalyear(osv.osv):
#    _inherit = "account.fiscalyear"
#    
#    def create_period(self, cr, uid, ids, context=None, interval=1):
#        period_obj = self.pool.get('account.period')
#        for fy in self.browse(cr, uid, ids, context=context):
#            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
#            
#            while ds.strftime('%Y-%m-%d') < fy.date_stop:
#                de = ds + relativedelta(months=interval, days=-1)
#
#                if de.strftime('%Y-%m-%d') > fy.date_stop:
#                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')
#
#                period_obj.create(cr, uid, {
#                    'name': ds.strftime('%m/%Y'),
#                    'code': ds.strftime('%m/%Y'),
#                    'date_start': ds.strftime('%Y-%m-%d'),
#                    'date_stop': de.strftime('%Y-%m-%d'),
#                    'fiscalyear_id': fy.id,
#                })
#                ds = ds + relativedelta(months=interval)
#        return True
    
class sisb_account_fiscalyear(osv.osv):
    _name = "sisb.account.fiscalyear"
    _description = "Fiscal Year"
    _columns = {
        'name': fields.char('Year', required=True),
        'code': fields.char('Code', size=6, required=True),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period_ids': fields.one2many('sisb.account.period', 'fiscalyear_id', 'Periods'),

    }
    _defaults = {
        
    }
    _order = "date_start, id"


    def _check_duration(self, cr, uid, ids, context=None):
        obj_fy = self.browse(cr, uid, ids[0], context=context)
        if obj_fy.date_stop < obj_fy.date_start:
            return False
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe start date of a fiscal year must precede its end date.', ['date_start','date_stop'])
    ]

    def create_period3(self, cr, uid, ids, context=None):
        return self.create_period(cr, uid, ids, context, 3)

    def create_period(self, cr, uid, ids, context=None, interval=1):
        period_obj = self.pool.get('sisb.account.period')
        for fy in self.browse(cr, uid, ids, context=context):
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
#            period_obj.create(cr, uid, {
#                    'name':  "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
#                    'code': ds.strftime('00/%Y'),
#                    'date_start': ds,
#                    'date_stop': ds,
#                    'special': True,
#                    'fiscalyear_id': fy.id,
#                })
            while ds.strftime('%Y-%m-%d') < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)

                if de.strftime('%Y-%m-%d') > fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')

                period_obj.create(cr, uid, {
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
        return True




class sisb_account_period(osv.osv):
    _name = "sisb.account.period"
    _description = "Account period"
    _columns = {
        'name': fields.char('Period Name', required=True),
        'code': fields.char('Code', size=12),
        'date_start': fields.date('Start of Period', required=True),
        'date_stop': fields.date('End of Period', required=True),
        'fiscalyear_id': fields.many2one('sisb.account.fiscalyear', 'Fiscal Year', required=True, select=True),
        
    }
    _defaults = {
       
    }
    _order = "date_start"
    _sql_constraints = [
        
    ]

    def _check_duration(self,cr,uid,ids,context=None):
        obj_period = self.browse(cr, uid, ids[0], context=context)
        if obj_period.date_stop < obj_period.date_start:
            return False
        return True

  
    _constraints = [
        (_check_duration, 'Error!\nThe duration of the Period(s) is/are invalid.', ['date_stop']),
        
    ]

    @api.returns('self')
    def next(self, cr, uid, period, step, context=None):
        ids = self.search(cr, uid, [('date_start','>',period.date_start)])
        if len(ids)>=step:
            return ids[step-1]
        return False