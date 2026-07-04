# -*- coding: utf-8 -*-
# from odoo import http


# class QuanLyCongViec(http.Controller):
#     @http.route('/quan_ly_cong_viec/quan_ly_cong_viec', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/quan_ly_cong_viec/quan_ly_cong_viec/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('quan_ly_cong_viec.listing', {
#             'root': '/quan_ly_cong_viec/quan_ly_cong_viec',
#             'objects': http.request.env['quan_ly_cong_viec.quan_ly_cong_viec'].search([]),
#         })

#     @http.route('/quan_ly_cong_viec/quan_ly_cong_viec/objects/<model("quan_ly_cong_viec.quan_ly_cong_viec"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('quan_ly_cong_viec.object', {
#             'object': obj
#         })
