from odoo import models, fields, api
class ChucVu(models.Model):
    _name = 'chuc_vu'
    _describe = 'Chức vụ của nhân viên'

    ma_chuc_vu = fields.Char("Mã chức vụ", reuired=True)
    ten_chuc_vu = fields.Char("Tên chức vụ", required=True)