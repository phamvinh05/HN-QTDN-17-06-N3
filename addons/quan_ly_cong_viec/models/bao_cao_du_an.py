# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BaoCaoDuAn(models.Model):
    _name = 'bao_cao_du_an'
    _description = 'Báo cáo hiệu quả tổng hợp theo dự án'
    _rec_name = 'du_an_id'

    # Lưu ý: du_an_id trỏ tới model 'projects' của module project_management.
    # Giống cách cong_viec.du_an_id được dùng trong toàn bộ module này, model này
    # giả định project_management luôn được cài cùng quan_ly_cong_viec (đúng với
    # môi trường thực tế của đồ án).
    du_an_id = fields.Many2one(
        'projects',
        string='Dự án',
        required=True,
        ondelete='cascade'
    )

    # ============ DANH SÁCH CÔNG VIỆC / NHIỆM VỤ THUỘC DỰ ÁN ============
    # QUAN TRỌNG: đây là One2many "ảo" (tính bằng search(), không có field Many2one
    # thật nào ở cong_viec/nhiem_vu trỏ ngược lại bao_cao_du_an). Vì vậy KHÔNG được
    # thêm store=True - Odoo yêu cầu inverse_name để lưu loại field này xuống DB,
    # và field ảo kiểu này không có inverse_name nào hợp lệ (sẽ lỗi "No inverse field
    # found" khi load module). Giữ non-store là đúng cho trường hợp này.
    #
    # Để tránh lỗi CacheMiss khi field khác @api.depends vào các field này (do compute
    # non-store dễ vỡ khi bị resolve lồng nhau), các hàm compute thống kê dưới đây
    # KHÔNG depends/đọc qua cong_viec_ids, nhiem_vu_ids - mà tự gọi search() riêng.
    cong_viec_ids = fields.One2many(
        'cong_viec',
        compute='_compute_cong_viec_ids',
        string='Danh sách công việc'
    )

    nhiem_vu_ids = fields.One2many(
        'nhiem_vu',
        compute='_compute_nhiem_vu_ids',
        string='Danh sách nhiệm vụ'
    )

    @api.depends('du_an_id')
    def _compute_cong_viec_ids(self):
        for record in self:
            if record.du_an_id:
                record.cong_viec_ids = self.env['cong_viec'].search([
                    ('du_an_id', '=', record.du_an_id.id),
                ])
            else:
                record.cong_viec_ids = False

    @api.depends('du_an_id')
    def _compute_nhiem_vu_ids(self):
        for record in self:
            if record.du_an_id:
                record.nhiem_vu_ids = self.env['nhiem_vu'].search([
                    ('cong_viec_id.du_an_id', '=', record.du_an_id.id),
                ])
            else:
                record.nhiem_vu_ids = False

    # ============ THỐNG KÊ (cùng công thức với bao_cao_hieu_qua, đổi phạm vi lọc) ============
    tong_cong_viec = fields.Integer(
        string='Tổng công việc',
        compute='_compute_thong_ke',
        store=True
    )

    tong_nhiem_vu = fields.Integer(
        string='Tổng nhiệm vụ',
        compute='_compute_thong_ke',
        store=True
    )

    nhiem_vu_hoan_thanh = fields.Integer(
        string='Nhiệm vụ hoàn thành',
        compute='_compute_thong_ke',
        store=True
    )

    nhiem_vu_tre_han = fields.Integer(
        string='Nhiệm vụ trễ hạn',
        compute='_compute_thong_ke',
        store=True
    )

    ty_le_hoan_thanh = fields.Float(
        string='Tỷ lệ hoàn thành (%)',
        compute='_compute_thong_ke',
        store=True,
        help='Tỷ lệ % nhiệm vụ đã hoàn thành trên tổng số nhiệm vụ của dự án'
    )

    diem_trung_binh = fields.Float(
        string='Điểm đánh giá TB',
        compute='_compute_diem_danh_gia',
        store=True,
        help='Điểm trung bình các nhiệm vụ đã được đánh giá trong dự án'
    )

    xep_loai = fields.Selection([
        ('a', 'A - Xuất sắc'),
        ('b', 'B - Khá'),
        ('c', 'C - Trung bình'),
        ('d', 'D - Yếu'),
    ], string='Xếp loại dự án', compute='_compute_xep_loai', store=True)

    ghi_chu = fields.Text(string='Ghi chú')

    def lam_moi_du_lieu(self):
        """Ép tính lại toàn bộ thống kê của báo cáo (gọi tay hoặc gọi từ model khác).

        Cách an toàn: tự tính giá trị bằng Python thuần (search/filter/sum), rồi ghi
        xuống bằng write() thông thường. KHÔNG dùng invalidate_cache() + gọi lại hàm
        compute trực tiếp - cách đó can thiệp vào internals của ORM và có thể làm vỡ
        cache của các record khác đang được dùng dở trong cùng request (gây lỗi
        '_unknown' object has no attribute 'id' khi Odoo đọc lại field Many2one).

        Được gọi từ nhiem_vu.write() mỗi khi % nhiệm vụ thay đổi, để báo cáo dự án
        luôn khớp với dữ liệu mới nhất mà không cần người dùng bấm tay "làm mới".
        """
        diem_map = {'xuat_sac': 10, 'tot': 8, 'trung_binh': 6, 'yeu': 4}

        for record in self:
            if not record.du_an_id:
                continue

            cong_viec = self.env['cong_viec'].search([('du_an_id', '=', record.du_an_id.id)])
            nhiem_vu = self.env['nhiem_vu'].search([('cong_viec_id.du_an_id', '=', record.du_an_id.id)])

            tong_cv = len(cong_viec)
            tong_nv = len(nhiem_vu)
            hoan_thanh = len(nhiem_vu.filtered(lambda n: n.trang_thai == 'hoan_thanh'))
            tre_han = len(nhiem_vu.filtered(lambda n: n.trang_thai == 'qua_han'))
            ty_le = (hoan_thanh / tong_nv * 100) if tong_nv > 0 else 0.0

            nhiem_vu_co_danh_gia = nhiem_vu.filtered(lambda n: n.danh_gia)
            if nhiem_vu_co_danh_gia:
                tong_diem = sum(diem_map.get(n.danh_gia, 0) for n in nhiem_vu_co_danh_gia)
                diem_tb = tong_diem / len(nhiem_vu_co_danh_gia)
            else:
                diem_tb = 0.0

            if ty_le >= 90 and diem_tb >= 8:
                xep_loai = 'a'
            elif ty_le >= 75 and diem_tb >= 6:
                xep_loai = 'b'
            elif ty_le >= 60:
                xep_loai = 'c'
            else:
                xep_loai = 'd'

            # Dùng write() thường - an toàn, không động tới internals của ORM cache
            record.write({
                'tong_cong_viec': tong_cv,
                'tong_nhiem_vu': tong_nv,
                'nhiem_vu_hoan_thanh': hoan_thanh,
                'nhiem_vu_tre_han': tre_han,
                'ty_le_hoan_thanh': ty_le,
                'diem_trung_binh': diem_tb,
                'xep_loai': xep_loai,
            })

    @api.model
    def _lam_moi_bao_cao_theo_du_an(self, project_ids):
        """Tìm và làm mới tất cả báo cáo bao_cao_du_an ứng với các project_ids cho trước.

        Hàm tiện ích để các model khác (nhiem_vu, cong_viec) gọi tới sau khi dữ liệu
        của họ thay đổi, không cần biết chi tiết logic tính toán bên trong.
        """
        if not project_ids:
            return
        bao_cao = self.search([('du_an_id', 'in', list(project_ids))])
        bao_cao.lam_moi_du_lieu()

    @api.depends('du_an_id')
    def _compute_thong_ke(self):
        """Tính toán thống kê nhiệm vụ/công việc của dự án.

        Tự gọi search() trực tiếp (KHÔNG đọc qua record.cong_viec_ids/nhiem_vu_ids)
        để tránh phụ thuộc compute lồng nhau gây lỗi CacheMiss. Công thức giống
        bao_cao_hieu_qua._compute_thong_ke, chỉ khác phạm vi lọc.
        """
        for record in self:
            if not record.du_an_id:
                record.tong_cong_viec = 0
                record.tong_nhiem_vu = 0
                record.nhiem_vu_hoan_thanh = 0
                record.nhiem_vu_tre_han = 0
                record.ty_le_hoan_thanh = 0.0
                continue

            cong_viec = self.env['cong_viec'].search([('du_an_id', '=', record.du_an_id.id)])
            nhiem_vu = self.env['nhiem_vu'].search([('cong_viec_id.du_an_id', '=', record.du_an_id.id)])

            tong_cv = len(cong_viec)
            tong_nv = len(nhiem_vu)
            hoan_thanh = len(nhiem_vu.filtered(lambda n: n.trang_thai == 'hoan_thanh'))
            tre_han = len(nhiem_vu.filtered(lambda n: n.trang_thai == 'qua_han'))

            record.tong_cong_viec = tong_cv
            record.tong_nhiem_vu = tong_nv
            record.nhiem_vu_hoan_thanh = hoan_thanh
            record.nhiem_vu_tre_han = tre_han
            record.ty_le_hoan_thanh = (hoan_thanh / tong_nv * 100) if tong_nv > 0 else 0.0

    @api.depends('du_an_id')
    def _compute_diem_danh_gia(self):
        """Tính điểm đánh giá trung bình của dự án (cùng bảng điểm với bao_cao_hieu_qua).
        Tự search() trực tiếp, không đọc qua nhiem_vu_ids, cùng lý do với _compute_thong_ke.
        """
        diem_map = {
            'xuat_sac': 10,
            'tot': 8,
            'trung_binh': 6,
            'yeu': 4
        }
        for record in self:
            if not record.du_an_id:
                record.diem_trung_binh = 0.0
                continue

            nhiem_vu = self.env['nhiem_vu'].search([('cong_viec_id.du_an_id', '=', record.du_an_id.id)])
            nhiem_vu_co_danh_gia = nhiem_vu.filtered(lambda n: n.danh_gia)
            if nhiem_vu_co_danh_gia:
                tong_diem = sum(diem_map.get(n.danh_gia, 0) for n in nhiem_vu_co_danh_gia)
                record.diem_trung_binh = tong_diem / len(nhiem_vu_co_danh_gia)
            else:
                record.diem_trung_binh = 0.0

    @api.depends('ty_le_hoan_thanh', 'diem_trung_binh')
    def _compute_xep_loai(self):
        """Xếp loại dự án dựa trên tỷ lệ hoàn thành và điểm đánh giá.

        Dùng đúng ngưỡng với bao_cao_hieu_qua._compute_xep_loai để nhất quán cách đánh giá
        trong toàn hệ thống (nhân viên và dự án dùng cùng 1 thước đo).
        """
        for record in self:
            if record.ty_le_hoan_thanh >= 90 and record.diem_trung_binh >= 8:
                record.xep_loai = 'a'
            elif record.ty_le_hoan_thanh >= 75 and record.diem_trung_binh >= 6:
                record.xep_loai = 'b'
            elif record.ty_le_hoan_thanh >= 60:
                record.xep_loai = 'c'
            else:
                record.xep_loai = 'd'