# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LichSuLamViec(models.Model):
    _name = 'lich_su_lam_viec'
    _description = 'Bảng chứa thông tin lịch sử làm việc'
    _rec_name = 'ten_cong_viec'

    # Mã lịch sử làm việc - tự động tạo bằng sequence
    ma_lich_su = fields.Char(
        string="Mã lịch sử",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    ten_cong_viec = fields.Char(string="Tên công việc đã làm", required=True)
    
    # Many2one liên kết - suffix _id
    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string="Nhân viên",
        required=True,
        ondelete='cascade'
    )
    phong_ban_id = fields.Many2one(
        'phong_ban',
        string="Phòng ban",
        ondelete='set null'
    )
    
    ngay_bat_dau = fields.Date(string="Ngày bắt đầu")
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc")
    ghi_chu = fields.Text(string="Ghi chú")

    @api.model
    def create(self, vals):
        """Tự động tạo mã lịch sử khi tạo mới"""
        if vals.get('ma_lich_su', 'Mới') == 'Mới':
            vals['ma_lich_su'] = self.env['ir.sequence'].next_by_code('lich_su_lam_viec.sequence') or 'LS001'
        return super(LichSuLamViec, self).create(vals)

    def name_get(self):
        """Hiển thị tên công việc"""
        result = []
        for record in self:
            name = record.ten_cong_viec or record.ma_lich_su or f'Lịch sử #{record.id}'
            result.append((record.id, name))
        return result
