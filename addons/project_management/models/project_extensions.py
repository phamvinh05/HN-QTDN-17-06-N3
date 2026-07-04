# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CongViecExtend(models.Model):
    """Kế thừa model cong_viec để thêm field du_an_id từ module project_management"""
    _inherit = 'cong_viec'
    
    # Liên kết Many2one tới model projects từ project_management
    du_an_id = fields.Many2one(
        'projects', 
        string='Dự án', 
        ondelete='cascade',
        help='Dự án từ module Project Management. Mỗi công việc chỉ thuộc một dự án.'
    )

