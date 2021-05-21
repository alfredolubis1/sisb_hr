from openerp import fields, models, api, _
import werkzeug.urls
from openerp import http
from openerp.http import request


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    
    @api.multi
    def _get_signup_url_for_action_id(self, action=None, view_type=None, menu_id=None, res_id=None, model=None):
        """ generate a signup url for the given partner ids and action, possibly overriding
            the url state components (menu_id, id, view_type) """

        res = dict.fromkeys(self.ids, False)
        # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url = http.request.httprequest.environ['HTTP_REFERER']
        for partner in self:
            # when required, make sure the partner has a valid signup token
            if self.env.context.get('signup_valid') and not partner.user_ids:
                partner.signup_prepare()

            route = 'login'
            # the parameters to encode for the query
            query = dict(db=self.env.cr.dbname)
            signup_type = self.env.context.get('signup_force_type_in_url', partner.signup_type or '')
            if signup_type:
                route = 'reset_password' if signup_type == 'reset' else signup_type

            if partner.signup_token and signup_type:
                query['token'] = partner.signup_token
            elif partner.user_ids:
                query['login'] = partner.user_ids[0].login
            else:
                continue        # no signup token, no user, thus no signup url!

            fragment = dict()
            base = '/web#'
            if action == '/mail/view':
                base = '/mail/view?'
            elif action:
                fragment['action'] = action
            if view_type:
                fragment['view_type'] = view_type
            if menu_id:
                fragment['menu_id'] = menu_id
            if model:
                fragment['model'] = model
            if res_id:
                fragment['id'] = res_id

            if fragment:
                query['redirect'] = base + werkzeug.urls.url_encode(fragment)

            res[partner.id] = werkzeug.urls.url_join(base_url, "/web/%s?%s" % (route, werkzeug.urls.url_encode(query)))
        return res

    @api.multi
    def get_url(self, emp_id, object):
        url = ''
        print('emp_id = ', emp_id)
        employee = self.env['hr.employee'].sudo().search([('id','=',emp_id.id)])
        if not emp_id:
            model_id = request.params['args'][0][0]
            print('args = ',request.params['args'])
            view_type = request.params['args'][1]['params']['view_type']
            model = request.params['args'][1]['params']['model']
            action = request.params['args'][1]['params']['action']
            url = str(http) + '/web#id=' + str(model_id) + '&view_type=' + str(view_type) + '&model=' + str(model) + '&action=' + str(action)
        if emp_id:
            other_url = request.httprequest.environ
            action = request.params['args'][1]['params']['action']
            print('object2 = ', object)
            url = employee.user_id.partner_id.with_context(signup_force_type_in_url='')._get_signup_url_for_action_id(action=action,view_type='form',model=object, res_id =object.id)[employee.user_id.partner_id.id]
        return url