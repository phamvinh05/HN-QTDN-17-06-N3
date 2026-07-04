# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PhongBan(models.Model):
    _name = 'phong_ban'
    _description = 'Phòng ban của nhân viên'
    _rec_name = 'ten_phong_ban'

    # Mã phòng ban - tự động tạo bằng sequence
    ma_phong_ban = fields.Char(
        string="Mã phòng ban",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    ten_phong_ban = fields.Char(string="Tên phòng ban", required=True)
    mo_ta = fields.Text(string="Mô tả")

    # One2many liên kết với nhân viên - suffix _ids
    nhan_vien_ids = fields.One2many(
        'nhan_vien',
        'phong_ban_id',
        string='Danh sách nhân viên'
    )

    @api.model
    def create(self, vals):
        """Tự động tạo mã phòng ban khi tạo mới"""
        if vals.get('ma_phong_ban', 'Mới') == 'Mới':
            vals['ma_phong_ban'] = self.env['ir.sequence'].next_by_code('phong_ban.sequence') or 'PB001'
        return super(PhongBan, self).create(vals)

    def name_get(self):
        """Hiển thị tên phòng ban"""
        result = []
        for record in self:
            name = record.ten_phong_ban or record.ma_phong_ban or f'Phòng ban #{record.id}'
            result.append((record.id, name))
        return result
