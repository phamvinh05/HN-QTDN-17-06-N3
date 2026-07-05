# -*- coding: utf-8 -*-

import logging
import json
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    _logger.warning("google-generativeai library not installed. Gemini AI features will be disabled.")


class GeminiAIProvider(models.Model):
    """
    Google Gemini AI Provider cho Risk Management
    
    Tính năng:
    - Phân tích mô tả dự án để tìm risks tiềm ẩn
    - Generate mitigation plans thông minh
    - Phân tích đa chiều từ data dự án
    - Root cause analysis nâng cao
    """
    _name = 'gemini.ai.provider'
    _description = 'Google Gemini AI Provider for Risk Management'
    
    name = fields.Char(string='Provider Name', default='Google Gemini AI', readonly=True)
    api_key = fields.Char(string='API Key', help='Google AI Studio API Key')
    model_name = fields.Selection([
        ('gemini-2.5-flash', 'Gemini 2.5 Flash (ổn định, khuyên dùng)'),
        ('gemini-2.5-pro', 'Gemini 2.5 Pro'),
        ('gemini-3.5-flash', 'Gemini 3.5 Flash (mới nhất)'),
    ], string='Model', default='gemini-2.5-flash', required=True,
       help='Lưu ý: gemini-pro, gemini-1.5-flash, gemini-1.5-pro đã bị Google khai tử '
            '(shutdown), gọi vào sẽ báo lỗi 404. Chỉ chọn model trong danh sách này.')
    is_active = fields.Boolean(string='Active', default=True)
    temperature = fields.Float(string='Temperature', default=0.7, help='0.0-1.0: Controls randomness')
    max_tokens = fields.Integer(string='Max Output Tokens', default=2048)
    last_used = fields.Datetime(string='Last Used')
    total_requests = fields.Integer(string='Total Requests', default=0, readonly=True)
    
    _sql_constraints = [
        ('unique_provider', 'UNIQUE(name)', 'Only one Gemini provider can exist!')
    ]
    
    @api.model
    def get_provider(self):
        """Lấy provider instance (singleton pattern)"""
        provider = self.search([], limit=1)
        if not provider:
            provider = self.create({
                'name': 'Google Gemini AI',
                'model_name': 'gemini-2.5-flash',
            })
        return provider

    @api.model
    def action_open_settings(self):
        """Mở đúng form của bản ghi singleton (tự tạo nếu chưa có).

        Dùng làm action cho menu "Gemini AI Settings" thay vì act_window
        tĩnh trỏ thẳng vào 'New' - tránh lỗi 'Only one Gemini provider can
        exist' khi người dùng vô tình bấm Save trên form trống.
        """
        provider = self.get_provider()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gemini AI Settings',
            'res_model': 'gemini.ai.provider',
            'view_mode': 'form',
            'res_id': provider.id,
            'target': 'current',
        }
    
    def _configure_gemini(self):
        """Configure Gemini API với API key"""
        if not GEMINI_AVAILABLE:
            raise UserError("Thư viện google-generativeai chưa được cài đặt. Vui lòng chạy: pip install google-generativeai")
        
        if not self.api_key:
            raise UserError("API Key chưa được cấu hình. Vui lòng vào Cấu hình > AI Settings để thêm API Key.")
        
        try:
            genai.configure(api_key=self.api_key)
            return genai.GenerativeModel(self.model_name)
        except Exception as e:
            _logger.error(f"Error configuring Gemini: {str(e)}")
            raise UserError(f"Lỗi khi cấu hình Gemini API: {str(e)}")
    
    def _update_usage_stats(self):
        """Cập nhật thống kê sử dụng"""
        self.write({
            'last_used': fields.Datetime.now(),
            'total_requests': self.total_requests + 1
        })
    
    @api.model
    def analyze_project_description(self, project):
        """
        Sử dụng Gemini để phân tích mô tả dự án và tìm risks tiềm ẩn
        
        Args:
            project: recordset của model projects
            
        Returns:
            list: Danh sách risks dưới dạng dict
        """
        provider = self.get_provider()
        
        if not provider.is_active:
            _logger.warning("Gemini AI provider is not active")
            return []
        
        if not project.description:
            return []
        
        try:
            model = provider._configure_gemini()
            
            prompt = f"""
Bạn là chuyên gia quản lý rủi ro dự án. Hãy phân tích thông tin dự án sau và xác định các rủi ro tiềm ẩn:

**Thông tin dự án:**
- Tên dự án: {project.projects_name}
- Mô tả: {project.description or 'Không có'}
- Ngày bắt đầu: {project.start_date or 'Chưa xác định'}
- Ngày kết thúc dự kiến: {project.actual_end_date or 'Chưa xác định'}
- Tiến độ hiện tại: {project.progress:.1f}%
- Số lượng công việc: {len(project.task_ids)}
- Ngân sách: {sum(project.budget_ids.mapped('budget_planned')) if project.budget_ids else 0:,.0f} VND

**Yêu cầu:**
Trả về JSON với cấu trúc sau (KHÔNG thêm markdown hoặc text khác):
{{
    "risks": [
        {{
            "type": "schedule" hoặc "budget" hoặc "resource" hoặc "quality" hoặc "scope",
            "name": "Tên rủi ro ngắn gọn (dưới 80 ký tự)",
            "description": "Mô tả chi tiết rủi ro",
            "probability": 0-100 (số nguyên),
            "impact": 1-10 (số thập phân),
            "root_cause": "Nguyên nhân gốc rễ",
            "mitigation_plan": "Kế hoạch khắc phục chi tiết",
            "confidence": 60-95 (độ tin cậy)
        }}
    ]
}}

Chỉ phân tích các rủi ro thực sự quan trọng (tối đa 3-5 rủi ro). Nếu không phát hiện rủi ro nào, trả về {{"risks": []}}.
"""
            
            _logger.info(f"Sending request to Gemini for project {project.projects_id}")
            response = model.generate_content(prompt)
            
            provider._update_usage_stats()
            
            # Parse response
            response_text = response.text.strip()
            
            # Remove markdown code blocks nếu có
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            risks = result.get('risks', [])
            
            _logger.info(f"Gemini analysis completed. Found {len(risks)} risks for project {project.projects_id}")
            
            return risks
            
        except json.JSONDecodeError as e:
            _logger.error(f"Failed to parse Gemini response: {str(e)}\nResponse: {response_text}")
            return []
        except Exception as e:
            _logger.error(f"Error in Gemini analysis: {str(e)}")
            return []
    
    @api.model
    def generate_mitigation_plan(self, risk_assessment):
        """
        Sử dụng Gemini để generate kế hoạch khắc phục chi tiết
        
        Args:
            risk_assessment: recordset của model risk.assessment
            
        Returns:
            str: Kế hoạch khắc phục chi tiết
        """
        provider = self.get_provider()
        
        if not provider.is_active:
            return risk_assessment.mitigation_plan  # Fallback to existing plan
        
        try:
            model = provider._configure_gemini()
            
            prompt = f"""
Bạn là chuyên gia quản lý rủi ro dự án. Hãy tạo kế hoạch khắc phục CHI TIẾT cho rủi ro sau:

**Thông tin rủi ro:**
- Tên: {risk_assessment.name}
- Loại: {dict(risk_assessment._fields['risk_type'].selection).get(risk_assessment.risk_type)}
- Mức độ: {dict(risk_assessment._fields['risk_level'].selection).get(risk_assessment.risk_level)}
- Xác suất: {risk_assessment.probability}%
- Tác động: {risk_assessment.impact_score}/10
- Điểm rủi ro: {risk_assessment.risk_score:.1f}
- Mô tả: {risk_assessment.description}
- Nguyên nhân: {risk_assessment.root_cause}

**Yêu cầu:**
Tạo kế hoạch khắc phục THỰC TẾ, CỤ THỂ với:
1. Hành động ngay lập tức (Quick wins - 1-2 ngày)
2. Giải pháp trung hạn (1-2 tuần)
3. Giải pháp dài hạn (phòng ngừa)
4. Người chịu trách nhiệm đề xuất
5. Metrics để đo lường hiệu quả

Format: Text markdown, có bullet points, dễ đọc, KHÔNG trả về JSON.
"""
            
            response = model.generate_content(prompt)
            provider._update_usage_stats()
            
            mitigation_plan = response.text.strip()
            
            _logger.info(f"Generated mitigation plan for risk {risk_assessment.id}")
            
            return mitigation_plan
            
        except Exception as e:
            _logger.error(f"Error generating mitigation plan: {str(e)}")
            return risk_assessment.mitigation_plan
    
    @api.model
    def analyze_root_cause(self, risk_assessment):
        """
        Sử dụng Gemini để phân tích nguyên nhân gốc rễ (Root Cause Analysis)
        
        Args:
            risk_assessment: recordset của model risk.assessment
            
        Returns:
            str: Phân tích nguyên nhân chi tiết
        """
        provider = self.get_provider()
        
        if not provider.is_active:
            return risk_assessment.root_cause
        
        try:
            model = provider._configure_gemini()
            
            project = risk_assessment.project_id
            
            prompt = f"""
Bạn là chuyên gia phân tích rủi ro. Sử dụng phương pháp 5 WHYs để phân tích nguyên nhân gốc rễ:

**Rủi ro:**
{risk_assessment.name}

**Thông tin dự án:**
- Tiến độ: {project.progress:.1f}%
- Số tasks: {len(project.task_ids)} ({len(project.task_ids.filtered(lambda t: t.trang_thai == 'hoan_thanh'))} hoàn thành)
- Budget spent: {sum(project.budget_ids.mapped('budget_spent')):,.0f} / {sum(project.budget_ids.mapped('budget_planned')):,.0f} VND
- Team size: {len(project.task_ids.mapped('nhan_vien_phan_cong_ids'))} người

**Mô tả rủi ro:**
{risk_assessment.description}

**Yêu cầu:**
1. Áp dụng 5 WHYs để tìm nguyên nhân gốc rễ
2. Xác định contributing factors (yếu tố đóng góp)
3. Đánh giá mức độ kiểm soát của từng nguyên nhân (controllable/uncontrollable)
4. Đề xuất prevention strategy

Format: Text markdown, có cấu trúc rõ ràng.
"""
            
            response = model.generate_content(prompt)
            provider._update_usage_stats()
            
            root_cause = response.text.strip()
            
            _logger.info(f"Generated root cause analysis for risk {risk_assessment.id}")
            
            return root_cause
            
        except Exception as e:
            _logger.error(f"Error in root cause analysis: {str(e)}")
            return risk_assessment.root_cause
    
    @api.model
    def comprehensive_project_analysis(self, project):
        """
        Phân tích toàn diện dự án bằng Gemini AI
        
        Returns:
            dict: {
                'risks': [...],
                'insights': str,
                'recommendations': str
            }
        """
        provider = self.get_provider()
        
        if not provider.is_active:
            return {'risks': [], 'insights': '', 'recommendations': ''}
        
        try:
            model = provider._configure_gemini()
            
            # Collect comprehensive data
            total_budget = sum(project.budget_ids.mapped('budget_planned'))
            total_spent = sum(project.budget_ids.mapped('budget_spent'))
            spent_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0
            
            tasks = project.task_ids
            completed_tasks = tasks.filtered(lambda t: t.trang_thai == 'hoan_thanh')
            delayed_tasks = tasks.filtered(lambda t: t.ngay_ket_thuc and t.ngay_ket_thuc < fields.Date.today() and t.trang_thai != 'hoan_thanh')
            
            prompt = f"""
Bạn là AI chuyên gia quản lý dự án. Phân tích TOÀN DIỆN dự án sau:

**DỮ LIỆU DỰ ÁN:**

Tổng quan:
- Tên: {project.projects_name}
- Trạng thái: {dict(project._fields['status'].selection).get(project.status)}
- Tiến độ: {project.progress:.1f}%
- Ngày bắt đầu: {project.start_date}
- Deadline: {project.actual_end_date}

Công việc:
- Tổng số: {len(tasks)}
- Hoàn thành: {len(completed_tasks)} ({len(completed_tasks)/len(tasks)*100 if tasks else 0:.1f}%)
- Trễ hạn: {len(delayed_tasks)} ({len(delayed_tasks)/len(tasks)*100 if tasks else 0:.1f}%)

Ngân sách:
- Kế hoạch: {total_budget:,.0f} VND
- Đã chi: {total_spent:,.0f} VND ({spent_percentage:.1f}%)
- Còn lại: {total_budget - total_spent:,.0f} VND

Team:
- Số người: {len(project.task_ids.mapped('nhan_vien_phan_cong_ids'))}

**YÊU CẦU PHÂN TÍCH:**
Trả về JSON với cấu trúc:
{{
    "risks": [
        {{
            "type": "schedule/budget/resource/quality/scope",
            "name": "Tên ngắn gọn",
            "description": "Mô tả",
            "probability": 0-100,
            "impact": 1-10,
            "root_cause": "Nguyên nhân",
            "mitigation_plan": "Giải pháp",
            "confidence": 70-95
        }}
    ],
    "insights": "Những phát hiện quan trọng về tình hình dự án (2-3 đoạn)",
    "recommendations": "Top 3-5 khuyến nghị ưu tiên để cải thiện dự án"
}}

QUAN TRỌNG: Chỉ trả về JSON thuần, KHÔNG thêm markdown hoặc text khác.
"""
            
            _logger.info(f"Sending comprehensive analysis request to Gemini for project {project.projects_id}")
            response = model.generate_content(prompt)
            
            provider._update_usage_stats()
            
            # Parse response
            response_text = response.text.strip()
            
            # Remove markdown
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            _logger.info(f"Comprehensive analysis completed for project {project.projects_id}")
            
            return result
            
        except Exception as e:
            _logger.error(f"Error in comprehensive analysis: {str(e)}")
            return {'risks': [], 'insights': '', 'recommendations': ''}
    
    @api.model
    def generate_project_summary(self, project):
        """
        Sinh tóm tắt tình hình dự án bằng ngôn ngữ tự nhiên (feature AI #2), để đăng vào chatter.
        Trả về text markdown ngắn (không phải JSON). Luôn có fallback rule-based nếu chưa
        cấu hình API key hoặc Gemini lỗi, để tính năng vẫn hoạt động được không cần AI.
        """
        provider = self.get_provider()

        tasks = project.task_ids
        completed = tasks.filtered(lambda t: t.trang_thai == 'hoan_thanh')
        delayed = tasks.filtered(lambda t: t.trang_thai == 'tam_dung' or (
            t.ngay_ket_thuc and t.ngay_ket_thuc < fields.Date.today() and t.trang_thai != 'hoan_thanh'
        ))
        total_budget = sum(project.budget_ids.mapped('budget_planned'))
        total_spent = sum(project.budget_ids.mapped('budget_spent'))

        # Lấy SPI/CPI mới nhất đã ghi nhận (nếu có), để tóm tắt bám sát chỉ số PM chuẩn
        RiskMetric = self.env['risk.metric']
        spi_rec = RiskMetric.search([('project_id', '=', project.id), ('metric_type', '=', 'spi')],
                                     order='date desc', limit=1)
        cpi_rec = RiskMetric.search([('project_id', '=', project.id), ('metric_type', '=', 'cpi')],
                                     order='date desc', limit=1)
        spi_text = f"{spi_rec.value:.2f}" if spi_rec else "chưa có dữ liệu"
        cpi_text = f"{cpi_rec.value:.2f}" if cpi_rec else "chưa có dữ liệu"
        open_risks = project.risk_assessment_ids.filtered(lambda r: r.status not in ('resolved', 'accepted'))

        # Fallback không dùng AI - tính sẵn để dùng khi chưa cấu hình key hoặc Gemini lỗi
        fallback_text = (
            f"Dự án {project.projects_name} đang ở tiến độ {project.progress:.1f}% "
            f"({len(completed)}/{len(tasks)} công việc hoàn thành, {len(delayed)} công việc trễ/tạm dừng). "
            f"Ngân sách đã chi {total_spent:,.0f}/{total_budget:,.0f} VND. "
            f"SPI: {spi_text}, CPI: {cpi_text}. "
            f"Hiện có {len(open_risks)} rủi ro đang mở cần theo dõi."
        )

        if not provider.is_active or not provider.api_key:
            return fallback_text

        try:
            model = provider._configure_gemini()
            prompt = f"""
Bạn là trợ lý quản lý dự án. Viết TÓM TẮT TÌNH HÌNH DỰ ÁN ngắn gọn (3-4 đoạn văn, không
bullet, không JSON) dựa CHÍNH XÁC trên số liệu dưới đây, không suy đoán thêm:

**Dự án:** {project.projects_name} ({project.projects_id})
- Trạng thái: {dict(project._fields['status'].selection).get(project.status)}
- Tiến độ: {project.progress:.1f}%
- Công việc: {len(tasks)} tổng, {len(completed)} hoàn thành, {len(delayed)} trễ/tạm dừng
- Ngân sách: đã chi {total_spent:,.0f} / {total_budget:,.0f} VND
- SPI hiện tại: {spi_text}
- CPI hiện tại: {cpi_text}
- Số rủi ro đang mở: {len(open_risks)}

Giọng văn chuyên nghiệp, tiếng Việt, gửi cho quản lý đọc nhanh trên hệ thống. Đoạn cuối
nêu 1-2 khuyến nghị ngắn nếu SPI/CPI < 0.9, ngân sách vượt, hoặc nhiều rủi ro đang mở;
nếu mọi thứ ổn thì ghi nhận tích cực, không bịa vấn đề.
"""
            response = model.generate_content(prompt)
            provider._update_usage_stats()
            return response.text.strip()
        except Exception as e:
            _logger.error(f"Error generating project summary: {str(e)}")
            return fallback_text

    @api.model
    def suggest_task_assignee(self, task, candidates_data):
        """
        Viết lời giải thích ngắn cho gợi ý phân công nhân viên (feature AI #3), dựa trên
        danh sách ứng viên ĐÃ được xếp hạng sẵn bằng rule-based (workload/hiệu suất) truyền vào.
        Trả về '' nếu AI không khả dụng - hàm gọi sẽ tự dùng kết quả rule-based thuần túy.
        """
        provider = self.get_provider()
        if not provider.is_active or not provider.api_key or not candidates_data:
            return ''

        try:
            model = provider._configure_gemini()
            danh_sach = "\n".join([
                f"- {c['ten']}: đang có {c['workload']} nhiệm vụ active, "
                f"điểm hiệu suất trung bình {c['diem_hieu_suat']:.1f}/4"
                for c in candidates_data
            ])
            prompt = f"""
Có 1 nhiệm vụ mới cần phân công:
- Tên: {task.ten_nhiem_vu}
- Mô tả: {task.mo_ta or 'Không có'}

Ứng viên (đã xếp hạng theo workload thấp -> cao, hiệu suất cao -> thấp):
{danh_sach}

Viết 2-3 câu tiếng Việt giải thích vì sao ứng viên ĐẦU TIÊN phù hợp nhất, chỉ dựa trên
workload và hiệu suất đã cho, không bịa thêm tiêu chí không có trong dữ liệu.
"""
            response = model.generate_content(prompt)
            provider._update_usage_stats()
            return response.text.strip()
        except Exception as e:
            _logger.error(f"Error generating assignee suggestion: {str(e)}")
            return ''

    def action_test_connection(self):
        """Test Gemini API connection"""
        self.ensure_one()
        
        try:
            model = self._configure_gemini()
            response = model.generate_content("Hello! Just testing the connection. Reply with 'OK'.")
            
            if response and response.text:
                self._update_usage_stats()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Kết nối thành công!',
                        'message': f'Gemini API hoạt động bình thường. Response: {response.text[:100]}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi kết nối',
                    'message': f'Không thể kết nối Gemini API: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }