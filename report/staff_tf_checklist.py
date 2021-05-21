# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2011-Today Serpent Consulting Services PVT. LTD.
#    (<http://www.serpentcs.com>)
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
from openerp.report import report_sxw
from openerp import models


class staff_transfer_checklist_form(report_sxw.rml_parse):
    _name = "report.sisb_hr.staff_tf_checklist_form"
    def __init__(self, cr, uid, name, context):
        super(staff_transfer_checklist_form, self).__init__(cr, uid, name,context=context)
        self.localcontext.update({

        })

class report_staff_tf_checklist(models.AbstractModel):
    _name = 'report.sisb_hr.staff_tf_checklist_form'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.staff_tf_checklist_form'
    _wrapped_report_class = staff_transfer_checklist_form

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=
