## Tổng quan các module và luồng chính

### 1. Module `nhan_su` – Quản lý nhân sự nền tảng

- **Mục đích chính**: Cung cấp dữ liệu nhân sự chuẩn để các module khác (quản lý công việc, dự án) sử dụng.
- **Các model chính**:
  - **`nhan_vien`**:
    - Thông tin cá nhân: họ tên đệm, tên, họ và tên đầy đủ, ngày sinh, giới tính, quê quán, email, số điện thoại, ảnh.
    - Liên kết:
      - `chuc_vu_id` → `chuc_vu`: chức vụ của nhân viên.
      - `phong_ban_id` → `phong_ban`: phòng ban của nhân viên.
      - `lich_su_lam_viec_ids` → `lich_su_lam_viec`: lịch sử làm việc theo thời gian.
    - `ma_nhan_vien` sinh tự động bằng sequence `nhan_vien.sequence`.
  - **`chuc_vu`**:
    - Quản lý danh sách chức vụ (`ma_chuc_vu`, `ten_chuc_vu`).
    - Ràng buộc mã chức vụ duy nhất, tự sinh qua sequence `chuc_vu.sequence` nếu không nhập.
    - One2many `nhan_vien_ids` chứa danh sách nhân viên thuộc chức vụ đó.
  - **`phong_ban`**:
    - Quản lý phòng ban (`ma_phong_ban`, `ten_phong_ban`, mô tả).
    - Mã phòng ban tự sinh từ sequence `phong_ban.sequence`.
    - One2many `nhan_vien_ids` chứa danh sách nhân viên trong phòng.
  - **`lich_su_lam_viec`**:
    - Lưu lịch sử làm việc theo từng nhân viên: tên công việc, phòng ban, ngày bắt đầu/kết thúc, ghi chú.
    - Mã lịch sử `ma_lich_su` sinh tự động từ `lich_su_lam_viec.sequence`.
    - Liên kết:
      - `nhan_vien_id` → `nhan_vien` (bắt buộc).
      - `phong_ban_id` → `phong_ban`.

### 2. Module `quan_ly_cong_viec` – Quản lý công việc, nhiệm vụ, hiệu suất

- **Mục đích chính**: Quản lý công việc, nhiệm vụ, tiến độ, báo cáo hiệu quả làm việc; **phụ thuộc dữ liệu nhân sự từ `nhan_su`**.
- **Các model chính**:
  - **`cong_viec`**:
    - Thông tin công việc: mã (tự sinh từ `cong_viec.sequence`), tên, mô tả, ngày bắt đầu/kết thúc, mức độ ưu tiên, trạng thái.
    - Liên kết với nhân sự:
      - `nguoi_phu_trach_id` → `nhan_vien`: người chịu trách nhiệm chính (bắt buộc).
      - `nhan_vien_phan_cong_ids` (Many2many) → `nhan_vien`: danh sách nhân viên thực hiện.
    - Thời gian, hiệu suất:
      - `gio_lam_du_kien`, `gio_lam_thuc_te`.
      - `ti_le_hoan_thanh` (% hoàn thành, dùng để tính tiến độ dự án ở module `project_management`).
  - **`nhiem_vu`**:
    - Quản lý nhiệm vụ chi tiết của từng công việc: mã nhiệm vụ (tự sinh `nhiem_vu.sequence`), tên, mô tả, ngày bắt đầu/kết thúc, ngày hoàn thành thực tế.
    - Tích hợp nhân sự:
      - `nguoi_thuc_hien_id` → `nhan_vien`: người trực tiếp thực hiện (bắt buộc).
      - `nguoi_giao_viec_id` → `nhan_vien`: người giao nhiệm vụ.
    - Trạng thái, tiến độ:
      - `trang_thai` được **tự động tính** dựa trên `ti_le_hoan_thanh` và ngày kết thúc (chưa bắt đầu / đang thực hiện / hoàn thành / quá hạn).
      - `ti_le_hoan_thanh` (% hoàn thành nhiệm vụ).
    - Liên kết:
      - `cong_viec_id` → `cong_viec`: nhiệm vụ thuộc công việc nào.
      - `tien_do_ids` → `tien_do`: lịch sử cập nhật tiến độ nhiệm vụ.
  - **`tien_do`**:
    - Ghi nhận các lần cập nhật tiến độ: mã tiến độ (tự sinh `tien_do.sequence`), ngày cập nhật, nội dung, tỷ lệ hoàn thành, file đính kèm.
    - Tích hợp nhân sự:
      - `nguoi_cap_nhat_id` → `nhan_vien`: người cập nhật tiến độ.
    - Liên kết:
      - `nhiem_vu_id` → `nhiem_vu`: nhiệm vụ được cập nhật (bắt buộc).
    - Khi tạo mới, tự động:
      - Cấp mã `ma_tien_do`.
      - Cập nhật lại `ti_le_hoan_thanh` của `nhiem_vu` tương ứng.
  - **`bao_cao_hieu_qua`**:
    - Lập báo cáo hiệu quả làm việc của một nhân viên **theo tháng/năm**.
    - Thông tin chính:
      - `nhan_vien_id` → `nhan_vien`.
      - `thang`, `nam`.
    - Thống kê tự động:
      - Lấy danh sách nhiệm vụ (`nhiem_vu_ids`) mà nhân viên là `nguoi_thuc_hien_id` trong khoảng thời gian tháng/năm.
      - Tính: tổng nhiệm vụ, số nhiệm vụ hoàn thành, số nhiệm vụ trễ hạn, tỷ lệ hoàn thành (%).
      - Tính điểm trung bình từ đánh giá (`danh_gia` của `nhiem_vu`) và xếp loại (A/B/C/D) dựa trên tỷ lệ hoàn thành + điểm TB.
  - **`nhan_vien_extend` (kế thừa `nhan_vien`)**:
    - Thêm các thống kê công việc:
      - `cong_viec_phu_trach_ids`: danh sách công việc mà nhân viên là `nguoi_phu_trach_id`.
      - `so_cong_viec_phu_trach`, `so_cong_viec_dang_thuc_hien`, `so_cong_viec_hoan_thanh`: các trường compute thống kê nhanh khối lượng và trạng thái công việc.

### 3. Module `project_management` – Quản lý dự án, ngân sách, chi phí

- **Mục đích chính**: Quản lý dự án, phê duyệt dự án, ngân sách và chi phí; **tích hợp chặt với `nhan_su` và `quan_ly_cong_viec`**.
- **Các model chính**:
  - **`projects`**:
    - Thông tin dự án:
      - Mã dự án `projects_id` (preview từ sequence `projects.code`, tự sinh khi lưu).
      - Tên dự án, ngày bắt đầu, ngày kết thúc thực tế.
      - `manager_name` → `nhan_vien`: quản lý dự án (từ module `nhan_su`).
    - Theo dõi tiến độ:
      - `task_ids` (One2many) → `cong_viec` (field `du_an_id` được thêm từ `CongViecExtend`).
      - `progress` (% tiến độ) được **tự động tính** bằng trung bình `ti_le_hoan_thanh` của tất cả công việc thuộc dự án.
      - Nút/ action `action_view_task_chart` mở biểu đồ (graph view) các `cong_viec` theo dự án.
    - Quy trình xét duyệt dự án:
      - `approval_state`: Nháp → Chờ xét duyệt → Đã phê duyệt / Từ chối.
      - `approver_id`, `approval_date`, `approval_signature`, `rejection_reason`.
      - Actions:
        - `action_submit_approval`: gửi dự án đi xét duyệt (yêu cầu có `manager_name`).
        - `action_approve`: kiểm tra đã ký (`approval_signature`), đặt trạng thái `approved`, lưu người phê duyệt & ngày phê duyệt, **tự động tạo các công việc cốt lõi**.
        - `action_reject`: từ chối dự án, bắt buộc nhập lý do.
        - `action_reset_draft`: reset về trạng thái nháp, xoá thông tin duyệt.
      - Tự động tạo công việc cốt lõi (`_create_core_tasks`):
        - Kiểm tra model `cong_viec` (module `quan_ly_cong_viec`) có tồn tại.
        - Nếu có, tạo danh sách 5 công việc chuẩn (khởi động, lập kế hoạch, kiểm tra chất lượng, báo cáo định kỳ, bàn giao) với:
          - `du_an_id` trỏ về dự án hiện tại.
          - `nguoi_phu_trach_id` là `manager_name`.
          - Ngày bắt đầu/kết thúc lấy từ ngày dự án.
  - **`budgets`**:
    - Quản lý ngân sách dự án:
      - Mã ngân sách, tên ngân sách, `projects_id` → `projects`.
      - Các trường số: ngân sách dự toán, phân bổ, dự trù, đã chi (`budget_spent`), chênh lệch (`budget_difference`).
    - Liên kết:
      - `expense_ids` → `expenses`: danh sách chi phí thực tế thuộc ngân sách.
    - Tự động tính:
      - `budget_spent` = tổng `amount` của `expense_ids`.
      - `budget_difference` = `budget_planned` − `budget_spent`.
  - **`expenses`**:
    - Quản lý chi phí thực tế:
      - Tên khoản chi, số tiền, ngày chi (mặc định ngày hiện tại).
    - Liên kết:
      - `cong_viec_id` → `cong_viec`: chi phí gắn với công việc cụ thể (từ module `quan_ly_cong_viec`).
      - `budgets_id` → `budgets`: chi phí thuộc ngân sách nào.
    - Việc gắn chi phí vào `budgets_id` giúp cập nhật lại `budget_spent` và chênh lệch ngân sách.
  - **`employees`** (trong `project_management`):
    - Bảng chứa thành viên tham gia (có thể là legacy/độc lập), không phải bảng `nhan_vien` chuẩn của module `nhan_su`.
    - Có thể không cần sử dụng nếu bạn chuẩn hoá hoàn toàn sang `nhan_su.nhan_vien`.
  - **`NhanVienExtend` (kế thừa `nhan_vien`)**:
    - Thêm:
      - `has_project_management`: cờ kiểm tra hệ thống có model `projects` hay không.
      - `du_an_tham_gia_ids` (Many2many) → `projects`: danh sách dự án mà nhân viên tham gia.
    - Dùng để hiển thị dự án tham gia trên form nhân viên khi có cài module `project_management`.
  - **`CongViecExtend` (kế thừa `cong_viec`)**:
    - Thêm field:
      - `du_an_id` → `projects`: mỗi công việc thuộc về một dự án.
    - Đây là cầu nối chính giữa `cong_viec` (module `quan_ly_cong_viec`) và `projects` (module `project_management`).

---

### 4. Các luồng chạy chính giữa 3 module

#### 4.1. Luồng dữ liệu nhân sự → công việc/nhiệm vụ → báo cáo hiệu quả

- **Bước 1 – Khởi tạo nhân sự (`nhan_su`)**:
  - Người dùng tạo **nhân viên**, **chức vụ**, **phòng ban**, **lịch sử làm việc** trong module `nhan_su`.
  - Tất cả thông tin nhân viên đều nằm ở model `nhan_vien`.
- **Bước 2 – Gán nhân sự vào công việc (`quan_ly_cong_viec`)**:
  - Khi tạo **công việc** (`cong_viec`):
    - Chọn `nguoi_phu_trach_id` (bắt buộc) từ `nhan_vien`.
    - Có thể chọn thêm nhiều nhân viên trong `nhan_vien_phan_cong_ids`.
  - Khi tạo **nhiệm vụ** (`nhiem_vu`):
    - Chọn `nguoi_thuc_hien_id` và `nguoi_giao_viec_id` đều là `nhan_vien`.
    - Gắn `cong_viec_id` để nhiệm vụ thuộc về một công việc cụ thể.
- **Bước 3 – Cập nhật tiến độ và hoàn thành nhiệm vụ**:
  - Người dùng tạo các bản ghi **`tien_do`**:
    - Chọn `nhiem_vu_id` (nhiệm vụ), `nguoi_cap_nhat_id` (nhân viên cập nhật).
    - Nhập nội dung, tỷ lệ hoàn thành; hệ thống tự động:
      - Tạo mã `ma_tien_do`.
      - Cập nhật `ti_le_hoan_thanh` cho `nhiem_vu`.
  - Dựa trên `ti_le_hoan_thanh` và ngày kết thúc, **trạng thái `nhiem_vu`** được tính toán tự động.
- **Bước 4 – Tổng hợp hiệu quả làm việc (`bao_cao_hieu_qua`)**:
  - Người dùng tạo **báo cáo hiệu quả** cho một `nhan_vien` theo `thang`/`nam`.
  - Hệ thống tự tìm các **nhiệm vụ** mà nhân viên đó là `nguoi_thuc_hien_id` trong tháng/năm tương ứng, rồi:
    - Đếm tổng số nhiệm vụ, số nhiệm vụ hoàn thành, số nhiệm vụ trễ hạn.
    - Tính tỷ lệ hoàn thành và điểm đánh giá trung bình dựa trên trường `danh_gia` trong `nhiem_vu`.
    - Xếp loại A/B/C/D theo quy tắc đã định.

#### 4.2. Luồng dự án → công việc → tiến độ dự án (kết nối `project_management` & `quan_ly_cong_viec`)

- **Bước 1 – Tạo dự án (`projects`)**:
  - Người dùng tạo dự án:
    - Nhập/preview mã dự án, tên dự án, ngày bắt đầu, ngày kết thúc thực tế.
    - Chọn `manager_name` (quản lý dự án) là một `nhan_vien` từ module `nhan_su`.
- **Bước 2 – Gửi phê duyệt và phê duyệt dự án**:
  - Từ trạng thái Nháp, người dùng dùng `action_submit_approval` để chuyển sang Chờ xét duyệt.
  - Khi phê duyệt (`action_approve`):
    - Hệ thống kiểm tra đã có chữ ký `approval_signature`.
    - Ghi lại `approver_id` (thường chính là `manager_name`) và `approval_date`.
    - **Gọi `_create_core_tasks` để tự động tạo 5 công việc cốt lõi** trong model `cong_viec`:
      - Mỗi công việc:
        - Gắn `du_an_id` → dự án hiện tại.
        - Gắn `nguoi_phu_trach_id` = `manager_name`.
        - Ngày bắt đầu/kết thúc lấy từ dự án.
- **Bước 3 – Quản lý công việc chi tiết trong dự án (`cong_viec` & `nhiem_vu`)**:
  - Người dùng có thể:
    - Sử dụng các công việc cốt lõi được tạo tự động.
    - Hoặc tạo thêm công việc mới, **gắn `du_an_id`** về dự án tương ứng (thông qua `CongViecExtend`).
  - Trong mỗi `cong_viec`, có thể tạo nhiều `nhiem_vu` và `tien_do` như luồng 4.1.
- **Bước 4 – Tính tiến độ dự án**:
  - Model `projects` có:
    - `task_ids` là danh sách `cong_viec` thuộc dự án.
    - Hàm `_compute_progress`:
      - Lấy trung bình `ti_le_hoan_thanh` của tất cả `task_ids`.
      - Gán vào `progress` (% tiến độ dự án).
  - Người dùng có thể dùng action `action_view_task_chart` để xem biểu đồ công việc của dự án (graph view của `cong_viec` được lọc theo `du_an_id`).

#### 4.3. Luồng dự án → ngân sách → chi phí công việc (kết nối `project_management` & `quan_ly_cong_viec`)

- **Bước 1 – Thiết lập ngân sách cho dự án (`budgets`)**:
  - Tạo `budgets`:
    - Chọn `projects_id` (dự án).
    - Nhập các giá trị ngân sách: dự toán, phân bổ, dự trù.
- **Bước 2 – Ghi nhận chi phí theo công việc (`expenses`)**:
  - Khi phát sinh chi phí:
    - Tạo bản ghi `expenses`:
      - Nhập tên khoản chi, số tiền, ngày chi.
      - Gắn `cong_viec_id` → công việc (từ `quan_ly_cong_viec`) để biết chi phí thuộc công việc nào.
      - Gắn `budgets_id` → ngân sách để chi phí cộng dồn vào ngân sách dự án.
- **Bước 3 – Theo dõi ngân sách – thực chi – chênh lệch**:
  - Model `budgets` tự động:
    - Tính `budget_spent` = tổng `amount` của tất cả `expenses` thuộc ngân sách đó.
    - Tính `budget_difference` = `budget_planned` − `budget_spent`.
  - Qua đó, có thể:
    - Xem mức độ sử dụng ngân sách theo từng dự án.
    - Kết hợp với tiến độ dự án (`progress` của `projects`) để đánh giá hiệu quả sử dụng ngân sách.

#### 4.4. Góc nhìn từ nhân viên (tổng hợp từ cả 3 module)

- Trên form **`nhan_vien`** (module `nhan_su`), 2 module còn lại mở rộng thêm:
  - Từ `quan_ly_cong_viec`:
    - Nhân viên nhìn thấy:
      - `cong_viec_phu_trach_ids`: danh sách công việc đang/phải phụ trách.
      - Các chỉ số: tổng công việc phụ trách, số công việc đang thực hiện, số công việc đã hoàn thành.
  - Từ `project_management`:
    - Nhân viên nhìn thấy:
      - `du_an_tham_gia_ids`: danh sách dự án mà nhân viên tham gia.
    - Cờ `has_project_management` cho phép view xử lý linh hoạt khi module dự án có/không được cài.
- Đồng thời:
  - `bao_cao_hieu_qua` cho phép đánh giá hiệu quả làm việc theo từng nhân viên, từng tháng/năm dựa trên `nhiem_vu` và `tien_do`.
  - Việc phân quyền, menus, views tương ứng được định nghĩa trong các file `views/*.xml` và `security/ir.model.access.csv` của từng module.

---

### 5. Tổng kết ngắn

- **`nhan_su`**: là nền dữ liệu nhân viên (nhân sự, chức vụ, phòng ban, lịch sử làm việc).
- **`quan_ly_cong_viec`**: sử dụng dữ liệu nhân viên để quản lý công việc, nhiệm vụ, tiến độ, báo cáo hiệu quả.
- **`project_management`**: tổ chức dự án, phê duyệt, ngân sách, chi phí, và kết nối chặt với công việc (`cong_viec`) + nhân sự (`nhan_vien`) để tạo luồng dự án → công việc → tiến độ → chi phí.


