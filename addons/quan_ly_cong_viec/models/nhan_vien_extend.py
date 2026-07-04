# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NhanVienExtend(models.Model):
    """Kế thừa model nhan_vien để thêm thông tin từ module quan_ly_cong_viec"""
    _inherit = 'nhan_vien'
    
    # ============ CÔNG VIỆC ============
    # Các công việc mà nhân viên phụ trách
    cong_viec_phu_trach_ids = fields.One2many(
        'cong_viec',
        'nguoi_phu_trach_id',
        string='Công việc phụ trách',
        help='Danh sách công việc mà nhân viên này phụ trách'
    )
    
    # Thống kê công việc
    so_cong_viec_phu_trach = fields.Integer(
        string='Số công việc phụ trách',
        compute='_compute_thong_ke_cong_viec',
        store=False
    )
    
    so_cong_viec_dang_thuc_hien = fields.Integer(
        string='Số công việc đang thực hiện',
        compute='_compute_thong_ke_cong_viec',
        store=False
    )
    
    so_cong_viec_hoan_thanh = fields.Integer(
        string='Số công việc hoàn thành',
        compute='_compute_thong_ke_cong_viec',
        store=False
    )
    
    @api.depends('cong_viec_phu_trach_ids', 'cong_viec_phu_trach_ids.trang_thai')
    def _compute_thong_ke_cong_viec(self):
        """Thống kê công việc của nhân viên"""
        for record in self:
            record.so_cong_viec_phu_trach = len(record.cong_viec_phu_trach_ids)
            record.so_cong_viec_dang_thuc_hien = len(
                record.cong_viec_phu_trach_ids.filtered(
                    lambda c: c.trang_thai == 'dang_thuc_hien'
                )
            )
            record.so_cong_viec_hoan_thanh = len(
                record.cong_viec_phu_trach_ids.filtered(
                    lambda c: c.trang_thai == 'hoan_thanh'
                )
            )

