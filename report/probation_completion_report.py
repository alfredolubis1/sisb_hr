from openerp.osv import osv
import time

from openerp.report import report_sxw
from openerp.osv import osv



class Probation_Completion_Report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Probation_Completion_Report, self).__init__(cr, uid, name, context=context)
        ids = context.get('active_ids')
        employee_obj = self.pool['hr.employee']
        docs = employee_obj.browse(cr, uid, ids, context)


        self.localcontext.update({
            'docs': docs,
            # 'getLines': self._lines_get,
        })
        self.context = context

    # def _lines_get(self, student):
    #     invoice_obj = self.pool['account.invoice']
    #     invoice = invoice_obj.search(self.cr, self.uid,
    #             [('student_id', '=', student.id), ('account_id.type', 'in', ['receivable', 'payable']),('state', '<>', 'paid')])
    #     invoices = invoice_obj.browse(self.cr, self.uid, invoice)
    #     return invoices


class sisb_probation_completion_report(osv.AbstractModel):
    _name = 'report.sisb_hr.sisb_probation_completion_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.sisb_probation_completion_report'
    _wrapped_report_class = Probation_Completion_Report





class probation_appraisals_letter(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(probation_appraisals_letter, self).__init__(cr, uid, name, context=context)
        ids = context.get('active_ids')
        employee_obj = self.pool['hr.employee']
        docs = employee_obj.browse(cr, uid, ids, context)


        self.localcontext.update({
            'docs': docs,
            # 'getLines': self._lines_get,
        })
     

 


class sisb_probation_appraisals_report(osv.AbstractModel):
    _name = 'report.sisb_hr.sisb_probation_appraisals_report'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.sisb_probation_appraisals_report'
    _wrapped_report_class = probation_appraisals_letter




class generate_board_item(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(generate_board_item, self).__init__(cr, uid, name, context=context)
        ids = context.get('active_ids')
        employee_obj = self.pool['hr.employee']
        docs = employee_obj.browse(cr, uid, ids, context)


        self.localcontext.update({
            'docs': docs,
        })
     

 


class generate_on_board_item(osv.AbstractModel):
    _name = 'report.sisb_hr.generate_on_board_item'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.generate_on_board_item'
    _wrapped_report_class = generate_board_item




class generate_ref_letter(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(generate_ref_letter, self).__init__(cr, uid, name, context=context)
        ids = context.get('active_ids')
        employee_obj = self.pool['hr.employee']
        docs = employee_obj.browse(cr, uid, ids, context)
        print('docs = ', docs)
        print('context = ', context)


        self.localcontext.update({
            'docs': docs,
        })
     

 


class generate_reference_letter(osv.AbstractModel):
    _name = 'report.sisb_hr.generate_reference_letter'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.generate_reference_letter'
    _wrapped_report_class = generate_ref_letter



class generate_ref_letter_with_salary(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(generate_ref_letter_with_salary, self).__init__(cr, uid, name, context=context)
        ids = context.get('active_ids')
        employee_obj = self.pool['hr.employee']
        docs = employee_obj.browse(cr, uid, ids, context)
        print('docs = ', docs)
        print('context = ', context)


        self.localcontext.update({
            'docs': docs,
        })
     

 


class generate_reference_letter_with_salary(osv.AbstractModel):
    _name = 'report.sisb_hr.generate_reference_letter_with_salary'
    _inherit = 'report.abstract_report'
    _template = 'sisb_hr.generate_reference_letter_with_salary'
    _wrapped_report_class = generate_ref_letter_with_salary