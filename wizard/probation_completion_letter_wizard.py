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

import time
from openerp.osv import fields, osv

class probationcompletion_letter(osv.osv_memory):

    _name = "probation.completion.letter"
    _description = "Probation Completion Letter"
    _columns = {
        #'term_id' : fields.many2one('academic.term', 'Term', required=True),
        'new_salary': fields.integer('New Salary'),
        'option': fields.selection([
                        ('new', 'New Salary'), #Early Years Section
                        ('same', 'Same Salary'),
                        ], 'Option'),
    }

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        datas = {
            'ids': context.get('active_ids', []),
            'model': 'hr.employee',
            'form': data
        }
        datas['form']['ids'] = datas['ids']
        if data['section'] == 'nk':
            return self.pool['report'].get_action(cr, uid, [], 'sisb_project.report_nk_student_handbook_new', data=datas, context=context)
        elif data['section'] == 'primary':
            return self.pool['report'].get_action(cr, uid, [], 'sisb_project.report_nk_primary_handbook', data=datas, context=context)


