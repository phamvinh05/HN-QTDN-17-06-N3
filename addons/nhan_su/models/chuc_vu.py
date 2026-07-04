# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ChucVu(models.Model):
    _name = 'chuc_vu'
    _description = 'Chức vụ của nhân viên'
    _rec_name = 'ten_chuc_vu'
    _sql_constraints = [
        ('ma_chuc_vu_unique', 'UNIQUE(ma_chuc_vu)', 'Mã chức vụ phải duy nhất!')
    ]

    # Mã chức vụ - có thể nhập thủ công hoặc tự động tạo
    ma_chuc_vu = fields.Char(
        string="Mã chức vụ",
        required=True,
        copy=False,
        help="Nhập mã chức vụ hoặc để trống để tự động tạo"
    )
    ten_chuc_vu = fields.Char(string="Tên chức vụ", required=True)

    
    

    # One2many liên kết với nhân viên - suffix _ids
    nhan_vien_ids = fields.One2many(
        'nhan_vien',
        'chuc_vu_id',
        string='Danh sách nhân viên'
    )

    @api.model
    def create(self, vals):
        """Tự động tạo mã chức vụ khi không nhập mã"""
        if not vals.get('ma_chuc_vu'):
            vals['ma_chuc_vu'] = self.env['ir.sequence'].next_by_code('chuc_vu.sequence') or 'CV001'
        return super(ChucVu, self).create(vals)

    def name_get(self):
        """Hiển thị tên chức vụ"""
        result = []
        for record in self:
            name = record.ten_chuc_vu or record.ma_chuc_vu or "Chức vụ #%s" % record.id
            result.append((record.id, name))
        return result
