from openerp import models, fields, api, _

class exit_interview_resign(models.TransientModel):
    _name = "hr.exit.interview"

    name                = fields.Char(string="")
    employee_number     = fields.Char("Employee ID")
    position_id         = fields.Many2one('employee_position_id', string="Position")
    department_id       = fields.Many2one('department_id', string="Department/Section")
    join_date           = fields.Date(string="Start Working Date")
    end_wk_date         = fields.Date(string="Last Working Date")
    effective_date      = fields.Date(string="Effective Date")
    wk_condition_ids    = fields.One2many('wk.condition.template', 'exit_intvw_id', string="Work Condition")
        
