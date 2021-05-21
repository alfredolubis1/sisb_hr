# -*- coding: utf-8 -*-
##############################################################################
#
#    TigernixERP, Open Source Management Solution
#    Copyright (C) 2004-today Tigernix, Pte Ltd. (<http://www.tigernix.com>)
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

from openerp.addons.crm import crm
from openerp.osv import fields, osv
from openerp import tools



class employee_demographic_report(osv.Model):
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        company_list = []
        employee_obj = self.pool.get('hr.employee')
        employee_id  = employee_obj.search(cr, uid, [], context=context)
        employee     = employee_obj.browse(cr, uid, employee_id)
        # company      =
        # if employee:
        #     for rec in employee:
        #         for line in rec.user_id:
        #             if line.company_id:
        #                 company_list.append(line.company_id.id)
        company_obj = self.pool.get('res.company').search(cr, uid, [], context=context)
        for company in company_obj:
            if company not in company_list:
                company_list.append(company)
        domain+=([('company_id', 'in', company_list)])
        res = super(employee_demographic_report,self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        return res

        
    _name = "employee.demographic"
    _auto = False
    _columns = {
        'name'          : fields.char(string="Employee"), 
        'company_id'    : fields.many2one('res.company', string="Company", readonly=True),
        'gender'        : fields.selection([
                                            ('male','Male'),
                                            ('female','Female'),
                                            ],string="Gender"),
        'marital'       : fields.selection([
                                            ('single','Single'),
                                            ('married','Married'),
                                            ('widower','Widower'),
                                            ('divorced','Divorced'),
                                            ], string="Marital Status"),
        'data_id'       : fields.integer('Data' , readonly=True),
        'amount'        : fields.integer('# Amount', readonly=True),
    }


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'employee_demographic')
        cr.execute("""
            create or replace view employee_demographic as (
                SELECT 
                    he.id as id,
                    he.id as data_id,
                    he.gender as gender,
                    he.marital as marital,
                    rr.name as name,
                    rr.company_id as company_id,
                    1 as amount
                FROM 
                    hr_employee he , resource_resource rr
                WHERE
                    he.id = rr.id 
                AND 
                    rr.active = true
                )""")



class employee_demographic_age(osv.Model):

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        company_list = []
        employee_obj = self.pool.get('hr.employee')
        employee_id  = employee_obj.search(cr, uid, [], context=context)
        employee     = employee_obj.browse(cr, uid, employee_id)
        # company      =
        # if employee:
        #     for rec in employee:
        #         for line in rec.user_id:
        #             if line.company_id:
        #                 company_list.append(line.company_id.id)
        company_obj = self.pool.get('res.company').search(cr, uid, [], context=context)
        for company in company_obj:
            if company not in company_list:
                company_list.append(company)
        domain+=([('company_id', 'in', company_list)])
        res = super(employee_demographic_age,self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        return res

    _name = "demographic.age"
    _auto = False
    _columns = {    
        'name': fields.char("Employee"),
        'amount': fields.integer('# Amount', readonly=True),
        'company_id': fields.many2one('res.company', "Company"),
        'data_id': fields.integer("Data", readonly=True),
        'country_id': fields.many2one('res.country', "Nationality", readonly=True),
        'gender': fields.selection([
                                        ('male','Male'),
                                        ('female','Female')
                                    ], string="Gender"),
        'marital_status': fields.selection([
                                        ('single','Single'),
                                        ('married','Married'),
                                        ('widower','Widower'),
                                        ('divorced','Divoced')
                                    ], string="Marital Status"),
        'age_range': fields.selection([
                                        ('under20','Age < 20'),
                                        ('between20_30', 'Age 20 - 29'),
                                        ('between30_40', 'Age 30 - 39'),
                                        ('greater40', 'Age > 40')
                                    ], string="Age Range")

    }


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'demographic_age')
        cr.execute("""
            create or replace view demographic_age as (
                SELECT 
                    rr.name as name,
                    he.id as id,
                    he.id as data_id,
                    rr.company_id as company_id,
                    1 as amount,
                    'under20' as age_range,
                    he.marital as marital_status,
                    he.gender as gender,
                    he.country_id as country_id
                FROM 
                    hr_employee he, resource_resource rr
                WHERE
                    rr.id = he.id
                    AND
                    EXTRACT(YEAR FROM AGE(he.birthday)) < 20
                UNION

                SELECT 
                    rr.name as name,
                    he.id as id,
                    he.id as data_id,
                    rr.company_id as company_id,
                    1 as amount,
                    'between20_30' as age_range,
                    he.marital as marital_status,
                    he.gender as gender,
                    he.country_id as country_id
                FROM 
                    hr_employee he, resource_resource rr
                WHERE 
                    rr.id = he.id
                    AND
                    EXTRACT(YEAR FROM AGE(he.birthday)) >= 20
                    AND
                    EXTRACT(YEAR FROM AGE(he.birthday)) <= 29
                UNION

                SELECT 
                    rr.name as name,
                    he.id as id,
                    he.id as data_id,
                    rr.company_id as company_id,
                    1 as amount,
                    'between30_40' as age_range,
                    he.marital as marital_status,
                    he.gender as gender,
                    he.country_id as country_id
                FROM 
                    hr_employee he, resource_resource rr
                WHERE 
                    rr.id = he.id
                    AND
                    EXTRACT(YEAR FROM AGE(he.birthday)) >= 30
                    AND
                    EXTRACT(YEAR FROM AGE(he.birthday)) <= 39
                UNION
                
                SELECT 
                    rr.name as name,
                    he.id as id,
                    he.id as data_id,
                    rr.company_id as company_id,
                    1 as amount,
                    'greater40' as age_range,
                    he.marital as marital_status,
                    he.gender as gender,
                    he.country_id as country_id
                FROM 
                    hr_employee he, resource_resource rr
                WHERE 
                    rr.id = he.id
                    AND
                    EXTRACT(YEAR FROM AGE(he.birthday)) >= 40
                
                ORDER BY age_range
            )
        """)

class employee_demographic_marital_status(osv.Model):
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        company_list = []
        employee_obj = self.pool.get('hr.employee')
        employee_id  = employee_obj.search(cr, uid, [], context=context)
        employee     = employee_obj.browse(cr, uid, employee_id)
        # company      =
        # if employee:
        #     for rec in employee:
        #         for line in rec.user_id:
        #             if line.company_id:
        #                 company_list.append(line.company_id.id)
        company_obj = self.pool.get('res.company').search(cr, uid, [], context=context)
        for company in company_obj:
            if company not in company_list:
                company_list.append(company)
        domain+=([('company_id', 'in', company_list)])
        res = super(employee_demographic_marital_status,self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        return res

    _name = "demographic.marital.status"
    _auto = False
    _columns = {    
        'name': fields.char("Employee"),
        'amount': fields.integer('# Amount', readonly=True),
        'company_id': fields.many2one('res.company', "Company"),
        'data_id': fields.integer("Data", readonly=True),
        # 'gender': fields.selection
        'marital_status': fields.selection([
            ('single','Single'),
            ('married', 'Married'),
            ('widower', 'Widow'),
            ('divorced', 'Divorce')
        ], string="Marital Status")

    }


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'demographic_marital_status')
        cr.execute("""
            CREATE OR REPLACE VIEW demographic_marital_status as (
                SELECT 
                    he.id as id,
                    he.id as data_id,
                    rr.name as name,
                    rr.company_id as company_id,
                    'single' as marital_status
                FROM 
                    hr_employee he, resource_resource rr
                WHERE
                    rr.id = he.id 
                    AND
                    he.marital = 'single'
                UNION

                SELECT 
                    he.id as id,
                    he.id as data_id,
                    rr.name as name,
                    rr.company_id as company_id,
                    'married' as marital_status
                FROM 
                    hr_employee he, resource_resource rr
                WHERE
                    rr.id = he.id 
                    AND
                    he.marital = 'married'
                UNION

                SELECT 
                    he.id as id,
                    he.id as data_id,
                    rr.name as name,
                    rr.company_id as company_id,
                    'widower' as marital_status
                FROM 
                    hr_employee he, resource_resource rr
                WHERE
                    rr.id = he.id 
                    AND
                    he.marital = 'widower'
                UNION

                SELECT 
                    he.id as id,
                    he.id as data_id,
                    rr.name as name,
                    rr.company_id as company_id,
                    'divorced' as marital_status
                FROM 
                    hr_employee he, resource_resource rr
                WHERE
                    rr.id = he.id 
                    AND
                    he.marital = 'divorced'
            )
        """)

class employee_report(osv.Model):
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        company_list = []
        employee_obj = self.pool.get('hr.employee')
        employee_id  = employee_obj.search(cr, uid, [], context=context)
        employee     = employee_obj.browse(cr, uid, employee_id)
        # company      =
        # if employee:
        #     for rec in employee:
        #         for line in rec.user_id:
        #             if line.company_id:
        #                 company_list.append(line.company_id.id)
        company_obj = self.pool.get('res.company').search(cr, uid, [], context=context)
        for company in company_obj:
            if company not in company_list:
                company_list.append(company)
        domain+=([('company_id', 'in', company_list)])
        res = super(employee_report,self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        return res




    _name = "employee.report"
    _auto = False
    _columns = {
        'name'          : fields.char(string="Employee"), 
        'company_id'    : fields.many2one('res.company', string="Company", readonly=True),
        'data_id'       : fields.integer('Data' , readonly=True),
        'day'           : fields.integer('Day', readonly=True),
        'amount'        : fields.integer('# Amount', readonly=True),
        'state'         : fields.selection([
                                            ('new','New'),
                                            ('probation','Probation'),
                                            ('contract','Contract'),
                                            ('permanent','Permanent'),
                                            ('resign','Resign'),
                                            ], string="Employment Types")
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'employee_report')
        cr.execute("""
            create or replace view employee_report as (
                SELECT 
                    he.id as id,
                    rp.name as name,
                    he.id AS data_id,
                    rr.company_id as company_id,
                    1 AS amount,
                    he.probation_end_date::date - (SELECT CURRENT_DATE)::date as day,
                    he.employee_state as state
                FROM 
                    hr_employee he 
                LEFT JOIN 
                    res_partner rp on (rp.id = (SELECT ru.partner_id FROM res_users ru WHERE ru.id = he.user_id))
                LEFT JOIN 
                    resource_resource rr on (rr.id = he.id)
                WHERE 
                    employee_state != 'resign' AND
                  
                    CASE WHEN employee_state = 'probation' THEN
                        (SELECT (he.probation_end_date::date - (SELECT CURRENT_DATE)::date)) < 30
                    ELSE
                        (SELECT (he.contract_end_date::date - (SELECT CURRENT_DATE)::date)) < 30
                    END
                
                )""")
        # fetch = cr.fetchall()
        # print('fetch = ', fetch)
        # return fetch