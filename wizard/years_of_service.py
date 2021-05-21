# -*- coding: utf-8 -*-
import time
import base64
import re
from openerp import models, fields, api, _
from datetime import datetime
from openerp.tools.translate import _


class years_of_service_wizard(models.TransientModel):
    _name = "years.of.service"

    company_id = fields.Many2one('res.company', string="Company")
    options = fields.Selection([
        ('one_comp','One Company'),
        ('multi_comp','Multiple Company')
    ], default="one_comp", string="Options")
    company_ids = fields.Many2many('res.company', string="Select Company")
    from_year_th = fields.Integer(string="From")
    to_year_th = fields.Integer(string="To")

    @api.multi
    def print_report(self):
        data = self.read()[0]
        datas = {
                'ids': [],
                'model': 'hr.attendance',
                'form': data
                }
        return self.pool['report'].get_action(self._cr, self._uid, [], 'sisb_hr.years_of_service_report', data=datas, context=self._context)