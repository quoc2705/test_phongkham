# Tổng kết phiên làm việc — PhòngKhám+

Tài liệu gom **những gì đã làm** trong các lượt chat gần đây (bạn yêu cầu + agent triển khai).  
Dùng để nhớ phạm vi thay đổi, file liên quan và cách kiểm tra nhanh.

**Cập nhật:** 2026-05-22

---

## 1. Bác sĩ (`fe/js/pages/bac-si/dashboard.js`, `fe/css/styles.css`)

### Tra cứu hồ sơ / lịch hôm nay
- Tìm bệnh nhân: nút **Tìm** inline, lọc theo ngày, vùng kết quả cuộn được.
- **Lịch hôm nay:** ẩn lịch trạng thái `HOAN_THANH`.
- Lịch **tiêm chủng** (`TIEM_CHUNG`): nút **Tiêm chủng** → mở hồ sơ → trang **Tiêm chủng** (không qua chẩn đoán).
- Tra cứu hồ sơ khi là lần tiêm: hiển thị block tiêm (trạng thái, ghi chú đặt lịch / sau tiêm, bảng lịch sử tiêm), không để trống chẩn đoán/toa như khám thường.

### Khám & chẩn đoán
- Sau chẩn đoán: thêm **Không kê đơn**; giao diện **Kê đơn** chỉnh lại gọn hơn.
- Đã **bỏ** trên luồng chẩn đoán: tái khám, chat, duyệt thuốc đặc thù, bước “Tiêm chủng” (tiêm chỉ làm từ menu / lịch tiêm).

### Tiêm chủng
- Form có **Ghi chú**; **Huỷ tiêm** khi không đạt (chống chỉ định) → PATCH `lich-tiem`, hủy lịch, ghi hồ sơ `CHONG_CHI_DINH` — **không trừ kho**.
- **Lưu tiêm** (`DA_TIEM`) → `chi_dinh_tiem` + cập nhật `lich-tiem` + `hoan_thanh` lịch.
- **Trừ tồn kho vaccine:** khi xác nhận **Đã tiêm**, trừ 1 liều từ `KhoVaccine` (lô còn hạn, FIFO theo ngày nhập). Hết tồn → báo lỗi, không lưu.
- Gợi ý trên form: lưu tiêm sẽ trừ kho; huỷ tiêm không trừ.

### Sidebar bác sĩ
- Đổi tên mục → **Tiêm chủng** (chỉ tiêm, không còn card xét nghiệm trên trang đó).
- Gỡ **Chat bác sĩ**, **Duyệt thuốc đặc thù**.

### Backend liên quan bác sĩ
- `be/benhan/views.py`: tìm hồ sơ theo ngày dùng khoảng thời gian timezone (`bounds_for_local_days`), tránh lọc ngày sai.
- `be/benhan/views.py` — `chi_dinh_tiem`: khi `trang_thai = DA_TIEM` gọi trừ kho.
- `be/thuoc/stock.py`: hàm `tru_ton_vaccine_mot_lieu` (dùng chung).
- `be/lichhen/views.py` — `thuc_hien_tiem`: dùng cùng logic trừ kho (API này FE bác sĩ chưa gọi trực tiếp).

---

## 2. Lễ tân (`fe/js/pages/le-tan/dashboard.js`)

### Lấy số walk-in (chưa hẹn)
- Chọn **Khám bệnh** hoặc **Tiêm chủng**.
- Tiêm chủng: bắt buộc chọn **vaccine**; gửi `loai_lich: TIEM_CHUNG` + `vaccine`.
- Hàng chờ: thêm cột **Loại** (khám / tiêm).

### Backend lễ tân
- `be/lichhen/serializers.py` — `WalkInLichHenSerializer`: thêm `vaccine`, validate tiêm phải có vaccine.
- `be/lichhen/views.py` — `walk_in`: tạo `LichTiem` kèm lịch khi `TIEM_CHUNG`.

---

## 3. Bệnh nhân (`fe/js/pages/benh-nhan/`)

- Gỡ **Chat bác sĩ** (menu, script, mô tả đăng nhập, card demo nếu có).

---

## 4. Admin (`fe/js/pages/admin/dashboard.js`)

- Menu **Thông báo** → **Quản lý thông báo**.

---

## 5. Kế toán (`fe/js/pages/ke-toan/dashboard.js`, `fe/js/pages/kho/dashboard.js`)

- Thêm mục **Quản lý kho** (nhúng `PageKhoDashboard` trong `ketoan-main`, `skipNav`).

---

## 6. Kho vaccine — hành vi mới (quan trọng)

| Thao tác | Trừ `KhoVaccine`? |
|----------|-------------------|
| Bác sĩ **Lưu tiêm** (`DA_TIEM`) qua `chi_dinh_tiem` | **Có** (−1, FIFO) |
| Bác sĩ **Huỷ tiêm** / chống chỉ định | **Không** |
| Lễ tân chỉ **lấy số** tiêm (walk-in) | **Không** (chỉ khi bác sĩ xác nhận đã tiêm) |
| API `lich-tiem/.../thuc_hien_tiem/` | **Có** (cùng hàm trừ kho) |

---

## 7. Danh sách file đã chạm (chính)

| Khu vực | File |
|---------|------|
| Bác sĩ FE | `fe/js/pages/bac-si/dashboard.js`, `fe/css/styles.css` |
| Lễ tân FE | `fe/js/pages/le-tan/dashboard.js` |
| Bệnh nhân FE | `fe/js/pages/benh-nhan/dashboard.js`, `login.js`, `index.html` (nếu có) |
| Admin FE | `fe/js/pages/admin/dashboard.js` |
| Kế toán / Kho FE | `fe/js/pages/ke-toan/dashboard.js`, `fe/js/pages/kho/dashboard.js` |
| Hồ sơ / tiêm BE | `be/benhan/views.py` |
| Lịch hẹn BE | `be/lichhen/views.py`, `be/lichhen/serializers.py` |
| Tồn vaccine BE | `be/thuoc/stock.py` (**mới**) |
| Thời gian BE | `be/phongkham/time_utils.py` (nếu đã dùng cho lọc ngày) |

---

## 8. Cách kiểm tra nhanh

1. **Ctrl+F5** trình duyệt sau khi đổi FE.  
2. **Restart Django** sau khi đổi BE.  
3. **Tiêm:** nhập kho vaccine (số lượng > 0, còn hạn) → bác sĩ Tiêm chủng → Lưu → kiểm tra kho giảm 1.  
4. **Huỷ tiêm:** kho không đổi.  
5. **Lễ tân:** walk-in tiêm + chọn vaccine → bác sĩ thấy lịch TIEM_CHUNG hôm nay → Tiêm chủng.  
6. **Walk-in khám:** `loai_lich: KHAM_BENH` như cũ.

---

## 9. Đăng ký ca làm bác sĩ (`doctor_schedule`) — mới

### Database
- Bảng **`doctor_schedule`**: `bac_si`, `ngay_lam`, `ca_lam` (SANG / CHIEU / TOI), `ghi_chu`.
- Unique: một BS chỉ đăng ký một lần cho mỗi (ngày, ca).
- Migration: `be/nguoidung/migrations/0002_doctor_schedule.py` — chạy `python manage.py migrate`.

### Phân ca (giờ VN / TIME_ZONE)
| Ca | Giờ |
|----|-----|
| Sáng | 06:00 – 11:59 |
| Chiều | 12:00 – 17:59 |
| Tối | 18:00 – 21:59 |

### API
| Endpoint | Mô tả |
|----------|--------|
| `GET/POST /api/doctor-schedule/` | CRUD; `?my=true` — ca của BS đang đăng nhập |
| `POST /api/doctor-schedule/dang_ky_nhieu/` | `{ ngay_lam, ca_lam: ['SANG','CHIEU'], ghi_chu? }` |
| `GET /lich-hen/lich-hen/bac_si_xep_hang/?ngay=&ca_lam=` | Chỉ BS đã đăng ký ca + `is_working` |

### Lễ tân
- Check-in / lấy số / gán BS: dropdown chỉ BS **đúng ca** (theo giờ hẹn hoặc ca hiện tại).
- Tự chọn BS walk-in: chỉ chọn trong BS đã đăng ký ca hôm nay; không có ai → lỗi rõ.

### Bác sĩ FE
- Menu **Đăng ký ca làm** — đăng ký/xóa ca, xem danh sách.

### File
- `be/nguoidung/models.py` — `DoctorSchedule`
- `be/nguoidung/doctor_schedule.py` — tiện ích phân ca
- `be/nguoidung/views.py` — `DoctorScheduleViewSet`
- `be/lichhen/views.py` — lọc `bac_si_xep_hang`, `walk_in`, `phan_cong_bac_si`
- `fe/js/pages/bac-si/dashboard.js`, `fe/js/pages/le-tan/dashboard.js`

---

## 10. Việc chưa làm / có thể làm thêm

- Form tiêm chưa cho bác sĩ **chọn tay lô / hạn** (đang FIFO tự động; có thể gửi `lo_vaccine` + `han_su_dung` nếu bổ sung UI).
- Chống bấm **Lưu tiêm** hai lần (tránh trừ kho 2 lần) — chưa có idempotency.
- Cột loại lịch trên **Lịch trong ngày** lễ tân (nếu cần tương tự hàng chờ).

---

## 10. Ghi chú phiên chat

- Một số thay đổi đầu phiên (tìm BN, revert/redo UI tìm kiếm) đã được tóm trong lịch sử chat; file này tập trung **kết quả cuối** đang có trên code.
- Transcript đầy đủ (nếu cần tra câu hỏi từng lượt): thư mục agent-transcripts, id phiên `78211476-fd43-44f4-bbc7-230e5c1e13c9`.
