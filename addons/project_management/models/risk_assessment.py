# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class RiskAssessment(models.Model):
    _name = 'risk.assessment'
    _description = 'Đánh giá rủi ro dự án'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'risk_score desc, detected_date desc'

    name = fields.Char('Tên rủi ro', required=True, tracking=True)
    project_id = fields.Many2one('projects', string='Dự án', required=True, ondelete='cascade', tracking=True)
    
    risk_type = fields.Selection([
        ('schedule', 'Rủi ro tiến độ'),
        ('budget', 'Rủi ro ngân sách'),
        ('resource', 'Rủi ro nguồn lực'),
        ('quality', 'Rủi ro chất lượng'),
        ('scope', 'Rủi ro phạm vi')
    ], string='Loại rủi ro', required=True, tracking=True)
    
    risk_level = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('critical', 'Nghiêm trọng')
    ], string='Mức độ rủi ro', compute='_compute_risk_level', store=True, tracking=True)
    
    probability = fields.Float('Xác suất (%)', default=0.5, help='Xác suất xảy ra rủi ro (0-100%)')
    impact_score = fields.Float('Điểm tác động', default=5.0, help='Mức độ tác động (1-10)')
    risk_score = fields.Float('Điểm rủi ro', compute='_compute_risk_score', store=True, 
                              help='Điểm rủi ro = Xác suất x Tác động / 10')
    
    description = fields.Text('Mô tả', help='Mô tả chi tiết về rủi ro')
    root_cause = fields.Text('Nguyên nhân gốc', help='Phân tích nguyên nhân gốc (AI generated)')
    mitigation_plan = fields.Text('Kế hoạch khắc phục', help='Đề xuất biện pháp phòng ngừa/khắc phục')
    
    status = fields.Selection([
        ('identified', 'Đã phát hiện'),
        ('analyzing', 'Đang phân tích'),
        ('mitigating', 'Đang khắc phục'),
        ('resolved', 'Đã giải quyết'),
        ('accepted', 'Chấp nhận rủi ro')
    ], string='Trạng thái', default='identified', tracking=True)
    
    detected_date = fields.Datetime('Ngày phát hiện', default=fields.Datetime.now, readonly=True)
    resolved_date = fields.Datetime('Ngày giải quyết', readonly=True)
    
    ai_confidence = fields.Float('Độ tin cậy AI (%)', default=0.0, 
                                 help='Độ tin cậy của AI trong việc phát hiện rủi ro (0-100%)')
    is_ai_detected = fields.Boolean('Phát hiện bởi AI', default=False)
    
    assigned_to = fields.Many2one('nhan_vien', string='Người phụ trách', 
                                  help='Người chịu trách nhiệm xử lý rủi ro')
    
    # Related fields để hiển thị thông tin dự án
    project_progress = fields.Float(related='project_id.progress', string='Tiến độ dự án', readonly=True)
    project_status = fields.Selection(related='project_id.status', string='Trạng thái dự án', readonly=True)
    
    @api.depends('probability', 'impact_score')
    def _compute_risk_score(self):
        """Tính điểm rủi ro = Xác suất (0-1) * Tác động * 10"""
        for record in self:
            # probability giờ là 0.0-1.0 (ví dụ: 0.7 = 70%)
            record.risk_score = record.probability * record.impact_score * 10
    
    @api.depends('risk_score')
    def _compute_risk_level(self):
        """Tự động phân loại mức độ rủi ro dựa trên điểm số"""
        for record in self:
            if record.risk_score >= 70:
                record.risk_level = 'critical'
            elif record.risk_score >= 50:
                record.risk_level = 'high'
            elif record.risk_score >= 30:
                record.risk_level = 'medium'
            else:
                record.risk_level = 'low'
    
    def action_start_mitigation(self):
        """Bắt đầu khắc phục rủi ro"""
        self.write({'status': 'mitigating'})
        return True
    
    def action_resolve(self):
        """Đánh dấu rủi ro đã được giải quyết"""
        self.write({
            'status': 'resolved',
            'resolved_date': fields.Datetime.now()
        })
        return True
    
    def action_accept_risk(self):
        """Chấp nhận rủi ro (không xử lý)"""
        self.write({'status': 'accepted'})
        return True
    
    def action_enhance_with_gemini(self):
        """Nâng cấp phân tích rủi ro bằng Gemini AI"""
        self.ensure_one()
        
        try:
            gemini = self.env['gemini.ai.provider'].get_provider()
            
            if not gemini.is_active or not gemini.api_key:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Gemini AI chưa sẵn sàng',
                        'message': 'Vui lòng cấu hình API key trong menu Cấu hình > Gemini AI Settings',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
            # Generate mitigation plan nâng cao
            _logger.info(f"Enhancing risk {self.id} with Gemini AI - Starting...")
            enhanced_mitigation = gemini.generate_mitigation_plan(self)
            _logger.info(f"Mitigation plan length: {len(enhanced_mitigation) if enhanced_mitigation else 0}")
            
            # Root cause analysis nâng cao
            enhanced_root_cause = gemini.analyze_root_cause(self)
            _logger.info(f"Root cause length: {len(enhanced_root_cause) if enhanced_root_cause else 0}")
            
            # Kiểm tra xem có dữ liệu mới không
            if not enhanced_mitigation and not enhanced_root_cause:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Gemini AI không trả về dữ liệu',
                        'message': 'Vui lòng kiểm tra API key và kết nối internet',
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            
            # Chỉ cập nhật các field có dữ liệu mới
            update_vals = {'ai_confidence': min(self.ai_confidence + 10, 95)}
            
            if enhanced_mitigation and enhanced_mitigation != self.mitigation_plan:
                update_vals['mitigation_plan'] = enhanced_mitigation
                _logger.info(f"Updated mitigation_plan for risk {self.id}")
            
            if enhanced_root_cause and enhanced_root_cause != self.root_cause:
                update_vals['root_cause'] = enhanced_root_cause
                _logger.info(f"Updated root_cause for risk {self.id}")
            
            # Cập nhật và commit
            self.write(update_vals)
            self.env.cr.commit()  # Force commit để đảm bảo dữ liệu được lưu
            
            _logger.info(f"Successfully enhanced risk {self.id} with Gemini AI")
            
            # Trả về notification thành công - KHÔNG reload form để tránh mất dữ liệu
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Gemini AI phân tích hoàn tất',
                    'message': 'Đã nâng cấp Root Cause và Mitigation Plan. Vui lòng cuộn xuống các tab để xem!',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error enhancing risk with Gemini: {str(e)}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': f'Không thể sử dụng Gemini AI: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def name_get(self):
        """Hiển thị tên rủi ro kèm điểm số"""
        result = []
        for record in self:
            name = f"{record.name} ({record.risk_score:.1f})"
            result.append((record.id, name))
        return result


class RiskMetric(models.Model):
    _name = 'risk.metric'
    _description = 'Chỉ số theo dõi rủi ro'
    _order = 'date desc'
    
    project_id = fields.Many2one('projects', string='Dự án', required=True, ondelete='cascade')
    
    metric_type = fields.Selection([
        ('cpi', 'CPI - Cost Performance Index'),
        ('spi', 'SPI - Schedule Performance Index'),
        ('burn_rate', 'Burn Rate - Tốc độ chi tiêu'),
        ('velocity', 'Velocity - Tốc độ hoàn thành'),
        ('defect_rate', 'Defect Rate - Tỷ lệ lỗi'),
        ('resource_utilization', 'Sử dụng nguồn lực')
    ], string='Loại chỉ số', required=True)
    
    value = fields.Float('Giá trị', required=True)
    threshold_min = fields.Float('Ngưỡng tối thiểu', help='Giá trị dưới ngưỡng này là cảnh báo')
    threshold_max = fields.Float('Ngưỡng tối đa', help='Giá trị trên ngưỡng này là cảnh báo')
    date = fields.Date('Ngày đo', default=fields.Date.context_today, required=True)
    
    is_anomaly = fields.Boolean('Bất thường', compute='_compute_is_anomaly', store=True,
                                help='AI phát hiện giá trị bất thường')
    notes = fields.Text('Ghi chú')
    
    @api.depends('value', 'threshold_min', 'threshold_max')
    def _compute_is_anomaly(self):
        """Phát hiện giá trị bất thường"""
        for record in self:
            is_anomaly = False
            if record.threshold_min and record.value < record.threshold_min:
                is_anomaly = True
            if record.threshold_max and record.value > record.threshold_max:
                is_anomaly = True
            record.is_anomaly = is_anomaly


class RiskPrediction(models.Model):
    _name = 'risk.prediction'
    _description = 'Dự báo rủi ro AI'
    _order = 'prediction_date desc'
    
    project_id = fields.Many2one('projects', string='Dự án', required=True, ondelete='cascade')
    
    prediction_type = fields.Selection([
        ('completion_date', 'Ngày hoàn thành dự kiến'),
        ('final_cost', 'Chi phí cuối kỳ'),
        ('resource_shortage', 'Thiếu hụt nguồn lực'),
        ('delay_probability', 'Xác suất trễ hạn')
    ], string='Loại dự báo', required=True)
    
    predicted_value = fields.Char('Giá trị dự báo', required=True)
    confidence_level = fields.Float('Độ tin cậy (%)', default=0.0, 
                                    help='Độ tin cậy của dự báo (0-100%)')
    prediction_date = fields.Datetime('Ngày dự báo', default=fields.Datetime.now, readonly=True)
    model_used = fields.Char('Model AI', help='Tên thuật toán/model AI được sử dụng')
    notes = fields.Text('Ghi chú')
