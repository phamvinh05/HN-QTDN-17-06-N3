from odoo import models, fields, api


class VanBanDi(models.Model):
    _name = 'van_ban_di'
    _description = 'Bảng chứa thông tin văn bản đi'

    ten_van_ban = fields.Char("Tên văn bản đi", required=True)
   
