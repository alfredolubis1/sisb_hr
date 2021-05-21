from openerp import models, fields, api, _
from openerp.exceptions import ValidationError, AccessError


class wizard_emp_transfer_confirmation(models.TransientModel):
    _name = "employee.transfer.confirmation"

    name = fields.Char("Name")

    @api.multi
    def transfer_employee(self):
        print('self = ', self._context)
        context = self._context
        tf_obj = self.env[context['active_model']].search([('id','=',context['active_id'])])
        for rec in tf_obj:
            all_returned_item = rec.tf_boarding_list_ids.filtered(lambda x: x.is_returned == True)
            for emp in rec.employee_id:
                emp.boarding_list_ids = [(3, k.id , 0)for k in all_returned_item]
                emp.off_boarding_list_ids = [(4, i.id, 0)for i in all_returned_item]
            if rec.application_source_id:
                for l in rec.application_source_id:
                    l.write({'state': 'confirmed'})
        return tf_obj.write({'state': 'accept','notes': 'All the changes for this emp will be updated on the Effective Date'})


