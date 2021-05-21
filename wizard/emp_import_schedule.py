# -*- encoding: utf-8 -*-

import base64
from openerp import api, fields, models
import tempfile
from openerp import pooler, _
import base64
from openerp.exceptions import except_orm, Warning, RedirectWarning
import csv
import re
import cStringIO
import openerp.tools as tools
from ..utility.utils import hour_float_to_time as hftt
from tempfile import TemporaryFile


class SISBEmp_Import(models.TransientModel):
    _name = "sisb.emp.import.schedule"

    name = fields.Binary("File")

    @api.one
    def import_employee_schedule(self):
        active_id = self.env.context.get('active_id')
        model = self.env[self._context['active_model']].search([('id', '=', self._context['active_id'])])
        form = self.read()
        wk_time_line_obj = self.env['work.time.line']
        wk_time_structure_obj = self.env['work.time.structure'].search([])
        context = dict(self._context or {})
        fdata = form and base64.decodestring(form[0]['name']) or False
        input = cStringIO.StringIO(fdata)
        input.seek(0)
        data = list(csv.reader(input, quotechar='"' or '"', delimiter=','))
        headers = data[0]
        all_sched = []
        for rec in model:
            if rec.wk_time_structure_ids:
                for sched in rec.wk_time_structure_ids:
                    sched.unlink()
            
            for detail in data[1:]:
                sched_id = False
                for time in wk_time_structure_obj:
                    # if hftt(time.start_hour) == detail[2] and hftt(time.late_tolerance) == detail[3] and hftt(time.start_break_hour) == detail[4] and hftt(time.end_break_hour) == detail[5] and hftt(time.end_hour) == detail[6]:
                    print('detail2 = ', detail[2])
                    if time.shift_code == detail[2]:
                        sched_id = time
                if sched_id:
                    sched_date = wk_time_line_obj.create({'date_from': detail[0], 'date_to': detail[1], 'wk_time_structure_id': sched_id.id})
                else:
                    sched_date = wk_time_line_obj.create({'date_from': detail[0], 'date_to': detail[1]})
                all_sched.append(sched_date.id)
            rec.wk_time_structure_ids = [(6, 0, all_sched)]