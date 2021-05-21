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

from datetime import datetime, timedelta
import time
from openerp.osv import osv
from openerp.report import report_sxw

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

tot = {}

overall_comments = {}

class lateness_early_co_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(lateness_early_co_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
        })
        self.context = context



class lateness_early_checkout_report(osv.AbstractModel):
    _name = 'report.sisb_hr.lateness_early_checkout_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.lateness_early_checkout_report'
    _wrapped_report_class = lateness_early_co_report