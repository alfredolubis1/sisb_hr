from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from datetime import date, time, datetime
import base64
import csv


class ExportEmployeeScheduleTemplateWiz(models.TransientModel):
    _name = 'export.employee.schedule.template.wiz'

    data = fields.Binary('Template')
    filename = fields.Char('File name')
