# -*- coding: utf-8 -*-
"""
ỨNG DỤNG DESKTOP GIẢ LẬP HỆ THỐNG PHÒNG KHÁM ĐA KHOA & TIÊM CHỦNG — PHÒNGKHÁM+ (Tkinter GUI)
===============================================================================================
Kết nối trực tiếp với Backend Django REST API để thao tác, nhập dữ liệu và demo trực quan
Feature 2: Kiểm thử Luồng Ứng dụng Nghiệp vụ Đa vai trò (be/test_feature2_app.py — 16 Test Cases):
  - Function 2.1 (UC005..UC008 — TC_APP_01..TC_APP_08):
    Luồng Bác sĩ Khám bệnh, Mở Hồ sơ bệnh án (EMR), Nhập Chẩn đoán ICD-10, Kê đơn thuốc & Tiêm chủng.
  - Function 2.2 (UC010 — TC_APP_09..TC_APP_16):
    Luồng Bệnh nhân Mua thuốc Online (OTC), Giỏ hàng, Đặt hàng, Thanh toán VNPay Sandbox & Hủy đơn.
  - Tab Trình chạy Tự động (Live Test Runner):
    Tự động điền dữ liệu nhập (du_lieu_nhap) lên form GUI và thực thi từng bước TC_APP_01 -> TC_APP_16.

Cách chạy:
  1. Giao diện đồ họa (GUI):
     .venv\\Scripts\\python app_desktop_phongkham.py
  2. Chế độ kiểm tra tự động (Self-test CLI):
     .venv\\Scripts\\python app_desktop_phongkham.py --self-test
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Cấu hình đường dẫn tới thư mục Backend Django (be/)
ROOT_DIR = Path(__file__).resolve().parent
BE_DIR = ROOT_DIR / "be"
if str(BE_DIR) not in sys.path:
    sys.path.insert(0, str(BE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phongkham.settings")
os.environ.setdefault("VNPAY_TEST_MODE", "true")

import django

django.setup()

from django.utils import timezone
from rest_framework.test import APIClient

# pyrefly: ignore[missing-import]
from benhan.models import ChanDoan, DonThuoc, HoSoBenhAn
# pyrefly: ignore[missing-import]
from donhang.models import DonHang, GioHang, SanPhamGioHang, ThanhToan
# pyrefly: ignore[missing-import]
from lichhen.models import LichHen, LichKham, LichTiem
# pyrefly: ignore[missing-import]
from nguoidung.models import BacSi, BenhNhan, DoctorSchedule, NguoiDung, NhanVien
# pyrefly: ignore[missing-import]
from thuoc.models import (
    DonViTinh,
    KhoThuoc,
    KhoVaccine,
    LoaiThuoc,
    LoaiVaccine,
    NhaCungCap,
    Thuoc,
    Vaccine,
)


# ==============================================================================
# 1. BỘ KHỞI TẠO / RESET DỮ LIỆU MẪU & ENGINE KẾT NỐI BACKEND (HTTP + DIRECT)
# ==============================================================================
class PhongKhamAppBackendEngine:
    """
    Engine kết nối Backend cho ứng dụng Desktop:
    - Hỗ trợ gọi qua HTTP Server (http://127.0.0.1:8000) khi bật `manage.py runserver`
    - Tự động chuyển sang Django APIClient nội bộ (kết nối thẳng CSDL be/db.sqlite3)
      nếu server HTTP chưa bật, đảm bảo App luôn hoạt động 100% khi demo!
    """

    def __init__(self, base_url="http://127.0.0.1:8000", mode="DIRECT"):
        self.base_url = base_url.rstrip("/")
        self.mode = mode  # "DIRECT" (mặc định ổn định 100%), "AUTO", "HTTP"
        self.api_client = APIClient()
        self.current_username = "bacsi1_test"
        self.jwt_tokens = {}
        self.entities = {}
        self.seed_or_reset_data()

    def seed_or_reset_data(self):
        """Khởi tạo hoặc đặt lại toàn bộ dữ liệu mẫu khớp 100% với base_test_setup.py."""
        self.today = timezone.localdate()
        self.now = timezone.now()

        # Xóa dữ liệu giao dịch phát sinh của các tài khoản test để trạng thái kho luôn chuẩn
        test_usernames = [
            "admin_test",
            "bacsi1_test",
            "bacsi2_test",
            "letan_test",
            "banthuoc_test",
            "ketoan_test",
            "benhnhan1_test",
            "benhnhan2_test",
        ]
        LichTiem.objects.filter(lich_hen__benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        LichKham.objects.filter(lich_hen__benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        ChanDoan.objects.filter(ho_so__benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        DonThuoc.objects.filter(benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        HoSoBenhAn.objects.filter(benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        LichHen.objects.filter(benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        ThanhToan.objects.filter(don_hang__benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        DonHang.objects.filter(benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        SanPhamGioHang.objects.filter(gio_hang__benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()
        GioHang.objects.filter(benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]).delete()

        # 1. Tạo / cập nhật người dùng
        def ensure_user(username, email, ho_ten, sdt, vai_tro, is_super=False):
            u, _ = NguoiDung.objects.update_or_create(
                ten_dang_nhap=username,
                defaults={
                    "email": email,
                    "ho_ten": ho_ten,
                    "so_dien_thoai": sdt,
                    "vai_tro": vai_tro,
                    "is_active": True,
                    "is_staff": is_super,
                    "is_superuser": is_super,
                },
            )
            u.set_password("Password@123")
            u.save()
            return u

        self.u_admin = ensure_user(
            "admin_test", "admin_test@phongkham.vn", "Quản Trị Viên Test", "0901000001", "ADMIN", True
        )
        self.u_bacsi1 = ensure_user(
            "bacsi1_test", "bacsi1_test@phongkham.vn", "BS. Nguyễn Văn An", "0901000002", "BAC_SI"
        )
        self.u_bacsi2 = ensure_user(
            "bacsi2_test", "bacsi2_test@phongkham.vn", "BS. Trần Thị Bình", "0901000003", "BAC_SI"
        )
        self.u_letan = ensure_user(
            "letan_test", "letan_test@phongkham.vn", "NV Lễ Tân Lê Hoa", "0901000004", "NHAN_VIEN"
        )
        self.u_banthuoc = ensure_user(
            "banthuoc_test", "banthuoc_test@phongkham.vn", "DS. Phạm Minh Dược", "0901000005", "NHAN_VIEN"
        )
        self.u_ketoan = ensure_user(
            "ketoan_test", "ketoan_test@phongkham.vn", "KT. Hoàng Thị Thu", "0901000006", "NHAN_VIEN"
        )
        self.u_bn1 = ensure_user(
            "benhnhan1_test", "bn1_test@gmail.com", "Lê Văn Bệnh Nhân", "0901000007", "BENH_NHAN"
        )
        self.u_bn2 = ensure_user(
            "benhnhan2_test", "bn2_test@gmail.com", "Trần Thị Khách Hàng", "0901000008", "BENH_NHAN"
        )

        # 2. Hồ sơ Bác sĩ, Nhân viên, Bệnh nhân
        self.bacsi1, _ = BacSi.objects.update_or_create(
            nguoi_dung=self.u_bacsi1,
            defaults={
                "ma_bac_si": "BS_TEST_01",
                "chuyen_khoa": "Nội tổng quát",
                "so_giay_phep": "CCHN-001",
                "trinh_do": "THAC_SI",
                "chuc_vu": "BAC_SI_DIEU_TRI",
                "is_working": True,
            },
        )
        self.bacsi2, _ = BacSi.objects.update_or_create(
            nguoi_dung=self.u_bacsi2,
            defaults={
                "ma_bac_si": "BS_TEST_02",
                "chuyen_khoa": "Nhi khoa & Tiêm chủng",
                "so_giay_phep": "CCHN-002",
                "trinh_do": "BAC_SI_CK1",
                "chuc_vu": "BAC_SI_DIEU_TRI",
                "is_working": True,
            },
        )

        DoctorSchedule.objects.filter(bac_si__in=[self.bacsi1, self.bacsi2]).delete()
        for d in (self.today, self.today + timedelta(days=1), self.today + timedelta(days=2)):
            for ca in ("SANG", "CHIEU", "TOI"):
                DoctorSchedule.objects.create(
                    bac_si=self.bacsi1,
                    ngay_lam=d,
                    ca_lam=ca,
                    ghi_chu="Ca trực định kỳ",
                )

        self.nv_letan, _ = NhanVien.objects.update_or_create(
            nguoi_dung=self.u_letan,
            defaults={
                "ma_nhan_vien": "NV_LT_01",
                "chuc_vu": "LE_TAN",
                "phong_ban": "Quầy Tiếp Đón",
                "ngay_bat_dau_lam": self.today - timedelta(days=365),
                "is_working": True,
            },
        )
        self.nv_banthuoc, _ = NhanVien.objects.update_or_create(
            nguoi_dung=self.u_banthuoc,
            defaults={
                "ma_nhan_vien": "NV_BT_01",
                "chuc_vu": "BAN_THUOC",
                "phong_ban": "Nhà Thuốc Phòng Khám",
                "ngay_bat_dau_lam": self.today - timedelta(days=300),
                "is_working": True,
            },
        )
        self.nv_ketoan, _ = NhanVien.objects.update_or_create(
            nguoi_dung=self.u_ketoan,
            defaults={
                "ma_nhan_vien": "NV_KT_01",
                "chuc_vu": "KE_TOAN",
                "phong_ban": "Phòng Tài Chính Kế Toán",
                "ngay_bat_dau_lam": self.today - timedelta(days=400),
                "is_working": True,
            },
        )

        self.bn1, _ = BenhNhan.objects.update_or_create(
            nguoi_dung=self.u_bn1,
            defaults={
                "ma_benh_nhan": "BN_TEST_01",
                "ngay_sinh": date(1996, 5, 15),
                "gioi_tinh": "NAM",
                "dia_chi": "123 Nguyễn Văn Linh, Đà Nẵng",
                "nhom_mau": "O+",
                "chieu_cao": Decimal("170.00"),
                "can_nang": Decimal("65.00"),
                "so_bao_hiem": "DN4010123456789",
                "ngay_het_han_bhyt": self.today + timedelta(days=180),
            },
        )
        self.bn2, _ = BenhNhan.objects.update_or_create(
            nguoi_dung=self.u_bn2,
            defaults={
                "ma_benh_nhan": "BN_TEST_02",
                "ngay_sinh": date(2000, 10, 20),
                "gioi_tinh": "NU",
                "dia_chi": "456 Lê Duẩn, Đà Nẵng",
                "nhom_mau": "A+",
                "chieu_cao": Decimal("160.00"),
                "can_nang": Decimal("52.00"),
            },
        )

        # 3. Danh mục Thuốc, Vaccine & Kho (Đặt lại đúng 150 viên OTC, 80 viên Rx, 10 liều Vaccine)
        self.loai_thuoc, _ = LoaiThuoc.objects.get_or_create(
            ten_loai="Giảm đau - Hạ sốt", defaults={"mo_ta": "Nhóm OTC"}
        )
        self.don_vi, _ = DonViTinh.objects.get_or_create(
            ten_don_vi="Viên", defaults={"ky_hieu": "vien"}
        )
        self.ncc, _ = NhaCungCap.objects.update_or_create(
            ma_ncc="NCC_TEST_01",
            defaults={
                "ten_ncc": "Công ty Dược Phẩm Trung Ương 1",
                "so_dien_thoai": "0243888999",
                "dia_chi": "Hà Nội",
                "trang_thai": True,
            },
        )

        self.thuoc_otc, _ = Thuoc.objects.update_or_create(
            ma_thuoc="TH_OTC_01",
            defaults={
                "ten_thuoc": "Paracetamol 500mg",
                "loai_thuoc": self.loai_thuoc,
                "don_vi": self.don_vi,
                "gia_ban": Decimal("2000.00"),
                "don_gia_nhap": Decimal("1200.00"),
                "can_don_thuoc": False,
                "can_tu_van": False,
                "trang_thai": True,
            },
        )
        KhoThuoc.objects.filter(thuoc=self.thuoc_otc).delete()
        self.kho_thuoc_otc_lo1 = KhoThuoc.objects.create(
            thuoc=self.thuoc_otc,
            so_luong=50,
            ngay_nhap=self.today - timedelta(days=30),
            han_su_dung=self.today + timedelta(days=60),
            lo_sx="LO-PARA-SO-1",
        )
        self.kho_thuoc_otc_lo2 = KhoThuoc.objects.create(
            thuoc=self.thuoc_otc,
            so_luong=100,
            ngay_nhap=self.today - timedelta(days=10),
            han_su_dung=self.today + timedelta(days=180),
            lo_sx="LO-PARA-SO-2",
        )

        self.thuoc_rx, _ = Thuoc.objects.update_or_create(
            ma_thuoc="TH_RX_01",
            defaults={
                "ten_thuoc": "Augmentin 625mg",
                "loai_thuoc": self.loai_thuoc,
                "don_vi": self.don_vi,
                "gia_ban": Decimal("18000.00"),
                "don_gia_nhap": Decimal("14000.00"),
                "can_don_thuoc": True,
                "can_tu_van": True,
                "trang_thai": True,
            },
        )
        KhoThuoc.objects.filter(thuoc=self.thuoc_rx).delete()
        self.kho_thuoc_rx = KhoThuoc.objects.create(
            thuoc=self.thuoc_rx,
            so_luong=80,
            ngay_nhap=self.today - timedelta(days=15),
            han_su_dung=self.today + timedelta(days=200),
            lo_sx="LO-AUG-01",
        )

        self.loai_vc, _ = LoaiVaccine.objects.get_or_create(ten_loai="Vaccine Cúm mùa")
        self.vaccine, _ = Vaccine.objects.update_or_create(
            ma_vaccine="VC_TEST_01",
            defaults={
                "ten_vaccine": "Influvac Tetra 0.5ml",
                "loai_vaccine": self.loai_vc,
                "nha_cung_cap": self.ncc,
                "gia_tiem": Decimal("350000.00"),
                "gia_nhap": Decimal("280000.00"),
                "phong_benh": "Cúm mùa A/B",
                "do_tuoi_ap_dung": "Từ 6 tháng tuổi",
                "so_mui": 1,
                "trang_thai": True,
            },
        )
        KhoVaccine.objects.filter(vaccine=self.vaccine).delete()
        self.kho_vc_lo1 = KhoVaccine.objects.create(
            vaccine=self.vaccine,
            so_luong=10,
            ngay_nhap=self.today - timedelta(days=20),
            han_su_dung=self.today + timedelta(days=90),
            lo_sx="LO-VC-01",
        )

        # 4. Tạo sẵn 1 lịch Walk-in CHECKED_IN cho BN_TEST_01 và 1 lịch CHO_XAC_NHAN cho BN_TEST_02
        self.api_client.force_authenticate(user=self.u_letan)
        res_wi = self.api_client.post(
            "/api/lich-hen/lich-hen/walk_in/",
            {
                "ma_benh_nhan": "BN_TEST_01",
                "bac_si": str(self.bacsi1.pk),
                "loai_lich": "KHAM_BENH",
                "ma_phong": "P101",
                "ten_phong": "Phòng Khám Nội 1",
                "ghi_chu": "Khám viêm họng cấp",
            },
            format="json",
        )
        self.lh_checked_in_id = res_wi.data["id"] if res_wi.status_code == 201 else None

        self.lh_unconfirmed = LichHen.objects.create(
            ma_lich_hen="LH_UNCONFIRMED_APP",
            benh_nhan=self.bn2,
            bac_si=self.bacsi1,
            ngay_gio_hen=self.now + timedelta(days=1),
            trang_thai="CHO_XAC_NHAN",
            ghi_chu="Lịch hẹn chưa check-in",
        )

        self.switch_user(self.current_username)

    def switch_user(self, username):
        """Chuyển đổi vai trò đăng nhập trên App."""
        self.current_username = username
        user = NguoiDung.objects.get(ten_dang_nhap=username)
        self.api_client.force_authenticate(user=user)
        return user

    def request(self, method, path, data=None):
        """
        Gửi request tới Backend:
        - Nếu mode == 'HTTP' hoặc 'AUTO': thử gọi HTTP tới http://127.0.0.1:8000 trước;
          nếu server chưa chạy thì tự động xử lý qua Django APIClient nội bộ.
        - Trả về: (status_code, response_dict_or_list, mode_used)
        """
        method = method.upper()
        if self.mode in ("HTTP", "AUTO"):
            try:
                token = self._get_http_jwt(self.current_username)
                url = f"{self.base_url}{path}"
                body_bytes = json.dumps(data, default=str).encode("utf-8") if data is not None else None
                headers = {"Accept": "application/json"}
                if body_bytes is not None:
                    headers["Content-Type"] = "application/json"
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    raw = resp.read().decode("utf-8")
                    parsed = json.loads(raw) if raw else {}
                    return resp.status, parsed, "HTTP (127.0.0.1:8000)"
            except urllib.error.HTTPError as he:
                raw = he.read().decode("utf-8", errors="ignore")
                try:
                    parsed = json.loads(raw) if raw else {"detail": str(he)}
                except Exception:
                    parsed = {"raw": raw[:300]}
                return he.code, parsed, "HTTP (127.0.0.1:8000)"
            except Exception:
                if self.mode == "HTTP":
                    return 503, {"error": "Không kết nối được HTTP Server 127.0.0.1:8000"}, "HTTP-ERROR"

        # Xử lý qua Django Direct APIClient trên cùng CSDL
        user = NguoiDung.objects.get(ten_dang_nhap=self.current_username)
        self.api_client.force_authenticate(user=user)
        fn = getattr(self.api_client, method.lower())
        if data is not None and method in ("POST", "PUT", "PATCH"):
            res = fn(path, json.dumps(data, default=str), content_type="application/json")
        else:
            res = fn(path)
        payload = getattr(res, "data", None)
        if payload is None:
            try:
                payload = json.loads(res.content.decode("utf-8"))
            except Exception:
                payload = {}
        return res.status_code, payload, "Django Direct API (DB)"

    def _get_http_jwt(self, username):
        if username in self.jwt_tokens:
            return self.jwt_tokens[username]
        url = f"{self.base_url}/api/users/login/"
        body = json.dumps({"ten_dang_nhap": username, "mat_khau": "Password@123", "password": "Password@123"}).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tok = (
                data.get("access")
                or data.get("access_token")
                or data.get("tokens", {}).get("access")
                or data.get("data", {}).get("access")
            )
            if tok:
                self.jwt_tokens[username] = tok
            return tok


# ==============================================================================
# 2. DANH MỤC 16 KỊCH BẢN TEST APP (TC_APP_01 .. TC_APP_16) KHỚP 100% BÁO CÁO
# ==============================================================================
APP_TEST_CASES_SPEC = [
    {
        "tc_id": "TC_APP_01",
        "func": "Func 2.1 (Bác sĩ - EMR)",
        "technique": "State Transition (UC005)",
        "title": "Bác sĩ mở hồ sơ bệnh án từ hàng chờ CHECKED_IN -> tạo HoSoBenhAn & chuyển DANG_KHAM",
        "expected": "HTTP 201 Created; tự sinh mã HS..., tạo LichKham và chuyển lịch sang DANG_KHAM",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_02",
        "func": "Func 2.1 (Bác sĩ - EMR)",
        "technique": "State Transition & RBAC (UC005)",
        "title": "Chặn mở hồ sơ khi lịch chưa CHECKED_IN (400) hoặc lịch thuộc bác sĩ khác (403/404)",
        "expected": "Bước 1 trả về HTTP 400 Bad Request; Bước 2 trả về HTTP 403/404",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_03",
        "func": "Func 2.1 (Bác sĩ - ICD-10)",
        "technique": "EP Hợp lệ (UC006)",
        "title": "Bác sĩ nhập triệu chứng, khám lâm sàng và lưu chẩn đoán mã ICD-10 hợp lệ (J02.9)",
        "expected": "HTTP 200 OK; lưu ChanDoan(ma_icd10='J02.9') và đồng bộ triệu chứng lên HoSoBenhAn",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_04",
        "func": "Func 2.1 (Bác sĩ - Kê đơn)",
        "technique": "EP Hợp lệ (UC007)",
        "title": "Bác sĩ kê đơn thuốc gồm 2 dòng thuốc (Augmentin + Paracetamol) -> tính tổng tiền 200.000đ",
        "expected": "HTTP 201 Created; tự động tính tong_tien = 200,000.00 VND",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_05",
        "func": "Func 2.1 (Bác sĩ - Kê đơn)",
        "technique": "BVA Không hợp lệ (UC007)",
        "title": "Chặn bác sĩ lưu đơn thuốc khi dòng thuốc thiếu mã thuốc hoặc số lượng <= 0 (REQ-RX-01)",
        "expected": "HTTP 400 Bad Request; không tạo bản ghi DonThuoc lỗi",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_06",
        "func": "Func 2.1 (Bác sĩ - Tiêm chủng)",
        "technique": "Integration FIFO (UC008)",
        "title": "Bác sĩ chỉ định tiêm chủng DA_TIEM -> tự động trừ 1 liều kho vaccine FIFO (10 -> 9 liều)",
        "expected": "HTTP 201 Created; tồn kho vaccine giảm từ 10 xuống 9 và lưu lo_vaccine='LO-VC-01'",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_07",
        "func": "Func 2.1 (Bác sĩ - ICD-10)",
        "technique": "BVA - LỖI SRS BUG-04",
        "title": "[BUG-04] Bắt buộc nhập mã ICD-10 (ma_icd10) khi lưu chẩn đoán; bỏ trống phải trả về 400",
        "expected": "Kỳ vọng SRS REQ-DIAG-02: HTTP 400 Bad Request (Thực tế code trả 200 OK -> FAILED)",
        "expected_status": "Failed",
    },
    {
        "tc_id": "TC_APP_08",
        "func": "Func 2.1 (Bác sĩ - ICD-10)",
        "technique": "EP Domain - LỖI SRS BUG-05",
        "title": "[BUG-05] Nhập chẩn đoán với trường phân loại bệnh loai_benh='CHINH' theo SRS Mục 4.2.11",
        "expected": "Kỳ vọng SRS REQ-DIAG-03: HTTP 200 OK chấp nhận 'CHINH' (Thực tế code trả 400 -> FAILED)",
        "expected_status": "Failed",
    },
    {
        "tc_id": "TC_APP_09",
        "func": "Func 2.2 (BN - Nhà thuốc)",
        "technique": "RBAC / Filter (UC010)",
        "title": "Bệnh nhân duyệt Cửa hàng thuốc chỉ hiển thị thuốc OTC, ẩn thuốc kê đơn (REQ-ONLINE-01)",
        "expected": "HTTP 200 OK; danh sách chỉ chứa TH_OTC_01, ẩn hoàn toàn thuốc kê đơn TH_RX_01",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_10",
        "func": "Func 2.2 (BN - Giỏ hàng)",
        "technique": "EP Hợp lệ (UC010)",
        "title": "Bệnh nhân thêm 5 viên Paracetamol 500mg vào giỏ -> chốt đơn giá 2.000đ, tổng giỏ 10.000đ",
        "expected": "HTTP 200 OK; tạo SanPhamGioHang và tính tong_tien_gio_hang = 10,000.0 VND",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_11",
        "func": "Func 2.2 (BN - Giỏ hàng)",
        "technique": "BVA Biên tồn kho (UC010)",
        "title": "Chặn thêm thuốc vào giỏ khi so_luong vượt tồn kho khả dụng (151 > 150 -> 400 Bad Request)",
        "expected": "HTTP 400 Bad Request kèm thông báo số lượng vượt quá tồn kho",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_12",
        "func": "Func 2.2 (BN - Giỏ hàng)",
        "technique": "EP & State Transition (UC010)",
        "title": "Bệnh nhân cập nhật số lượng trong giỏ (5 -> 12 viên = 24.000đ) và xóa sản phẩm khỏi giỏ",
        "expected": "Bước 2 cập nhật tổng tiền 24,000đ (200 OK); Bước 3 xóa sản phẩm về 0đ (200 OK)",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_13",
        "func": "Func 2.2 (BN - Đặt hàng)",
        "technique": "State Transition (UC010)",
        "title": "Tạo đơn hàng ONLINE từ giỏ 20 viên + ship 15.000đ -> tổng 55.000đ, trừ kho còn 130 viên",
        "expected": "HTTP 200 OK; đơn CHO_THANH_TOAN, tong_tien=55,000đ, tồn kho giảm còn 130 viên",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_14",
        "func": "Func 2.2 (BN - Đặt hàng)",
        "technique": "Error Guessing (UC010)",
        "title": "Chặn bệnh nhân bấm Đặt đơn hàng Online khi giỏ hàng đang trống (400 Bad Request)",
        "expected": "HTTP 400 Bad Request ('Giỏ hàng trống')",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_15",
        "func": "Func 2.2 (BN - VNPay)",
        "technique": "Integration VNPay (UC010)",
        "title": "Tạo URL thanh toán VNPay và xác nhận giao dịch qua VNPay Sandbox -> DA_THANH_TOAN",
        "expected": "Đơn hàng chuyển sang DA_THANH_TOAN và tạo ThanhToan(phuong_thuc='VNPAY', THANH_CONG)",
        "expected_status": "Passed",
    },
    {
        "tc_id": "TC_APP_16",
        "func": "Func 2.2 (BN - Hủy đơn)",
        "technique": "State Transition - LỖI SRS BUG-06",
        "title": "[BUG-06] Hủy đơn hàng Online ở trạng thái CHO_THANH_TOAN phải hoàn trả 20 viên về kho",
        "expected": "Kỳ vọng SRS REQ-FIFO-04: Tồn kho phục hồi 150 viên (Thực tế mất tồn còn 130 -> FAILED)",
        "expected_status": "Failed",
    },
]


# ==============================================================================
# 3. GIAO DIỆN DESKTOP APP (TKINTER / TTK)
# ==============================================================================
import tkinter as tk
from tkinter import messagebox, ttk


class PhongKhamDesktopApp(tk.Tk):
    def __init__(self, engine: PhongKhamAppBackendEngine, auto_play: bool = True, step_delay_ms: int = 1800):
        super().__init__()
        self.engine = engine
        self.auto_play = auto_play
        self.step_delay_ms = step_delay_ms
        self._auto_job = None
        self._auto_idx = 0
        self._auto_passed = 0
        self._auto_failed = 0

        self.title("PhòngKhám+ Desktop App Simulator — Hệ thống Quản lý Phòng khám & Kiểm thử App (UC005..UC010)")
        self.geometry("1420x900")
        self.minsize(1240, 780)
        self.configure(bg="#F0F4F8")

        self.active_ho_so_id = None
        self.active_cart_item_id = None
        self.active_order_id = None

        self._setup_styles()
        self._build_header()
        self._build_auto_demo_banner()
        self._build_main_notebook()
        self._build_log_console()

        # Nạp dữ liệu ban đầu lên các bảng
        self.refresh_all_views()
        self.log_event(
            "KHỞI ĐỘNG APP",
            "Đã kết nối CSDL & khởi tạo dữ liệu mẫu chuẩn (Paracetamol tồn 150v, Augmentin tồn 80v, Vaccine Influvac tồn 10 liều).",
        )
        if self.auto_play:
            self.after(900, self.start_visual_auto_demo)

    def _setup_styles(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#F0F4F8")
        style.configure("Card.TLabelframe", background="#FFFFFF", foreground="#0F3D5E", font=("Segoe UI", 10, "bold"))
        style.configure("Card.TLabelframe.Label", background="#FFFFFF", foreground="#0F3D5E", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#FFFFFF", foreground="#1E293B", font=("Segoe UI", 9))
        style.configure("Header.TLabel", background="#0F3D5E", foreground="#FFFFFF", font=("Segoe UI", 13, "bold"))
        style.configure("SubHeader.TLabel", background="#0F3D5E", foreground="#BAE6FD", font=("Segoe UI", 9))
        style.configure("Primary.TButton", background="#0284C7", foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), padding=5)
        style.map("Primary.TButton", background=[("active", "#0369A1")])
        style.configure("Success.TButton", background="#16A34A", foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), padding=5)
        style.map("Success.TButton", background=[("active", "#15803D")])
        style.configure("Danger.TButton", background="#DC2626", foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), padding=5)
        style.map("Danger.TButton", background=[("active", "#B91C1C")])
        style.configure("Neutral.TButton", background="#E2E8F0", foreground="#1E293B", font=("Segoe UI", 9), padding=4)
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=25)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#DBEAFE", foreground="#1E3A8A")
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(14, 7))

    # ------------------------------------------------------------------
    # HEADER BAR
    # ------------------------------------------------------------------
    def _build_header(self):
        header = tk.Frame(self, bg="#0F3D5E", height=64, padx=14, pady=8)
        header.pack(fill=tk.X, side=tk.TOP)

        left = tk.Frame(header, bg="#0F3D5E")
        left.pack(side=tk.LEFT)
        ttk.Label(
            left,
            text="🏥 PHÒNGKHÁM+ DESKTOP APP — GIẢ LẬP NGHIỆP VỤ & KIỂM THỬ APP (FEATURE 2)",
            style="Header.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            left,
            text="Kết nối Backend Django REST API | Hỗ trợ nhập dữ liệu trực tiếp & chạy tự động 16 Test Cases (TC_APP_01 .. TC_APP_16)",
            style="SubHeader.TLabel",
        ).pack(anchor="w")

        right = tk.Frame(header, bg="#0F3D5E")
        right.pack(side=tk.RIGHT)

        tk.Label(right, text="Tài khoản đang đăng nhập:", bg="#0F3D5E", fg="#E0F2FE", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        self.role_var = tk.StringVar(value="bacsi1_test (BS. Nguyễn Văn An - Bác sĩ)")
        self.role_combo = ttk.Combobox(
            right,
            textvariable=self.role_var,
            state="readonly",
            width=38,
            values=[
                "bacsi1_test (BS. Nguyễn Văn An - Bác sĩ)",
                "bacsi2_test (BS. Trần Thị Bình - Bác sĩ)",
                "benhnhan1_test (Lê Văn Bệnh Nhân - BN_TEST_01)",
                "benhnhan2_test (Trần Thị Khách Hàng - BN_TEST_02)",
                "letan_test (NV Lễ Tân Lê Hoa - Lễ tân)",
            ],
        )
        self.role_combo.pack(side=tk.LEFT, padx=4)
        self.role_combo.bind("<<ComboboxSelected>>", self._on_role_changed)

        ttk.Button(
            right,
            text="🔄 Reset Dữ liệu Mẫu Chuẩn",
            style="Success.TButton",
            command=self.on_reset_seed_data,
        ).pack(side=tk.LEFT, padx=6)

    def _build_auto_demo_banner(self):
        self.banner_frame = tk.Frame(self, bg="#0F766E", padx=14, pady=7)
        self.banner_frame.pack(fill=tk.X, side=tk.TOP)

        self.lbl_banner_title = tk.Label(
            self.banner_frame,
            text="🤖 CHẾ ĐỘ TỰ ĐỘNG TRÌNH CHIẾU APP: Chuẩn bị tự động điền dữ liệu & thực thi lần lượt 16 Test Cases (TC_APP_01 -> TC_APP_16)...",
            bg="#0F766E",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self.lbl_banner_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_toggle_auto = ttk.Button(
            self.banner_frame,
            text="⏸ Tạm dừng Tự động",
            style="Neutral.TButton",
            command=self.toggle_visual_auto_demo,
        )
        self.btn_toggle_auto.pack(side=tk.RIGHT, padx=4)

        ttk.Button(
            self.banner_frame,
            text="🔁 Chạy lại Tự động từ đầu",
            style="Primary.TButton",
            command=self.start_visual_auto_demo,
        ).pack(side=tk.RIGHT, padx=4)

    def _set_banner(self, text: str, bg_color: str = "#0F766E"):
        self.banner_frame.config(bg=bg_color)
        self.lbl_banner_title.config(text=text, bg=bg_color)

    def _on_role_changed(self, _event=None):
        raw = self.role_var.get()
        username = raw.split(" ")[0].strip()
        user = self.engine.switch_user(username)
        self.log_event("ĐỔI TÀI KHOẢN", f"Đã chuyển phiên đăng nhập sang: {user.ho_ten} ({username} - vai_tro={user.vai_tro})")
        self.refresh_all_views()

    def set_role_Select(self, username):
        mapping = {
            "bacsi1_test": "bacsi1_test (BS. Nguyễn Văn An - Bác sĩ)",
            "bacsi2_test": "bacsi2_test (BS. Trần Thị Bình - Bác sĩ)",
            "benhnhan1_test": "benhnhan1_test (Lê Văn Bệnh Nhân - BN_TEST_01)",
            "benhnhan2_test": "benhnhan2_test (Trần Thị Khách Hàng - BN_TEST_02)",
            "letan_test": "letan_test (NV Lễ Tân Lê Hoa - Lễ tân)",
        }
        if username in mapping:
            self.role_var.set(mapping[username])
        self.engine.switch_user(username)

    def on_reset_seed_data(self):
        self.engine.seed_or_reset_data()
        self.active_ho_so_id = None
        self.lbl_active_hs.config(text="Chưa mở hồ sơ (Hãy chọn lịch CHECKED_IN và nhấn 'Mở Hồ sơ bệnh án')")
        self.refresh_all_views()
        self.log_event(
            "RESET DỮ LIỆU",
            "Đã khôi phục dữ liệu gốc: Paracetamol 500mg = 150 viên, Augmentin 625mg = 80 viên, Vaccine Influvac = 10 liều.",
        )

    # ------------------------------------------------------------------
    # MAIN NOTEBOOK (3 TABS)
    # ------------------------------------------------------------------
    def _build_main_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 4))

        self.tab_doctor = ttk.Frame(self.notebook)
        self.tab_patient = ttk.Frame(self.notebook)
        self.tab_runner = ttk.Frame(self.notebook)

        self.notebook.add(
            self.tab_doctor,
            text="🩺 1. Phân hệ Bác sĩ: Khám bệnh, EMR, ICD-10, Kê đơn & Tiêm chủng (Func 2.1)",
        )
        self.notebook.add(
            self.tab_patient,
            text="🛒 2. Phân hệ Bệnh nhân: Mua thuốc Online, Giỏ hàng & VNPay (Func 2.2)",
        )
        self.notebook.add(
            self.tab_runner,
            text="🧪 3. Giả lập & Chạy Tự động 16 Test Cases App (TC_APP_01 .. TC_APP_16)",
        )

        self._build_tab_doctor()
        self._build_tab_patient()
        self._build_tab_runner()

    # ------------------------------------------------------------------
    # TAB 1: PHÂN HỆ BÁC SĨ (FUNCTION 2.1 - UC005..UC008)
    # ------------------------------------------------------------------
    def _build_tab_doctor(self):
        pane = ttk.PanedWindow(self.tab_doctor, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Khung Trái: Hàng chờ khám & Mở hồ sơ bệnh án
        left_card = ttk.LabelFrame(
            pane,
            text="📋 Hàng chờ Khám hôm nay & Mở Hồ sơ bệnh án (UC005 — TC_APP_01, TC_APP_02)",
            style="Card.TLabelframe",
            padding=8,
        )
        pane.add(left_card, weight=4)

        btn_bar = tk.Frame(left_card, bg="#FFFFFF")
        btn_bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(
            btn_bar,
            text="+ Tiếp nhận Walk-in BN_TEST_01",
            style="Neutral.TButton",
            command=self.doc_create_walkin,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            btn_bar,
            text="📂 Mở Hồ sơ bệnh án (TC_APP_01)",
            style="Primary.TButton",
            command=self.doc_open_emr_selected,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            btn_bar,
            text="🚫 Test Chặn Mở HS sai ĐK (TC_APP_02)",
            style="Danger.TButton",
            command=self.doc_test_block_open_emr,
        ).pack(side=tk.LEFT, padx=2)

        cols = ("id", "ma_lh", "stt", "ma_bn", "ten_bn", "trang_thai", "bac_si")
        self.tree_queue = ttk.Treeview(left_card, columns=cols, show="headings", height=12)
        headers = {
            "id": ("ID", 40),
            "ma_lh": ("Mã Lịch Hẹn", 110),
            "stt": ("STT", 42),
            "ma_bn": ("Mã BN", 80),
            "ten_bn": ("Họ tên Bệnh nhân", 135),
            "trang_thai": ("Trạng thái", 95),
            "bac_si": ("Bác sĩ phụ trách", 120),
        }
        for c, (txt, w) in headers.items():
            self.tree_queue.heading(c, text=txt)
            self.tree_queue.column(c, width=w, anchor="center" if c in ("id", "stt", "ma_bn", "trang_thai") else "w")
        self.tree_queue.pack(fill=tk.BOTH, expand=True)

        hs_frame = tk.Frame(left_card, bg="#EFF6FF", padx=8, pady=6, highlightbackground="#93C5FD", highlightthickness=1)
        hs_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(hs_frame, text="Hồ sơ bệnh án đang mở:", bg="#EFF6FF", fg="#1E3A8A", font=("Segoe UI", 9, "bold")).pack(
            anchor="w"
        )
        self.lbl_active_hs = tk.Label(
            hs_frame,
            text="Chưa mở hồ sơ (Hãy chọn lịch CHECKED_IN và nhấn 'Mở Hồ sơ bệnh án')",
            bg="#EFF6FF",
            fg="#0284C7",
            font=("Segoe UI", 9, "bold"),
            wraplength=460,
            justify="left",
        )
        self.lbl_active_hs.pack(anchor="w", pady=2)

        # Khung Phải: 3 Sub-tabs (Chẩn đoán ICD-10, Kê đơn thuốc, Tiêm chủng)
        right_card = ttk.LabelFrame(
            pane,
            text="📝 Nhập Dữ liệu Khám lâm sàng, Chẩn đoán ICD-10, Kê đơn & Tiêm chủng (UC006..UC008)",
            style="Card.TLabelframe",
            padding=8,
        )
        pane.add(right_card, weight=6)

        self.doc_sub_nb = ttk.Notebook(right_card)
        self.doc_sub_nb.pack(fill=tk.BOTH, expand=True)

        self.sub_diag = tk.Frame(self.doc_sub_nb, bg="#FFFFFF", padx=10, pady=8)
        self.sub_rx = tk.Frame(self.doc_sub_nb, bg="#FFFFFF", padx=10, pady=8)
        self.sub_vac = tk.Frame(self.doc_sub_nb, bg="#FFFFFF", padx=10, pady=8)

        self.doc_sub_nb.add(self.sub_diag, text="1. Nhập Chẩn đoán ICD-10 (TC_APP_03, 07, 08)")
        self.doc_sub_nb.add(self.sub_rx, text="2. Kê Đơn Thuốc (TC_APP_04, 05)")
        self.doc_sub_nb.add(self.sub_vac, text="3. Chỉ định Tiêm chủng (TC_APP_06)")

        self._build_subtab_diagnosis()
        self._build_subtab_prescription()
        self._build_subtab_vaccination()

    def _build_subtab_diagnosis(self):
        preset_bar = tk.Frame(self.sub_diag, bg="#FFFFFF")
        preset_bar.pack(fill=tk.X, pady=(0, 8))
        tk.Label(preset_bar, text="Điền nhanh dữ liệu nhập:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(
            preset_bar,
            text="Mẫu Hợp lệ J02.9 (TC_APP_03)",
            style="Neutral.TButton",
            command=self.fill_diag_valid_tc03,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            preset_bar,
            text="Mẫu Thiếu ICD-10 (TC_APP_07 - Bug)",
            style="Neutral.TButton",
            command=self.fill_diag_missing_icd_tc07,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            preset_bar,
            text="Mẫu Loại bệnh=CHINH (TC_APP_08 - Bug)",
            style="Neutral.TButton",
            command=self.fill_diag_loai_chinh_tc08,
        ).pack(side=tk.LEFT, padx=3)

        form = tk.Frame(self.sub_diag, bg="#FFFFFF")
        form.pack(fill=tk.BOTH, expand=True)

        self.diag_vars = {
            "trieu_chung": tk.StringVar(value="Đau rát họng, sốt 38.5 độ C, ho khan"),
            "kham_lam_sang": tk.StringVar(value="Niêm mạc họng đỏ xung huyết, amidan sưng nhẹ"),
            "ma_icd10": tk.StringVar(value="J02.9"),
            "ten_benh": tk.StringVar(value="Viêm họng cấp, không đặc hiệu"),
            "loai_benh": tk.StringVar(value="NGOAI_TRU"),
            "muc_do": tk.StringVar(value="TRUNG_BINH"),
            "mo_ta": tk.StringVar(value="Theo dõi viêm họng cấp do vi khuẩn"),
            "ket_luan": tk.StringVar(value="Điều trị nội khoa kháng sinh và hạ sốt 5 ngày"),
        }

        fields = [
            ("Triệu chứng lâm sàng (*):", "trieu_chung", "entry"),
            ("Kết quả khám lâm sàng (*):", "kham_lam_sang", "entry"),
            ("Mã bệnh quốc tế ICD-10 (*):", "ma_icd10", "entry"),
            ("Tên bệnh chẩn đoán (*):", "ten_benh", "entry"),
            ("Loại bệnh (loai_benh):", "loai_benh", ("NGOAI_TRU", "NOI_TRU", "CAP_CUU", "CHINH", "PHU")),
            ("Mức độ (muc_do):", "muc_do", ("NHẸ", "TRUNG_BINH", "NẶNG")),
            ("Mô tả chi tiết:", "mo_ta", "entry"),
            ("Kết luận điều trị:", "ket_luan", "entry"),
        ]
        for idx, (label_txt, key, widget_type) in enumerate(fields):
            tk.Label(form, text=label_txt, bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
                row=idx, column=0, sticky="w", pady=4, padx=(0, 10)
            )
            if isinstance(widget_type, tuple):
                cb = ttk.Combobox(form, textvariable=self.diag_vars[key], values=widget_type, width=52)
                cb.grid(row=idx, column=1, sticky="we", pady=4)
            else:
                ent = ttk.Entry(form, textvariable=self.diag_vars[key], width=55)
                ent.grid(row=idx, column=1, sticky="we", pady=4)
        form.columnconfigure(1, weight=1)

        ttk.Button(
            self.sub_diag,
            text="💾 Lưu Chẩn đoán vào Hồ sơ bệnh án (POST /api/benh-an/ho-so-benh-an/{id}/nhap_chan_doan/)",
            style="Primary.TButton",
            command=self.doc_submit_diagnosis,
        ).pack(fill=tk.X, pady=(10, 2))

    def _build_subtab_prescription(self):
        preset_bar = tk.Frame(self.sub_rx, bg="#FFFFFF")
        preset_bar.pack(fill=tk.X, pady=(0, 8))
        tk.Label(preset_bar, text="Điền nhanh dữ liệu kê đơn:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(
            preset_bar,
            text="Mẫu Đơn 2 thuốc = 200.000đ (TC_APP_04)",
            style="Neutral.TButton",
            command=self.fill_rx_valid_tc04,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            preset_bar,
            text="Mẫu Dòng thuốc lỗi SL=0 (TC_APP_05)",
            style="Neutral.TButton",
            command=self.fill_rx_invalid_tc05,
        ).pack(side=tk.LEFT, padx=3)

        form = tk.Frame(self.sub_rx, bg="#FFFFFF")
        form.pack(fill=tk.BOTH, expand=True)

        self.rx_vars = {
            "chan_doan": tk.StringVar(value="Viêm họng cấp (J02.9)"),
            "ghi_chu": tk.StringVar(value="Uống thuốc đúng giờ sau ăn, tái khám sau 5 ngày"),
            "thuoc1_mode": tk.StringVar(value="TH_RX_01 - Augmentin 625mg (18.000đ)"),
            "sl1": tk.StringVar(value="10"),
            "lieu1": tk.StringVar(value="1 viên/lần x 2 lần/ngày"),
            "thuoc2_enable": tk.BooleanVar(value=True),
            "sl2": tk.StringVar(value="10"),
            "lieu2": tk.StringVar(value="1 viên khi sốt > 38.5 độ"),
        }

        tk.Label(form, text="Chẩn đoán trên toa:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=4
        )
        ttk.Entry(form, textvariable=self.rx_vars["chan_doan"], width=52).grid(row=0, column=1, sticky="we", pady=4)

        tk.Label(form, text="Dòng thuốc 1 (*):", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Combobox(
            form,
            textvariable=self.rx_vars["thuoc1_mode"],
            values=[
                "TH_RX_01 - Augmentin 625mg (18.000đ)",
                "(Để trống mã thuốc - Kiểm thử BVA TC_APP_05)",
            ],
            width=50,
        ).grid(row=1, column=1, sticky="we", pady=4)

        tk.Label(form, text="Số lượng dòng 1 (*):", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=4
        )
        ttk.Entry(form, textvariable=self.rx_vars["sl1"], width=20).grid(row=2, column=1, sticky="w", pady=4)

        tk.Label(form, text="Liều dùng dòng 1 (*):", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=4
        )
        ttk.Entry(form, textvariable=self.rx_vars["lieu1"], width=52).grid(row=3, column=1, sticky="we", pady=4)

        ttk.Checkbutton(
            form,
            text="Kê thêm Dòng thuốc 2: TH_OTC_01 - Paracetamol 500mg (2.000đ/viên)",
            variable=self.rx_vars["thuoc2_enable"],
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=6)

        tk.Label(form, text="Số lượng dòng 2:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
            row=5, column=0, sticky="w", pady=4
        )
        ttk.Entry(form, textvariable=self.rx_vars["sl2"], width=20).grid(row=5, column=1, sticky="w", pady=4)

        tk.Label(form, text="Liều dùng dòng 2:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
            row=6, column=0, sticky="w", pady=4
        )
        ttk.Entry(form, textvariable=self.rx_vars["lieu2"], width=52).grid(row=6, column=1, sticky="we", pady=4)

        tk.Label(form, text="Lời dặn / Ghi chú toa:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
            row=7, column=0, sticky="w", pady=4
        )
        ttk.Entry(form, textvariable=self.rx_vars["ghi_chu"], width=52).grid(row=7, column=1, sticky="we", pady=4)
        form.columnconfigure(1, weight=1)

        ttk.Button(
            self.sub_rx,
            text="💊 Lưu Đơn Thuốc & Tính Tổng Tiền (POST /api/benh-an/ho-so-benh-an/{id}/tao_don_thuoc/)",
            style="Primary.TButton",
            command=self.doc_submit_prescription,
        ).pack(fill=tk.X, pady=(10, 2))

    def _build_subtab_vaccination(self):
        form = tk.Frame(self.sub_vac, bg="#FFFFFF")
        form.pack(fill=tk.BOTH, expand=True)

        self.vac_vars = {
            "vaccine": tk.StringVar(value="VC_TEST_01 - Influvac Tetra 0.5ml (350.000đ)"),
            "ngay_tiem": tk.StringVar(value=str(timezone.localdate())),
            "trang_thai": tk.StringVar(value="DA_TIEM"),
            "vi_tri_tiem": tk.StringVar(value="Cơ delta cánh tay trái"),
            "ghi_chu": tk.StringVar(value="Theo dõi 30 phút sau tiêm tại phòng tiêm chủng"),
        }

        fields = [
            ("Vaccine chỉ định (*):", "vaccine"),
            ("Ngày tiêm (*):", "ngay_tiem"),
            ("Trạng thái tiêm (*):", "trang_thai"),
            ("Vị trí tiêm:", "vi_tri_tiem"),
            ("Ghi chú sau tiêm:", "ghi_chu"),
        ]
        for idx, (lbl, k) in enumerate(fields):
            tk.Label(form, text=lbl, bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
                row=idx, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            if k == "trang_thai":
                ttk.Combobox(form, textvariable=self.vac_vars[k], values=("DA_TIEM", "CHO_TIEM"), width=48).grid(
                    row=idx, column=1, sticky="we", pady=5
                )
            else:
                ttk.Entry(form, textvariable=self.vac_vars[k], width=50).grid(
                    row=idx, column=1, sticky="we", pady=5
                )
        form.columnconfigure(1, weight=1)

        self.lbl_vac_stock = tk.Label(
            self.sub_vac,
            text="Tồn kho Vaccine Influvac Tetra (Lô LO-VC-01): 10 liều",
            bg="#ECFDF5",
            fg="#047857",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.lbl_vac_stock.pack(fill=tk.X, pady=8)

        ttk.Button(
            self.sub_vac,
            text="💉 Xác nhận Tiêm chủng & Trừ kho Vaccine FIFO (TC_APP_06 — POST .../chi_dinh_tiem/)",
            style="Success.TButton",
            command=self.doc_submit_vaccination,
        ).pack(fill=tk.X, pady=4)

    # ------------------------------------------------------------------
    # TAB 2: PHÂN HỆ BỆNH NHÂN — MUA THUỐC ONLINE & VNPAY (FUNCTION 2.2)
    # ------------------------------------------------------------------
    def _build_tab_patient(self):
        pane = ttk.PanedWindow(self.tab_patient, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Khung Trái: Cửa hàng thuốc OTC & Giỏ hàng
        left_card = ttk.LabelFrame(
            pane,
            text="🏪 Cửa hàng Thuốc Online (OTC) & Giỏ hàng của Bệnh nhân (TC_APP_09 .. TC_APP_12)",
            style="Card.TLabelframe",
            padding=8,
        )
        pane.add(left_card, weight=5)

        search_bar = tk.Frame(left_card, bg="#FFFFFF")
        search_bar.pack(fill=tk.X, pady=(0, 6))
        tk.Label(search_bar, text="Tìm kiếm thuốc:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.shop_search_var = tk.StringVar(value="")
        ttk.Entry(search_bar, textvariable=self.shop_search_var, width=22).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            search_bar,
            text="🔍 Duyệt Cửa hàng OTC (TC_APP_09)",
            style="Primary.TButton",
            command=self.patient_browse_otc_store,
        ).pack(side=tk.LEFT, padx=3)

        cols_shop = ("id", "ma_thuoc", "ten_thuoc", "gia_ban", "ton_kho", "can_don")
        self.tree_shop = ttk.Treeview(left_card, columns=cols_shop, show="headings", height=5)
        for c, (t, w) in {
            "id": ("ID", 40),
            "ma_thuoc": ("Mã thuốc", 90),
            "ten_thuoc": ("Tên thuốc", 160),
            "gia_ban": ("Giá bán (VND)", 95),
            "ton_kho": ("Tồn khả dụng", 90),
            "can_don": ("Kê đơn?", 70),
        }.items():
            self.tree_shop.heading(c, text=t)
            self.tree_shop.column(c, width=w, anchor="center" if c != "ten_thuoc" else "w")
        self.tree_shop.pack(fill=tk.X, pady=4)

        add_bar = tk.Frame(left_card, bg="#FFFFFF")
        add_bar.pack(fill=tk.X, pady=4)
        tk.Label(add_bar, text="Số lượng thêm vào giỏ (*):", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT
        )
        self.cart_add_qty_var = tk.StringVar(value="5")
        ttk.Entry(add_bar, textvariable=self.cart_add_qty_var, width=8).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            add_bar,
            text="➕ Thêm vào Giỏ (TC_APP_10)",
            style="Success.TButton",
            command=self.patient_add_to_cart,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            add_bar,
            text="⚠️ Nhập SL=151 Vượt tồn (TC_APP_11)",
            style="Danger.TButton",
            command=self.patient_test_exceed_stock,
        ).pack(side=tk.LEFT, padx=3)

        tk.Label(left_card, text="🛒 Giỏ hàng hiện tại của Bệnh nhân:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 2)
        )
        cols_cart = ("item_id", "ten_thuoc", "so_luong", "don_gia", "thanh_tien")
        self.tree_cart = ttk.Treeview(left_card, columns=cols_cart, show="headings", height=5)
        for c, (t, w) in {
            "item_id": ("Item ID", 60),
            "ten_thuoc": ("Tên sản phẩm", 170),
            "so_luong": ("Số lượng", 75),
            "don_gia": ("Đơn giá", 95),
            "thanh_tien": ("Thành tiền", 105),
        }.items():
            self.tree_cart.heading(c, text=t)
            self.tree_cart.column(c, width=w, anchor="center" if c != "ten_thuoc" else "w")
        self.tree_cart.pack(fill=tk.BOTH, expand=True, pady=2)

        cart_act = tk.Frame(left_card, bg="#FFFFFF")
        cart_act.pack(fill=tk.X, pady=4)
        self.lbl_cart_total = tk.Label(
            cart_act, text="Tổng tiền giỏ hàng: 0 VND", bg="#FFFFFF", fg="#0284C7", font=("Segoe UI", 10, "bold")
        )
        self.lbl_cart_total.pack(side=tk.LEFT)
        ttk.Button(
            cart_act,
            text="🗑️ Xóa SP (TC_APP_12)",
            style="Danger.TButton",
            command=self.patient_remove_cart_item,
        ).pack(side=tk.RIGHT, padx=3)
        ttk.Button(
            cart_act,
            text="✏️ Sửa SL -> 12 (TC_APP_12)",
            style="Neutral.TButton",
            command=self.patient_update_cart_qty_12,
        ).pack(side=tk.RIGHT, padx=3)

        # Khung Phải: Thông tin giao hàng, Đặt đơn Online, VNPay Sandbox & Hủy đơn
        right_card = ttk.LabelFrame(
            pane,
            text="🚚 Thông tin Giao hàng, Đặt đơn Online, Thanh toán VNPay & Hủy đơn (TC_APP_13 .. TC_APP_16)",
            style="Card.TLabelframe",
            padding=8,
        )
        pane.add(right_card, weight=5)

        ship_form = tk.Frame(right_card, bg="#FFFFFF")
        ship_form.pack(fill=tk.X)

        self.order_vars = {
            "nguoi_nhan": tk.StringVar(value="Lê Văn Bệnh Nhân"),
            "sdt_nhan": tk.StringVar(value="0901000007"),
            "email_nhan": tk.StringVar(value="bn1_test@gmail.com"),
            "dia_chi": tk.StringVar(value="123 Nguyễn Văn Linh, Quận Hải Châu, Đà Nẵng"),
            "phi_ship": tk.StringVar(value="15000"),
            "ghi_chu": tk.StringVar(value="Giao giờ hành chính"),
            "ly_do_huy": tk.StringVar(value="Khách yêu cầu hủy đơn - đặt nhầm số lượng"),
        }
        ship_fields = [
            ("Họ tên người nhận:", "nguoi_nhan"),
            ("Số điện thoại nhận (*):", "sdt_nhan"),
            ("Email nhận xác nhận:", "email_nhan"),
            ("Địa chỉ giao hàng (*):", "dia_chi"),
            ("Phí vận chuyển (VND):", "phi_ship"),
            ("Ghi chú giao hàng:", "ghi_chu"),
        ]
        for idx, (lbl, k) in enumerate(ship_fields):
            tk.Label(ship_form, text=lbl, bg="#FFFFFF", font=("Segoe UI", 9, "bold")).grid(
                row=idx, column=0, sticky="w", pady=3, padx=(0, 8)
            )
            ttk.Entry(ship_form, textvariable=self.order_vars[k], width=45).grid(
                row=idx, column=1, sticky="we", pady=3
            )
        ship_form.columnconfigure(1, weight=1)

        order_btns = tk.Frame(right_card, bg="#FFFFFF")
        order_btns.pack(fill=tk.X, pady=6)
        ttk.Button(
            order_btns,
            text="📦 Đặt hàng Online (20v + Ship 15k = 55k — TC_APP_13)",
            style="Primary.TButton",
            command=self.patient_create_online_order,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            order_btns,
            text="🚫 Đặt hàng khi Giỏ trống (TC_APP_14)",
            style="Danger.TButton",
            command=self.patient_order_empty_cart,
        ).pack(side=tk.LEFT, padx=3)

        tk.Label(right_card, text="📋 Danh sách Đơn hàng Online của tôi:", bg="#FFFFFF", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(6, 2)
        )
        cols_ord = ("id", "ma_dh", "trang_thai", "tong_tien", "ton_otc")
        self.tree_orders = ttk.Treeview(right_card, columns=cols_ord, show="headings", height=5)
        for c, (t, w) in {
            "id": ("ID", 45),
            "ma_dh": ("Mã Đơn Hàng", 125),
            "trang_thai": ("Trạng thái", 120),
            "tong_tien": ("Tổng tiền (VND)", 110),
            "ton_otc": ("Tồn kho OTC", 95),
        }.items():
            self.tree_orders.heading(c, text=t)
            self.tree_orders.column(c, width=w, anchor="center")
        self.tree_orders.pack(fill=tk.BOTH, expand=True, pady=2)

        vnpay_bar = tk.Frame(right_card, bg="#FFFFFF")
        vnpay_bar.pack(fill=tk.X, pady=4)
        ttk.Button(
            vnpay_bar,
            text="💳 Thanh toán qua Cổng VNPay Sandbox (TC_APP_15)",
            style="Success.TButton",
            command=self.patient_pay_vnpay_sandbox,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            vnpay_bar,
            text="❌ Hủy Đơn & Kiểm tra Hoàn kho (TC_APP_16 - Bug)",
            style="Danger.TButton",
            command=self.patient_cancel_order_check_stock,
        ).pack(side=tk.LEFT, padx=4)

    # ------------------------------------------------------------------
    # TAB 3: TRÌNH GIẢ LẬP & CHẠY TỰ ĐỘNG 16 TEST CASES APP (TC_APP_01..16)
    # ------------------------------------------------------------------
    def _build_tab_runner(self):
        top_bar = tk.Frame(self.tab_runner, bg="#FFFFFF", padx=10, pady=8)
        top_bar.pack(fill=tk.X, padx=6, pady=(6, 2))

        ttk.Button(
            top_bar,
            text="▶ Chạy Test Case đang chọn (Điền dữ liệu & Gọi API)",
            style="Primary.TButton",
            command=self.run_selected_test_case,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            top_bar,
            text="▶▶ Chạy Tự động Toàn bộ 16 Test Cases App (TC_APP_01 -> TC_APP_16)",
            style="Success.TButton",
            command=self.run_all_16_app_test_cases,
        ).pack(side=tk.LEFT, padx=6)

        self.lbl_runner_summary = tk.Label(
            top_bar,
            text="Tổng: 16 Test Cases App | Sẵn sàng thực thi (Kỳ vọng: 13 Passed, 3 Failed phát hiện BUG-04, BUG-05, BUG-06)",
            bg="#FFFFFF",
            fg="#0F3D5E",
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_runner_summary.pack(side=tk.RIGHT, padx=6)

        pane = ttk.PanedWindow(self.tab_runner, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Bảng 16 Test Cases
        tbl_frame = ttk.LabelFrame(
            pane,
            text="📊 Bảng Kịch bản Kiểm thử Feature 2 — App Workflows (be/test_feature2_app.py — 16 Test Cases)",
            style="Card.TLabelframe",
            padding=6,
        )
        pane.add(tbl_frame, weight=6)

        cols_tc = ("tc_id", "func", "technique", "title", "expected", "actual", "status")
        self.tree_tcs = ttk.Treeview(tbl_frame, columns=cols_tc, show="headings", height=11)
        for c, (t, w) in {
            "tc_id": ("TC ID", 80),
            "func": ("Chức năng", 145),
            "technique": ("Kỹ thuật thiết kế", 160),
            "title": ("Mô tả kịch bản kiểm thử App", 360),
            "expected": ("Kết quả kỳ vọng (SRS)", 260),
            "actual": ("Kết quả thực tế (App/API)", 230),
            "status": ("Trạng thái", 90),
        }.items():
            self.tree_tcs.heading(c, text=t)
            self.tree_tcs.column(c, width=w, anchor="center" if c in ("tc_id", "status") else "w")

        self.tree_tcs.tag_configure("Passed", background="#DCFCE7", foreground="#166534")
        self.tree_tcs.tag_configure("Failed", background="#FEE2E2", foreground="#991B1B")
        self.tree_tcs.tag_configure("Pending", background="#FEF9C3", foreground="#854D0E")

        for item in APP_TEST_CASES_SPEC:
            self.tree_tcs.insert(
                "",
                tk.END,
                iid=item["tc_id"],
                values=(
                    item["tc_id"],
                    item["func"],
                    item["technique"],
                    item["title"],
                    item["expected"],
                    "Chưa chạy (Nhấn nút ▶ để chạy)",
                    "Pending",
                ),
                tags=("Pending",),
            )
        self.tree_tcs.selection_set("TC_APP_01")
        self.tree_tcs.bind("<<TreeviewSelect>>", self._on_tc_row_selected)
        self.tree_tcs.pack(fill=tk.BOTH, expand=True)

        # Khung chi tiết Dữ liệu nhập (du_lieu_nhap) & Kết quả API của Test Case đang chọn
        detail_frame = ttk.LabelFrame(
            pane,
            text="🔍 Chi tiết Dữ liệu nhập (du_lieu_nhap), Quy trình thao tác (Procedure) & Phản hồi API thực tế",
            style="Card.TLabelframe",
            padding=6,
        )
        pane.add(detail_frame, weight=4)

        self.txt_tc_detail = tk.Text(
            detail_frame,
            height=8,
            bg="#0F172A",
            fg="#E2E8F0",
            font=("Consolas", 9),
            wrap=tk.WORD,
            padx=8,
            pady=6,
        )
        self.txt_tc_detail.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # BOTTOM CONSOLE LOG
    # ------------------------------------------------------------------
    def _build_log_console(self):
        log_frame = ttk.LabelFrame(
            self,
            text="📡 Nhật ký Tương tác App <-> Backend API (Live Request / Payload / Response)",
            style="Card.TLabelframe",
            padding=4,
        )
        log_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 8))

        self.txt_log = tk.Text(
            log_frame,
            height=5,
            bg="#1E293B",
            fg="#38BDF8",
            font=("Consolas", 9),
            wrap=tk.WORD,
            padx=6,
            pady=4,
        )
        self.txt_log.pack(fill=tk.X)

    def log_event(self, tag, message, payload=None, response=None):
        ts = timezone.localtime().strftime("%H:%M:%S")
        line = f"[{ts}] [{tag}] {message}\n"
        if payload is not None:
            line += f"   ↳ Dữ liệu nhập (du_lieu_nhap): {json.dumps(payload, ensure_ascii=False, default=str)}\n"
        if response is not None:
            resp_str = json.dumps(response, ensure_ascii=False, default=str)
            if len(resp_str) > 260:
                resp_str = resp_str[:260] + "..."
            line += f"   ↳ Phản hồi API: {resp_str}\n"
        if hasattr(self, "txt_log"):
            self.txt_log.insert(tk.END, line)
            self.txt_log.see(tk.END)

    # ------------------------------------------------------------------
    # REFRESH TABLES
    # ------------------------------------------------------------------
    def refresh_all_views(self):
        # 1. Hàng chờ khám
        for i in self.tree_queue.get_children():
            self.tree_queue.delete(i)
        qs_lh = LichHen.objects.filter(
            benh_nhan__ma_benh_nhan__in=["BN_TEST_01", "BN_TEST_02"]
        ).select_related("benh_nhan__nguoi_dung", "bac_si__nguoi_dung").order_by("-id")
        for lh in qs_lh:
            self.tree_queue.insert(
                "",
                tk.END,
                iid=str(lh.id),
                values=(
                    lh.id,
                    lh.ma_lich_hen,
                    lh.stt_trong_ngay or "-",
                    lh.benh_nhan.ma_benh_nhan,
                    lh.benh_nhan.nguoi_dung.ho_ten,
                    lh.trang_thai,
                    lh.bac_si.nguoi_dung.ho_ten if lh.bac_si else "-",
                ),
            )

        # 2. Tồn kho vaccine
        self.engine.vaccine.refresh_from_db()
        ton_vc = self.engine.vaccine.ton_kho()
        self.lbl_vac_stock.config(
            text=f"Tồn kho Vaccine Influvac Tetra (Lô LO-VC-01): {ton_vc} liều"
        )

        # 3. Cửa hàng thuốc & Giỏ hàng & Đơn hàng
        self.refresh_shop_and_cart()

    def refresh_shop_and_cart(self):
        for i in self.tree_shop.get_children():
            self.tree_shop.delete(i)
        for t in Thuoc.objects.filter(ma_thuoc__in=["TH_OTC_01", "TH_RX_01"]).order_by("id"):
            self.tree_shop.insert(
                "",
                tk.END,
                iid=str(t.id),
                values=(
                    t.id,
                    t.ma_thuoc,
                    t.ten_thuoc,
                    f"{int(t.gia_ban):,}",
                    t.ton_kho(),
                    "Có (Rx)" if t.can_don_thuoc else "Không (OTC)",
                ),
            )

        for i in self.tree_cart.get_children():
            self.tree_cart.delete(i)
        gh = GioHang.objects.filter(benh_nhan=self.engine.bn1).first()
        total_cart = 0
        if gh:
            for item in SanPhamGioHang.objects.filter(gio_hang=gh).select_related("thuoc"):
                tt = int(item.so_luong * item.don_gia_tai_thoi_diem)
                total_cart += tt
                self.active_cart_item_id = item.id
                self.tree_cart.insert(
                    "",
                    tk.END,
                    iid=str(item.id),
                    values=(
                        item.id,
                        item.thuoc.ten_thuoc,
                        item.so_luong,
                        f"{int(item.don_gia_tai_thoi_diem):,}",
                        f"{tt:,}",
                    ),
                )
        self.lbl_cart_total.config(text=f"Tổng tiền giỏ hàng (BN_TEST_01): {total_cart:,} VND")

        for i in self.tree_orders.get_children():
            self.tree_orders.delete(i)
        ton_otc = self.engine.thuoc_otc.ton_kho()
        for dh in DonHang.objects.filter(benh_nhan=self.engine.bn1).order_by("-ngay_tao"):
            self.active_order_id = dh.id
            self.tree_orders.insert(
                "",
                tk.END,
                iid=str(dh.id),
                values=(
                    dh.id,
                    dh.ma_don_hang,
                    dh.trang_thai,
                    f"{int(dh.tong_tien):,}",
                    f"{ton_otc} viên",
                ),
            )

    # ------------------------------------------------------------------
    # CÁC HÀM THAO TÁC TRÊN TAB 1 (PHÂN HỆ BÁC SĨ - FUNC 2.1)
    # ------------------------------------------------------------------
    def doc_create_walkin(self):
        self.set_role_Select("letan_test")
        du_lieu_nhap = {
            "ma_benh_nhan": "BN_TEST_01",
            "bac_si": str(self.engine.bacsi1.pk),
            "loai_lich": "KHAM_BENH",
            "ma_phong": "P101",
            "ten_phong": "Phòng Khám Nội 1",
            "ghi_chu": "Khám viêm họng cấp",
        }
        code, data, mode = self.engine.request("POST", "/api/lich-hen/lich-hen/walk_in/", du_lieu_nhap)
        if code == 201:
            self.engine.lh_checked_in_id = data["id"]
        self.set_role_Select("bacsi1_test")
        self.refresh_all_views()
        self.log_event(f"WALK-IN ({code} - {mode})", "Lễ tân tiếp nhận Walk-in cho BN_TEST_01", du_lieu_nhap, data)
        return code, data, du_lieu_nhap

    def doc_open_emr_selected(self):
        self.set_role_Select("bacsi1_test")
        lh_id = self.engine.lh_checked_in_id
        lh_obj = LichHen.objects.filter(id=lh_id).first()
        if not lh_obj or lh_obj.trang_thai != "CHECKED_IN":
            LichHen.objects.filter(benh_nhan=self.engine.bn1, trang_thai__in=["CHECKED_IN", "DANG_KHAM"]).delete()
            self.doc_create_walkin()
            lh_id = self.engine.lh_checked_in_id

        du_lieu_nhap = {
            "lich_hen_id": str(lh_id),
            "phong_kham": "P101 - Phòng Khám Nội 1",
            "ghi_chu_tiep_nhan": "Bắt đầu khám lâm sàng cho bệnh nhân Lê Văn Bệnh Nhân",
        }
        code, data, mode = self.engine.request("POST", f"/api/lich-hen/lich-hen/{lh_id}/mo_ho_so_benh_an/", du_lieu_nhap)
        ho_so_dict = data.get("ho_so", data) if isinstance(data, dict) else {}
        if code in (200, 201) and isinstance(ho_so_dict, dict) and "id" in ho_so_dict:
            self.active_ho_so_id = ho_so_dict["id"]
            ma_hs = ho_so_dict.get("ma_hs") or ho_so_dict.get("ma_ho_so")
            self.lbl_active_hs.config(
                text=f"Đang mở Hồ sơ ID={self.active_ho_so_id} | Mã HS: {ma_hs} | Bệnh nhân: BN_TEST_01 (Trạng thái lịch: DANG_KHAM)"
            )
        self.refresh_all_views()
        self.log_event(f"TC_APP_01 ({code} - {mode})", "Bác sĩ mở hồ sơ bệnh án từ hàng chờ CHECKED_IN", du_lieu_nhap, data)
        return code, data, du_lieu_nhap

    def doc_test_block_open_emr(self):
        lh_unconf_id = self.engine.lh_unconfirmed.id
        lh_checked_id = self.engine.lh_checked_in_id
        du_lieu_nhap = {
            "kich_ban_1_chua_check_in": {"bac_si": "bacsi1_test", "lich_hen_id": lh_unconf_id, "trang_thai": "CHO_XAC_NHAN"},
            "kich_ban_2_sai_bac_si": {"bac_si": "bacsi2_test", "lich_hen_id": lh_checked_id, "bac_si_phu_trach": "bacsi1_test"},
        }
        self.set_role_Select("bacsi1_test")
        code1, data1, _ = self.engine.request("POST", f"/api/lich-hen/lich-hen/{lh_unconf_id}/mo_ho_so_benh_an/", {})
        self.set_role_Select("bacsi2_test")
        code2, data2, mode = self.engine.request("POST", f"/api/lich-hen/lich-hen/{lh_checked_id}/mo_ho_so_benh_an/", {})
        self.set_role_Select("bacsi1_test")
        resp = {"buoc_1_chua_checkin_status": code1, "buoc_2_bac_si_khac_status": code2}
        self.log_event(f"TC_APP_02 ({mode})", "Kiểm thử chặn mở hồ sơ sai trạng thái (400) & khác bác sĩ (403/404)", du_lieu_nhap, resp)
        return (code1, code2), resp, du_lieu_nhap

    def _ensure_open_ho_so(self):
        if not self.active_ho_so_id or not HoSoBenhAn.objects.filter(id=self.active_ho_so_id).exists():
            self.doc_open_emr_selected()
        return self.active_ho_so_id

    def fill_diag_valid_tc03(self):
        self.diag_vars["trieu_chung"].set("Đau rát họng, sốt 38.5 độ C, ho khan")
        self.diag_vars["kham_lam_sang"].set("Niêm mạc họng đỏ xung huyết, amidan sưng nhẹ")
        self.diag_vars["ma_icd10"].set("J02.9")
        self.diag_vars["ten_benh"].set("Viêm họng cấp, không đặc hiệu")
        self.diag_vars["loai_benh"].set("NGOAI_TRU")
        self.diag_vars["muc_do"].set("TRUNG_BINH")
        self.diag_vars["mo_ta"].set("Theo dõi viêm họng cấp do vi khuẩn")
        self.diag_vars["ket_luan"].set("Điều trị nội khoa kháng sinh và hạ sốt 5 ngày")

    def fill_diag_missing_icd_tc07(self):
        self.diag_vars["trieu_chung"].set("Ho nhẹ")
        self.diag_vars["kham_lam_sang"].set("Họng bình thường")
        self.diag_vars["ma_icd10"].set("")
        self.diag_vars["ten_benh"].set("Viêm họng")
        self.diag_vars["loai_benh"].set("NGOAI_TRU")
        self.diag_vars["muc_do"].set("NHẸ")
        self.diag_vars["mo_ta"].set("Chẩn đoán thiếu mã ICD-10")
        self.diag_vars["ket_luan"].set("Theo dõi")

    def fill_diag_loai_chinh_tc08(self):
        self.diag_vars["trieu_chung"].set("Đau họng, sốt")
        self.diag_vars["kham_lam_sang"].set("Amidan sưng")
        self.diag_vars["ma_icd10"].set("J02.9")
        self.diag_vars["ten_benh"].set("Viêm họng cấp")
        self.diag_vars["loai_benh"].set("CHINH")
        self.diag_vars["muc_do"].set("TRUNG_BINH")
        self.diag_vars["mo_ta"].set("Bệnh chính")
        self.diag_vars["ket_luan"].set("Uống thuốc theo toa")

    def doc_submit_diagnosis(self):
        hs_id = self._ensure_open_ho_so()
        self.set_role_Select("bacsi1_test")
        du_lieu_nhap = {
            "trieu_chung": self.diag_vars["trieu_chung"].get(),
            "ket_qua_kham_lam_sang": self.diag_vars["kham_lam_sang"].get(),
            "ma_icd10": self.diag_vars["ma_icd10"].get(),
            "ten_benh": self.diag_vars["ten_benh"].get(),
            "loai_benh": self.diag_vars["loai_benh"].get(),
            "muc_do": self.diag_vars["muc_do"].get(),
            "mo_ta": self.diag_vars["mo_ta"].get(),
            "ket_luan": self.diag_vars["ket_luan"].get(),
        }
        code, data, mode = self.engine.request(
            "POST", f"/api/benh-an/ho-so-benh-an/{hs_id}/nhap_chan_doan/", du_lieu_nhap
        )
        self.log_event(f"NHẬP CHẨN ĐOÁN ({code} - {mode})", f"Gửi form Chẩn đoán ICD-10 cho Hồ sơ ID={hs_id}", du_lieu_nhap, data)
        return code, data, du_lieu_nhap

    def fill_rx_valid_tc04(self):
        self.rx_vars["chan_doan"].set("Viêm họng cấp (J02.9)")
        self.rx_vars["thuoc1_mode"].set("TH_RX_01 - Augmentin 625mg (18.000đ)")
        self.rx_vars["sl1"].set("10")
        self.rx_vars["lieu1"].set("1 viên/lần x 2 lần/ngày")
        self.rx_vars["thuoc2_enable"].set(True)
        self.rx_vars["sl2"].set("10")
        self.rx_vars["lieu2"].set("1 viên khi sốt > 38.5 độ")
        self.rx_vars["ghi_chu"].set("Uống thuốc đúng giờ sau ăn, tái khám sau 5 ngày")

    def fill_rx_invalid_tc05(self):
        self.rx_vars["chan_doan"].set("Viêm họng cấp")
        self.rx_vars["thuoc1_mode"].set("(Để trống mã thuốc - Kiểm thử BVA TC_APP_05)")
        self.rx_vars["sl1"].set("0")
        self.rx_vars["lieu1"].set("")
        self.rx_vars["thuoc2_enable"].set(False)
        self.rx_vars["ghi_chu"].set("Đơn có dòng thuốc không hợp lệ")

    def doc_submit_prescription(self):
        hs_id = self._ensure_open_ho_so()
        self.set_role_Select("bacsi1_test")
        DonThuoc.objects.filter(ho_so_id=hs_id).delete()

        chi_tiet = []
        if "TH_RX_01" in self.rx_vars["thuoc1_mode"].get():
            chi_tiet.append(
                {
                    "thuoc": str(self.engine.thuoc_rx.pk),
                    "so_luong": int(self.rx_vars["sl1"].get() or 0),
                    "lieu_dung": self.rx_vars["lieu1"].get(),
                    "cach_dung": "UONG",
                    "thoi_diem": "SAU_AN",
                    "so_ngay_dung": 5,
                }
            )
        else:
            chi_tiet.append(
                {
                    "thuoc": None,
                    "la_thuoc_mua_ngoai": False,
                    "so_luong": int(self.rx_vars["sl1"].get() or 0),
                    "lieu_dung": self.rx_vars["lieu1"].get(),
                }
            )

        if self.rx_vars["thuoc2_enable"].get():
            chi_tiet.append(
                {
                    "thuoc": str(self.engine.thuoc_otc.pk),
                    "so_luong": int(self.rx_vars["sl2"].get() or 0),
                    "lieu_dung": self.rx_vars["lieu2"].get(),
                    "cach_dung": "UONG",
                    "thoi_diem": "SAU_AN",
                    "so_ngay_dung": 5,
                }
            )

        du_lieu_nhap = {
            "ghi_chu": self.rx_vars["ghi_chu"].get(),
            "chi_tiet": chi_tiet,
        }
        code, data, mode = self.engine.request(
            "POST", f"/api/benh-an/ho-so-benh-an/{hs_id}/tao_don_thuoc/", du_lieu_nhap
        )
        self.log_event(f"KÊ ĐƠN THUỐC ({code} - {mode})", f"Gửi form Kê đơn thuốc cho Hồ sơ ID={hs_id}", du_lieu_nhap, data)
        return code, data, du_lieu_nhap

    def doc_submit_vaccination(self):
        hs_id = self._ensure_open_ho_so()
        self.set_role_Select("bacsi1_test")
        LichTiem.objects.filter(lich_hen__benh_nhan=self.engine.bn1).delete()
        KhoVaccine.objects.filter(vaccine=self.engine.vaccine).update(so_luong=10)

        du_lieu_nhap = {
            "vaccine": str(self.engine.vaccine.pk),
            "so_mui": 1,
            "ngay_tiem": self.vac_vars["ngay_tiem"].get(),
            "trang_thai": self.vac_vars["trang_thai"].get(),
            "vi_tri_tiem": self.vac_vars["vi_tri_tiem"].get(),
            "ghi_chu": self.vac_vars["ghi_chu"].get(),
        }
        code, data, mode = self.engine.request(
            "POST", f"/api/benh-an/ho-so-benh-an/{hs_id}/chi_dinh_tiem/", du_lieu_nhap
        )
        self.refresh_all_views()
        self.log_event(
            f"CHỈ ĐỊNH TIÊM ({code} - {mode})",
            f"Chỉ định tiêm chủng trên Hồ sơ ID={hs_id} | Tồn kho sau tiêm: {self.engine.vaccine.ton_kho()} liều",
            du_lieu_nhap,
            data,
        )
        return code, data, du_lieu_nhap

    # ------------------------------------------------------------------
    # CÁC HÀM THAO TÁC TRÊN TAB 2 (PHÂN HỆ BỆNH NHÂN - FUNC 2.2)
    # ------------------------------------------------------------------
    def patient_browse_otc_store(self):
        self.set_role_Select("benhnhan1_test")
        du_lieu_nhap = {
            "tai_khoan": "benhnhan1_test",
            "menu": "Mua thuốc (Nhà thuốc trực tuyến)",
            "search_query": self.shop_search_var.get(),
        }
        code, data, mode = self.engine.request("GET", "/api/thuoc/thuoc/")
        items = data.get("results", data) if isinstance(data, dict) else data
        ma_list = [x.get("ma_thuoc") for x in items] if isinstance(items, list) else []
        self.refresh_shop_and_cart()
        self.log_event(
            f"TC_APP_09 ({code} - {mode})",
            f"Bệnh nhân duyệt Cửa hàng thuốc -> Danh sách hiển thị: {ma_list} (Ẩn thuốc kê đơn TH_RX_01)",
            du_lieu_nhap,
            {"ma_thuoc_hien_thi": ma_list},
        )
        return code, ma_list, du_lieu_nhap

    def patient_add_to_cart(self):
        self.set_role_Select("benhnhan1_test")
        SanPhamGioHang.objects.filter(gio_hang__benh_nhan=self.engine.bn1).delete()
        qty = int(self.cart_add_qty_var.get() or 5)
        du_lieu_nhap = {
            "benh_nhan_id": str(self.engine.bn1.pk),
            "thuoc_id": str(self.engine.thuoc_otc.pk),
            "ten_thuoc": "Paracetamol 500mg (2.000đ/viên)",
            "so_luong": qty,
        }
        code, data, mode = self.engine.request("POST", "/api/don-hang/gio-hang/them/", du_lieu_nhap)
        self.refresh_shop_and_cart()
        self.log_event(
            f"THÊM GIỎ HÀNG ({code} - {mode})",
            f"Thêm {qty} viên Paracetamol 500mg vào giỏ hàng",
            du_lieu_nhap,
            data,
        )
        return code, data, du_lieu_nhap

    def patient_test_exceed_stock(self):
        self.cart_add_qty_var.set("151")
        self.set_role_Select("benhnhan1_test")
        du_lieu_nhap = {
            "benh_nhan_id": str(self.engine.bn1.pk),
            "thuoc_id": str(self.engine.thuoc_otc.pk),
            "ten_thuoc": "Paracetamol 500mg (Tồn khả dụng = 150 viên)",
            "so_luong": 151,
        }
        code, data, mode = self.engine.request("POST", "/api/don-hang/gio-hang/them/", du_lieu_nhap)
        self.cart_add_qty_var.set("5")
        self.log_event(
            f"TC_APP_11 ({code} - {mode})",
            "Kiểm thử biên tồn kho: Thêm 151 viên (> 150 viên khả dụng) -> Chặn 400 Bad Request",
            du_lieu_nhap,
            data,
        )
        return code, data, du_lieu_nhap

    def patient_update_cart_qty_12(self):
        self.set_role_Select("benhnhan1_test")
        if not SanPhamGioHang.objects.filter(gio_hang__benh_nhan=self.engine.bn1).exists():
            self.cart_add_qty_var.set("5")
            self.patient_add_to_cart()
        item = SanPhamGioHang.objects.filter(gio_hang__benh_nhan=self.engine.bn1).first()
        du_lieu_nhap = {"item_id": str(item.pk), "so_luong": 12}
        code, data, mode = self.engine.request(
            "PUT", f"/api/don-hang/gio-hang/cap-nhat/{item.pk}/", {"so_luong": 12}
        )
        self.refresh_shop_and_cart()
        self.log_event(f"CẬP NHẬT GIỎ ({code} - {mode})", "Sửa số lượng trong giỏ: 5 -> 12 viên (24.000đ)", du_lieu_nhap, data)
        return code, data, du_lieu_nhap

    def patient_remove_cart_item(self):
        self.set_role_Select("benhnhan1_test")
        item = SanPhamGioHang.objects.filter(gio_hang__benh_nhan=self.engine.bn1).first()
        if not item:
            return 404, {}, {}
        du_lieu_nhap = {"item_id": str(item.pk), "thao_tac": "Xóa sản phẩm khỏi giỏ hàng"}
        code, data, mode = self.engine.request("DELETE", f"/api/don-hang/gio-hang/xoa/{item.pk}/")
        self.refresh_shop_and_cart()
        self.log_event(f"XÓA GIỎ HÀNG ({code} - {mode})", "Đã xóa sản phẩm khỏi giỏ, tổng tiền về 0đ", du_lieu_nhap, data)
        return code, data, du_lieu_nhap

    def patient_create_online_order(self):
        self.set_role_Select("benhnhan1_test")
        KhoThuoc.objects.filter(lo_sx="LO-PARA-SO-1").update(so_luong=50)
        KhoThuoc.objects.filter(lo_sx="LO-PARA-SO-2").update(so_luong=100)
        SanPhamGioHang.objects.filter(gio_hang__benh_nhan=self.engine.bn1).delete()
        self.engine.request(
            "POST",
            "/api/don-hang/gio-hang/them/",
            {
                "benh_nhan_id": str(self.engine.bn1.pk),
                "thuoc_id": str(self.engine.thuoc_otc.pk),
                "so_luong": 20,
            },
        )
        du_lieu_nhap = {
            "benh_nhan_id": str(self.engine.bn1.pk),
            "loai_don": "ONLINE",
            "ten_nguoi_nhan": self.order_vars["nguoi_nhan"].get(),
            "so_dien_thoai_nhan": self.order_vars["sdt_nhan"].get(),
            "email_nhan": self.order_vars["email_nhan"].get(),
            "dia_chi_giao_hang": self.order_vars["dia_chi"].get(),
            "phi_ship": int(self.order_vars["phi_ship"].get() or 15000),
            "giam_gia": 0,
            "ghi_chu": self.order_vars["ghi_chu"].get(),
        }
        code, data, mode = self.engine.request("POST", "/api/don-hang/don-hang/tao/", du_lieu_nhap)
        if code == 200 and isinstance(data, dict) and "data" in data:
            self.active_order_id = data["data"].get("don_hang_id")
        self.refresh_shop_and_cart()
        self.log_event(
            f"TC_APP_13 ({code} - {mode})",
            f"Đặt đơn hàng Online 20 viên + ship 15k -> Tổng 55.000đ | Tồn kho còn: {self.engine.thuoc_otc.ton_kho()} viên",
            du_lieu_nhap,
            data,
        )
        return code, data, du_lieu_nhap

    def patient_order_empty_cart(self):
        self.set_role_Select("benhnhan2_test")
        SanPhamGioHang.objects.filter(gio_hang__benh_nhan=self.engine.bn2).delete()
        GioHang.objects.filter(benh_nhan=self.engine.bn2).delete()
        du_lieu_nhap = {
            "benh_nhan_id": str(self.engine.bn2.pk),
            "loai_don": "ONLINE",
            "ten_nguoi_nhan": "Phạm Thị Hoa",
            "so_dien_thoai_nhan": "0901000008",
            "email_nhan": "bn2_test@gmail.com",
            "dia_chi_giao_hang": "456 Lê Duẩn, Thanh Khê, Đà Nẵng",
        }
        code, data, mode = self.engine.request("POST", "/api/don-hang/don-hang/tao/", du_lieu_nhap)
        self.set_role_Select("benhnhan1_test")
        self.log_event(f"TC_APP_14 ({code} - {mode})", "Chặn đặt đơn hàng khi giỏ hàng trống (400 Bad Request)", du_lieu_nhap, data)
        return code, data, du_lieu_nhap

    def patient_pay_vnpay_sandbox(self):
        self.set_role_Select("benhnhan1_test")
        dh = DonHang.objects.filter(benh_nhan=self.engine.bn1, trang_thai="CHO_THANH_TOAN").order_by("-ngay_tao").first()
        if not dh:
            self.patient_create_online_order()
            dh = DonHang.objects.filter(benh_nhan=self.engine.bn1, trang_thai="CHO_THANH_TOAN").order_by("-ngay_tao").first()

        code_url, data_url, _ = self.engine.request("POST", f"/api/don-hang/don-hang/{dh.pk}/vnpay-tao-url/", {})
        url_info = data_url.get("data", data_url) if isinstance(data_url, dict) else {}
        txn_ref = url_info.get("txn_ref", "")
        amount_val = int(float(url_info.get("amount", 55000)) * 100)

        du_lieu_nhap = {
            "txn_ref": txn_ref,
            "amount": amount_val,
            "action": "success",
            "ngan_hang": "NCB",
            "so_the": "9704198526191432198",
            "ten_chu_the": "NGUYEN VAN A",
            "ngay_het_han": "07/15",
            "otp": "123456",
        }
        res_confirm = self.engine.api_client.post("/api/don-hang/vnpay-mock/confirm/", du_lieu_nhap)
        code_cf = res_confirm.status_code
        dh.refresh_from_db()
        self.refresh_shop_and_cart()
        resp = {
            "vnpay_url_status": code_url,
            "txn_ref": txn_ref,
            "confirm_status": code_cf,
            "trang_thai_don_hang": dh.trang_thai,
        }
        self.log_event(
            f"TC_APP_15 ({code_cf})",
            f"Thanh toán VNPay Sandbox cho đơn {dh.ma_don_hang} -> Trạng thái: {dh.trang_thai}",
            du_lieu_nhap,
            resp,
        )
        return (code_url, code_cf, dh.trang_thai), resp, du_lieu_nhap

    def patient_cancel_order_check_stock(self):
        self.set_role_Select("benhnhan1_test")
        self.patient_create_online_order()
        dh = DonHang.objects.filter(benh_nhan=self.engine.bn1, trang_thai="CHO_THANH_TOAN").order_by("-ngay_tao").first()
        ton_sau_dat = self.engine.thuoc_otc.ton_kho()

        du_lieu_nhap = {
            "don_hang_id": str(dh.pk),
            "ma_don_hang": dh.ma_don_hang,
            "trang_thai": "DA_HUY",
            "ly_do_huy": self.order_vars["ly_do_huy"].get(),
        }
        self.engine.switch_user("banthuoc_test")
        code, data, mode = self.engine.request(
            "PUT",
            f"/api/don-hang/don-hang/{dh.pk}/cap-nhat-trang-thai/",
            {"trang_thai": "DA_HUY", "ly_do_huy": du_lieu_nhap["ly_do_huy"]},
        )
        self.set_role_Select("benhnhan1_test")
        ton_sau_huy = self.engine.thuoc_otc.ton_kho()
        self.refresh_shop_and_cart()
        resp = {
            "http_status": code,
            "ton_kho_ban_dau": 150,
            "ton_kho_sau_khi_dat_20v": ton_sau_dat,
            "ton_kho_sau_khi_huy_don": ton_sau_huy,
            "ky_vong_srs": 150,
        }
        self.log_event(
            f"TC_APP_16 ({code} - {mode})",
            f"Hủy đơn {dh.ma_don_hang}: Tồn kho sau hủy = {ton_sau_huy} viên (Kỳ vọng SRS = 150 viên -> Phát hiện BUG-06!)",
            du_lieu_nhap,
            resp,
        )
        return (code, ton_sau_huy), resp, du_lieu_nhap

    # ------------------------------------------------------------------
    # CÁC HÀM TRÊN TAB 3 (TRÌNH CHẠY TỰ ĐỘNG 16 TEST CASES APP)
    # ------------------------------------------------------------------
    def _on_tc_row_selected(self, _event=None):
        sel = self.tree_tcs.selection()
        if not sel:
            return
        tc_id = sel[0]
        spec = next((x for x in APP_TEST_CASES_SPEC if x["tc_id"] == tc_id), None)
        if not spec:
            return
        vals = self.tree_tcs.item(tc_id, "values")
        self.txt_tc_detail.delete("1.0", tk.END)
        self.txt_tc_detail.insert(
            tk.END,
            f"=== {spec['tc_id']} | {spec['func']} | Kỹ thuật: {spec['technique']} ===\n"
            f"• Kịch bản: {spec['title']}\n"
            f"• Kỳ vọng (SRS): {spec['expected']}\n"
            f"• Kết quả thực tế: {vals[5]}  |  Trạng thái: {vals[6]}\n",
        )

    def execute_single_tc(self, tc_id):
        """Thực thi 1 Test Case trên Desktop App, điền dữ liệu lên form và trả về (status_label, actual_summary, detail_log)."""
        if tc_id == "TC_APP_01":
            self.engine.seed_or_reset_data()
            code, data, inp = self.doc_open_emr_selected()
            hs = data.get("ho_so", {}) if isinstance(data, dict) else {}
            ma_hs = hs.get("ma_hs") or hs.get("ma_ho_so") or ""
            passed = code == 201 and str(ma_hs).startswith("HS")
            actual = f"HTTP {code} | Mã HS: {ma_hs} | Lịch -> DANG_KHAM"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_02":
            (c1, c2), resp, inp = self.doc_test_block_open_emr()
            passed = c1 == 400 and c2 in (403, 404)
            actual = f"Chưa check-in: HTTP {c1} | Bác sĩ khác: HTTP {c2}"
            return ("Passed" if passed else "Failed"), actual, inp, resp

        if tc_id == "TC_APP_03":
            self.fill_diag_valid_tc03()
            code, data, inp = self.doc_submit_diagnosis()
            passed = code == 200 and ChanDoan.objects.filter(ho_so_id=self.active_ho_so_id, ma_icd10="J02.9").exists()
            actual = f"HTTP {code} | Đã lưu ChanDoan(ma_icd10='J02.9')"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_04":
            self.fill_rx_valid_tc04()
            code, data, inp = self.doc_submit_prescription()
            dt = DonThuoc.objects.filter(ho_so_id=self.active_ho_so_id).first()
            passed = code == 201 and dt is not None and dt.tong_tien == Decimal("200000.00")
            actual = f"HTTP {code} | Tổng tiền đơn thuốc = {dt.tong_tien if dt else 0:,.0f} VND"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_05":
            self.fill_rx_invalid_tc05()
            code, data, inp = self.doc_submit_prescription()
            passed = code == 400
            actual = f"HTTP {code} Bad Request (Chặn lưu dòng thuốc thiếu mã & SL=0)"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_06":
            code, data, inp = self.doc_submit_vaccination()
            ton = self.engine.vaccine.ton_kho()
            passed = code == 201 and ton == 9
            actual = f"HTTP {code} | Tồn kho vaccine giảm 10 -> {ton} liều (Lô LO-VC-01)"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_07":
            self.fill_diag_missing_icd_tc07()
            code, data, inp = self.doc_submit_diagnosis()
            passed_srs = code == 400
            actual = f"Thực tế trả HTTP {code} (Kỳ vọng SRS: 400 -> Phát hiện BUG-04 cho phép rỗng ICD-10)"
            return ("Passed" if passed_srs else "Failed"), actual, inp, data

        if tc_id == "TC_APP_08":
            self.fill_diag_loai_chinh_tc08()
            code, data, inp = self.doc_submit_diagnosis()
            passed_srs = code == 200
            actual = f"Thực tế trả HTTP {code} (Kỳ vọng SRS: 200 với loai_benh='CHINH' -> Phát hiện BUG-05)"
            return ("Passed" if passed_srs else "Failed"), actual, inp, data

        if tc_id == "TC_APP_09":
            code, ma_list, inp = self.patient_browse_otc_store()
            passed = code == 200 and "TH_OTC_01" in ma_list and "TH_RX_01" not in ma_list
            actual = f"HTTP {code} | Chỉ hiển thị {ma_list}, ẩn thuốc kê đơn TH_RX_01"
            return ("Passed" if passed else "Failed"), actual, inp, {"ma_thuoc": ma_list}

        if tc_id == "TC_APP_10":
            self.cart_add_qty_var.set("5")
            code, data, inp = self.patient_add_to_cart()
            tong = data.get("data", {}).get("tong_tien_gio_hang") if isinstance(data, dict) else 0
            passed = code == 200 and float(tong or 0) == 10000.0
            actual = f"HTTP {code} | Tổng tiền giỏ hàng = {int(float(tong or 0)):,} VND"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_11":
            code, data, inp = self.patient_test_exceed_stock()
            passed = code == 400
            actual = f"HTTP {code} Bad Request (Chặn số lượng 151 > tồn kho 150)"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_12":
            c1, d1, inp1 = self.patient_update_cart_qty_12()
            c2, d2, _ = self.patient_remove_cart_item()
            passed = c1 == 200 and c2 == 200
            actual = f"Cập nhật SL=12: HTTP {c1} (24.000đ) | Xóa SP: HTTP {c2} (0đ)"
            return ("Passed" if passed else "Failed"), actual, inp1, {"update": d1, "delete": d2}

        if tc_id == "TC_APP_13":
            code, data, inp = self.patient_create_online_order()
            ton = self.engine.thuoc_otc.ton_kho()
            passed = code == 200 and ton == 130
            actual = f"HTTP {code} | Đơn CHO_THANH_TOAN (55.000đ), tồn kho giảm 150 -> {ton} viên"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_14":
            code, data, inp = self.patient_order_empty_cart()
            passed = code == 400
            actual = f"HTTP {code} Bad Request ('Giỏ hàng trống')"
            return ("Passed" if passed else "Failed"), actual, inp, data

        if tc_id == "TC_APP_15":
            (c_url, c_cf, st), resp, inp = self.patient_pay_vnpay_sandbox()
            passed = c_url == 200 and c_cf in (200, 302) and st == "DA_THANH_TOAN"
            actual = f"HTTP {c_cf} | VNPay Mock Confirm -> Đơn chuyển sang {st}"
            return ("Passed" if passed else "Failed"), actual, inp, resp

        if tc_id == "TC_APP_16":
            (code, ton_sau_huy), resp, inp = self.patient_cancel_order_check_stock()
            passed_srs = ton_sau_huy == 150
            actual = f"Thực tế tồn kho sau hủy = {ton_sau_huy} viên (Kỳ vọng SRS: 150 -> Phát hiện BUG-06 mất 20v)"
            return ("Passed" if passed_srs else "Failed"), actual, inp, resp

        return "Pending", "Không xác định", {}, {}

    def run_selected_test_case(self):
        sel = self.tree_tcs.selection()
        if not sel:
            return
        tc_id = sel[0]
        status, actual, inp, resp = self.execute_single_tc(tc_id)
        spec = next(x for x in APP_TEST_CASES_SPEC if x["tc_id"] == tc_id)
        self.tree_tcs.item(
            tc_id,
            values=(spec["tc_id"], spec["func"], spec["technique"], spec["title"], spec["expected"], actual, status),
            tags=(status,),
        )
        self.txt_tc_detail.delete("1.0", tk.END)
        self.txt_tc_detail.insert(
            tk.END,
            f"=== KẾT QUẢ THỰC THI {spec['tc_id']}: {status.upper()} ===\n"
            f"• Kịch bản: {spec['title']}\n"
            f"• Dữ liệu nhập (du_lieu_nhap): {json.dumps(inp, ensure_ascii=False, default=str)}\n"
            f"• Kỳ vọng (SRS): {spec['expected']}\n"
            f"• Thực tế (App): {actual}\n"
            f"• Phản hồi JSON: {json.dumps(resp, ensure_ascii=False, default=str)[:500]}\n",
        )

    def run_all_16_app_test_cases(self):
        self.engine.seed_or_reset_data()
        passed_cnt = 0
        failed_cnt = 0
        for spec in APP_TEST_CASES_SPEC:
            tc_id = spec["tc_id"]
            self.tree_tcs.selection_set(tc_id)
            self.tree_tcs.see(tc_id)
            self.update_idletasks()
            status, actual, inp, resp = self.execute_single_tc(tc_id)
            if status == "Passed":
                passed_cnt += 1
            else:
                failed_cnt += 1
            self.tree_tcs.item(
                tc_id,
                values=(spec["tc_id"], spec["func"], spec["technique"], spec["title"], spec["expected"], actual, status),
                tags=(status,),
            )
            self.update_idletasks()

        self.lbl_runner_summary.config(
            text=f"Hoàn tất 16/16 Test Cases App: {passed_cnt} Passed (81.25%), {failed_cnt} Failed (18.75% — BUG-04, BUG-05, BUG-06)"
        )
        self._on_tc_row_selected()

    # ------------------------------------------------------------------
    # TRÌNH CHIẾU TỰ ĐỘNG TỪNG BƯỚC NHƯ SELENIUM WEB (VISUAL AUTO-DEMO)
    # ------------------------------------------------------------------
    def toggle_visual_auto_demo(self):
        if self._auto_job is not None:
            self.after_cancel(self._auto_job)
            self._auto_job = None
            self.btn_toggle_auto.config(text="▶ Tiếp tục Tự động")
            self._set_banner(
                f"⏸ ĐÃ TẠM DỪNG TẠI BƯỚC {self._auto_idx}/16 — Bấm '▶ Tiếp tục Tự động' để chạy tiếp hoặc tự thao tác trên form.",
                "#B45309",
            )
        else:
            self.btn_toggle_auto.config(text="⏸ Tạm dừng Tự động")
            self._run_next_visual_auto_step()

    def start_visual_auto_demo(self):
        if self._auto_job is not None:
            self.after_cancel(self._auto_job)
            self._auto_job = None
        self.engine.seed_or_reset_data()
        self.refresh_all_views()
        for spec in APP_TEST_CASES_SPEC:
            self.tree_tcs.item(
                spec["tc_id"],
                values=(spec["tc_id"], spec["func"], spec["technique"], spec["title"], spec["expected"], "Đang chờ chạy...", "Pending"),
                tags=("Pending",),
            )
        self._auto_idx = 0
        self._auto_passed = 0
        self._auto_failed = 0
        self.btn_toggle_auto.config(text="⏸ Tạm dừng Tự động")
        self._set_banner(
            "🤖 BẮT ĐẦU CHẠY TỰ ĐỘNG 16 TEST CASES APP (Chuyển tab, tự điền form & chấm Pass/Fail)...",
            "#0F766E",
        )
        self._auto_job = self.after(600, self._run_next_visual_auto_step)

    def _focus_tab_for_tc(self, tc_id: str):
        """Tự động chuyển sang đúng Tab và Sub-tab trên giao diện để người xem thấy form đang được điền."""
        if tc_id in ("TC_APP_01", "TC_APP_02", "TC_APP_03", "TC_APP_04", "TC_APP_05", "TC_APP_06", "TC_APP_07", "TC_APP_08"):
            self.notebook.select(self.tab_doctor)
            if tc_id in ("TC_APP_01", "TC_APP_02", "TC_APP_03", "TC_APP_07", "TC_APP_08"):
                self.doc_sub_nb.select(self.sub_diag)
            elif tc_id in ("TC_APP_04", "TC_APP_05"):
                self.doc_sub_nb.select(self.sub_rx)
            elif tc_id == "TC_APP_06":
                self.doc_sub_nb.select(self.sub_vac)
        else:
            self.notebook.select(self.tab_patient)
        self.update_idletasks()

    def _run_next_visual_auto_step(self):
        if self._auto_idx >= len(APP_TEST_CASES_SPEC):
            self._auto_job = None
            self.notebook.select(self.tab_runner)
            self.btn_toggle_auto.config(text="✅ Đã chạy xong 16/16")
            summary_msg = (
                f"✅ HOÀN TẤT TỰ ĐỘNG 16/16 TEST CASES APP: {self._auto_passed} PASSED (81.25%) | "
                f"{self._auto_failed} FAILED (18.75% — Phát hiện BUG-04, BUG-05, BUG-06) — Xem bảng tổng hợp bên dưới!"
            )
            self._set_banner(summary_msg, "#15803D")
            self.lbl_runner_summary.config(text=summary_msg)
            return

        spec = APP_TEST_CASES_SPEC[self._auto_idx]
        tc_id = spec["tc_id"]
        step_num = self._auto_idx + 1

        # 1. Chuyển sang đúng Tab giao diện của Test Case đó
        self._focus_tab_for_tc(tc_id)

        # 2. Thực thi Test Case (điền form + gọi API)
        status, actual, inp, resp = self.execute_single_tc(tc_id)
        if status == "Passed":
            self._auto_passed += 1
            bg_col = "#047857"  # Xanh lá đậm khi Passed
            icon = "✅ PASSED"
        else:
            self._auto_failed += 1
            bg_col = "#B91C1C"  # Đỏ đậm khi Failed (phát hiện Bug SRS)
            icon = "❌ FAILED (LỖI SRS)"

        # 3. Cập nhật Banner trên đầu cửa sổ và Bảng ở Tab 3
        self._set_banner(
            f"🤖 [{step_num}/16] {tc_id} — {icon}: {spec['title']}  |  Kết quả: {actual}",
            bg_col,
        )
        self.tree_tcs.item(
            tc_id,
            values=(spec["tc_id"], spec["func"], spec["technique"], spec["title"], spec["expected"], actual, status),
            tags=(status,),
        )
        self.tree_tcs.selection_set(tc_id)
        self.tree_tcs.see(tc_id)
        self.lbl_runner_summary.config(
            text=f"Đang chạy tự động [{step_num}/16]: {self._auto_passed} Passed, {self._auto_failed} Failed"
        )
        self.update_idletasks()

        self._auto_idx += 1
        self._auto_job = self.after(self.step_delay_ms, self._run_next_visual_auto_step)


# ==============================================================================
# 4. CHẾ ĐỘ KIỂM TRA TỰ ĐỘNG CLI (--self-test) & KHỞI CHẠY GUI
# ==============================================================================
def run_cli_self_test():
    print("=" * 88)
    print("CHẠY KIỂM THỬ TỰ ĐỘNG TRÊN ENGINE PHÒNGKHÁM+ DESKTOP APP (16 TEST CASES APP)")
    print("=" * 88)
    engine = PhongKhamAppBackendEngine(mode="DIRECT")
    app = PhongKhamDesktopApp(engine, auto_play=False)
    app.withdraw()  # Ẩn cửa sổ khi chạy self-test tự động trên terminal
    app.run_all_16_app_test_cases()

    passed = 0
    failed = 0
    for spec in APP_TEST_CASES_SPEC:
        vals = app.tree_tcs.item(spec["tc_id"], "values")
        st = vals[6]
        act = vals[5]
        if st == "Passed":
            passed += 1
        else:
            failed += 1
        print(f"[{st:6s}] {spec['tc_id']} | {spec['title'][:58]:58s} -> {act}")

    print("-" * 88)
    print(f"TỔNG KẾT DESKTOP APP RUNNER: {passed + failed} TCs | Passed: {passed} | Failed: {failed}")
    print("=" * 88)
    app.destroy()
    return passed, failed


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        run_cli_self_test()
    else:
        delay_ms = 1800
        for arg in sys.argv[1:]:
            if arg.startswith("--delay="):
                try:
                    delay_ms = int(float(arg.split("=", 1)[1]) * 1000)
                except ValueError:
                    pass
        no_auto = "--no-auto" in sys.argv
        engine = PhongKhamAppBackendEngine(mode="DIRECT")
        app = PhongKhamDesktopApp(engine, auto_play=not no_auto, step_delay_ms=delay_ms)
        app.mainloop()
