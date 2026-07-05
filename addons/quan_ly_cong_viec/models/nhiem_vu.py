# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date


class NhiemVu(models.Model):
    _name = 'nhiem_vu'
    _description = 'Bảng quản lý nhiệm vụ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'ten_nhiem_vu'

    # Quy đổi đánh giá chất lượng -> điểm số, dùng để tính điểm hiệu suất trung bình
    # cho tính năng AI gợi ý phân công (action_ai_goi_y_nguoi_thuc_hien bên dưới)
    _DIEM_DANH_GIA = {'xuat_sac': 4, 'tot': 3, 'trung_binh': 2, 'yeu': 1}

    # Mã nhiệm vụ - tự động tạo bằng sequence
    ma_nhiem_vu = fields.Char(
        string="Mã nhiệm vụ",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    
    ten_nhiem_vu = fields.Char(string="Tên nhiệm vụ", required=True)
    mo_ta = fields.Text(string="Mô tả")
    ngay_bat_dau = fields.Date(string="Ngày bắt đầu")
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc")
    ngay_hoan_thanh_thuc_te = fields.Date(string="Ngày hoàn thành thực tế")
    
    # ============ TÍCH HỢP VỚI MODULE NHÂN SỰ ============
    # Thay thế Char bằng Many2one để liên kết với nhân viên
    nguoi_thuc_hien_id = fields.Many2one(
        'nhan_vien',
        string='Người thực hiện',
        ondelete='restrict',
        help='Nhân viên được giao nhiệm vụ này. Có thể để trống lúc mới tạo '
             'để dùng nút "AI gợi ý người thực hiện" (nút gọi type="object" '
             'sẽ tự lưu tạm bản ghi trước khi chạy - nếu field này required, '
             'Odoo sẽ chặn lưu tạm vì thiếu giá trị bắt buộc, khiến nút không '
             'bao giờ chạy được cho nhiệm vụ mới. Ràng buộc bắt buộc phải có '
             'người thực hiện được chuyển xuống _check_nguoi_thuc_hien_truoc_khi_hoan_thanh '
             'bên dưới, chỉ áp dụng khi nhiệm vụ chuyển sang trạng thái thực sự cần có người.)'
    )
    
    @api.constrains('trang_thai', 'nguoi_thuc_hien_id')
    def _check_nguoi_thuc_hien_truoc_khi_hoan_thanh(self):
        """Bắt buộc phải có người thực hiện trước khi nhiệm vụ được coi là
        đang thực hiện/hoàn thành - nhưng KHÔNG chặn lúc mới tạo (trạng thái
        'chua_bat_dau'), để nút AI gợi ý người thực hiện dùng được ngay."""
        for record in self:
            if record.trang_thai != 'chua_bat_dau' and not record.nguoi_thuc_hien_id:
                raise ValidationError(
                    "Nhiệm vụ '%s' cần có người thực hiện trước khi chuyển "
                    "sang trạng thái khác 'Chưa bắt đầu'." % record.ten_nhiem_vu
                )
    
    # Người giao việc
    nguoi_giao_viec_id = fields.Many2one(
        'nhan_vien',
        string='Người giao việc',
        ondelete='set null',
        help='Nhân viên giao nhiệm vụ'
    )
    
    trang_thai = fields.Selection(
        selection=[
            ('chua_bat_dau', 'Chưa bắt đầu'),
            ('dang_thuc_hien', 'Đang thực hiện'),
            ('hoan_thanh', 'Hoàn thành'),
            ('qua_han', 'Quá hạn'),
        ],
        string="Trạng thái",
        default='chua_bat_dau',
        compute='_compute_trang_thai',
        store=True
    )
    ti_le_hoan_thanh = fields.Float(string="Tỷ lệ hoàn thành (%)", default=0.0)
    
    # Đánh giá chất lượng
    danh_gia = fields.Selection([
        ('xuat_sac', 'Xuất sắc'),
        ('tot', 'Tốt'),
        ('trung_binh', 'Trung bình'),
        ('yeu', 'Yếu'),
    ], string='Đánh giá')
    
    nhan_xet = fields.Text(string='Nhận xét')
    
    @api.depends('ngay_ket_thuc', 'ti_le_hoan_thanh')
    def _compute_trang_thai(self):
        """Tự động tính trạng thái dựa trên thời gian và tiến độ"""
        for record in self:
            if record.ti_le_hoan_thanh >= 100:
                record.trang_thai = 'hoan_thanh'
            elif record.ti_le_hoan_thanh > 0:
                if record.ngay_ket_thuc and date.today() > record.ngay_ket_thuc:
                    record.trang_thai = 'qua_han'
                else:
                    record.trang_thai = 'dang_thuc_hien'
            else:
                if record.ngay_ket_thuc and date.today() > record.ngay_ket_thuc:
                    record.trang_thai = 'qua_han'
                else:
                    record.trang_thai = 'chua_bat_dau'
    
    # Liên kết Many2one - suffix _id
    cong_viec_id = fields.Many2one('cong_viec', string='Công việc', ondelete='cascade')
    
    # Liên kết One2many - suffix _ids
    tien_do_ids = fields.One2many(
        'tien_do',
        'nhiem_vu_id',
        string='Lịch sử tiến độ'
    )

    # ============ PHỤ THUỘC GIỮA CÁC NHIỆM VỤ ============
    # Quan hệ Many2many tự thân (self-referencing): một nhiệm vụ có thể có nhiều
    # nhiệm vụ tiền đề (phải hoàn thành trước) và là tiền đề của nhiều nhiệm vụ khác.
    nhiem_vu_truoc_ids = fields.Many2many(
        'nhiem_vu',
        'nhiem_vu_dependency_rel',
        'nhiem_vu_id',
        'nhiem_vu_truoc_id',
        string='Nhiệm vụ tiền đề',
        domain="[('cong_viec_id', '=', cong_viec_id)]",   # <-- Quan trọng
        help='Chỉ hiển thị nhiệm vụ thuộc cùng một công việc'
    )
    nhiem_vu_sau_ids = fields.Many2many(
        'nhiem_vu',
        'nhiem_vu_dependency_rel',
        'nhiem_vu_truoc_id',
        'nhiem_vu_id',
        string='Nhiệm vụ phụ thuộc vào nhiệm vụ này',
        help='Các nhiệm vụ đang chờ nhiệm vụ này hoàn thành (chỉ để xem, tính ngược từ nhiệm vụ tiền đề)'
    )

    @api.constrains('nhiem_vu_truoc_ids')
    def _check_nhiem_vu_truoc_khong_vong_lap(self):
        """Chặn việc thiết lập phụ thuộc vòng (A phụ thuộc B, B phụ thuộc A, hoặc dài hơn)
        và chặn việc tự chọn chính mình làm tiền đề."""
        for record in self:
            if record in record.nhiem_vu_truoc_ids:
                raise ValidationError(
                    f'Nhiệm vụ "{record.ten_nhiem_vu or record.ma_nhiem_vu}" không thể là tiền đề của chính nó.'
                )

            # Duyệt theo chiều tiền đề để phát hiện vòng lặp (DFS)
            da_xet = set()
            hang_doi = list(record.nhiem_vu_truoc_ids)
            while hang_doi:
                nv = hang_doi.pop()
                if nv.id == record.id:
                    raise ValidationError(
                        f'Phát hiện phụ thuộc vòng tròn liên quan đến nhiệm vụ '
                        f'"{record.ten_nhiem_vu or record.ma_nhiem_vu}". '
                        f'Vui lòng kiểm tra lại danh sách nhiệm vụ tiền đề.'
                    )
                if nv.id in da_xet:
                    continue
                da_xet.add(nv.id)
                hang_doi.extend(nv.nhiem_vu_truoc_ids)

    @api.model
    def create(self, vals):
        """Tự động tạo mã nhiệm vụ khi tạo mới"""
        if vals.get('ma_nhiem_vu', 'Mới') == 'Mới':
            vals['ma_nhiem_vu'] = self.env['ir.sequence'].next_by_code('nhiem_vu.sequence') or 'NV001'
        res = super(NhiemVu, self).create(vals)
        res._kiem_tra_va_xu_ly_canh_bao_qua_han()
        return res

    def _kiem_tra_tien_de_da_hoan_thanh(self):
        """Trả về danh sách tên các nhiệm vụ tiền đề CHƯA hoàn thành (rỗng nếu đã đủ điều kiện)."""
        self.ensure_one()
        chua_xong = self.nhiem_vu_truoc_ids.filtered(lambda nv: nv.trang_thai != 'hoan_thanh')
        return chua_xong

    # ============ CẢNH BÁO TRỄ HẠN (mail.activity) ============
    _MA_HOAT_DONG_QUA_HAN = 'quan_ly_cong_viec.mail_activity_type_qua_han'

    def _tim_nguoi_nhan_canh_bao(self):
        """Tìm tài khoản res.users phù hợp để gán activity nhắc nhở.

        Ưu tiên: tài khoản có email khớp với nguoi_thuc_hien_id.email.
        Nếu không tìm được, trả về (None, ghi_chu) để hàm gọi tự quyết định gán cho ai.
        """
        self.ensure_one()
        user = False
        if self.nguoi_thuc_hien_id and self.nguoi_thuc_hien_id.email:
            user = self.env['res.users'].search(
                [('email', '=', self.nguoi_thuc_hien_id.email)], limit=1
            )
        return user

    def _kiem_tra_va_xu_ly_canh_bao_qua_han(self):
        """Tạo mail.activity cảnh báo khi nhiệm vụ ở trạng thái 'qua_han'.
        Tự động đóng (done) activity cảnh báo nếu nhiệm vụ không còn quá hạn nữa.

        Được gọi sau create()/write() để đọc đúng giá trị trang_thai đã compute xong.
        """
        ActivityType = self.env['mail.activity.type'].sudo()
        activity_type = ActivityType.search([('name', '=', 'Cảnh báo trễ hạn')], limit=1)
        if not activity_type:
            # Tạo loại hoạt động riêng cho cảnh báo trễ hạn nếu chưa có (chạy 1 lần đầu tiên)
            activity_type = ActivityType.create({
                'name': 'Cảnh báo trễ hạn',
                'category': 'default',
            })

        for record in self:
            activity_dang_mo = self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'nhiem_vu'),
                ('res_id', '=', record.id),
                ('activity_type_id', '=', activity_type.id),
            ])

            if record.trang_thai == 'qua_han':
                if not activity_dang_mo:
                    nguoi_nhan = record._tim_nguoi_nhan_canh_bao()
                    if nguoi_nhan:
                        ghi_chu = (
                            f'Nhiệm vụ "{record.ten_nhiem_vu}" (mã {record.ma_nhiem_vu}) '
                            f'đã quá hạn (hạn: {record.ngay_ket_thuc}). Vui lòng cập nhật tiến độ.'
                        )
                        user_id = nguoi_nhan.id
                    else:
                        # Không tìm được tài khoản của nhân viên thực hiện -> gán tạm cho
                        # người đang vận hành hệ thống, kèm ghi chú rõ ràng để không bị bỏ sót.
                        ghi_chu = (
                            f'Nhiệm vụ "{record.ten_nhiem_vu}" (mã {record.ma_nhiem_vu}) đã quá hạn '
                            f'(hạn: {record.ngay_ket_thuc}). Không tìm được tài khoản hệ thống khớp với '
                            f'nhân viên thực hiện ({record.nguoi_thuc_hien_id.ho_ten or ""}), '
                            f'vui lòng nhắc nhở trực tiếp.'
                        )
                        user_id = self.env.user.id
                    self.env['mail.activity'].sudo().create({
                        'res_model_id': self.env['ir.model']._get('nhiem_vu').id,
                        'res_id': record.id,
                        'activity_type_id': activity_type.id,
                        'summary': 'Nhiệm vụ quá hạn',
                        'note': ghi_chu,
                        'user_id': user_id,
                        'date_deadline': fields.Date.today(),
                    })
            else:
                # Nhiệm vụ không còn quá hạn -> đóng các activity cảnh báo đang mở (nếu có)
                if activity_dang_mo:
                    activity_dang_mo.action_done()

    def write(self, vals):
        """Kiểm tra phụ thuộc trước khi ghi, và ngăn chặn lưu giá trị mới nếu vi phạm"""
        
        # Lấy giá trị cũ trước khi ghi
        old_values = {}
        if 'ti_le_hoan_thanh' in vals:
            for record in self:
                old_values[record.id] = record.ti_le_hoan_thanh

        # === KIỂM TRA PHỤ THUỘC ===
        ti_le_moi = vals.get('ti_le_hoan_thanh')
        if ti_le_moi is not None and ti_le_moi > 0:
            for record in self:
                chua_xong = record._kiem_tra_tien_de_da_hoan_thanh()
                if chua_xong:
                    ten_ds = ', '.join(chua_xong.mapped(lambda nv: nv.ten_nhiem_vu or nv.ma_nhiem_vu))
                    raise UserError(
                        f'Không thể cập nhật tiến độ cho nhiệm vụ "{record.ten_nhiem_vu}" vì còn '
                        f'nhiệm vụ tiền đề chưa hoàn thành: {ten_ds}.'
                    )

        # Nếu không có lỗi thì mới ghi dữ liệu
        projects_truoc = self.mapped('cong_viec_id.du_an_id').filtered(lambda p: p)

        res = super(NhiemVu, self).write(vals)

        # === XỬ LÝ SAU KHI GHI THÀNH CÔNG ===
        if any(f in vals for f in ('ti_le_hoan_thanh', 'ngay_ket_thuc')):
            self._kiem_tra_va_xu_ly_canh_bao_qua_han()

        if 'ti_le_hoan_thanh' in vals:
            projects_sau = self.mapped('cong_viec_id.du_an_id').filtered(lambda p: p)
            tat_ca_projects = projects_truoc | projects_sau
            
            for project in tat_ca_projects:
                try:
                    project._auto_detect_risks()
                except Exception as e:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"AI re-scan error: {str(e)}")

            try:
                self.env['bao_cao_du_an']._lam_moi_bao_cao_theo_du_an(tat_ca_projects.ids)
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Refresh report error: {str(e)}")

        return res
    @api.onchange('ti_le_hoan_thanh')
    def _onchange_ti_le_hoan_thanh(self):
        """Kiểm tra phụ thuộc NGAY KHI thay đổi % hoàn thành trên form"""
        if self.ti_le_hoan_thanh and self.ti_le_hoan_thanh > 0:
            chua_xong = self._kiem_tra_tien_de_da_hoan_thanh()
            if chua_xong:
                ten_ds = ', '.join(chua_xong.mapped(lambda nv: nv.ten_nhiem_vu or nv.ma_nhiem_vu))
                warning = {
                    'title': 'Cảnh báo phụ thuộc',
                    'message': f'Không thể cập nhật tiến độ cho nhiệm vụ "{self.ten_nhiem_vu}" vì còn '
                            f'nhiệm vụ tiền đề chưa hoàn thành: {ten_ds}.',
                    'type': 'warning'
                }
                # Khôi phục lại giá trị cũ (không cho thay đổi)
                self.ti_le_hoan_thanh = self._origin.ti_le_hoan_thanh if self._origin else 0.0
                return {'warning': warning}

    @api.model
    def _cron_quet_nhiem_vu_qua_han(self):
        """Cron job hàng ngày: quét toàn bộ nhiệm vụ chưa hoàn thành để phát hiện các
        nhiệm vụ TỰ chuyển sang quá hạn do thời gian trôi qua (không ai sửa field nào),
        và tạo/đóng cảnh báo tương ứng.

        Cần chạy định kỳ vì _compute_trang_thai phụ thuộc vào date.today(), nên trạng thái
        có thể đổi từ 'chua_bat_dau'/'dang_thuc_hien' sang 'qua_han' chỉ vì sang ngày mới,
        mà không có write() nào được gọi để trigger logic cảnh báo trong hàm write().
        """
        nhiem_vu_can_quet = self.search([('trang_thai', '!=', 'hoan_thanh')])
        nhiem_vu_can_quet._kiem_tra_va_xu_ly_canh_bao_qua_han()

    def _tinh_ung_vien_goi_y(self, so_luong=3):
        """Rule-based: xếp hạng nhân viên phù hợp nhất để giao nhiệm vụ này, dựa trên:
        - Workload hiện tại (số nhiệm vụ chưa hoàn thành đang giữ) - càng ít càng ưu tiên
        - Điểm hiệu suất trung bình từ nhiệm vụ đã hoàn thành trước đó (field danh_gia) -
          càng cao càng ưu tiên
        Trả về list[dict] đã xếp hạng, tối đa `so_luong` ứng viên.
        """
        self.ensure_one()
        NhanVien = self.env['nhan_vien']
        NhiemVu = self.env['nhiem_vu']
        ket_qua = []
        for nv in NhanVien.search([]):
            workload = NhiemVu.search_count([
                ('nguoi_thuc_hien_id', '=', nv.id),
                ('trang_thai', 'in', ['chua_bat_dau', 'dang_thuc_hien', 'qua_han']),
            ])
            da_xong = NhiemVu.search([
                ('nguoi_thuc_hien_id', '=', nv.id),
                ('trang_thai', '=', 'hoan_thanh'),
                ('danh_gia', '!=', False),
            ])
            if da_xong:
                diem_hieu_suat = sum(
                    self._DIEM_DANH_GIA.get(n.danh_gia, 2) for n in da_xong
                ) / len(da_xong)
            else:
                diem_hieu_suat = 2.0  # chưa có lịch sử -> coi như trung bình

            ket_qua.append({
                'ten': nv.ho_ten or nv.ma_nhan_vien,
                'workload': workload,
                'diem_hieu_suat': diem_hieu_suat,
            })

        # Xếp hạng: workload thấp trước, cùng workload thì hiệu suất cao trước
        ket_qua.sort(key=lambda x: (x['workload'], -x['diem_hieu_suat']))
        return ket_qua[:so_luong]

    def action_ai_goi_y_nguoi_thuc_hien(self):
        """Gợi ý nhân viên phù hợp cho nhiệm vụ này (feature AI #3). Không tự động gán -
        chỉ đăng gợi ý vào chatter để người dùng tự quyết định (an toàn hơn tự ý đổi
        nguoi_thuc_hien_id, tránh thay đổi dữ liệu ngoài ý muốn)."""
        self.ensure_one()
        ung_vien = self._tinh_ung_vien_goi_y()

        if not ung_vien:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Không có ứng viên',
                    'message': 'Chưa có nhân viên nào trong hệ thống để gợi ý.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        giai_thich_ai = self.env['gemini.ai.provider'].suggest_task_assignee(self, ung_vien)

        noi_dung = "<b>Gợi ý phân công (AI):</b><ul>"
        for c in ung_vien:
            noi_dung += (
                f"<li>{c['ten']} — đang có {c['workload']} nhiệm vụ active, "
                f"điểm hiệu suất trung bình {c['diem_hieu_suat']:.1f}/4</li>"
            )
        noi_dung += "</ul>"
        if giai_thich_ai:
            noi_dung += f"<p>{giai_thich_ai}</p>"

        self.message_post(body=noi_dung, subject='Gợi ý phân công nhân viên (AI)')

        # Mở lại CHÍNH bản ghi này thay vì chỉ hiện toast - Odoo sẽ fetch lại
        # dữ liệu (bao gồm chatter) qua 1 lệnh gọi mạng nội bộ (RPC), KHÔNG
        # tải lại toàn bộ trang/JS/CSS như tag 'reload' - nhanh hơn nhiều,
        # đặc biệt cần thiết cho nhiệm vụ MỚI (vừa được tự lưu ngầm bởi Odoo
        # khi bấm nút này trên form chưa Save) để chatter hiện ngay gợi ý.
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nhiệm vụ',
            'res_model': 'nhiem_vu',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def name_get(self):
        """Hiển thị mã và tên nhiệm vụ"""
        result = []
        for record in self:
            if record.ten_nhiem_vu:
                name = f"{record.ma_nhiem_vu} - {record.ten_nhiem_vu}"
            else:
                name = record.ma_nhiem_vu or f'Nhiệm vụ #{record.id}'
            result.append((record.id, name))
        return result