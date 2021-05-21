# -*- encoding: utf-8 -*-
##############################################################################
#
#    TigernixERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2011-2012 Serpent Consulting Services (<http://www.serpentcs.com>)
#    Copyright (C) 2013-2014 Serpent Consulting Services (<http://www.serpentcs.com>)
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

from openerp import models, fields, api, _

class activate_deactivate_employee(models.TransientModel):

    _name = 'employee.activation.deactivation'
    _description = 'Activate Or Deactivate Employee'
    
    active = fields.Boolean('Active')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    employee_id_display = fields.Many2one('hr.employee', string="Employee", related="employee_id")
    name = fields.Text("Reason")



    # @api.model
    # def default_get(self, fields):
    #     res = super(activate_deactivate_employee, self).default_get(fields)
    #     emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    #     if 'schedule_id' in fields:
    #         res.update({'schedule_id': emp.working_time_id.id})
    #     if 'start_hour' in fields:
    #         res.update({'start_hour': emp.end_hour})

    @api.onchange('employee_id')
    def onchange_employ(self):
        if self.employee_id:
            self.active = self.employee_id.active
        if not self.employee_id:
            self.active = False

    @api.multi
    def process_employee(self):
        for rec in self.employee_id:
            rec.update({
                'active': self.active,
                'deactivate_reason': self.name
            })
        # emp_ids = self._context.get('active_ids')
        # res = {}
        # emp_obj = self.env['hr.employee']
        # user_obj = self.env['res.users']
        # for emp in emp_obj.browse(emp_ids):
        #     user = False
        #     if emp.resource_id and emp.resource_id.user_id :
        #         user = emp.resource_id and emp.resource_id.user_id
        #         emp.write({'active':False, 'resource_id.user_id.active':False, 'deactivate_reason': self.reason})
        #         user.write({'active':False})
        #     else:
        #         emp.write({'deactivate_reason': self.reason, 'active':False})
        # return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
