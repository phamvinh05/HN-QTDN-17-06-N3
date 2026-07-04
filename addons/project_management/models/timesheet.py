from odoo import models, fields, api

class ProjectTimesheet(models.Model):
    _name = 'project.timesheet'
    _description = 'Bảng chấm công / Timesheet'

    task_id = fields.Many2one('cong_viec', string='Nhiệm vụ', required=True)
    employee_id = fields.Many2one('nhan_vien', string='Nhân viên')
    date = fields.Date(default=fields.Date.today)
    hours = fields.Float(string='Số giờ')
    description = fields.Text()
    
    @api.depends('hours')
    def _compute_total_hours(self):
        # Tính tổng giờ cho task (có thể thêm field vào cong_viec)
        pass