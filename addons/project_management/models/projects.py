from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class Projects(models.Model):
    _name = 'projects'
    _description = 'Quản lý dự án'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    projects_id = fields.Char("Mã dự án", required=True, copy=False, readonly=True, default='New')
    projects_name = fields.Char("Tên dự án")
    
    manager_name = fields.Many2one('nhan_vien', string="Quản lý dự án")

    start_date = fields.Date("Ngày bắt đầu")
    actual_end_date = fields.Date("Ngày kết thúc thực tế")

    progress = fields.Float(
        "Tiến độ (%)",
        compute='_compute_progress',
        inverse='_inverse_progress',
        store=True,
        help="Tiến độ dự án (0-100%). Có thể nhập tay, nhưng sẽ được tính lại khi danh sách công việc thay đổi."
    )
    status = fields.Selection(
        selection=[
            ('not_started', 'Chưa bắt đầu'),
            ('in_progress', 'Đang thực hiện'),
            ('completed', 'Hoàn thành'),
            ('delayed', 'Trì hoãn'),
            ('cancelled', 'Hủy bỏ')
        ], 
        string='Trạng thái', store=True
    )

    ly_do_1 = fields.Text(string="Lý do hủy bỏ", help="Lý do hủy bỏ công việc")

    task_ids = fields.One2many(
        'cong_viec', 
        'du_an_id', 
        string='Công việc',
        help='Danh sách công việc thuộc dự án này (field du_an_id được thêm bởi module project_management)'
    )

    # ============ TRƯỜNG XÉT DUYỆT DỰ ÁN ============
    approval_state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending', 'Chờ xét duyệt'),
        ('approved', 'Đã phê duyệt'),
        ('rejected', 'Từ chối')
    ], string='Trạng thái duyệt', default='draft', tracking=True)
    
    approver_id = fields.Many2one('nhan_vien', string='Người phê duyệt', readonly=True)
    approval_date = fields.Datetime(string='Ngày phê duyệt', readonly=True)
    approval_signature = fields.Binary(string='Chữ ký phê duyệt')
    rejection_reason = fields.Text(string='Lý do từ chối') 

    @api.depends('task_ids.trang_thai', 'task_ids.ti_le_hoan_thanh')
    def _compute_progress(self):
        """Tính tiến độ dự án từ công việc (cong_viec), đồng thời đồng bộ `status`
        theo % thực tế để tránh lệch pha (ví dụ progress=100% mà status vẫn
        'Chưa bắt đầu', hoặc progress=40% mà status đã 'Hoàn thành').

        Không tự động đổi khi status đang là 'delayed' (trì hoãn) hoặc 'cancelled'
        (hủy bỏ), vì 2 trạng thái này mang thông tin riêng (lịch trình/quyết định
        quản lý) không chỉ đơn thuần suy ra từ %.
        """
        for project in self:
            if project.task_ids:
                # Tính trung bình tỷ lệ hoàn thành của tất cả công việc
                total_progress = sum(project.task_ids.mapped('ti_le_hoan_thanh'))
                progress = total_progress / len(project.task_ids)
                project.progress = progress

                if project.status not in ('delayed', 'cancelled'):
                    if progress >= 100.0 and project.status != 'completed':
                        project.status = 'completed'
                    elif progress < 100.0 and progress > 0.0 and project.status in (False, 'not_started', 'completed'):
                        project.status = 'in_progress'
                    elif progress == 0.0 and project.status == 'completed':
                        # % tụt về 0 (ví dụ công việc con bị reset) nhưng vẫn đánh dấu hoàn thành
                        project.status = 'not_started'
            else:
                project.progress = 0.0

    def _inverse_progress(self):
        """Cho phép người dùng nhập/sửa trực tiếp tiến độ dự án trên form.

        Giá trị người dùng nhập sẽ được lưu lại.
        Khi danh sách công việc hoặc % hoàn thành công việc thay đổi,
        hàm compute vẫn sẽ tính lại để đồng bộ theo công việc.
        """
        # Không cần xử lý gì thêm, Odoo sẽ tự ghi giá trị `progress`
        # được người dùng nhập vào record.
        for project in self:
            project.progress = project.progress


    def name_get(self):
        result = []
        for record in self:
            name = f"{record.projects_id}"

            result.append((record.id, name))
        return result
    
    budget_ids = fields.One2many('budgets', inverse_name='projects_id', string="Ngân sách Dự án")

    # ============ FIELD TỔNG HỢP CHO DASHBOARD (mục 7) ============
    # One2many ngược từ risk.assessment, dùng để đếm/lọc rủi ro của dự án ngay trên dashboard
    risk_assessment_ids = fields.One2many(
        'risk.assessment', 'project_id', string='Rủi ro',
        help='Danh sách các rủi ro được AI phát hiện cho dự án này'
    )

    risk_count_dang_mo = fields.Integer(
        string='Số rủi ro đang mở',
        compute='_compute_dashboard_summary',
        store=True,
        help='Số lượng rủi ro chưa được xử lý (trạng thái khác resolved/dismissed)'
    )

    risk_level_cao_nhat = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('critical', 'Nghiêm trọng'),
        ('none', 'Không có rủi ro'),
    ], string='Mức rủi ro cao nhất', compute='_compute_dashboard_summary', store=True)

    tong_ngan_sach_du_toan = fields.Float(
        string='Tổng ngân sách dự toán',
        compute='_compute_dashboard_summary',
        store=True,
        help='Tổng budget_planned của tất cả ngân sách thuộc dự án'
    )

    tong_chi_phi_thuc_te = fields.Float(
        string='Tổng chi phí thực tế',
        compute='_compute_dashboard_summary',
        store=True,
        help='Tổng budget_spent của tất cả ngân sách thuộc dự án'
    )

    @api.depends(
        'risk_assessment_ids.status', 'risk_assessment_ids.risk_level',
        'budget_ids.budget_planned', 'budget_ids.budget_spent'
    )
    def _compute_dashboard_summary(self):
        """Tổng hợp các chỉ số nhanh cho dashboard: rủi ro đang mở, mức rủi ro cao nhất,
        và tổng ngân sách/chi phí. Tách riêng khỏi _compute_progress để không làm phình
        logic tính tiến độ hiện có."""
        muc_do_uu_tien = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        for record in self:
            risk_dang_mo = record.risk_assessment_ids.filtered(
                lambda r: r.status not in ('resolved', 'accepted')
            )
            record.risk_count_dang_mo = len(risk_dang_mo)

            if risk_dang_mo:
                # Lấy mức rủi ro nghiêm trọng nhất trong các rủi ro đang mở
                cao_nhat = max(risk_dang_mo, key=lambda r: muc_do_uu_tien.get(r.risk_level, 0))
                record.risk_level_cao_nhat = cao_nhat.risk_level
            else:
                record.risk_level_cao_nhat = 'none'

            record.tong_ngan_sach_du_toan = sum(record.budget_ids.mapped('budget_planned'))
            record.tong_chi_phi_thuc_te = sum(record.budget_ids.mapped('budget_spent'))

    @api.model
    def _get_next_project_code(self):
        """Lấy mã dự án tiếp theo chưa sử dụng trong database"""
        sequence = self.env['ir.sequence'].search([('code', '=', 'projects.code')], limit=1)
        if sequence:
            # Lấy số tiếp theo từ sequence
            next_number = sequence.number_next
            # Tạo mã dự án dự kiến
            prefix = sequence.prefix or 'DA'
            padding = sequence.padding or 5
            next_code = f"{prefix}{str(next_number).zfill(padding)}"
            
            # Kiểm tra xem mã này đã tồn tại trong database chưa
            while self.search([('projects_id', '=', next_code)], limit=1):
                next_number += 1
                next_code = f"{prefix}{str(next_number).zfill(padding)}"
            
            return next_code
        return 'DA00001'

    @api.model
    def default_get(self, fields_list):
        """Hiển thị preview mã dự án trong form KHÔNG tăng sequence"""
        res = super(Projects, self).default_get(fields_list)
        if 'projects_id' in fields_list:
            res['projects_id'] = self._get_next_project_code()
        return res

    @api.model
    def create(self, vals):
        """Tự động sinh mã dự án khi lưu và đồng bộ sequence"""
        if not vals.get('projects_id') or vals.get('projects_id') == 'New':
            # Lấy mã tiếp theo chưa sử dụng
            next_code = self._get_next_project_code()
            vals['projects_id'] = next_code
            
            # Đồng bộ sequence với số vừa sử dụng
            sequence = self.env['ir.sequence'].search([('code', '=', 'projects.code')], limit=1)
            if sequence:
                # Lấy số từ mã vừa tạo (bỏ prefix)
                used_number = int(next_code.replace(sequence.prefix or 'DA', ''))
                # Cập nhật sequence để số tiếp theo là used_number + 1
                if used_number >= sequence.number_next:
                    sequence.write({'number_next': used_number + 1})
        
        project = super(Projects, self).create(vals)
        
        # Tự động phát hiện rủi ro khi tạo dự án mới (chạy async để không block)
        project.with_delay()._auto_detect_risks() if hasattr(project, 'with_delay') else project._auto_detect_risks()
        
        return project
    
    def write(self, vals):
        """Tự động phát hiện lại rủi ro khi dự án có thay đổi quan trọng.

        Ngoài ra: chặn việc set tay status = 'completed' khi dự án còn công việc
        (task_ids) chưa hoàn tất thực tế, để tránh lệch pha status/progress
        (áp dụng cùng nguyên tắc với ValidationError trong cong_viec.py).
        """
        if vals.get('status') == 'completed':
            for project in self:
                if project.task_ids and project.progress < 100.0:
                    raise UserError(
                        "Không thể đánh dấu dự án '%s' là Hoàn thành vì vẫn còn "
                        "công việc chưa hoàn tất (tiến độ hiện tại: %.1f%%)."
                        % (project.projects_name, project.progress)
                    )

        result = super(Projects, self).write(vals)
        
        # Các field quan trọng trigger AI re-scan
        important_fields = {
            'progress', 'status', 'actual_end_date', 'start_date',
            'approval_state'
        }
        
        # Nếu có thay đổi về các field quan trọng, chạy lại AI
        if any(field in vals for field in important_fields):
            for project in self:
                _logger.info(f"Dự án {project.projects_id} có thay đổi quan trọng, chạy lại AI phát hiện rủi ro...")
                project._auto_detect_risks()
        
        return result

    def action_view_task_chart(self):
        """Xem biểu đồ công việc - sử dụng cong_viec"""
        self.ensure_one()  # Đảm bảo phương thức chỉ xử lý một bản ghi
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biểu Đồ Công Việc',
            'res_model': 'cong_viec',
            'view_mode': 'graph',
            'domain': [('du_an_id', '=', self.id)],  # Lọc công việc theo dự án hiện tại
            'context': {'search_default_group_by_du_an_id': self.id},
            'target': 'current',
        }

    # ============ CÁC PHƯƠNG THỨC XÉT DUYỆT ============
    def action_submit_approval(self):
        """Gửi dự án đi xét duyệt"""
        for record in self:
            if not record.manager_name:
                raise UserError('Vui lòng chọn Quản lý dự án trước khi gửi xét duyệt!')
            record.approval_state = 'pending'

    def action_approve(self):
        """Phê duyệt dự án - yêu cầu có chữ ký"""
        for record in self:
            if not record.approval_signature:
                raise UserError('Vui lòng ký tên trước khi phê duyệt!')
            record.write({
                'approval_state': 'approved',
                'approver_id': record.manager_name.id,
                'approval_date': fields.Datetime.now(),
            })
            # Tự động tạo công việc cốt lõi khi phê duyệt
            record._create_core_tasks()

    def _create_core_tasks(self):
        """Tạo các công việc cốt lõi cho dự án đã được phê duyệt"""
        self.ensure_one()
        
        # Kiểm tra module quan_ly_cong_viec có được cài đặt
        try:
            CongViec = self.env['cong_viec']
        except KeyError:
            # Module chưa cài, bỏ qua
            _logger.warning(f"Module quan_ly_cong_viec chưa được cài đặt. Không thể tạo công việc tự động cho dự án {self.projects_id}")
            return
        
        # Kiểm tra manager_name (required field)
        if not self.manager_name:
            _logger.warning(f"Dự án {self.projects_id} không có quản lý dự án. Không thể tạo công việc tự động.")
            return  # Không có manager, không thể tạo công việc
        
        # Danh sách 5 công việc cốt lõi
        core_tasks = [
            {'ten': 'Khởi động dự án và thống nhất phạm vi', 'uu_tien': 'cao'},
            {'ten': 'Lên kế hoạch và phân bổ nguồn lực', 'uu_tien': 'cao'},
            {'ten': 'Kiểm tra chất lượng', 'uu_tien': 'trung_binh'},
            {'ten': 'Báo cáo định kỳ', 'uu_tien': 'trung_binh'},
            {'ten': 'Đóng gói và bàn giao', 'uu_tien': 'cao'},
        ]
        
        # Tạo công việc với error handling
        created_count = 0
        created_tasks = []
        for task in core_tasks:
            try:
                new_task = CongViec.create({
                    'ten_cong_viec': task['ten'],
                    'du_an_id': self.id,
                    'muc_do_uu_tien': task['uu_tien'],
                    'trang_thai': 'moi',
                    'nguoi_phu_trach_id': self.manager_name.id,
                    'ngay_bat_dau': self.start_date,
                    'ngay_ket_thuc': self.actual_end_date,
                })
                created_tasks.append(new_task)
                created_count += 1
            except Exception as e:
                # Log lỗi nhưng không dừng quá trình
                _logger.error(f"Lỗi khi tạo công việc '{task['ten']}' cho dự án {self.projects_id}: {str(e)}")
        


    def action_reject(self):
        """Từ chối dự án"""
        for record in self:
            if not record.rejection_reason:
                raise UserError('Vui lòng nhập lý do từ chối!')
            record.approval_state = 'rejected'

    def action_reset_draft(self):
        """Đặt lại trạng thái nháp"""
        for record in self:
            record.write({
                'approval_state': 'draft',
                'approval_signature': False,
                'approver_id': False,
                'approval_date': False,
                'rejection_reason': False,
            })

    def action_print_approval_pdf(self):
        """In báo cáo phê duyệt dự án dạng PDF"""
        self.ensure_one()
        if self.approval_state != 'approved':
            raise UserError('Chỉ có thể in báo cáo cho dự án đã được phê duyệt!')
        return self.env.ref('project_management.action_report_project_approval').report_action(self)
    
    def _auto_detect_risks(self):
        """Tự động phát hiện rủi ro cho dự án (gọi AI engine)"""
        self.ensure_one()
        
        try:
            # Lấy AI engine
            RiskAIEngine = self.env['risk.ai.engine']
            RiskAssessment = self.env['risk.assessment']

            # Ghi lại chỉ số SPI/CPI tại thời điểm hiện tại (giữ lịch sử để vẽ biểu đồ xu hướng).
            # Chạy trước mọi nhánh, kể cả khi dự án đã hoàn thành/hủy, để có điểm dữ liệu cuối cùng.
            RiskAIEngine.compute_and_log_metrics(self)
            
            # Nếu dự án đã hoàn thành hoặc bị hủy, tự động resolve tất cả rủi ro AI
            if self.status in ['completed', 'cancelled'] or self.progress >= 100:
                ai_risks = RiskAssessment.search([
                    ('project_id', '=', self.id),
                    ('is_ai_detected', '=', True),
                    ('status', 'not in', ['resolved', 'accepted'])
                ])
                if ai_risks:
                    ai_risks.write({
                        'status': 'resolved',
                        'resolved_date': fields.Datetime.now()
                    })
                    _logger.info(f"Dự án {self.projects_id} đã hoàn thành. Đã resolve {len(ai_risks)} rủi ro AI.")
                return  # Không phát hiện rủi ro mới
            
            # Xóa các rủi ro cũ đã được AI phát hiện để tránh duplicate
            # Chỉ xóa rủi ro chưa được xử lý (identified, analyzing)
            old_ai_risks = RiskAssessment.search([
                ('project_id', '=', self.id),
                ('is_ai_detected', '=', True),
                ('status', 'in', ['identified', 'analyzing'])
            ])
            if old_ai_risks:
                old_ai_risks.unlink()
                _logger.info(f"Đã xóa {len(old_ai_risks)} rủi ro AI cũ của dự án {self.projects_id}")
            
            # Phát hiện các loại rủi ro
            all_risks = []
            
            # 1. Rủi ro tiến độ
            schedule_risks = RiskAIEngine.detect_schedule_risk(self)
            all_risks.extend(schedule_risks)
            
            # 2. Rủi ro ngân sách
            budget_risks = RiskAIEngine.detect_budget_risk(self)
            all_risks.extend(budget_risks)
            
            # 3. Rủi ro nguồn lực
            resource_risks = RiskAIEngine.detect_resource_risk(self)
            all_risks.extend(resource_risks)

            # 4. Rủi ro cấp nhiệm vụ (chi tiết hơn, nhìn vào từng nhiệm vụ thay vì công việc)
            task_level_risks = RiskAIEngine.detect_task_level_risk(self)
            all_risks.extend(task_level_risks)
            
            # Nếu không có rủi ro nào được phát hiện, tạo một rủi ro mặc định cho dự án mới
            if not all_risks and not self.task_ids and not self.budget_ids:
                all_risks.append({
                    'name': 'Dự án mới thiếu thông tin',
                    'risk_type': 'scope',
                    'probability': 0.70,  # 70% = 0.70 trong Odoo
                    'impact_score': 6.0,
                    'description': f'Dự án "{self.projects_name}" vừa được tạo nhưng chưa có công việc và ngân sách. Cần bổ sung thông tin chi tiết.',
                    'root_cause': 'Dự án ở giai đoạn khởi tạo, chưa có kế hoạch chi tiết.',
                    'mitigation_plan': '1. Họp kickoff meeting\n2. Xác định scope và deliverables\n3. Lập danh sách công việc\n4. Phân bổ ngân sách\n5. Assign team members',
                    'ai_confidence': 0.85  # 85% = 0.85 trong Odoo
                })
            
            # Tạo bản ghi risk assessment cho mỗi rủi ro phát hiện
            created_risks = []
            for risk_data in all_risks:
                risk_data['project_id'] = self.id
                risk_data['is_ai_detected'] = True
                risk_data['status'] = 'identified'
                risk_data['assigned_to'] = self.manager_name.id if self.manager_name else False
                new_risk = RiskAssessment.create(risk_data)
                created_risks.append(new_risk)
            
            if created_risks:
                _logger.info(f"✓ AI đã phát hiện {len(created_risks)} rủi ro cho dự án {self.projects_id}")
                # Gửi notification cho user
                self.message_post(
                    body=f"AI đã tự động phát hiện {len(created_risks)} rủi ro tiềm ẩn. Vào menu 'AI Quản lý rủi ro' để xem chi tiết.",
                    subject="AI phát hiện rủi ro",
                    message_type='notification'
                )
            else:
                _logger.info(f"Không phát hiện rủi ro nào cho dự án {self.projects_id}")
            
        except Exception as e:
            # Không để lỗi AI làm gián đoạn việc tạo dự án
            _logger.warning(f"Không thể chạy AI phát hiện rủi ro cho dự án {self.projects_id}: {str(e)}", exc_info=True)
    
    def action_run_risk_detection(self):
        """Action button để chạy lại AI phát hiện rủi ro thủ công"""
        self.ensure_one()
        self._auto_detect_risks()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AI Phát hiện rủi ro',
                'message': 'Đã quét xong! Kiểm tra menu "AI Quản lý rủi ro" để xem kết quả.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_ai_tom_tat_bao_cao(self):
        """AI tóm tắt tình hình dự án, đăng thẳng vào chatter (feature AI #2)."""
        self.ensure_one()
        try:
            summary = self.env['gemini.ai.provider'].generate_project_summary(self)
        except Exception as e:
            _logger.error(f"Lỗi khi tạo tóm tắt AI cho dự án {self.projects_id}: {str(e)}")
            summary = False

        if not summary:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Không thể tạo tóm tắt',
                    'message': 'Không tạo được tóm tắt, vui lòng thử lại sau.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        self.message_post(body=summary, subject='Tóm tắt tình hình dự án (AI)')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Đã đăng tóm tắt',
                'message': 'Xem chi tiết trong phần trao đổi (chatter) bên dưới form.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _cron_ai_tom_tat_bao_cao_hang_tuan(self):
        """Cron hàng tuần: tự động đăng tóm tắt AI cho các dự án đang active."""
        for project in self.search([('status', 'in', ['in_progress', 'not_started'])]):
            try:
                project.action_ai_tom_tat_bao_cao()
            except Exception as e:
                _logger.error(f"Lỗi cron tóm tắt AI cho dự án {project.projects_id}: {str(e)}")

    def action_nhan_ban_du_an(self):
        """Nhân bản dự án thành 1 dự án mới "sạch": giữ lại cấu trúc công việc/nhiệm vụ
        (tên, mô tả, giờ dự kiến, mức độ ưu tiên, phụ thuộc giữa nhiệm vụ), nhưng KHÔNG
        copy: tiến độ, người phụ trách/thực hiện, ngày bắt đầu/kết thúc thực tế, trạng thái
        phê duyệt, rủi ro, ngân sách đã chi.

        Hữu ích khi dự án mới có cấu trúc công việc giống dự án cũ (ví dụ chạy lại 1 quy
        trình định kỳ), tránh phải tạo lại từ đầu thủ công.
        """
        self.ensure_one()

        # 1) Tạo dự án mới - mã tự sinh (để trống 'New' để create() tự xử lý đúng sequence)
        du_an_moi = self.create({
            'projects_id': 'New',
            'projects_name': f"{self.projects_name} (Bản sao)",
            'status': 'not_started',
            'approval_state': 'draft',
            # Không copy: start_date, actual_end_date, manager_name (để người tạo tự điền lại
            # cho phù hợp với lần chạy mới, tránh nhầm lẫn với ngày của dự án gốc)
        })

        # 2) Copy từng công việc, giữ map {id công việc cũ -> record công việc mới}
        # để sau đó copy nhiệm vụ đúng vào công việc tương ứng.
        map_cong_viec_cu_moi = {}
        for cv_cu in self.task_ids:
            cv_moi = self.env['cong_viec'].create({
                'ma_cong_viec': 'Mới',
                'ten_cong_viec': cv_cu.ten_cong_viec,
                'mo_ta': cv_cu.mo_ta,
                'muc_do_uu_tien': cv_cu.muc_do_uu_tien,
                'trang_thai': 'moi',
                'gio_lam_du_kien': cv_cu.gio_lam_du_kien,
                'du_an_id': du_an_moi.id,
                # nguoi_phu_trach_id là field BẮT BUỘC trên cong_viec, nên phải giữ lại
                # giá trị cũ (dù lý tưởng là để trống cho dự án "sạch") - người dùng có
                # thể tự đổi lại sau khi nhân bản.
                'nguoi_phu_trach_id': cv_cu.nguoi_phu_trach_id.id,
                # Không copy: ngay_bat_dau, ngay_ket_thuc, ti_le_hoan_thanh, gio_lam_thuc_te
                # (đều là dữ liệu thực thi của lần chạy cũ). nguoi_phu_trach_id PHẢI giữ lại
                # vì là field bắt buộc của model cong_viec.
            })
            map_cong_viec_cu_moi[cv_cu.id] = cv_moi

        # 3) Copy nhiệm vụ thuộc các công việc trên, giữ map tương tự để xử lý dependency
        map_nhiem_vu_cu_moi = {}
        for cv_cu in self.task_ids:
            cv_moi = map_cong_viec_cu_moi[cv_cu.id]
            for nv_cu in cv_cu.nhiem_vu_ids:
                nv_moi = self.env['nhiem_vu'].create({
                    'ma_nhiem_vu': 'Mới',
                    'ten_nhiem_vu': nv_cu.ten_nhiem_vu,
                    'mo_ta': nv_cu.mo_ta,
                    'cong_viec_id': cv_moi.id,
                    # nguoi_thuc_hien_id là field BẮT BUỘC của model nhiem_vu, nên phải giữ
                    # lại giá trị cũ, cùng lý do với nguoi_phu_trach_id ở công việc.
                    'nguoi_thuc_hien_id': nv_cu.nguoi_thuc_hien_id.id,
                    # Không copy: ngay_bat_dau, ngay_ket_thuc, ngay_hoan_thanh_thuc_te,
                    # nguoi_giao_viec_id, ti_le_hoan_thanh, danh_gia, nhan_xet (dữ liệu
                    # thực thi của lần chạy cũ). trang_thai/ti_le_hoan_thanh giữ default.
                })
                map_nhiem_vu_cu_moi[nv_cu.id] = nv_moi

        # 4) Khôi phục lại quan hệ phụ thuộc giữa nhiệm vụ (mục 4) trên các nhiệm vụ MỚI,
        # tương ứng 1-1 với quan hệ phụ thuộc của các nhiệm vụ CŨ.
        for nv_cu_id, nv_moi in map_nhiem_vu_cu_moi.items():
            nv_cu = self.env['nhiem_vu'].browse(nv_cu_id)
            tien_de_moi_ids = [
                map_nhiem_vu_cu_moi[tien_de.id].id
                for tien_de in nv_cu.nhiem_vu_truoc_ids
                if tien_de.id in map_nhiem_vu_cu_moi
            ]
            if tien_de_moi_ids:
                nv_moi.write({'nhiem_vu_truoc_ids': [(6, 0, tien_de_moi_ids)]})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Dự án nhân bản',
            'res_model': 'projects',
            'view_mode': 'form',
            'res_id': du_an_moi.id,
            'target': 'current',
        }