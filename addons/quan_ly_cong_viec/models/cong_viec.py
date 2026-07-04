# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CongViec(models.Model):
    _name = 'cong_viec'
    _description = 'Bảng quản lý công việc'
    _rec_name = 'ten_cong_viec'

    # Mã công việc - tự động tạo bằng sequence
    ma_cong_viec = fields.Char(
        string="Mã công việc",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    
    ten_cong_viec = fields.Char(string="Tên công việc", required=True)
    mo_ta = fields.Text(string="Mô tả")
    ngay_bat_dau = fields.Date(string="Ngày bắt đầu")
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc")
    muc_do_uu_tien = fields.Selection(
        selection=[
            ('thap', 'Thấp'),
            ('trung_binh', 'Trung bình'),
            ('cao', 'Cao'),
            ('khan_cap', 'Khẩn cấp'),
        ],
        string="Mức độ ưu tiên",
        default='trung_binh'
    )
    trang_thai = fields.Selection(
        selection=[
            ('moi', 'Mới'),
            ('dang_thuc_hien', 'Đang thực hiện'),
            ('hoan_thanh', 'Hoàn thành'),
            ('tam_dung', 'Tạm dừng'),
        ],
        string="Trạng thái",
        default='moi'
    )
    
    # ============ TÍCH HỢP VỚI MODULE NHÂN SỰ ============
    # Người phụ trách công việc
    nguoi_phu_trach_id = fields.Many2one(
        'nhan_vien',
        string='Người phụ trách',
        required=True,
        ondelete='restrict',
        help='Nhân viên chịu trách nhiệm công việc này'
    )
    
    # Nhân viên được phân công (Many2many):
    # - Nếu công việc có nhiệm vụ con -> tự tính từ nguoi_thuc_hien_id của các nhiệm vụ đó
    #   (tránh lệch dữ liệu giữa "Nhân viên thực hiện" và người thực hiện từng nhiệm vụ)
    # - Nếu chưa có nhiệm vụ nào -> giữ giá trị nhập tay (công việc chưa breakdown)
    nhan_vien_phan_cong_ids = fields.Many2many(
        'nhan_vien',
        'cong_viec_nhan_vien_rel',
        'cong_viec_id',
        'nhan_vien_id',
        string='Nhân viên thực hiện',
        compute='_compute_nhan_vien_phan_cong_ids',
        store=True,
        readonly=False,
        help='Tự động tổng hợp từ "Người thực hiện" của các nhiệm vụ con. '
            'Nếu công việc chưa có nhiệm vụ nào, có thể chọn tay.'
    )

    @api.depends('nhiem_vu_ids.nguoi_thuc_hien_id')
    def _compute_nhan_vien_phan_cong_ids(self):
        for record in self:
            if record.nhiem_vu_ids:
                record.nhan_vien_phan_cong_ids = [(6, 0, record.nhiem_vu_ids.nguoi_thuc_hien_id.ids)]
            else:
                # Không có nhiệm vụ con: giữ nguyên giá trị hiện tại (cho phép chọn tay)
                record.nhan_vien_phan_cong_ids = record.nhan_vien_phan_cong_ids
        
    # Giờ làm dự kiến và thực tế
    gio_lam_du_kien = fields.Float(string='Giờ làm dự kiến')

    # Giờ làm thực tế:
    # - Nếu công việc có nhiệm vụ con -> tự cộng dồn so_gio_lam từ tất cả tien_do của các nhiệm vụ đó
    # - Nếu chưa có nhiệm vụ nào -> giữ giá trị nhập tay
    gio_lam_thuc_te = fields.Float(
        string='Giờ làm thực tế',
        compute='_compute_gio_lam_thuc_te',
        store=True,
        readonly=False,
        default=0.0,
        help='Tự động cộng dồn số giờ làm từ lịch sử tiến độ của các nhiệm vụ con. '
             'Nếu công việc chưa có nhiệm vụ nào, có thể nhập tay.'
    )

    @api.depends('nhiem_vu_ids.tien_do_ids.so_gio_lam')
    def _compute_gio_lam_thuc_te(self):
        for record in self:
            if record.nhiem_vu_ids:
                record.gio_lam_thuc_te = sum(
                    record.nhiem_vu_ids.mapped('tien_do_ids.so_gio_lam')
                )
            else:
                # Không có nhiệm vụ con: giữ nguyên giá trị hiện tại (cho phép nhập tay)
                record.gio_lam_thuc_te = record.gio_lam_thuc_te

    # ============ LIÊN KẾT NGƯỢC VỚI NHIỆM VỤ ============
    # Một công việc có nhiều nhiệm vụ (nhiem_vu.cong_viec_id trỏ về đây)
    nhiem_vu_ids = fields.One2many(
        'nhiem_vu',
        'cong_viec_id',
        string='Nhiệm vụ',
        help='Danh sách nhiệm vụ chi tiết thuộc công việc này'
    )

    # Tỷ lệ hoàn thành:
    # - Nếu công việc có nhiệm vụ con -> tự tính trung bình % hoàn thành các nhiệm vụ
    # - Nếu chưa có nhiệm vụ nào -> giữ giá trị nhập tay (ví dụ công việc cốt lõi mới tạo)
    ti_le_hoan_thanh = fields.Float(
        string='Tỷ lệ hoàn thành (%)',
        compute='_compute_ti_le_hoan_thanh',
        store=True,
        readonly=False,
        default=0.0,
        help='Tự động tính trung bình % hoàn thành của các nhiệm vụ con. '
             'Nếu công việc chưa có nhiệm vụ nào, có thể nhập tay.'
    )

    @api.depends('nhiem_vu_ids.ti_le_hoan_thanh')
    def _compute_ti_le_hoan_thanh(self):
        for record in self:
            if record.nhiem_vu_ids:
                tong = sum(record.nhiem_vu_ids.mapped('ti_le_hoan_thanh'))
                ti_le = tong / len(record.nhiem_vu_ids)
                record.ti_le_hoan_thanh = ti_le

                # Đồng bộ trạng thái theo % hoàn thành thực tế của nhiệm vụ con.
                # Không đụng vào trạng thái 'tam_dung' (do người dùng chủ động đặt).
                if record.trang_thai != 'tam_dung':
                    if ti_le >= 100.0 and record.trang_thai != 'hoan_thanh':
                        record.trang_thai = 'hoan_thanh'
                    elif ti_le < 100.0 and ti_le > 0.0 and record.trang_thai in ('moi', 'hoan_thanh'):
                        record.trang_thai = 'dang_thuc_hien'
                    elif ti_le == 0.0 and record.trang_thai == 'hoan_thanh':
                        # % tụt xuống 0 (ví dụ nhiệm vụ con bị reset) nhưng vẫn đang đánh dấu hoàn thành -> đưa về đang thực hiện
                        record.trang_thai = 'dang_thuc_hien'
            else:
                # Không có nhiệm vụ con: giữ nguyên giá trị hiện tại (cho phép nhập tay)
                record.ti_le_hoan_thanh = record.ti_le_hoan_thanh

    @api.model
    def create(self, vals):
        """Tạo công việc mới"""
        # Đồng bộ tỷ lệ hoàn thành với trạng thái khi tạo mới.
        # Lưu ý: lúc tạo mới, công việc chưa có nhiệm vụ con nào (nhiem_vu_ids rỗng),
        # nên việc set ti_le_hoan_thanh ở đây là hợp lệ và sẽ không bị compute ghi đè.
        trang_thai = vals.get('trang_thai')
        ti_le = vals.get('ti_le_hoan_thanh')
        # Nếu tạo mới đã chọn trạng thái hoàn thành nhưng chưa nhập % thì tự set 100%
        if trang_thai == 'hoan_thanh' and (ti_le is None or ti_le == 0.0):
            vals['ti_le_hoan_thanh'] = 100.0

        # Xử lý Mã công việc (Sequence)
        if vals.get('ma_cong_viec', 'Mới') == 'Mới':
            # Dùng 'or' để phòng trường hợp chưa có sequence thì lấy tạm CV001
            vals['ma_cong_viec'] = self.env['ir.sequence'].next_by_code('cong_viec.sequence') or 'CV001'
        
        return super(CongViec, self).create(vals)

    def write(self, vals):
        """Đồng bộ trạng thái và tỷ lệ hoàn thành khi cập nhật công việc

        - Nếu công việc KHÔNG có nhiệm vụ con: khi trạng thái được chuyển sang
          'hoan_thanh' mà % đang nhỏ hơn 100 -> tự động set 100 (giữ hành vi cũ).
        - Nếu công việc CÓ nhiệm vụ con: % hoàn thành do _compute_ti_le_hoan_thanh
          tự tính từ nhiệm vụ con, không cho phép người dùng set tay trạng thái
          'hoan_thanh' khi % thực tế (tính từ con) chưa đạt 100 -> chặn bằng lỗi.

          QUAN TRỌNG: việc validate này phải chạy SAU super().write(vals), không
          phải trước. Khi Save trên form, Odoo gửi MỘT lệnh write() duy nhất gồm
          cả thay đổi trạng_thai của công việc VÀ thay đổi (nested) của các
          nhiệm vụ con trong cùng vals (ví dụ user vừa sửa nhiệm vụ cuối cùng lên
          100% vừa đổi công việc cha thành 'hoan_thanh' rồi Save 1 lần). Nếu
          validate trước super().write(), record.ti_le_hoan_thanh vẫn là giá trị
          CŨ (chưa tính lại từ nhiệm vụ con vừa sửa) -> chặn oan dù thực ra đã đủ
          100%. Validate sau super().write() sẽ đọc được giá trị đã cập nhật
          đúng; nếu vẫn không hợp lệ, raise ValidationError ở đây sẽ rollback
          toàn bộ transaction (bao gồm cả các thay đổi nhiệm vụ con), nên vẫn an
          toàn về mặt dữ liệu.
        - Trigger AI re-scan khi có thay đổi quan trọng
        """
        res = super(CongViec, self).write(vals)

        if 'trang_thai' in vals and vals.get('trang_thai') == 'hoan_thanh':
            for record in self:
                if record.nhiem_vu_ids and record.ti_le_hoan_thanh < 100.0:
                    raise ValidationError(
                        "Không thể đánh dấu công việc '%s' là Hoàn thành vì vẫn còn "
                        "nhiệm vụ con chưa hoàn tất (tỷ lệ hoàn thành hiện tại: %.1f%%)."
                        % (record.ten_cong_viec, record.ti_le_hoan_thanh)
                    )

        # Chỉ xử lý khi có thay đổi trạng_thai
        # Lưu ý: chỉ ép % = 100 khi công việc KHÔNG có nhiệm vụ con,
        # vì nếu có nhiệm vụ con thì % đã được _compute_ti_le_hoan_thanh tự tính từ đó.
        if 'trang_thai' in vals:
            for record in self:
                if (record.trang_thai == 'hoan_thanh'
                        and not record.nhiem_vu_ids
                        and record.ti_le_hoan_thanh < 100.0):
                    record.ti_le_hoan_thanh = 100.0
        
        # Trigger AI re-scan cho dự án khi task có thay đổi quan trọng
        important_fields = {'trang_thai', 'ti_le_hoan_thanh', 'ngay_ket_thuc', 'nguoi_phu_trach_id'}
        if any(field in vals for field in important_fields):
            # Lấy danh sách dự án liên quan
            projects = self.mapped('du_an_id').filtered(lambda p: p)
            for project in projects:
                try:
                    # Gọi AI re-scan (chạy async nếu có thể)
                    project._auto_detect_risks()
                except Exception as e:
                    # Không để lỗi AI làm gián đoạn việc cập nhật task
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"Không thể chạy AI re-scan cho dự án {project.projects_id}: {str(e)}")

        return res

    def name_get(self):
        """Hiển thị mã và tên công việc"""
        result = []
        for record in self:
            if record.ten_cong_viec:
                name = f"{record.ma_cong_viec} - {record.ten_cong_viec}"
            else:
                name = record.ma_cong_viec or f'Công việc #{record.id}'
            result.append((record.id, name))
        return result