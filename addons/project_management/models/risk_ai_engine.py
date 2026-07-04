# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class RiskAIEngine(models.Model):
    """Engine AI phát hiện và phân tích rủi ro dự án"""
    _name = 'risk.ai.engine'
    _description = 'AI Engine cho phát hiện rủi ro'
    
    @api.model
    def detect_schedule_risk(self, project):
        """
        Phát hiện rủi ro tiến độ dựa trên:
        - Công việc delay
        - Tỷ lệ hoàn thành thấp
        - Ngày kết thúc gần kề
        """
        risks = []
        
        if not project.task_ids:
            return risks
        
        # Tính số công việc delay
        today = fields.Date.today()
        delayed_tasks = project.task_ids.filtered(
            lambda t: t.ngay_ket_thuc and t.ngay_ket_thuc < today and t.trang_thai != 'hoan_thanh'
        )
        
        delayed_count = len(delayed_tasks)
        total_tasks = len(project.task_ids)
        delayed_percentage = (delayed_count / total_tasks * 100) if total_tasks > 0 else 0
        
        # Rule 1: Nhiều công việc delay
        if delayed_percentage > 30:
            probability = min(delayed_percentage / 100.0, 1.0)  # Chuyển sang 0.0-1.0
            impact = 8.0 if delayed_percentage > 50 else 6.0
            
            description = f"Phát hiện {delayed_count}/{total_tasks} công việc ({delayed_percentage:.1f}%) bị trễ hạn."
            root_cause = "Nguyên nhân có thể do:\n"
            root_cause += "- Ước lượng thời gian không chính xác\n"
            root_cause += "- Thiếu nguồn lực hoặc nhân viên overload\n"
            root_cause += "- Các vấn đề kỹ thuật phát sinh\n"
            root_cause += "- Dependency giữa các task bị chậm"
            
            mitigation = "Đề xuất khắc phục:\n"
            mitigation += "✓ Review lại timeline và ưu tiên công việc quan trọng\n"
            mitigation += "✓ Bổ sung nguồn lực cho các task critical\n"
            mitigation += "✓ Tổ chức daily standup để theo dõi sát sao\n"
            mitigation += "✓ Cân nhắc extend deadline hoặc giảm scope"
            
            risks.append({
                'name': f'Rủi ro tiến độ: {delayed_percentage:.0f}% công việc trễ hạn',
                'risk_type': 'schedule',
                'probability': probability,
                'impact_score': impact,
                'description': description,
                'root_cause': root_cause,
                'mitigation_plan': mitigation,
                'ai_confidence': 0.85  # 85% = 0.85
            })
        
        # Rule 2: Tiến độ thấp khi sắp hết thời gian
        if project.actual_end_date:
            days_remaining = (project.actual_end_date - today).days
            if 0 < days_remaining <= 30 and project.progress < 70:
                probability = 0.90  # 90% = 0.90
                impact = 9.0
                
                description = f"Dự án còn {days_remaining} ngày nhưng chỉ hoàn thành {project.progress:.1f}%."
                root_cause = "Tốc độ thực hiện quá chậm so với kế hoạch. Nguy cơ cao không hoàn thành đúng hạn."
                mitigation = "Hành động khẩn cấp:\n"
                mitigation += "✓ Tập trung 100% team vào các task còn lại\n"
                mitigation += "✓ Cut scope: Loại bỏ features không cần thiết\n"
                mitigation += "✓ Làm thêm giờ hoặc thuê thêm freelancer\n"
                mitigation += "✓ Thông báo stakeholder về khả năng delay"
                
                risks.append({
                    'name': f'Nguy cơ cao trễ deadline ({days_remaining} ngày)',
                    'risk_type': 'schedule',
                    'probability': probability,
                    'impact_score': impact,
                    'description': description,
                    'root_cause': root_cause,
                    'mitigation_plan': mitigation,
                    'ai_confidence': 0.90  # 90% = 0.90
                })
        
        return risks
    
    @api.model
    def detect_budget_risk(self, project):
        """
        Phát hiện rủi ro ngân sách dựa trên:
        - Chi phí vượt budget
        - Tốc độ chi tiêu nhanh hơn tiến độ
        """
        risks = []
        
        if not project.budget_ids:
            return risks
        
        total_budget = sum(project.budget_ids.mapped('budget_planned'))
        total_spent = sum(project.budget_ids.mapped('budget_spent'))
        
        if total_budget <= 0:
            return risks
        
        spent_percentage = (total_spent / total_budget) * 100
        progress_percentage = project.progress
        
        # Rule 1: Chi tiêu vượt ngân sách
        if spent_percentage > 100:
            overrun = total_spent - total_budget
            probability = 100.0
            impact = 10.0
            
            description = f"Đã chi {total_spent:,.0f} VND, vượt ngân sách {overrun:,.0f} VND ({spent_percentage:.1f}%)."
            root_cause = "Ngân sách đã bị vượt:\n"
            root_cause += "- Ước lượng chi phí ban đầu không chính xác\n"
            root_cause += "- Phát sinh chi phí ngoài dự kiến\n"
            root_cause += "- Thiếu kiểm soát chi tiêu"
            
            mitigation = "Khắc phục ngay:\n"
            mitigation += "✓ DỪNG mọi chi tiêu không cần thiết\n"
            mitigation += "✓ Review lại tất cả expenses và cắt giảm\n"
            mitigation += "✓ Xin bổ sung ngân sách hoặc điều chỉnh scope\n"
            mitigation += "✓ Thiết lập approval process chặt chẽ hơn"
            
            risks.append({
                'name': f'Vượt ngân sách {spent_percentage - 100:.1f}%',
                'risk_type': 'budget',
                'probability': probability,
                'impact_score': impact,
                'description': description,
                'root_cause': root_cause,
                'mitigation_plan': mitigation,
                'ai_confidence': 95.0
            })
        
        # Rule 2: Chi tiêu nhanh hơn tiến độ (Burn rate cao)
        elif spent_percentage > progress_percentage + 20:
            probability = 0.80  # 80% = 0.80
            impact = 7.0
            
            description = f"Đã chi {spent_percentage:.1f}% ngân sách nhưng chỉ hoàn thành {progress_percentage:.1f}% công việc."
            root_cause = "Chi tiêu nhanh hơn tiến độ:\n"
            root_cause += "- Front-loading expenses (chi nhiều ở giai đoạn đầu)\n"
            root_cause += "- Năng suất làm việc thấp\n"
            root_cause += "- Chi phí cố định cao"
            
            mitigation = "Hành động:\n"
            mitigation += "✓ Phân tích chi tiết từng khoản chi\n"
            mitigation += "✓ Tối ưu hóa chi phí, loại bỏ waste\n"
            mitigation += "✓ Dự báo budget cuối kỳ (EAC)\n"
            mitigation += "✓ Tăng tốc độ hoàn thành công việc"
            
            risks.append({
                'name': f'Burn rate cao: Chi {spent_percentage:.0f}% vs Tiến độ {progress_percentage:.0f}%',
                'risk_type': 'budget',
                'probability': probability,
                'impact_score': impact,
                'description': description,
                'root_cause': root_cause,
                'mitigation_plan': mitigation,
                'ai_confidence': 0.80  # 80% = 0.80
            })
        
        # Rule 3: Sắp hết ngân sách
        elif spent_percentage > 80:
            probability = 0.70  # 70% = 0.70
            impact = 6.0
            
            remaining = total_budget - total_spent
            description = f"Đã sử dụng {spent_percentage:.1f}% ngân sách, còn lại {remaining:,.0f} VND."
            mitigation = "Cảnh báo:\n"
            mitigation += "✓ Theo dõi sát sao mọi chi tiêu\n"
            mitigation += "✓ Chuẩn bị kế hoạch dự phòng\n"
            mitigation += "✓ Đàm phán với nhà cung cấp để giảm cost"
            
            risks.append({
                'name': f'Cảnh báo: Sắp hết ngân sách ({spent_percentage:.0f}%)',
                'risk_type': 'budget',
                'probability': probability,
                'impact_score': impact,
                'description': description,
                'root_cause': 'Ngân sách sắp cạn kiệt',
                'mitigation_plan': mitigation,
                'ai_confidence': 0.75  # 75% = 0.75
            })
        
        return risks
    
    @api.model
    def detect_resource_risk(self, project):
        """
        Phát hiện rủi ro nguồn lực dựa trên:
        - Nhân viên overload
        - Phân bổ không đều
        """
        risks = []
        
        if not project.task_ids:
            return risks
        
        # Phân tích workload của từng nhân viên
        workload_data = {}
        for task in project.task_ids.filtered(lambda t: t.trang_thai in ['moi', 'dang_thuc_hien']):
            for employee in task.nhan_vien_phan_cong_ids:
                if employee not in workload_data:
                    workload_data[employee] = []
                workload_data[employee].append(task)
        
        # Tìm nhân viên overload (>5 tasks đang active)
        overloaded = []
        for employee, tasks in workload_data.items():
            if len(tasks) > 5:
                overloaded.append((employee, len(tasks)))
        
        if overloaded:
            probability = min(len(overloaded) * 20 + 40, 95) / 100.0  # Chuyển sang 0.0-1.0
            impact = 7.0
            
            overload_list = "\n".join([f"- {emp.ten_nv}: {count} công việc" for emp, count in overloaded])
            description = f"Phát hiện {len(overloaded)} nhân viên bị overload:\n{overload_list}"
            
            root_cause = "Phân bổ công việc không hợp lý:\n"
            root_cause += "- Một số nhân viên nhận quá nhiều task\n"
            root_cause += "- Thiếu resource planning\n"
            root_cause += "- Key persons bị phụ thuộc quá nhiều"
            
            mitigation = "Giải pháp:\n"
            mitigation += "✓ Cân bằng lại workload giữa các thành viên\n"
            mitigation += "✓ Reassign tasks từ người overload sang người rảnh\n"
            mitigation += "✓ Bổ sung thêm nhân sự nếu cần\n"
            mitigation += "✓ Ưu tiên task theo mức độ quan trọng"
            
            risks.append({
                'name': f'Rủi ro nguồn lực: {len(overloaded)} nhân viên overload',
                'risk_type': 'resource',
                'probability': probability,
                'impact_score': impact,
                'description': description,
                'root_cause': root_cause,
                'mitigation_plan': mitigation,
                'ai_confidence': 0.85  # 85% = 0.85
            })
        
        return risks

    @api.model
    def detect_task_level_risk(self, project):
        """
        Phát hiện rủi ro ở cấp NHIỆM VỤ (granularity nhỏ hơn detect_resource_risk,
        vốn chỉ nhìn ở cấp công việc/nhân viên tổng thể).

        Hai tình huống được phát hiện:
        1. Một nhân viên có >= 2 nhiệm vụ đang 'qua_han' cùng lúc trong dự án này
           -> rủi ro nguồn lực ở cấp độ cá nhân (khác overload tổng thể của
           detect_resource_risk, vì có thể số lượng nhiệm vụ không nhiều nhưng đều trễ).
        2. Một nhiệm vụ đã có tiến độ (chưa hoàn thành) nhưng KHÔNG được cập nhật tiến độ
           mới trong N ngày gần nhất -> rủi ro "đứng yên", có thể bị bỏ quên.
        """
        risks = []

        if not project.task_ids:
            return risks

        # Lấy toàn bộ nhiệm vụ chưa hoàn thành thuộc các công việc của dự án
        tat_ca_nhiem_vu = project.task_ids.mapped('nhiem_vu_ids').filtered(
            lambda nv: nv.trang_thai != 'hoan_thanh'
        )
        if not tat_ca_nhiem_vu:
            return risks

        # ---------- TÌNH HUỐNG 1: nhân viên có nhiều nhiệm vụ trễ liên tiếp ----------
        nhiem_vu_qua_han = tat_ca_nhiem_vu.filtered(lambda nv: nv.trang_thai == 'qua_han')
        nhan_vien_qua_han = {}
        for nv in nhiem_vu_qua_han:
            if nv.nguoi_thuc_hien_id:
                nhan_vien_qua_han.setdefault(nv.nguoi_thuc_hien_id, []).append(nv)

        nhan_vien_co_van_de = {emp: nvs for emp, nvs in nhan_vien_qua_han.items() if len(nvs) >= 2}
        if nhan_vien_co_van_de:
            probability = min(len(nhan_vien_co_van_de) * 25 + 35, 90) / 100.0
            impact = 6.0

            chi_tiet = "\n".join([
                f"- {emp.ho_ten}: {len(nvs)} nhiệm vụ quá hạn ({', '.join(n.ten_nhiem_vu for n in nvs)})"
                for emp, nvs in nhan_vien_co_van_de.items()
            ])
            description = (
                f"Phát hiện {len(nhan_vien_co_van_de)} nhân viên có từ 2 nhiệm vụ quá hạn "
                f"trở lên trong dự án:\n{chi_tiet}"
            )
            root_cause = (
                "Có thể do:\n"
                "- Nhân viên đang gặp khó khăn với nhiều nhiệm vụ cùng lúc\n"
                "- Nhiệm vụ được giao không phù hợp với năng lực/thời gian thực tế\n"
                "- Thiếu theo dõi tiến độ ở cấp nhiệm vụ chi tiết"
            )
            mitigation = (
                "Giải pháp:\n"
                "✓ Trao đổi trực tiếp với nhân viên để tìm nguyên nhân cụ thể\n"
                "✓ Xem xét điều chỉnh deadline hoặc phân lại nhiệm vụ cho người khác\n"
                "✓ Ưu tiên hỗ trợ hoàn thành các nhiệm vụ quá hạn lâu nhất trước"
            )

            risks.append({
                'name': f'Rủi ro cấp nhiệm vụ: {len(nhan_vien_co_van_de)} nhân viên có nhiệm vụ trễ liên tiếp',
                'risk_type': 'resource',
                'probability': probability,
                'impact_score': impact,
                'description': description,
                'root_cause': root_cause,
                'mitigation_plan': mitigation,
                'ai_confidence': 0.8
            })

        # ---------- TÌNH HUỐNG 2: nhiệm vụ "đứng yên" quá lâu ----------
        SO_NGAY_NGUONG = 7
        hom_nay = fields.Date.today()
        nhiem_vu_dung_yen = []
        for nv in tat_ca_nhiem_vu:
            if not nv.tien_do_ids:
                continue  # Chưa từng cập nhật tiến độ -> không tính vào trường hợp này
            ngay_cap_nhat_gan_nhat = max(
                nv.tien_do_ids.mapped(lambda t: t.ngay_cap_nhat.date() if t.ngay_cap_nhat else hom_nay)
            )
            so_ngay_im_lang = (hom_nay - ngay_cap_nhat_gan_nhat).days
            if so_ngay_im_lang >= SO_NGAY_NGUONG:
                nhiem_vu_dung_yen.append((nv, so_ngay_im_lang))

        if nhiem_vu_dung_yen:
            probability = min(len(nhiem_vu_dung_yen) * 15 + 30, 85) / 100.0
            impact = 5.0

            chi_tiet = "\n".join([
                f"- {nv.ten_nhiem_vu} ({nv.nguoi_thuc_hien_id.ho_ten if nv.nguoi_thuc_hien_id else 'chưa gán'}): "
                f"{so_ngay} ngày không cập nhật"
                for nv, so_ngay in nhiem_vu_dung_yen
            ])
            description = (
                f"Phát hiện {len(nhiem_vu_dung_yen)} nhiệm vụ chưa hoàn thành nhưng không có "
                f"cập nhật tiến độ mới trong ít nhất {SO_NGAY_NGUONG} ngày:\n{chi_tiet}"
            )
            root_cause = (
                "Có thể do:\n"
                "- Nhiệm vụ bị bỏ quên hoặc không còn được ưu tiên\n"
                "- Nhân viên gặp khó khăn nhưng chưa báo cáo\n"
                "- Thiếu quy trình nhắc nhở cập nhật tiến độ định kỳ"
            )
            mitigation = (
                "Giải pháp:\n"
                "✓ Liên hệ người thực hiện để cập nhật tình hình thực tế\n"
                "✓ Xác nhận nhiệm vụ còn cần thiết hay nên huỷ/gộp\n"
                "✓ Thiết lập nhắc nhở định kỳ để tránh nhiệm vụ bị bỏ quên"
            )

            risks.append({
                'name': f'Rủi ro cấp nhiệm vụ: {len(nhiem_vu_dung_yen)} nhiệm vụ đứng yên quá lâu',
                'risk_type': 'schedule',
                'probability': probability,
                'impact_score': impact,
                'description': description,
                'root_cause': root_cause,
                'mitigation_plan': mitigation,
                'ai_confidence': 0.75
            })

        return risks

    @api.model
    def compute_and_log_metrics(self, project):
        """
        Tính các chỉ số theo dõi rủi ro (SPI, CPI) cho dự án và ghi vào risk.metric.

        - SPI (Schedule Performance Index) = % tiến độ thực tế / % tiến độ kỳ vọng theo thời gian.
          SPI < 1: dự án đang trễ tiến độ. SPI > 1: dự án đang nhanh hơn kế hoạch.
        - CPI (Cost Performance Index) = (% tiến độ x ngân sách dự toán) / chi phí thực tế đã chi.
          CPI < 1: chi phí đang vượt giá trị công việc thực hiện được (lãng phí).
          CPI > 1: chi phí đang được sử dụng hiệu quả hơn kế hoạch.

        Mỗi lần gọi sẽ ghi thêm 1 bản ghi risk.metric mới cho mỗi chỉ số (giữ lịch sử theo thời gian
        để vẽ biểu đồ xu hướng), không sửa lại bản ghi cũ.
        """
        RiskMetric = self.env['risk.metric']
        today = fields.Date.today()
        created_metrics = []

        # ---------- TÍNH SPI ----------
        if project.start_date and project.actual_end_date:
            tong_so_ngay = (project.actual_end_date - project.start_date).days
            so_ngay_da_troi = (today - project.start_date).days

            if tong_so_ngay > 0:
                # % thời gian kỳ vọng đã trôi qua (không vượt quá 100%)
                ti_le_thoi_gian_ky_vong = max(min(so_ngay_da_troi / tong_so_ngay, 1.0), 0.0) * 100

                if ti_le_thoi_gian_ky_vong > 0:
                    spi = project.progress / ti_le_thoi_gian_ky_vong
                else:
                    # Dự án chưa đến ngày bắt đầu nhưng đã có tiến độ -> coi như đang vượt kế hoạch
                    spi = 1.0 if project.progress == 0 else 2.0

                metric = RiskMetric.create({
                    'project_id': project.id,
                    'metric_type': 'spi',
                    'value': spi,
                    'threshold_min': 0.9,  # Dưới 0.9: cảnh báo trễ tiến độ
                    'threshold_max': 0.0,  # Không giới hạn trên cho SPI
                    'date': today,
                    'notes': (
                        f"Tiến độ thực tế: {project.progress:.1f}%, "
                        f"tiến độ kỳ vọng theo thời gian: {ti_le_thoi_gian_ky_vong:.1f}%"
                    ),
                })
                created_metrics.append(metric)

        # ---------- TÍNH CPI ----------
        if project.budget_ids:
            total_budget = sum(project.budget_ids.mapped('budget_planned'))
            total_spent = sum(project.budget_ids.mapped('budget_spent'))

            if total_spent > 0 and total_budget > 0:
                # Giá trị công việc đã hoàn thành, quy theo ngân sách dự toán
                earned_value = (project.progress / 100.0) * total_budget
                cpi = earned_value / total_spent

                metric = RiskMetric.create({
                    'project_id': project.id,
                    'metric_type': 'cpi',
                    'value': cpi,
                    'threshold_min': 0.9,  # Dưới 0.9: cảnh báo chi phí kém hiệu quả
                    'threshold_max': 0.0,
                    'date': today,
                    'notes': (
                        f"Giá trị hoàn thành: {earned_value:,.0f} VND, "
                        f"chi phí thực tế: {total_spent:,.0f} VND"
                    ),
                })
                created_metrics.append(metric)

        return created_metrics

    @api.model
    def analyze_project_risks(self, project_id):
        """
        Phân tích tất cả các loại rủi ro cho một dự án
        Tích hợp với Gemini AI để phân tích nâng cao
        Trả về danh sách các rủi ro được phát hiện
        """
        project = self.env['projects'].browse(project_id)
        if not project.exists():
            return []

        all_risks = []

        # BƯỚC 0: Tính và ghi các chỉ số theo dõi (SPI, CPI) vào risk.metric
        self.compute_and_log_metrics(project)

        # BƯỚC 1: Phát hiện rủi ro bằng Rule-based AI
        _logger.info(f"[Rule-based AI] Analyzing project {project.projects_id}")
        all_risks.extend(self.detect_schedule_risk(project))
        all_risks.extend(self.detect_budget_risk(project))
        all_risks.extend(self.detect_resource_risk(project))
        all_risks.extend(self.detect_task_level_risk(project))
        
        # BƯỚC 2: Phân tích bổ sung bằng Gemini AI (nếu được kích hoạt)
        try:
            gemini = self.env['gemini.ai.provider'].get_provider()
            if gemini.is_active and gemini.api_key:
                _logger.info(f"[Gemini AI] Analyzing project {project.projects_id}")
                
                # Nếu dự án có mô tả, phân tích text-based risks
                if project.description:
                    gemini_risks = gemini.analyze_project_description(project)
                    if gemini_risks:
                        _logger.info(f"[Gemini AI] Found {len(gemini_risks)} additional risks from description")
                        all_risks.extend(gemini_risks)
                
                # Comprehensive analysis (tùy chọn - chỉ khi cần)
                # comprehensive_result = gemini.comprehensive_project_analysis(project)
                # if comprehensive_result.get('risks'):
                #     all_risks.extend(comprehensive_result['risks'])
        except Exception as e:
            _logger.warning(f"[Gemini AI] Not available or error: {str(e)}")
        
        # BƯỚC 3: Tạo hoặc cập nhật risk records
        RiskAssessment = self.env['risk.assessment']
        
        for risk_data in all_risks:
            risk_data['project_id'] = project.id
            risk_data['is_ai_detected'] = True
            risk_data['status'] = 'identified'
            
            # Kiểm tra xem rủi ro tương tự đã tồn tại chưa
            existing_risk = RiskAssessment.search([
                ('project_id', '=', project.id),
                ('risk_type', '=', risk_data['risk_type']),
                ('name', '=', risk_data['name']),
                ('status', 'in', ['identified', 'analyzing', 'mitigating'])
            ], limit=1)
            
            if existing_risk:
                # Cập nhật risk hiện có
                existing_risk.write({
                    'probability': risk_data['probability'],
                    'impact_score': risk_data['impact_score'],
                    'description': risk_data['description'],
                    'root_cause': risk_data['root_cause'],
                    'mitigation_plan': risk_data['mitigation_plan'],
                    'ai_confidence': risk_data['ai_confidence'],
                })
                _logger.info(f"Updated existing risk: {risk_data['name']}")
            else:
                # Tạo mới risk
                RiskAssessment.create(risk_data)
                _logger.info(f"Created new risk: {risk_data['name']}")
        
        return all_risks
    
    @api.model
    def run_scheduled_analysis(self):
        """
        Scheduled job để chạy phân tích rủi ro tự động
        Chạy cho tất cả dự án đang active
        """
        projects = self.env['projects'].search([
            ('status', 'in', ['in_progress', 'not_started'])
        ])
        
        _logger.info(f"Starting scheduled risk analysis for {len(projects)} projects")
        
        total_risks = 0
        for project in projects:
            try:
                risks = self.analyze_project_risks(project.id)
                total_risks += len(risks)
                _logger.info(f"Project {project.projects_id}: Found {len(risks)} risks")
            except Exception as e:
                _logger.error(f"Error analyzing project {project.projects_id}: {str(e)}")
        
        _logger.info(f"Scheduled analysis completed. Total risks detected: {total_risks}")
        return True