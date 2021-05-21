# -*- coding: utf-8 -*-
import time
import math
from openerp import tools
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class employee_attendance_report_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(employee_attendance_report_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'attend_emp_print': self._attend_emp_print,
        })
    
    def _attend_emp_print(self, form):
        attend_obj = self.pool.get('hr.attendance') 
        data = []
        result = {}
        attend_ids = attend_obj.search(self.cr, self.uid,
        [('name','>=',form['start_date'] + ' 00:00:00'),
        ('name','<=',form['end_date'] + ' 23:59:59'),
        ('employee_id','in',form['employee_s']),
        ('action','=','sign_in')],
        order='name ASC')
        
       
        attend = attend_obj.browse(self.cr, self.uid, attend_ids, context=self.localcontext)
        
        for att in attend:
            sign_out_time = ''
            so_reason = ''
#            workhour_ids = ''
            workhour_float = ''
            workhour_ids_result = ''
            is_holiday = False;
            attend_ids2 = attend_obj.search(self.cr, self.uid, 
            [('name','>',att.name),('employee_id','=',att.employee_id.id),('action','=','sign_out')])
            attend2 = attend_obj.browse(self.cr, self.uid, attend_ids2, context=self.localcontext)
            for atte in attend2:
                sign_out_time = atte.name
                so_reason = atte.reason
                 # Compute interval duration between sign-in and sign-out time.
                signin_time = datetime.strptime(att.name, '%Y-%m-%d %H:%M:%S')
                signout_time = datetime.strptime(atte.name, '%Y-%m-%d %H:%M:%S')
                tz_signin_date = datetime.strptime(attend_obj.get_local_time(self.cr, self.uid,self.ids, options={'date':str(signin_time), 'datetime_format':'%Y-%m-%d %H:%M:%S'}, context=self.localcontext),'%Y-%m-%d %H:%M:%S')
                tz_signout_date = datetime.strptime(attend_obj.get_local_time(self.cr, self.uid,self.ids, options={'date':str(signout_time), 'datetime_format':'%Y-%m-%d %H:%M:%S'}, context=self.localcontext),'%Y-%m-%d %H:%M:%S')
#                print 'tz_signin_date',tz_signin_date
#                print 'tz_signout_date',tz_signout_date
                holidays_ids = self.pool.get('hr.holidays').search(self.cr, self.uid,
                    [('date_to','>=',str(tz_signin_date.date()) + ' 00:00:00'),
                    ('employee_id','in',form['employee_s']),
                    ('type','=','remove'),
                    # ('request_type','!=','allocation'),
                    ('state','=','validate'),
                    ],
                    order='date_from ASC')
                
                if len(holidays_ids) != 0:
                    holiday = self.pool.get('hr.holidays').browse(self.cr, self.uid, holidays_ids, context=self.localcontext)
                    end_date = 17
                    for item in holiday:
                        hol_date_to = datetime.strptime(str(item.date_to), '%Y-%m-%d %H:%M:%S')
                        if hol_date_to.date() == tz_signin_date.date():
                            is_holiday = True
                        else:
                            diff_day = self.pool.get('hr.holidays')._get_number_of_days(item.date_from,item.date_to)
                            duration = round(math.floor(diff_day)) + 1
                            j = 0
                            while(j < duration):
                                hol_date = datetime.strptime(str(item.date_from),  tools.DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=j)
                                if hol_date.date() ==  tz_signin_date.date():
                                    is_holiday = True
                                    end_date = item.date_to
                                    break
                                j+=1
                            
                                
                    if is_holiday == True:
#                        print 'HOLIDAY TRUE',signin_time.date()
                        if tz_signin_date.date() != tz_signout_date.date():
#                            print 'CHANGE DATE',end_date
                            
                            n_signout_time = signout_time
#                            hour = 5 because UTC time 12 = 5
                            if end_date == 12:
                                n_signout_time = n_signout_time.replace(minute=00, hour=5, second=00)
                            if end_date == 17 :
                                n_signout_time = n_signout_time.replace(minute=00, hour=10, second=00)
                            workhours = (n_signout_time - signin_time)
                        else:
#                            print 'NOT CHANGE DATE'
                            workhours = (signout_time - signin_time)
                    else :
                        if tz_signin_date.date() != tz_signout_date.date():
    #                    hour = 10 because UTC time 17 = 10
                            n_signout_time = signout_time
                            n_signout_time = n_signout_time.replace(minute=00, hour=10, second=00)
        #                    print 'signout_time1',n_signout_time
                            workhours = (n_signout_time - signin_time)
                        else :
                            workhours = (signout_time - signin_time) 
                        
                else :
                   
                    is_holiday = False
#                    print 'DATE',signin_time,signout_time
                    if tz_signin_date.date() != tz_signout_date.date():
    #                    hour = 10 because UTC time 17 = 10
#                        print '222',signin_time,signout_time
                       
                        n_signout_time = signout_time
                        n_signout_time = n_signout_time.replace(minute=00, hour=10, second=00)
    #                    print 'signout_time1',n_signout_time
                        workhours = (n_signout_time - signin_time) 
#                        print 'workhours',workhours
                    else :
#                        print 'BBBB',signout_time,signin_time
                        workhours = (signout_time - signin_time) 
#                        print 'workhours2',workhours
                
                workhour_total = ((workhours.seconds) / 60) / 60.0
#                workhour_ids = float("%.1f" % round(workhour_total,1))
#                workhour_ids_result = '{0:02.0f}:{1:02.0f}'.format(*divmod(workhour_ids * 60, 60))
#                
                mins, secs = divmod(workhours.seconds, 60)
                hours, mins = divmod(mins, 60)
                workhour_ids_result = '%02d:%02d:%02d' % (hours, mins, secs)
                
                workhour_float = (workhour_total)
#                print 'workhour_float',workhour_float
            result = {
                'employee': att.employee_id.name,
                'sign_in_time': att.name,
                'sign_out_time': sign_out_time,
                'action': att.action,
                'workhour':workhour_ids_result,
                'workhour_total': workhour_float,
                'si_reason': att.reason,
                'so_reason': so_reason,
                'total_of_late': att.late_or_leave_early,
                'is_holiday': is_holiday
                }
#            print 'result',result
            data.append(result)
            
        if data:

            return data
        else:
            return {}

class employee_attendance_summary_report(osv.AbstractModel):
    _name = 'report.sisb_hr.employee_attendance_summary_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.employee_attendance_summary_report'
    _wrapped_report_class = employee_attendance_report_print