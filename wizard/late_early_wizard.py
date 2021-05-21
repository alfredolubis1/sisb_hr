from openerp import api, fields, models, _
from datetime import date, datetime

class late_early_wiz(models.TransientModel):
    _name = "lateness.early.wiz"

    company_id  = fields.Many2one('res.company',string="Company", required=True)
    date_from   = fields.Date(string="From")
    date_to     = fields.Date(string="To")

    @api.multi
    def print_report(self):
        print "Hi Sunil"
        context = {}
        # data = self.read(self._cr, self._uid, self._ids, context=context)[0]
        # datas = {
        #    'ids': context.get('active_ids', []),
        #    'model': 'student.registration',
        #    'form': data
        # }
        # datas['form']['ids'] = datas['ids']
        # datas['form']['report'] = 'analytic-full'
        # assert len(self) == 1, 'This option should only be used for a single id at a time.'
        # self.sent = True
        return self.env['report'].get_action(self, 'sisb_hr.lateness_early_checkout_report')
    