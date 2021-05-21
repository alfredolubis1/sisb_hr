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

import time
import openerp
import datetime
from datetime import date
from datetime import datetime, timedelta
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, image_colorize, image_resize_image_big
from openerp.exceptions import except_orm, Warning, RedirectWarning
import calendar
from openerp.exceptions import ValidationError


class academic_week(models.Model):
    _name = "academic.week"


    name = fields.Char("Name", required=True)
    code = fields.Char("Code", required=True)
    date_start = fields.Date("Start Date", select=1, required=True)
    date_end = fields.Date("End Date", select=1, required=True)
    year_id = fields.Many2one('academic.year', "Academic Year", required=True, help="Related Academic Year")
    description = fields.Text("Description")

    @api.constrains('date_start','date_end')
    def _check_duration(self):
        if self.date_end and self.date_start and self.date_end < self.date_start:
            raise Warning(_('Error ! The duration of the Month(s) is/are invalid.'))

    
    @api.constrains('year_id','date_start','date_end')
    def _check_year_limit(self):
        if self.year_id and self.date_start and self.date_end:
            if self.year_id.date_stop < self.date_end or \
                self.year_id.date_stop < self.date_start or \
                self.year_id.date_start > self.date_start or \
                self.year_id.date_start > self.date_end:
                raise Warning(_('Invalid Weeks ! Some weeks overlap or the date period is not in the scope of the academic year.'))




class inherit_academic_year(models.Model):
    _inherit = 'academic.year'

    week_ids = fields.One2many('academic.week', 'year_id', "Weeks", help="Related Academic weeks")

    @api.multi
    def generate_academic_weeks(self):
        if self.week_ids:
            raise ValidationError(_("The week is already generated"))
        academic_week_obj = self.env['academic.week']
        FMT = '%Y-%m-%d'
        date_start  = self.date_start
        date_end    = self.date_stop
        start   = datetime.strptime(date_start, FMT)
        end     = datetime.strptime(date_end, FMT)
        day_step = timedelta(days=1)
        week_list_id = []
        week = 0
        while (start <= end):
            start_of_the_week = ''
            end_of_the_week = ''
            day = calendar.weekday(int(start.strftime("%Y")),int(start.strftime("%m")),int(start.strftime("%d")))
            if day != 6:
                start += day_step
                continue
            end_of_the_week = start
            sotw = (end_of_the_week - timedelta(days=6))
            if sotw < datetime.strptime(self.date_start, FMT):
                start_of_the_week = datetime.strptime(self.date_start, FMT)
            if sotw > datetime.strptime(self.date_start, FMT):
                start_of_the_week = sotw
            if start_of_the_week and end_of_the_week:
                week += 1
            academic_week = academic_week_obj.create({
                'name': 'Week',
                'code': week,
                'date_start': start_of_the_week.strftime(FMT),
                'date_end': end_of_the_week.strftime(FMT),
                'year_id': self.id,
            })
            if academic_week:
                self.write({'week_ids': [(4, academic_week.id)]})
            start += day_step
        return True
