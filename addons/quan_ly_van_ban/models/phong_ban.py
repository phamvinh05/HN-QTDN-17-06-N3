from odoo import models, fields, api
class PhongBan(models.Model):
    _name = 'phong_ban'
    _describe = 'Phòng ban của nhân viên'

    ma_phong_ban = fields.Char("Mã phòng ban", reuired=True)
    ten_phong_ban = fields.Char("Tên phòng ban", required=True)