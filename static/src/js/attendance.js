openerp.hr_attendance = function (instance) {
    
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    var _lt = instance.web._lt;

    instance.hr_attendance.AttendanceSlider = instance.web.Widget.extend({
        template: 'AttendanceSlider',
        init: function (parent) {
            this._super(parent);
            this.set({"signed_in": false});
        },
        start: function() {
            var self = this;
            var tmp = function() {
                var $sign_in_out_icon = this.$('#oe_attendance_sign_in_out_icon');
                $sign_in_out_icon.toggleClass("fa-sign-in", ! this.get("signed_in"));
                $sign_in_out_icon.toggleClass("fa-sign-out", this.get("signed_in"));
            };
            this.on("change:signed_in", this, tmp);
            _.bind(tmp, this)();
            this.$(".oe_attendance_sign_in_out").click(function(ev) {
                ev.preventDefault();


                var status_attendance = '';
                var employee_id = '';
                var shift_id = '';

                self.fetch('hr.employee',['name','state','user_id'],[['user_id', '=', instance.session.uid]]).done(function(employ){
                    status_attendance = employ[0].state;
                    employee_id = employ[0].id
                    self.fetch('hr.attendance',['name','action','shift_id'],[['employee_id','=',employee_id]]).done(function(att)
                    {
                        console.log('att = ', att)
                        var attendancedata = [];
                        var lastsign;
                        var data = att.map(function(x) {
                            var res = {}
                            if(x.action == 'sign_in')
                            {
                                now = new Date(x.name).addHours(8);
                                res = {'sign':new Date(x.name).addHours(8), 'action':x.action, 'shift_id':x.shift_id}
                                attendancedata.push(res)
                            }

                            })
                        if (attendancedata.length > 0)
                        {   
                            lastsign = attendancedata[0]
                            console.log('lastsign = ', lastsign)
                        }
                        console.log('lastsign = ', lastsign)
                        year = new Date().getFullYear()
                        month = new Date().getMonth() + 1
                        day = new Date().getDate()
                        today = year + '-' + month + '-' + day;
                        self.fetch('hr.schedule.shift.list',['id','name','employee_id','shift_id'],[['name', '=', today],['employee_id','=',employee_id]]).done(function(worktime){
                            console.log('worktime = ', worktime)
                            var dt_now = new Date().toLocaleString("en-US", {timeZone: 'Asia/Singapore'});
                            var dt = new Date(dt_now);
                            var skrg = new Date();
                            var utcDate = dt.toUTCString();
                            var hourServer = dt.getHours();
                            var minuteServer = dt.getMinutes();
                            var secondServer = dt.getSeconds();
                            var date = dt.getDate();
                            var month = dt.getMonth()+1; //January is 0!
                            var year = dt.getFullYear();

                            signdatetime = dt;
                            if(date < 10) {
                                date = '0'+ date
                            } 
                            if(month < 10) {
                                month = '0'+month
                            } 

                            today = year + '-' + month + '-' + date;
                            if (status_attendance === 'absent'){
                                if (worktime.length <= 0){
                                    self.ask_shift();
                                }
                                else if (worktime.length > 0){
                                    self.fetch('work.time.structure',['start_hour','end_hour','late_tolerance'],[['id', '=', worktime[0].shift_id[0]]]).done(function(shift){

                                        var starthour = parseInt(shift[0].start_hour);
                                        console.log('starthour = ', starthour)
                                        var endhour =  parseInt(shift[0].end_hour);
                                        var maxendhour = parseInt(endhour);
                                        var startsecond = 0;
                                        var start_minute_worktime = Math.round((shift[0].start_hour % 1) * 60);
                                        var maxstartminute = Math.round((shift[0].late_tolerance % 1) * 60);
                                        var startminute = parseInt(start_minute_worktime) + maxstartminute;
                                        //console.log(worktime[0].start_time)
                                        if  (startminute == 60){
                                            startminute = 0;
                                            starthour = starthour + 1;
                                            }
                                        if  (startminute > 60){
                                            startminute = startminute - 60;
                                            starthour = starthour + 1;
                                            }
                                        var end_minute_worktime = Math.round((shift[0].end_hour % 1) * 60);
                                        var endminute = parseInt(end_minute_worktime);

                                        self.fetch('hr.holidays',['employee_id','state','date_from1','date_to1','number_of_days'],[['employee_id', '=', employee_id],['state', '=', 'validate'],['date_from1', '<=',today],['date_to1', '>=', today],['type', '=', 'remove']]).done(function(holiday){
                                            
                                            // Check whether the Employee take a leave or not
                                            if (holiday.length > 0){
                                                self.fetch('days.holidays.days',['date1','state'],[['date1','=',today],['holiday_id','=', holiday.id],['state', '=', 'validated']]).done(function(hd_day){
                                                    if (hd_day.length > 0){
                                                        self.raise_holiday_error();
                                                    }
                                                });
                                            }
                                            else {
                                                if (hourServer > starthour ){
                                                    // if late then employee need to write a reason
                                                    self.add_reason_attendance(ev);
                                                }   
                                                else if (hourServer === starthour && minuteServer > maxstartminute){
                                                    // if late then employee need to write a reason
                                                    self.add_reason_attendance(ev);
                                                }
                                                else {
                                                    // if not late just let employee sign in
                                                    self.do_update_attendance();
                                                } 
                                            }
                                        });
                                    });
                                }
                            }

                            else if (status_attendance === 'present'){
                                self.fetch('work.time.structure',['start_hour','end_hour','late_tolerance'],[['id', '=', lastsign.shift_id[0]]]).done(function(shift){
                                    var starthour = parseInt(shift[0].start_hour);
                                    console.log('starthour = ', starthour)
                                    var endhour =  parseInt(shift[0].end_hour);
                                    var maxendhour = parseInt(endhour);
                                    var startsecond = 0;
                                    var start_minute_worktime = Math.round((shift[0].start_hour % 1) * 60);
                                    var maxstartminute = Math.round((shift[0].late_tolerance % 1) * 60);
                                    var startminute = parseInt(start_minute_worktime) + maxstartminute;
                                    //console.log(worktime[0].start_time)
                                    if  (startminute == 60){
                                        startminute = 0;
                                        starthour = starthour + 1;
                                        }
                                    if  (startminute > 60){
                                        startminute = startminute - 60;
                                        starthour = starthour + 1;
                                        }
                                    var end_minute_worktime = Math.round((shift[0].end_hour % 1) * 60);
                                    var endminute = parseInt(end_minute_worktime);
                                    
                                    if (lastsign != null){
                                        console.log('lasssss = ', lastsign)
                                        var sign_date = lastsign.sign.getDate();
                                        var sign_month = lastsign.sign.getMonth() + 1;
                                        var sign_year = lastsign.sign.getFullYear();
                                        var datenow = dt.getDate();
                                        var monthnow = dt.getMonth()+1; //January is 0!
                                        var yearnow = dt.getFullYear();
                                        var today_date = yearnow + '-' + monthnow + '-' + datenow;
                                        var signdate_user =  sign_year + '-' +  sign_month + '-' + sign_date;
                                        //console.log(today_date,signdate_user,status_attendance )
                                        console.log('today_date = ', today_date)
                                        console.log('signdate_user = ', signdate_user)
                                        if (today_date != signdate_user)
                                        {
                                            self.do_update_attendance(ev);
                                            // window.location.reload();
                                        }
                                        else if (today_date == signdate_user && hourServer < endhour){
                                            console.log('disini22222', self)
                                            self.add_reason_sign_out_attendance();
                                        }
                                        else if (today_date == signdate_user && endminute > 0){
                                            console.log('disini3')
                                            if (hourServer === endhour && minuteServer < endminute){
                                                self.add_reason_sign_out_attendance();
                                            }
                                            else{
                                                self.do_update_attendance(ev);
                                            }
                                        }
                                        else {
                                            console.log('sss')
                                            self.do_update_attendance(ev);
                                        }
                                    }

                                    else{
                                        console.log('disinisadasdasdasdas')
                                        if(hourServer < endhour){
                                            console.log('disini222221', self)
                                            self.add_reason_sign_out_attendance();
                                        }
                                        else if (endminute > 0){
                                            console.log('disini3')
                                            if (hourServer === endhour && minuteServer < endminute){
                                                self.add_reason_sign_out_attendance();
                                            }
                                        }
                                        else {
                                            console.log('sss')
                                            self.do_update_attendance(ev);
                                        }
                                    }
                                });
                            }
                            // if (worktime.length <= 0){
                            //     self.do_update_attendance();
                            // }

                            // var dt_now = new Date().toLocaleString("en-US", {timeZone: 'Asia/Singapore'});
                            // var dt = new Date(dt_now);
                            // var skrg = new Date();
                            // var utcDate = dt.toUTCString();
                            // var hourServer = dt.getHours();
                            // var minuteServer = dt.getMinutes();
                            // var secondServer = dt.getSeconds();
                            // var date = dt.getDate();
                            // var month = dt.getMonth()+1; //January is 0!
                            // var year = dt.getFullYear();

                            // signdatetime = dt;
                            // if(date < 10) {
                            //     date = '0'+date
                            // } 
                            // if(month < 10) {
                            //     month = '0'+month
                            // } 

                            // today = year + '-' + month + '-' + date;
                            // if(worktime.length > 0){
                            //     console.log('Here')
                            //     shift_id = self.current_shift(worktime[0].shift_id[0]);
                            //     console.log('shift_id = ', shift_id)
                            //     var starthour = parseInt(shift_id[0].start_hour);
                            //     console.log('starthour = ', starthour)
                            //     var endhour =  parseInt(shift_id[0].end_hour);
                            //     var maxendhour = parseInt(endhour);
                            //     var startsecond = 0;
                            //     var start_minute_worktime = Math.round((shift_id[0].start_hour % 1) * 60);
                            //     var maxstartminute = Math.round((shift_id[0].late_tolerance % 1) * 60);
                            //     var startminute = parseInt(start_minute_worktime) + maxstartminute;
                            //     //console.log(worktime[0].start_time)

                            //     if  (startminute == 60)
                            //     {
                            //         startminute = 0;
                            //         starthour = starthour + 1;
                            //     }
                            //     if  (startminute > 60)
                            //     {
                            //         startminute = startminute - 60;
                            //         starthour = starthour + 1;
                            //     }
                            
                            //     var end_minute_worktime = Math.round((shift_id[0].end_hour % 1) * 60);
                            //     var endminute = parseInt(end_minute_worktime);
                            //     self.fetch('hr.holidays',['employee_id','state','date_from1','date_to1','number_of_days'],[['employee_id', '=', employee_id],['state', '=', 'validate'],['date_from1', '<=',today],['date_to1', '>=', today],['type', '=', 'remove']]).done(function(holiday)
                            //     {   console.log('holiday = ', holiday)
                            //         if (holiday.length > 0){
                            //             is_holiday = true;
                            //         }
                            //         else {
                            //             is_holiday = false;
                            //         }
                            //         console.log('is_holiday = ', is_holiday)
                            //         console.log('holiday = ', holiday.length)
                            //         if (status_attendance === 'absent')
                            //         {   
                            //             if (is_holiday == true)
                            //             {
                            //                 console.log('disini 11')
                            //                 self.raise_holiday_error();
                            //             }
                            //             else if (is_holiday == false) 
                            //             {   
                            //                 console.log('disini 22')
                            //                 if (hourServer > starthour ){
                            //                     // self.write_value_from_js(late);
                            //                     self.add_reason_attendance(ev);

                            //                 }   
                            //                 else if (hourServer === starthour && minuteServer > maxstartminute){
                            //                     self.add_reason_attendance(ev);
                            //                 }
                            //                 else {
                            //                     self.do_update_attendance();
                            //                 } 
                            //             }
                            //         }
                            //         if (status_attendance === 'present')
                            //         {   
                            //             if (lastsign != null)
                            //             {   console.log('lasssss = ', lastsign)
                            //                 var sign_date = lastsign.sign.getDate();
                            //                 var sign_month = lastsign.sign.getMonth() + 1;
                            //                 var sign_year = lastsign.sign.getFullYear();
                            //                 var datenow = dt.getDate();
                            //                 var monthnow = dt.getMonth()+1; //January is 0!
                            //                 var yearnow = dt.getFullYear();
                            //                 var today_date = yearnow + '-' + monthnow + '-' + datenow;
                            //                 var signdate_user =  sign_year + '-' +  sign_month + '-' + sign_date;
                            //                 //console.log(today_date,signdate_user,status_attendance )
                            //                 console.log('today_date = ', today_date)
                            //                 console.log('signdate_user = ', signdate_user)
                            //                 if (today_date != signdate_user)
                            //                 {
                            //                     self.do_update_attendance(ev);
                            //                     // window.location.reload();
                            //                 }
                            //                 else if (today_date == signdate_user && hourServer < endhour){
                            //                     console.log('disini22222', self)
                            //                     self.add_reason_sign_out_attendance();
                            //                 }
                            //                 else if (today_date == signdate_user && endminute > 0){
                            //                     console.log('disini3')
                            //                     if (hourServer === endhour && minuteServer < endminute){
                            //                         self.add_reason_sign_out_attendance();
                            //                     }
                            //                     else{
                            //                         self.do_update_attendance(ev);
                            //                     }
                            //                 }
                            //                 else {
                            //                     console.log('sss')
                            //                     self.do_update_attendance(ev);
                            //                 }
                            //             }

                            //             else
                            //             {
                            //                 console.log('disinisadasdasdasdas')
                            //                 if(hourServer < endhour){
                            //                     console.log('disini222221', self)
                            //                     self.add_reason_sign_out_attendance();
                            //                 }
                            //                 else if (endminute > 0){
                            //                     console.log('disini3')
                            //                     if (hourServer === endhour && minuteServer < endminute){
                            //                         self.add_reason_sign_out_attendance();
                            //                     }
                            //                 }
                            //                 else {
                            //                     console.log('sss')
                            //                     self.do_update_attendance(ev);
                            //                 }
                            //             }

                            //         }
                            //     });
                            // };
                                
                        });
                    });
                });
                // self.do_update_attendance();
            });
            this.$el.tooltip({
                title: function() {
                    var last_text = instance.web.format_value(self.last_sign, {type: "datetime"});
                    var current_text = instance.web.format_value(new Date(), {type: "datetime"});
                    var duration = self.last_sign ? $.timeago(self.last_sign) : "none";
                    if (self.get("signed_in")) {
                        return _.str.sprintf(_t("Last sign in: %s,<br />%s.<br />Click to sign out."), last_text, duration);
                    } else {
                        return _.str.sprintf(_t("Click to Sign In at %s."), current_text);
                    }
                },
            });
            return this.check_attendance();
        },
        fetch: function (model, fields, domain, ctx){
            // return new instance.web.Model(model).query(fields).filter(domain).context(ctx).all();
            return new openerp.Model(model).query(fields).filter(domain).context(ctx).all();
        },

        add_reason_attendance: function(ev){
            var self = this;
            self.has_uncommitted_changes = new instance.web.ActionManager(self);
            self.rpc("/web/action/load", { action_id: "sisb_hr.sisb_action_attend_edit_form" }).done(function(result){
                self.action_manager = new instance.web.ActionManager(self);
                self.action_manager.do_action(result);
            });
        },
        add_reason_sign_out_attendance: function(ev){
            var self = this;
            self.has_uncommitted_changes = new instance.web.ActionManager(self);
            self.rpc("/web/action/load", { action_id: "sisb_hr.action_leave_early_wiz_form_view" }).done(function(result){
                self.action_manager = new instance.web.ActionManager(self);
                self.action_manager.do_action(result);
            });
        },
        do_action: function(/*...*/) {
            var am = this.action_manager;
            return am.do_action.apply(am, arguments);
        },

        ask_shift: function () {
            var self = this;
            var hr_employee = new instance.web.DataSet(self, 'hr.employee');
            hr_employee.call('attendance_ask_shift', [[self.employee.id]])
        },
        
        

        do_update_attendance: function () {
            var self = this;
            var hr_employee = new instance.web.DataSet(self, 'hr.employee');
            hr_employee.call('attendance_action_change', [
                [self.employee.id]
            ]).done(function (result) {
                self.last_sign = new Date();
                self.set({"signed_in": ! self.get("signed_in")});
            });
        },
        check_attendance: function () {
            var self = this;
            self.employee = false;
            this.$el.hide();
            var employee = new instance.web.DataSetSearch(self, 'hr.employee', self.session.user_context, [
                ['user_id', '=', self.session.uid]
            ]);
            return employee.read_slice(['id', 'name', 'state', 'last_sign', 'attendance_access']).then(function (res) {
                if (_.isEmpty(res) )
                    return;
                if (res[0].attendance_access === false){
                    return;
                }
                self.$el.show();
                self.employee = res[0];
                self.last_sign = instance.web.str_to_datetime(self.employee.last_sign);
                self.set({"signed_in": self.employee.state !== "absent"});
            });
        },
    });

    instance.web.UserMenu.include({
        do_update: function () {
            this._super();
            var self = this;
            this.update_promise.done(function () {
                if (!_.isUndefined(self.attendanceslider)) {
                    return;
                }
                // check current user is an employee
                var Users = new instance.web.Model('res.users');
                Users.call('has_group', ['base.group_user']).done(function(is_employee) {
                    if (is_employee) {
                        self.attendanceslider = new instance.hr_attendance.AttendanceSlider(self);
                        self.attendanceslider.prependTo(instance.webclient.$('.oe_systray'));
                    } else {
                        self.attendanceslider = null;
                    }
                });
            });
        },
    });
};

