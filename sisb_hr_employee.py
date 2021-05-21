import time
from datetime import date, datetime, timedelta
from dateutil import tz
from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp import api
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from tzlocal import get_localzone
import pytz
from .utility.utils import hour_float_to_time as hftt
from .utility.utils import ordinal_num as ordinal
from openerp.exceptions import ValidationError, AccessDenied, AccessError
from openerp import tools
import base64
import calendar
from pytz import timezone


def _employee_get(obj, cr, uid, context=None):
    ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)

    return ids and ids[0] or False

# @api.multi
# def _employee_state_get(self):
#     self._cr.execute('SELECT LOWER(name), name FROM employment_types ORDER BY sequence')
#     all_state = self._cr.fetchall()
#     return [(k, v) for k, v in all_state]

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    _description = "Employee"
    # _inherit = 'mail.thread'
    

    
    def create(self, cr, uid, vals, context=None):
        prefix_code = ''
        print('vals = ', vals)
        if vals.get('employee_no', '/') == '/' or vals.get('employee_no') == False:
            if vals.get('company_id'):
                company = self.pool.get('res.company').search(cr, uid, [('id', '=', vals['company_id'])], context=context)
                company_id = self.pool.get('res.company').browse(cr, uid, company)
                company_name = company_id.name
                print('company_name = ', company_name)
                if company_name == 'SISB Public Company Limited':
                    prefix_code = 'HQ'
                elif company_name == 'SISB SIRI Company Limited':
                    prefix_code = 'SIRI'
                else:
                    for rec in company_id.school_ids:
                        prefix_code = rec.code
            default_seq = self.pool.get('ir.sequence').search(cr, uid, [('code','=','hr.employee')], context=context)
            default_seq_obj = self.pool.get('ir.sequence').browse(cr, uid, default_seq)
            print('prefix_code = ', prefix_code)
            default_seq_obj.update({
                'prefix': prefix_code + '/',
            })
            vals['employee_no'] = self.pool['ir.sequence'].next_by_code(cr, uid, 'hr.employee',context=context) or '/'
        res = super(hr_employee, self).create(cr, uid, vals, context=context)
        return res

    def default_get(self, cr, uid, fields, context=None):
        res = super(hr_employee, self).default_get(cr, uid, fields, context=context)
        boarding_list_id = []
        boarding_obj = self.pool.get('hr.boarding.list').search(cr, uid,[], context=context)
        board_item = self.pool.get('hr.boarding.list').browse(cr, uid, boarding_obj)
        
        for item in board_item:
            print('item = ', item)
            line = (0,0, {
                        'boarding_id': item.id,
                        'department_id': item.department_id.id,
                        'note': item.note,
                    })
            boarding_list_id.append(line)
        if 'boarding_list_ids' in fields:
            res.update({'boarding_list_ids': boarding_list_id})
        return res

    def _curr_sched(self, cr, uid, ids, field_name, arg, context=None):
        Schedule    = self.pool['employee.schedule']
        sched       = self.pool.get('hr.schedule.shift.list')
        curr_sched  = sched.search(cr, uid, [('name', '=', datetime.now()),('employee_id', 'in', ids)], context=context)
        if curr_sched:
            l = sched.browse(cr, uid, curr_sched)
            schedule = [hftt(x.start_hour) + '-' + hftt(x.end_hour) for x in l.shift_id]
            return {
                employee_id : schedule[0]
                for employee_id in ids
            }
        else:
            schedule = 'None'
            return {
                employee_id: schedule
                for employee_id in ids
            }


    def _history_tf(self, cr, uid, ids, field_name, arg, context=None):
        Transfer = self.pool['hr.employee.transfer']
        return {
            employee_id: Transfer.search_count(cr, uid, [('employee_id', '=', employee_id), ('state', '=', 'transferred')], context=context)
            for employee_id in ids
        }

    def _leave_count(self, cr, uid, ids, field_name, arg, context=None):
        Holidays = self.pool['hr.holidays']
        return {
            employee_id: Holidays.search_count(cr,uid, [('employee_id', '=', employee_id), ('type', '=', 'remove')], context=context)
            for employee_id in ids
        }

    def _my_ot_list(self, cr, uid, ids, field_name, arg, context=None):
        Overtime = self.pool.get('hr.overtime.request.line')
        today_ot = Overtime.search(cr, uid, [('employee_id', 'in', ids),('date_overtime','=',datetime.now()),('state','=','approved')], context=context)
        print('today_od = ', today_ot)
        print('today_ot = ', today_ot, 'panjang = ', len(today_ot))
        if len(today_ot) == 0: 
            ot = 'None'
            return {
                employee_id: ot
                for employee_id in ids
            }
        else:
            ot = str(len(today_ot))
            return {
                employee_id: ot
                for employee_id in ids
            }
    
    def todays_shift(self, cr, uid, ids, context=None):
        selfobj = self.browse(cr, uid, ids)
        return {
            'name'      : "Today's Shift",
            'type'      : 'ir.actions.act_window',
            'view_type' : 'form',
            'view_mode' : 'calendar,tree,form',
            'res_model' : 'hr.schedule.shift.list',
            'context'   : {'search_default_employee_id': selfobj.id,
                           'search_default_today': True},
            # 'domain'    : {'employee_id': [('user_id.id','=',uid)]},
            'nodestroy' : True,
            'target'    : 'current',
        }

    def my_leave_list(self, cr, uid, ids, context=None):
        selfobj = self.browse(cr, uid, ids)
        form_view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sisb_hr','inherit_holidays_request_view')[1]
        return {
            'name'      : "Leave",
            'type'      : 'ir.actions.act_window',
            'view_type' : 'form',
            'view_mode' : 'calendar,tree,form',
            'views'     : [(False,'calendar'),(False,'tree'),(form_view,'form')],
            'res_model' : 'hr.holidays',
            'context'   : {'search_default_employee_id': selfobj.id,
                           'default_type': 'remove'},
            'domain'    : [('type','=','remove'),('employee_id','=',selfobj.id)],
            'nodestroy' : True,
            'target'    : 'current',
        }



    _columns = {
        #Contact Information Group
        'address_id'                             : fields.many2one('res.partner', 'Working Address', track_visibility="onchange"),
        'mobile_phone'                           : fields.char('Work Mobile', readonly=False, track_visibility="onchange"),
        'part_media_type_id'                     : fields.many2one('sosial.media.type', string="Messaging Apps", track_visibility="onchange"),
        'part_media_no'                          : fields.char("Messaging ID", track_visibility="onchange"),
        'work_location'                          : fields.char('Office Location', track_visibility="onchange"),
        'employee_code'                          : fields.char("Employee Code", track_visibility="onchange"),
        'supervisor_id'                          : fields.many2one("hr.employee", "Supervisor I", track_visibility="onchange", help="This User Will Approve your Leave Request in the Wait For 1st Approval State"),
        'supervisor_lvl2_id'                     : fields.many2one("hr.employee", "Supervisor II", track_visibility="onchange", help="This User Will Approve your Leave Request in the Wait For 2nd Approval State"),
        'campus_id'                              : fields.many2one("hr.campus.location", "Campus Code", track_visibility="onchange"),
        'name_on_report'                         : fields.char("Display on Report", track_visibility="onchange"),
        
        ##########################################################################################################################################
        'contract_history_ids'                   : fields.one2many('hr.contract.history', 'employee_id', string="Contract History"),
        'other_info_ids'                         : fields.one2many('hr.information.line', 'employee_id', string="Other Information"),
        'resource_id'                            : fields.many2one('resource.resource', 'Resource', ondelete='cascade', required=True, auto_join=True, track_visibility="onchange"),
        'rel_company_id'                         : fields.many2one('res.company', related="resource_id.company_id", string="Company", track_visibility="onchange"),
        'employee_position_id'                   : fields.many2one('hr.position', "Position", track_visibility="onchange"),
        # 'attendance'                             : fields.function(_state, type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Attendance'),
        # 'state'                                  : fields.related('attendance', type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Attendance'),
        'curr_schedule'                          : fields.function(_curr_sched, type="char", string="Schedule"),
        'history_transfer'                       : fields.function(_history_tf, type="integer", string="Transfer History"),
        'my_ot_list'                             : fields.function(_my_ot_list, type="char", string="My Overtime List"),
        'leave_count'                            : fields.function(_leave_count, type="integer", string="Leaves"),
        # 'last_sign'                              : fields.function(_last_sign, type='datetime', string='Last Sign'),
        # 'attendance_access'                      : fields.function(_attendance_access, string='Attendance Access', type='boolean'),
        'employ_id'                              : fields.many2one('hr.employee', string="Employee"),
        'boarding_list_ids'                      : fields.one2many('hr.boarding.list.line', 'boarding_list_id', string="Boarding List"),
        'off_boarding_list_ids'                  : fields.one2many('hr.boarding.list.line', 'off_boarding_list_id', string="Boarding List"),
        'housing_allowance'                      : fields.integer(string="Housing Allowance"),
        'car_allowance'                          : fields.integer(string="Car Allowance"),
        'airfare'                                : fields.char(string="Airfare"),
        'join_date'                              : fields.date("Date Join", track_visibility="onchange"), 
        'surname'                                : fields.char("Surname", track_visibility="onchange"),
        'allowance_type_ids'                     : fields.one2many('allowance.type.line', 'employee_id', string="Allowance"),
        'relocation_allowance'                   : fields.integer(string="Relocation Allowance"),
        'join_date'                              : fields.date('Join Date',track_visibility='onchange'),
        'country_id'                             : fields.many2one('res.country', 'Nationality',track_visibility='onchange'),
        'passport_id'                            : fields.char('Passport No',track_visibility='onchange', invisible=True),
        'bank_account_id'                        : fields.many2one('res.partner.bank', 'Bank Account Number',track_visibility='onchange', domain="[('partner_id','=',address_home_id)]", help="Employee bank salary account"),
        'address_home_id'                        : fields.many2one('res.partner', 'Home Address',track_visibility='onchange'),
        'total_emp'                              : fields.integer(string="Employee Total"),
        'emp_cur_ot_ids'                         : fields.many2many('employee.curr.overtime', string="Employee Current Overtime"),
        'employee_no'                            : fields.char(string="Employee Number", track_visibility="onchange"),
        'job_hstry_ids'                          : fields.one2many('employee.job.detail.line', 'employee_id', string="Job History"),
        'deactivate_reason'                      : fields.text(string="Deactivate Reason"),
        'birhtdate'                              : fields.date(string="Date of Birth"),
        'place_of_birth'                         : fields.char(string="Place of Birth"),
        'age'                                    : fields.integer(string="Age"),
        'salary'                                 : fields.integer(string="Salary", track_visibility='onchange'),

        #################################### Employee Leave Session ###################################
        'leave_structure_id'                     : fields.many2one('hr.holidays.structure', string="Leave Structure", track_visibility='onchange'),
        'emp_curr_leave_ids'                     : fields.one2many('hr.holidays.curr.leaves', 'employee_id', string="Leave Summary"),
        'leave_reset_month'                      : fields.selection([
                                                    (1, 'January'), 
                                                    (2, 'February'), 
                                                    (3, 'March'), 
                                                    (4, 'April'),
                                                    (5, 'May'), 
                                                    (6, 'June'), 
                                                    (7, 'July'), 
                                                    (8, 'August'),
                                                    (9, 'September'), 
                                                    (10, 'October'), 
                                                    (11, 'November'), 
                                                    (12, 'December')
                                                    ], string="Reset Month"),
        'reset_year'                             : fields.char("Reset Year"),
        'allocated_source_id'                    : fields.many2one('allocate.leaves.run', string="Allocated From", track_visibility='onchange'),
        'holiday_type_id'                        : fields.many2one('hr.holidays.type', string="Holiday Type"),
        ###############################################################################################
        'job_id'                                 : fields.many2one('hr.job', 'Position',track_visibility='onchange'),
        'department_id'                          : fields.many2one('hr.department', 'Department',track_visibility='onchange'),
        'parent_id'                              : fields.many2one('hr.employee', 'Manager',track_visibility='onchange'),
        'coach_id'                               : fields.many2one('hr.employee', 'Coach',track_visibility='onchange'),
        'supervisor'                             : fields.boolean("Is a Supervisor", track_visibility="onchange"),
        'overtime'                               : fields.boolean(string="Overtime"),

        #################################### Employee State Session ###################################
        'probation_start_date'                   : fields.date('Probation Start Date'),
        'probation_end_date'                     : fields.date('Probation End Date'),
        'contract_start_date'                    : fields.date('Contract Start Date'),
        'contract_end_date'                      : fields.date('Contract End Date'),
        ###############################################################################################


        'employee_state'                         : fields.selection(
                                                    [('new', 'New'),
                                                    ('probation', 'Probation'),
                                                    ('contract', 'Contract'),
                                                    ('permanent', 'Permanent'),
                                                    ('resign', 'Resign')], string="Employment Types", track_visibility="onchange")
        }
    _defaults = {
        'total_emp' : 1,
        'employee_no': '/',
        'employee_state': 'new',
    }

    # allocation_ids = fields.One2many('hr.holidays.allocation', 'employee_id', string="Previous Allocations")
    # active_allocation_ids = fields.One2many('hr.holidays.allocation', 'active_employee_id', string="Active Allocations")


    # def calculate_overtime(self, cr, uid, schedule, ot_obj, type, context=None):
    #     k = {}
    #     FMT = "%H:%M"
    #     ot_detail = {}
    #     minute_rounded = 0
    #     ot_length = ''
    #     singapore = pytz.timezone(schedule.default_timezone)
    #     singapore_time = datetime.now(singapore)
    #     overtime_id = self.pool.get('hr.overtime.request.line').browse(cr, uid, ot_obj)
    #     for rec in overtime_id:
    #         k['start_hour'] = rec.start_hour
    #         k['end_hour'] = rec.end_hour
    #         k['ot_type'] = rec.overtime_type_id and rec.overtime_type_id.id
    #     log_in_out = datetime.strftime(singapore_time, "%H:%M")
    #     print('log_in =', log_in_out)
    #     start_ot = '{0:02.0f}:{1:02.0f}'.format(*divmod(k['start_hour'] * 60, 60))
    #     end_ot = '{0:02.0f}:{1:02.0f}'.format(*divmod(k['end_hour'] * 60, 60))
    #     print('end_ot = ', end_ot)
    #     if type == 'sign_in':
    #         if datetime.strptime(log_in_out, FMT) <= datetime.strptime(start_ot, FMT):
    #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
    #         else:
    #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
    #     if type == 'sign_out':
    #         if datetime.strptime(log_in_out, FMT) >= datetime.strptime(end_ot, FMT):
    #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(start_ot, FMT)
    #         else:
    #             ot_length = datetime.strptime(end_ot, FMT) - datetime.strptime(log_in_out, FMT)
    #     seconds = ot_length.seconds
    #     hour_length = seconds / 3600.0
    #     if hour_length > (k['end_hour'] - k['start_hour']):
    #         hour_length = k['end_hour'] - k['start_hour']
    #     hour = seconds//3600
    #     minute = (seconds % 3600) // 60
    #     if minute <= 14:
    #         minute_rounded = 0
    #     elif 15 <= minute <= 29:
    #         minute_rounded = 15
    #     elif 30 <= minute <= 44:
    #         minute_rounded = 30
    #     elif 45 <= minute <= 59:
    #         minute_rounded = 45
    #     ot_rounded = ((hour * 3600.0) + (minute_rounded * 60.0)) / 3600.0
    #     print('type = ', k['ot_type'])
        
    #     ot_detail['start_ot']   = k['start_hour']
    #     ot_detail['end_ot']     = k['end_hour']
    #     ot_detail['ot_type']    = k['ot_type']
    #     ot_detail['ot_length']  = hour_length
    #     ot_detail['ot_rounded'] = ot_rounded
    #     return ot_detail


    # def attendance_action_change(self, cr, uid, ids, context=None):
    #     print('dasdadadad')
    #     if context is None:
    #         context = {}
    #     action_date = context.get('action_date', False)
    #     now = datetime.now()
    #     dt_now = now.strftime('%Y-%m-%d')
    #     print('dt_now =', dt_now)
    #     action = context.get('action', False)
    #     print('action = ', action)
    #     emp = self.pool.get('hr.employee')
    #     sisb_attendance = self.pool.get('hr.attendance')
    #     sched_obj = self.pool.get('employee.schedule.line')
    #     warning_sign = {'sign_in': _('Sign In'), 'sign_out': _('Sign Out')}
    #     for employee in self.browse(cr, uid, ids, context=context):
    #         schedule = self.check_schedule(cr, uid, employee)
    #         if not action:
    #             if employee.attendance == 'present': action = 'sign_out'
    #             if employee.attendance == 'absent': action = 'sign_in'
    #         if not schedule:
    #             raise osv.except_osv(_('Warning'), _('You Try to %s With no Work Schedule! \nPlease Ask HR Manager To Set Your Schedule')%(warning_sign[action],))
    #         res = self._action_check(cr, uid, employee.id, action_date, context)
    #         # if not self._action_check(cr, uid, employee.id, action_date, context):
    #         #     raise osv.except_osv(_('Warning'), _('You tried to %s with a date anterior to another event !\nTry to contact the HR Manager to correct attendances.')%(warning_sign[action],))
    #         vals = {'action': action, 'employee_id': employee.id}
    #         print('vals1 = ', vals)
    #         print('today = ', date.today())
    #         if action == 'sign_in':
    #             # ot_obj = self.pool.get('hr.overtime.request').search(cr, uid, [('state', '=', 'approved'),('employee_id','=',employee.id),('request_date', '<=', date.today())])
    #             ot_obj = self.pool.get('hr.overtime.request.line').search(cr, uid, [('date_overtime','=',dt_now), ('employee_id', '=', employee.id), ('end_hour', '=', schedule.start_hour),('state', '=', 'approved')])
    #             if ot_obj:
    #                 print('disini')
    #                 ot_obj_id = self.pool.get('hr.overtime.request.line').browse(cr, uid, ot_obj)
    #                 vals['overtime'] = True
    #                 # for ot in ot_obj_id.request_line_ids.filtered(lambda x: x.date_overtime == date.today()):
    #                 ot_detail = self.calculate_overtime(cr, uid, schedule, ot_obj, action)
    #                 vals['overtime_ids']   = [(0, 0, {
    #                                             'name': date.today(),
    #                                             'start_ot': ot_detail['start_ot'],
    #                                             'end_ot': ot_detail['end_ot'],
    #                                             'ot_length': ot_detail['ot_length'],
    #                                             'ot_rounded': ot_detail['ot_rounded'],
    #                                             'ot_type_id': ot_detail['ot_type']
    #                                             })]
    #             else: 
    #                 vals['overtime'] = False
    #             if action_date:
    #                 vals['name'] = action_date
    #             sisb_attendance.create(cr, uid, vals, context=context)
    #             print('vals = ', vals)
    #         if action == 'sign_out':
    #             last_att_obj = sisb_attendance.search(cr, uid, [('employee_id', '=', employee.id), ('action','=','sign_in')], limit=1, order="name DESC")
    #             print('last_att_obj = ', last_att_obj)
    #             last_att = sisb_attendance.browse(cr, uid, last_att_obj)

    #             ot_obj = self.pool.get('hr.overtime.request.line').search(cr, uid, [('date_overtime','=',dt_now), ('employee_id', '=', employee.id), ('start_hour', '=', schedule.end_hour), ('state', '=', 'approved')])
    #             print('ot_obj = ', ot_obj)
    #             ot = {}
    #             if ot_obj:
    #                 ot_obj_id = self.pool.get('hr.overtime.request.line').browse(cr, uid, ot_obj)
    #                 vals['overtime'] = True 
    #                 ot_detail = self.calculate_overtime(cr, uid, schedule, ot_obj, action)
    #                 ot.update({
    #                     'name': date.today(),
    #                     'start_ot': ot_detail['start_ot'],
    #                     'end_ot': ot_detail['end_ot'],
    #                     'ot_length': ot_detail['ot_length'],
    #                     'ot_rounded': ot_detail['ot_rounded'],
    #                     'ot_type_id':ot_detail['ot_type']
    #                     })
    #                 last_att.update({

    #                     'action': 'sign_out',
    #                     'overtime': True,
    #                     'sign_out': datetime.now(),
    #                     'overtime_ids': [(0, 0, ot)]
    #                 })
    #             else:
    #                 last_att.update({
    #                     'action': 'sign_out',
    #                     'sign_out': datetime.now(),
    #                     # 'overtime_ids': [(0, 0, ot)]
    #                 })
            
    #         # if action_date:
    #         #     vals['name'] = action_date
    #         # print('vals = ', vals)
    #         # sisb_attendance.create(cr, uid, vals, context=context)
    #         print('vals2 = ', vals)
    #     return True
    

    def birthdate_onchange(self, cursor, user, ids, birthdate, context=None):   
        res={}                                                                       
        if birthdate:                                                           
            birthdate = datetime.strptime(birthdate, "%Y-%m-%d")    
            today = datetime.now()                                    
            age_cal = relativedelta(today,birthdate)                            
            age= int(age_cal.years)                                            
            res = {'age': age}                                             
        return {'value': res} 


    def get_emp(self, cr, uid, ids, context=None):
        res = {}
        for emp in self.browse(cr, uid, ids, context=context):
            id = emp.id
            state = emp.attendance
            res.update({'id':id, 'attendance': state})
        return res

    def set_schedule(self, cr, uid, ids, context=None):
        warning_sign = {'sign_in': _('Sign In'), 'sign_out': _('Sign Out')}
        schedule = ''
        action = ''
        for employee in self.browse(cr, uid, ids, context=context):
            schedule = self.check_schedule(cr, uid, employee)
            if employee.attendance == 'present': 
                action = 'sign_out'
            if employee.attendance == 'absent': 
                action = 'sign_in'
            if not schedule:
                raise osv.except_osv(_('Warning'), _('You Try to %s With no Work Schedule! \nPlease Ask HR Manager To Set Your Schedule')%(warning_sign[action],))
    

    def check_schedule(self, cr, uid, employee_id, context=None):
        now = datetime.now()
        dt_now = now.strftime('%Y-%m-%d')
        sched_obj = self.pool.get('employee.schedule.line').search(cr, uid, [('date', '=', dt_now), ('employee_id', '=', employee_id.id)], limit=1)
        sched_id = self.pool.get('employee.schedule.line').browse(cr, uid, sched_obj)
        if not sched_id:
            return False
        else:
            return sched_id


    def holidays_error(self, cr, uid, ids, context=None):
        warning_sign = {'sign_in': _('Sign In'), 'sign_out': _('Sign Out')}
        sisb_emp = self.pool.get('hr.employee')
        employee_id = _employee_get(self, cr, uid, context=None)
        sisb_tmp_obj = sisb_emp.search(cr, uid, [('user_id', '=', employee_id)], context=context)
        emp_obj = sisb_emp.browse(cr, uid, sisb_tmp_obj, context=context)
        action = ''
        for employee in emp_obj:
            if employee.attendance == 'present': 
                action = 'sign_out'
            if employee.attendance == 'absent': 
                action = 'sign_in'
        raise osv.except_osv(_('Warning'), _('You Can not %s During Your Holiday')%(warning_sign[action],))

    def overtime_error(self, cr, uid, ids, context=None):
        sisb_emp = self.pool.get('hr.employee')
        employee_id = _employee_get(self, cr, uid, context=None)
        sisb_tmp_obj = sisb_emp.search(cr, uid, [('user_id', '=', employee_id)], context=context)
        emp_obj = sisb_emp.browse(cr, uid, sisb_tmp_obj, context=context)
        raise osv.except_osv(_('Warning'), _('You are not eligible for Overtime Please Ask Your HR or Head Department to Set your Overtime'))

    def set_boarding_lit(self, cr, uid, ids, context=None):
        boarding_list_obj = self.pool.get('hr.boarding.list').search(cr, uid, [], context=context) 
        board_item = self.pool.get('hr.boarding.list').browse(cr, uid, boarding_list_obj, context=context)
        boarding_list_ids = []
        for item in board_item:
            line = (0,0, {
                        'boarding_id': item.id,
                        'department_id': item.department_id.id,
                        'note': item.note,
                        'date_is_received': False
                    })
            boarding_list_ids.append(line) 
        emp_obj = self.pool.get('hr.employee').search(cr, uid, [], context=context)
        selfobj = self.browse(cr, uid, ids)
        print('selfobj =', selfobj)
        # employees = self.pool.get('hr.employee').browse(cr, uid, emp_obj, context=context)
        for emp in selfobj:
            emp.boarding_list_ids = [(5, 0, 0)]
            emp.update({'boarding_list_ids': boarding_list_ids})


    
    def cron_send_celebrate_one_year_email_emp(self, cr, uid, context=None):
        employee_obj = self.pool.get('hr.employee')
        employees = self.pool.get('hr.employee').search(cr, uid, [], context=context)
        for employee in employee_obj.browse(cr, uid, employees,context):
            if employee.join_date:
                employee_join_date = datetime.strptime(employee.join_date, "%Y-%m-%d").date()
                one_year_employee = employee_join_date + relativedelta(years=1)
                one_year = str(one_year_employee)
                if employee.join_date == one_year:
                    if employee.work_email:
                        mail_subject = "Celebrate 1 Year"
                        body = """
                        <div style="background-color:#FFF;">
                            Dear """+employee.name+""",<br/><br/>
        
                            Congratulation For Your 1 Year In SISB<br/>
                            """+employee.name+"""<br/><br/>
        
                            Would be grateful if you could check this out on your end.<br/><br/>
        
                            Thank You
                        </div>
                        """
                        val = {
                            'email_to': employee.work_email,
                            'body_html': body,
                            'subject': mail_subject,
                            'auto_delete': False
                        }
                        mail_send = self.pool.get('mail.mail').create(cr, uid, val, context)
                        mail = self.pool.get('mail.mail').browse(cr, uid, mail_send, context)
                        print ('mail = ', mail)
                        mail.send()


    def days_between(self, cr, uid, d1, d2, context=None):
        d1 = datetime.strptime(d1, "%Y-%m-%d")
        d2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((d2 - d1).days)


    def cron_send_email_birthday_reminder(self, cr, uid, context=None):
        all_emp = self.pool.get('hr.employee').search(cr, uid, [], context=context)
        all_employee = self.pool.get('hr.employee').browse(cr, uid, all_emp, context=context)
        now = datetime.now()
        b_day1 = now.strftime('%m-%d')
        for employee in all_employee:
            if employee.birthday:
                emp_bday= datetime.strptime(employee.birthday, "%Y-%m-%d")
                b_day = emp_bday.strftime('%m-%d')
                if b_day1 == b_day:
                    template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'sisb_hr_birthday_reminder_email')
                    if template:
                        mail_id = template.send_mail(employee.id)
                        mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
                        if mail:
                            return mail.send()
                    


    def cron_send_notification_for_exp_doc(self, cr, uid, context=None):
        print('context = ', context)
        FMT = '%Y-%m-%d'
        all_employee = self.pool.get('hr.employee').browse(cr, uid, self.pool.get('hr.employee').search(cr, uid, []))
        today = datetime.now()
        print('today = ', today)
        # today_str = datetime.strftime(today, FMT)
        ctx = {}
        today_str = today.strftime(FMT)
        print('today_str = ', today_str)
        for employee in all_employee:
            if employee.other_info_ids:
                print('employee name = ', employee.name)
                for identity in employee.other_info_ids:
                    day_to_notif = identity.name.exp_notif
                    print('day_to_notif = ', day_to_notif)
                    exp_date = identity.exp_date
                    print('exp_date = ', exp_date)
                    exp_date_obj = datetime.strptime(exp_date, FMT)
                    diff = self.days_between(cr, uid, d1=today_str, d2=exp_date, context=context)
                    print('diff = ', diff, 'type = ', type(diff))
                    if diff <= day_to_notif:
                        ctx.update({
                            'identity_type': identity.name.name,
                            'day_left': diff
                        })
                        template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'identity_type_expired_notification', context=ctx)
                        print('template = ', template)
                        print('context = ', context)
                        if template:
                            mail_id = template.send_mail(employee.id)
                            print('mail_id = ', mail_id)
                            mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
                            print('mail = ', mail)
                            if mail:
                                mail.send()
            elif not employee.other_info_ids:
                print('employee name1 = ', employee.name)
        return True




        # emp_id = _employee_get(self, cr, uid, context=None)
        # emp_obj = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',emp_id)], context=context)
        # all_emp = self.pool.get('hr.employee').search(cr, uid, [], context=context)
        # employee = self.pool.get('hr.employee').browse(cr, uid, emp_obj, context=context)
        # all_employee = self.pool.get('hr.employee').browse(cr, uid, all_emp, context=context)
        # year = str(datetime.now().year)
        # month = str(datetime.now().month)
        # day = str(datetime.now().day)
        # today = year+'-'+month+'-'+day
        # mail_subject = ''
        # exp_doc = ''
        # for employee in all_employee:
        #     if employee.passport_no and employee.passport_no_exp_date:
        #         diff = self.days_between(cr, uid, d1=today, d2=employee.passport_no_exp_date, context=context)
        #         print('diff = ', diff)
        #         if diff <= 45:
        #             template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'passport_expired_notification')
        #             if template:
        #                 mail_id = template.send_mail(employee.id)
        #                 print('mail_id = ', mail_id)
        #                 mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
        #                 print('mail = ', mail)
        #                 if mail:
        #                     mail.send()
        #     elif employee.visa and employee.visa_exp_date:
        #         diff = self.days_between(cr, uid, d1=today, d2=employee.visa_exp_date, context=context)
        #         if diff <= 45:
        #             template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'visa_expired_notification')
        #             if template:
        #                 mail_id = template.send_mail(employee.id)
        #                 print('mail_id = ', mail_id)
        #                 mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
        #                 print('mail = ', mail)
        #                 if mail:
        #                     mail.send()
        #     elif employee.teaching_license and employee.teaching_license_exp_date:
        #         diff = self.days_between(cr, uid, d1=today, d2=employee.teaching_license_exp_date, context=context)
        #         if diff <= 45:
        #             template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'teaching_license_expired_notification')
        #             if template:
        #                 mail_id = template.send_mail(employee.id)
        #                 print('mail_id = ', mail_id)
        #                 mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
        #                 print('mail = ', mail)
        #                 if mail:
        #                     mail.send() 
        #     elif employee.work_permit and employee.work_permit_exp_date:
        #         diff = self.days_between(cr, uid, d1=today, d2=employee.work_permit_exp_date, context=context)
        #         if diff <= 45:
        #             template = self.pool.get('ir.model.data').get_object(cr, uid, 'sisb_hr', 'work_permit_expired_notification')
        #             if template:
        #                 mail_id = template.send_mail(employee.id)
        #                 print('mail_id = ', mail_id)
        #                 mail = self.pool.get('mail.mail').browse(cr, uid, mail_id)
        #                 print('mail = ', mail)
        #                 if mail:
        #                     mail.send() 

    def wiz_req_on_board_item(self, cr, uid, ids, context=None):
        selfobj = self.browse(cr, uid, ids)
        all_item = []
        for rec in selfobj:
            for l in rec.boarding_list_ids:
                if not l.is_received:
                    all_item.append(l.id)
        print('all_item = ', all_item)
        return {
                'name'      : _('Request ON Boarding'),
                'type'      : 'ir.actions.act_window',
                'res_model' : 'req.onboard.wiz',
                'view_type' : 'form',
                'view_mode' : 'form',
                'nodestroy' : True,
                # 'context'   : {'default_employee_id': selfobj.id,
                #                'default_prev_shift_id': selfobj.working_time_id},
                # 'context'   : {'default_on_boarding_list_ids': [(4, i, 0) for i in all_item],
                #                 'default_employee_id': selfobj.id},
                'target'    : 'new',
            } 
       


            
    def get_day_left(self, cr, uid, employee, type, context=None):
        print('type = ', type)
        year = str(datetime.now().year)
        month = str(datetime.now().month)
        day = str(datetime.now().day)
        today = year+'-'+month+'-'+day
        diff = ''
        for rec in employee:
            if type == 'passport':
                diff = self.days_between(cr, uid, d1=today, d2=rec.passport_no_exp_date, context=context)
            if type == 'visa':
                diff = self.days_between(cr, uid, d1=today, d2=rec.visa_exp_date, context=context)
            if type == 'teaching':
                diff = self.days_between(cr, uid, d1=today, d2=rec.teaching_license_exp_date, context=context)
            if type == 'permit':
                diff = self.days_between(cr, uid, d1=today, d2=rec.work_permit_exp_date, context=context)

        return int(diff)


    def add_pro_rata_leave(self, cr, uid, emp, context=None):
        now = datetime.now()
        leave_run = self.pool.get('allocate.leaves.employee')
        allocate_leaves = self.pool.get('allocate.leaves.employee')
        curr_leave_obj = self.pool.get('hr.holidays.curr.leaves')
        current_leaves = []
        for rec in emp:
            if rec.leave_structure_id:
                contract_leave = self.pool.get('hr.holidays.structure').search(cr, uid, [('employee_type', '=', 'contract'), ('company_id', '=', rec.company_id.id)])
                print('contract_leave = ', contract_leave)
                if not contract_leave:
                    raise ValidationError(_("Please Set Structure Leave For %s before you set this employee to contract")%(rec.company_id.name))
                    # raise ValidationError(_("Your Leave balance For %s is %.2f.\n Your Request %.2f. Please Change Accordingly ")%(rec.holiday_status_id.name, leave.current_leave, rec.number_of_days))
                contract_now = datetime.strptime(rec.contract_start_date, "%Y-%m-%d")
                reset_leave_month = int(rec.department_id.leave_month_reset)
                rec.leave_structure_id = contract_leave[0]
                leave_structure_id = self.pool.get('hr.holidays.structure').browse(cr, uid, contract_leave)
                month_diff = (contract_now.year - (int(rec.reset_year) - 1)) * 12 + (contract_now.month - reset_leave_month)
                print('month_diff = ', month_diff)
                curr_leave_amt = 0
                for curr_leave in rec.emp_curr_leave_ids:
                    cr.execute('DELETE FROM hr_holidays_curr_leaves WHERE id=%s', (curr_leave.id,))
                    curr_leave_amt += 1
                allocated_hd = self.pool.get('hr.holidays').search(cr, uid, [('employee_id', '=', rec.id),('allocation_run_id', '=', rec.allocated_source_id.id)], order='id desc', limit=4)
                print('allocated_hd = ', allocated_hd)
                for hd in allocated_hd:
                    cr.execute('DELETE FROM hr_holidays WHERE id = %s',(hd, ))
                current_structure = self.pool.get('hr.holidays.structure').browse(cr, uid, contract_leave)
                for lv in current_structure.holiday_type_ids:
                    # if lv.employee_type == 'female_staff' and rec.gender != 'female':
                    #     continue
                    cr.execute('INSERT INTO hr_holidays (name, number_of_days, holiday_status_id, state, employee_id, type, holiday_type, date_to1, date_from1, date_allocate, approved_by, approved_date) VALUES \
                                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id \
                                ',('Automaticly Assign For new Contract Employee', lv.amount_to_allow, lv.leave_type.id, 'draft', rec.id, 'allocated', 'employee', datetime.now().date(), datetime.now().date(), datetime.now().date(), uid, datetime.now().date()))
                    lv_id = cr.fetchall()
                    print('lv_id = ', lv_id)
                    for line in rec.allocated_source_id:
                        line.allocation_line_ids = [(4, lv) for lv in lv_id[0]]
                        generated_hd = self.pool.get('hr.holidays').browse(cr, uid, lv_id[0])
                        for r in generated_hd:
                            r.button_approve(rec.allocated_source_id)
                # rec.allocated_source_id.button_confirm()
        return True
            






            # for curr_leave in rec.emp_curr_leave_ids:
            #     if curr_leave.leave_type_id.id not in current_leaves:
            #         current_leaves.append(curr_leave.leave_type_id.id)
            # for leaves in leave_structure_id.holiday_type_ids:
            #     if leaves.leave_type.employee_type == 'female_staff':
            #             if rec.gender != 'female':
            #                 continue
            #     if leaves.leave_type.id in current_leaves:
            #         for lv in rec.emp_curr_leave_ids.filtered(lambda x: x.leave_type_id == leaves.leave_type):
            #             lv.total_curr_leave += (leaves.amount_to_allow * (12 - month_diff))/12
            #             lv.current_leave += (leaves.amount_to_allow * (12 - month_diff))/12
            #     if leaves.leave_type.id not in current_leaves:
            #         leave_to_add = curr_leave_obj.create(cr, uid ,{
            #             'leave_type_id': leaves.leave_type.id,
            #             'total_curr_leave': (leaves.amount_to_allow * (12 - month_diff))/12,
            #             'total_taken_leave': 0.00,
            #             'current_leave': (leaves.amount_to_allow * (12 - month_diff))/12,
            #             'employee_id': rec.id,
            #             'state': 'validate'
            #         }, context=context)
            #         rec.emp_curr_leave_ids = [(4,leave_to_add)]
                    
                # for leaves in leave_structure_id.holiday_type_ids.filtered(lambda x: x.leave_type == curr_leave.leave_type_id):
                #     if leaves.leave_type.employee_type == 'female_staff':
                #         if rec.gender != 'female':
                #             continue
                #     # if curr_leave.leave_type_id == leaves.leave_type:
                #     curr_leave.total_curr_leave += (leaves.amount_to_allow * month_diff)/12
                # for leaves in leave_structure_id.holiday_type_ids.filtered(lambda x: x.leave_type != curr_leave.leave_type_id):
                #     # elif curr_leave.leave_type_id != leaves.leave_type:
                #     if leaves.leave_type.employee_type == 'female_staff':
                #         if rec.gender != 'female':
                #             continue
                #     leave_to_add = curr_leave_obj.create(cr, uid ,{
                #         'leave_type_id': leaves.leave_type.id,
                #         'total_curr_leave': (leaves.amount_to_allow * month_diff)/12,
                #         'total_taken_leave': 0.00,
                #         'current_leave': (leaves.amount_to_allow * month_diff)/12,
                #         'employee_id': rec.id,
                #         'state': 'validate'
                #     }, context=context)
                #     rec.emp_curr_leave_ids = [(4,leave_to_add)]

    
    def delta_days(self, cr, uid, date_from, date_to, context=None):
        FMT = '%Y-%m-%d'
        start   = datetime.strptime(date_from, '%Y-%m-%d')
        end     = datetime.strptime(date_to, '%Y-%m-%d')   
        step    = timedelta(days=1)
        date_list   = []
        weekend     = []
        all_day     = []
        value = {}
        while (start <= end):
            string_date = start.strftime('%Y-%m-%d')
            all_day.append(string_date)
            day = calendar.weekday(int(start.strftime("%Y")),int(start.strftime("%m")),int(start.strftime("%d")))
            if day == 5 or day == 6:
                str_date = start.strftime('%Y-%m-%d')
                weekend.append(str_date)
            else:
                str_date = start.strftime('%Y-%m-%d')
                date_list.append(str_date)
            start += step
        value['date_list'] = date_list
        value['weekend'] = weekend
        value['all_day'] = all_day
        return value
    
    def check_leave_day(self, cr, uid, employee_id, date, context=None):
        holiday = False
        if employee_id:
            hd = self.pool.get('hr.holidays').search(cr, uid, [
                ('employee_id', '=', employee_id),
                ('date_from1','<=', date),
                ('date_to1', '>=', date),
                ('type', 'in', ('remove', 'claim')),
                ('state', '=', 'validate')
            ])
            if hd:
                holiday = True
            else:
                holiday = False
            return holiday

    def check_emp_holiday(self, cr, uid, employee_id, day, context=None):
        now = date.today()
        dt_now = now.strftime('%Y-%m-%d')
        check = False
        department_id = False
        if employee_id:
            department_id = employee_id.department_id
        if department_id:
            if department_id.public_holiday_type == 'public':
                holiday_obj = self.pool.get('public.holidays.days').search(cr, uid, [])
                holiday = self.pool.get('public.holidays.days').browse(cr, uid, holiday_obj)
                for hd in holiday:
                    if hd.name == day:
                        check = True
                    else:
                        check = False
            if department_id.public_holiday_type == 'school':
                academic_years_obj = self.pool.get('academic.year').search(cr, uid, [('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.pool.get('school.holidays').search(cr, uid, [('year_id','=', academic_years_obj[0])])
                if school_holiday:
                    school_holiday_id = self.pool.get('school.holidays').browse(cr, uid, school_holiday[0])
                    for rec in school_holiday_id.line_ids:
                        if rec.date == day:
                            check = True
                        else: 
                            check = False
                else:
                    check =  False
            if department_id.public_holiday_type == 'both':
                holiday_obj = self.pool.get('public.holidays.days').search(cr, uid, [])
                holiday = self.pool.get('public.holidays.days').browse(cr, uid, holiday_obj)
                for hd in holiday:
                    if hd.name == day:
                        check = True
                    else:
                        check = False
                academic_years_obj = self.pool.get('academic.year').search(cr, uid, [('date_start', '<=', dt_now),('date_stop', '>=', dt_now)])
                school_holiday = self.pool.get('school.holidays').search(cr, uid, [('year_id','=', academic_years_obj[0])])
                if school_holiday:
                    school_holiday_id = self.pool.get('school.holidays').browse(cr, uid, school_holiday[0])
                    for rec in school_holiday_id.line_ids:
                        if rec.date == day:
                            check = True
                else:
                    if check:
                        return check
                    else:
                        check = False

            if not department_id:
                check = False
        return check


    def print_probation_completion_report(self, cr, uid, ids, context=None):
        # if context is None:
        #     context = {}
        # print('context = ', context)
        # data = {}
        # print('data = ', data)
        # datas = {
        #     'ids': context.get('active_ids', []),
        #     'model': 'hr.employee',
        #     'form': data
        # }
        # datas['form']['ids'] = datas['ids']
        # return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.sisb_probation_completion_report', data=datas, context=context)
        if context is None:
            context = {}
        print('context = ', context)
        data = {}
        print('data = ', data)
        datas = {
            'ids': ids,
            'model': 'hr.employee',
            'form': data
        }
        print('ids = ', ids)
        datas['form']['ids'] = datas['ids']
        pdf, format = self.pool['report'].get_pdf(cr, uid, ids, 'sisb_hr.sisb_probation_completion_report', data=datas, context=context), 'pdf'
        pdf_file = base64.encodestring(pdf)
        filename = "Probation Completion Report.pdf"
        probation_completion_letter_wizard = self.pool.get('probation.completion.letter').create(cr, uid, {'name': filename, 'file': pdf_file}, context=context)
        print('probation_completion_letter_wizard =', probation_completion_letter_wizard)
        return {
            'name': _('Probation Completion Report'),
            'res_id' : probation_completion_letter_wizard,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'probation.completion.letter',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            }



    def print_on_boarding_list(self, cr, uid, ids, context=None):
        print('ids = ', ids)

        if context is None:
            context = {}
        print('context = ', context)
        data = {}
        print('data = ', data)
        datas = {
            'ids': ids,
            'model': 'hr.employee',
            'form': data
        }
        datas['form']['ids'] = datas['ids']
        print('datas = ', datas)
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.generate_on_board_item', data=datas, context=context)


    def print_probation_appraisals_performance_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        print('context = ', context)
        data = {}
        print('data = ', data)
        datas = {
            'ids': context.get('active_ids', []),
            'model': 'hr.employee',
            'form': data
        }
        datas['form']['ids'] = datas['ids']
        return self.pool['report'].get_action(cr, uid, [], 'sisb_hr.sisb_probation_appraisals_report', data=datas, context=context)
           

    # def test_function(self,cr, uid, ids, context=None):
    #     emp = self.browse(cr, uid, ids)
    #     max_date = max(d.exp_date for d in emp.other_info_ids)
    #     all_data = len(emp.other_info_ids)
    #     contract_history = self.pool.get('hr.contract.history')
    #     all_data = all_data + 13
    #     if not (emp.contract_start_date and emp.contract_end_date) or (emp.contract_end_date and (not emp.contract_end_date)) or ((not emp.contract_start_date) and emp.contract_end_date):
    #         raise ValidationError(_("Contract Start Date and Contract End date must be filled"))
    #     if emp.contract_start_date < last_date_contract:
    #         raise ValidationError(_("Your new Contract start date for this Employee must greater than the Last Contract End Date %s")%(last_date_contract, ))
    #     if emp.contract_start_date > last_date_contract:
    #         if emp.contract_start_date < emp.contract_end_date:
    #             raise ValidationError(_("Contract Start date must greater than Contract End Date"))
    #         else:
    #             vals = {
    #                     'name': emp.name + "'s 1st Contract",
    #                     'start_date': emp.contract_start_date,
    #                     'end_date': emp.contract_end_date,
    #                     'employee_id': emp.id,
    #                 }
    #             new_contract = contract_history.create(cr, uid, vals, context=context)
    #             emp.contract_history_ids = [(4, new_contract, 0)]
    #     print('max_date = ', max_date)
    #     print('ordinal = ', ordinal(all_data))
    #     print('all_date = ', all_data)
             
    def set_probation(self, cr, uid, ids, context=None):
        emp = self.browse(cr, uid, ids)
        if not emp.probation_start_date or not emp.probation_end_date or (emp.probation_start_date >= emp.probation_end_date):
                raise ValidationError(_("Set The Probation Start Date and Probation End Date First and make sure Start date is greater than End Date"))
        else:
            return emp.write({'employee_state': 'probation'})

    def set_contract(self, cr, uid, ids, context=None):
        emp = self.browse(cr, uid, ids)
        contract_history = self.pool.get('hr.contract.history')
        if not emp.contract_start_date or not emp.contract_end_date or (emp.contract_start_date >= emp.contract_end_date):
            raise ValidationError(_("Set The Contract Start Date and Contract End Date First and make sure Start date is greater than End Date"))
        elif emp.contract_start_date < emp.probation_end_date:
            raise ValidationError(_("Contract Start Date must be greater than Probation End Date"))
        else:
            self.add_pro_rata_leave(cr, uid, emp, context=context)
            vals = {
                'name': emp.name + "'s 1st Contract",
                'start_date': emp.contract_start_date,
                'end_date': emp.contract_end_date,
                'employee_id': emp.id,
            }
            new_contract = contract_history.create(cr, uid, vals, context=context)
            emp.contract_history_ids = [(4, new_contract, 0)]
            return emp.write({'employee_state': 'contract'})

    def update_contract(self, cr, uid, ids, context=None):
        contract_history = self.pool.get('hr.contract.history')
        emp = self.browse(cr, uid, ids)
        print('emp = ', emp)
        last_date_contract = max(d.end_date for d in emp.contract_history_ids)
        contract_data = len(emp.contract_history_ids)
        
        if not (emp.contract_start_date and emp.contract_end_date) or (emp.contract_end_date and (not emp.contract_end_date)) or ((not emp.contract_start_date) and emp.contract_end_date):
            raise ValidationError(_("Contract Start Date and Contract End date must be filled"))
        if emp.contract_start_date < last_date_contract:
            raise ValidationError(_("Your new Contract start date for this Employee must greater than the Last Contract End Date %s")%(last_date_contract, ))
        if emp.contract_start_date >= last_date_contract:
            print('sdas')
            if emp.contract_start_date > emp.contract_end_date:
                raise ValidationError(_("Contract End date must greater than Contract Start Date"))
            else:
                name = emp.name
                contract = contract_data + 1
                contract = ordinal(contract)
                start_date = emp.contract_start_date
                end_date = emp.contract_end_date
                vals = {
                    'name': name + "'s " + contract + ' Contract',
                    'start_date': start_date,
                    'end_date': end_date,
                    'employee_id': emp.id
                }
                new_contract = contract_history.create(cr, uid, vals, context=context)
                print('new_contract = ', new_contract)
                emp.contract_history_ids = [(4, new_contract, 0)]

        return True

    # def create_contract_history(self, cr, uid, vals, context=None):
    #     contract_history = self.pool.get('hr.contract.history')
    #     emp = self.browse(cr, uid, ids)
    #     print('emp = ', emp)
    #     cr.execute("INSERT INTO hr_contract_ids name, start_date, end_date, employee_id VALUES \
    #         (%s, %s, %s, %s) RETURNING id\
    #         ",(vals['name'], vals['start_date'], vals['end_date'],vals['employee_id'], ))
    #     new_contract_id = cr.fetchall()
    #     print('new_contract_id = ', new_contract_id)
    #     return emp.write(cr, uid, {'contract_history_ids': [(4, id, 0) for id in new_contract_id]}, context=context)


    def permanent_employee(self, cr, uid, ids, context=None):  
        emp = self.browse(cr, uid, ids)
        # if emp.employee_state == 'new':
        #     if not emp.probation_start_date or not emp.probation_end_date or (emp.probation_start_date >= emp.probation_end_date):
        #         raise ValidationError(_("Set The Probation Start Date and Probation End Date First and make sure Start date is greater than End Date"))
        #     else:
        #         return emp.write({'employee_state': 'probation'})
        # if emp.employee_state == 'probation':
        #     if not emp.contract_start_date or not emp.contract_end_date or (emp.contract_start_date >= emp.contract_end_date):
        #         raise ValidationError(_("Set The Contract Start Date and Contract End Date First and make sure Start date is greater than End Date"))
        #     else:
        #         self.add_pro_rata_leave(cr, uid, emp, context=context)
        #         return emp.write({'employee_state': 'contract'})
        # if emp.employee_state == 'contract':
        return emp.write({'employee_state': 'permanent'})

        # print('emp = ', emp)
        # for rec in emp:
        #     print('rec = ', rec)
        #     if rec.employee_state == '2nd_contract':
        #         return rec.write({'employee_state': 'permanent'})
        #     else:
        #         return {
        #                 'name'      : _('Set Employee Stage'),
        #                 'type'      : 'ir.actions.act_window',
        #                 'res_model' : 'set.emp.state.wiz',
        #                 # 'view_id'   : view_id,
        #                 # 'res_id'    : late_wizard,
        #                 'view_type' : 'form',
        #                 'view_mode' : 'form',
        #                 'nodestroy' : True,
        #                 'context'   : {'default_emp_id': emp.id,
        #                                'default_employee_state': emp.employee_state},
        #                 'target'    : 'new',
#         #             }  


# class inherit_hr_timesheet_sheet(osv.osv):
#     _inherit = 'hr_timesheet_sheet.sheet'

#     _columns = {
#     'state_attendance' : fields.related('employee_id', 'attendance', type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Current Status', readonly=True),
#     }


class probation_completion_letter(osv.osv):
    _name = "probation.completion.letter"
    _inherit = 'mail.thread'


    _columns = {
    'name': fields.char(string="File Name", track_visibility='onchange'),
    'file': fields.binary(string="Probation Completion Letter", readonly=True, track_visibility='onchange')
    }

    def send_to_employee(self, cr, uid, ids, context=None):
        context = context
        selfobj = self.browse(cr, uid, ids)
        # print('test = ', test)
        print('context = ', context)
        compose_form = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        attachment_obj = self.pool.get('ir.attachment')
        attachment_id = ''
        for rec in self.browse(cr, uid, ids):
            attachment_data = {
                'name': 'Probation Completion Report',
                'datas_fname': rec.name,
                'datas': rec.file,
            }
            attachment_id = attachment_obj.create(cr, uid, attachment_data, context=context)
            print('attachment_id = ', attachment_id)
            attachment = attachment_obj.browse(cr, uid, attachment_id)
        cr.execute("SELECT rp.id FROM res_partner rp, res_users ru LEFT JOIN hr_employee he ON (he.user_id=ru.id) WHERE rp.id = ru.partner_id AND he.id=%s",(context.get('active_id'), ))
        partner_id = cr.fetchall()
        print('partner_id = ', partner_id)
        print('partner_id2 = ', partner_id[0])
        partner_ids = [pid for pid in partner_id[0]]
        ctx = {}
        ctx.update({
            'default_model': 'probation.completion.letter',
            'default_res_id': selfobj.id,
            'default_partner_ids': partner_ids,
            'default_recipient_ids': [partner_ids],
            'default_attachment_ids': [(6, 0, [attachment_id])],
            'mail_log_sender_id': uid,
            'mail_log_res_id': selfobj.id,
            'mail_log_model': 'probation.completion.letter',
            'default_composition_mode': 'comment',
            'mail_force_notify': True,
            'from_render_report': True,
            'mail_auto_delete': False,
        })
        print('ctx = ', ctx)
        return {
            'name': ('Send Probation Completion Report'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form, 'form')],
            'view_id': compose_form,
            'target': 'new',
            'context': ctx,
        }

# probation_completion_letter()

class reference_letter(osv.osv):
    _name = "reference.letter"
    _inherit = 'mail.thread'


    _columns = {
    'name': fields.char(string="File Name"),
    'file': fields.binary(string="Reference Letter", readonly=True)
    }

    def send_to_employee(self, cr, uid, ids, context=None):
        context = context
        selfobj = self.browse(cr, uid, ids)
        print('context = ', context)
        compose_form = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        print('compose_form = ', compose_form)
        attachment_obj = self.pool.get('ir.attachment')
        attachment_id = ''
        for rec in self.browse(cr, uid, ids):
            attachment_data = {
                'name': 'Employee Reference Report',
                'datas_fname': rec.name,
                'datas': rec.file,
            }
            attachment_id = attachment_obj.create(cr, uid, attachment_data, context=context)
            print('attachment_id = ', attachment_id)
            attachment = attachment_obj.browse(cr, uid, attachment_id)
        cr.execute("SELECT rp.id FROM res_partner rp, res_users ru LEFT JOIN hr_employee he ON (he.user_id=ru.id) WHERE rp.id = ru.partner_id AND he.id=%s",(context.get('active_id'), ))
        partner_id = cr.fetchall()
        print('partner_id = ', partner_id)
        print('partner_id2 = ', partner_id[0])
        partner_ids = [pid for pid in partner_id[0]]
        ctx = {}
        ctx.update({
            'default_model': 'reference.letter',
            'default_res_id': selfobj.id,
            'default_partner_ids': partner_ids,
            'default_recipient_ids': [partner_ids],
            'default_attachment_ids': [(6, 0, [attachment_id])],
            'mail_log_sender_id': uid,
            'mail_log_res_id': selfobj.id,
            'mail_log_model': 'reference.letter',
            'default_composition_model': 'comment',
            'mail_force_notify': True,
            'from_render_report': True,
            'mail_auto_delete': False,
        })
        print('ctx = ', ctx)
        return {
            'name': _('Send Employee Reference Letter'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form, 'form')],
            'view_id': compose_form,
            'target': 'new',
            'context': ctx,
            
        }