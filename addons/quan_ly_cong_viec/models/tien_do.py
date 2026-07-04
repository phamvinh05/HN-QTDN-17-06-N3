# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class TienDo(models.Model):
    _name = 'tien_do'
    _description = 'Bảng theo dõi tiến độ'
    _rec_name = 'ma_tien_do'

    # Mã tiến độ - tự động tạo bằng sequence
    ma_tien_do = fields.Char(
        string="Mã tiến độ",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    
    ngay_cap_nhat = fields.Datetime(string="Ngày cập nhật", default=fields.Datetime.now)
    noi_dung = fields.Text(string="Nội dung cập nhật", required=True)
    ti_le_hoan_thanh = fields.Float(string="Tỷ lệ hoàn thành (%)")

    # Số giờ thực tế đã làm cho riêng lần cập nhật này (ví dụ: "hôm nay làm 3 giờ").
    # Được cộng dồn lên cong_viec.gio_lam_thuc_te thông qua nhiem_vu_id.cong_viec_id.
    so_gio_lam = fields.Float(
        string="Số giờ làm (lần này)",
        default=0.0,
        help='Số giờ thực tế đã làm cho lần cập nhật tiến độ này. '
             'Sẽ được cộng dồn vào "Giờ làm thực tế" của công việc.'
    )
    
    # ============ TÍCH HỢP VỚI MODULE NHÂN SỰ ============
    # Thay Char bằng Many2one
    nguoi_cap_nhat_id = fields.Many2one(
        'nhan_vien',
        string='Người cập nhật',
        default=lambda self: self.env.context.get('default_nguoi_cap_nhat_id'),
        ondelete='set null',
        help='Nhân viên cập nhật tiến độ'
    )
    
    ghi_chu = fields.Text(string="Ghi chú")
    file_dinh_kem = fields.Binary(string="File đính kèm")
    ten_file = fields.Char(string="Tên file")
    
    # Liên kết Many2one - suffix _id
    nhiem_vu_id = fields.Many2one('nhiem_vu', string='Nhiệm vụ', ondelete='cascade', required=True)
    
    @api.model
    def create(self, vals):
        """Tự động tạo mã tiến độ và cập nhật tỷ lệ hoàn thành cho nhiệm vụ"""
        # Kiểm tra phụ thuộc TRƯỚC khi tạo, để báo lỗi rõ ràng ngay tại form Tiến độ
        # (tránh để lỗi bật lên từ nhiệm vụ một cách khó hiểu)
        ti_le_moi = vals.get('ti_le_hoan_thanh')
        nhiem_vu_id = vals.get('nhiem_vu_id')
        if ti_le_moi is not None and ti_le_moi > 0 and nhiem_vu_id:
            nhiem_vu = self.env['nhiem_vu'].browse(nhiem_vu_id)
            chua_xong = nhiem_vu._kiem_tra_tien_de_da_hoan_thanh()
            if chua_xong:
                ten_ds = ', '.join(chua_xong.mapped(lambda nv: nv.ten_nhiem_vu or nv.ma_nhiem_vu))
                raise UserError(
                    f'Không thể cập nhật tiến độ cho nhiệm vụ "{nhiem_vu.ten_nhiem_vu}" vì còn '
                    f'nhiệm vụ tiền đề chưa hoàn thành: {ten_ds}.'
                )

        # Tạo mã tiến độ tự động
        if vals.get('ma_tien_do', 'Mới') == 'Mới':
            vals['ma_tien_do'] = self.env['ir.sequence'].next_by_code('tien_do.sequence') or 'TD001'
        
        # Tạo record
        res = super(TienDo, self).create(vals)
        
        # Cập nhật tỷ lệ hoàn thành cho nhiệm vụ
        if res.nhiem_vu_id and 'ti_le_hoan_thanh' in vals:
            res.nhiem_vu_id.ti_le_hoan_thanh = vals['ti_le_hoan_thanh']
        
        return res

    def write(self, vals):
        """Xử lý khi SỬA LẠI một bản ghi tiến độ đã tồn tại (khác với create() ở trên,
        vốn chỉ xử lý khi TẠO MỚI). Nếu không có hàm này, việc sửa trực tiếp % hoàn thành
        của một dòng tiến độ cũ trong tab "Lịch sử tiến độ" sẽ không đồng bộ lên nhiệm vụ,
        khiến % công việc cha, activity cảnh báo, và AI rủi ro đều không được cập nhật theo.
        """
        ti_le_moi = vals.get('ti_le_hoan_thanh')
        if ti_le_moi is not None and ti_le_moi > 0:
            for record in self:
                nhiem_vu = record.nhiem_vu_id
                if nhiem_vu:
                    chua_xong = nhiem_vu._kiem_tra_tien_de_da_hoan_thanh()
                    if chua_xong:
                        ten_ds = ', '.join(chua_xong.mapped(lambda nv: nv.ten_nhiem_vu or nv.ma_nhiem_vu))
                        raise UserError(
                            f'Không thể cập nhật tiến độ cho nhiệm vụ "{nhiem_vu.ten_nhiem_vu}" vì còn '
                            f'nhiệm vụ tiền đề chưa hoàn thành: {ten_ds}.'
                        )

        res = super(TienDo, self).write(vals)

        # Đồng bộ % hoàn thành lên nhiệm vụ, giống logic trong create()
        if 'ti_le_hoan_thanh' in vals:
            for record in self:
                if record.nhiem_vu_id:
                    record.nhiem_vu_id.ti_le_hoan_thanh = vals['ti_le_hoan_thanh']

        return res

    def name_get(self):
        """Hiển thị mã tiến độ"""
        result = []
        for record in self:
            name = record.ma_tien_do or f'Tiến độ #{record.id}'
            result.append((record.id, name))
        return result