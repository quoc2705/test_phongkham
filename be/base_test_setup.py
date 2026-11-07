# -*- coding: utf-8 -*-
"""
Dữ liệu nền dùng chung (Test Fixture Setup) cho 5 file kiểm thử theo 5 Feature:
1. be/test_feature1_web.py         (Feature 1: Web SPA)
2. be/test_feature2_app.py         (Feature 2: App Workflow)
3. be/test_feature3_performance.py (Feature 3: Performance & Concurrency)
4. be/test_feature4_api.py         (Feature 4: REST API & RBAC)
5. be/test_feature5_unit.py        (Feature 5: Unit Testing)
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from nguoidung.models import NguoiDung, BacSi, BenhNhan, NhanVien, DoctorSchedule
from thuoc.models import (
    LoaiThuoc,
    DonViTinh,
    NhaCungCap,
    Thuoc,
    KhoThuoc,
    LoaiVaccine,
    Vaccine,
    KhoVaccine,
)


class BasePhongKhamTestSetup(TestCase):
    """Khởi tạo dữ liệu nền chuẩn cho các bộ kiểm thử Hệ thống Quản lý Phòng khám PhòngKhám+."""

    def setUp(self):
        self.today = timezone.localdate()
        self.now = timezone.now()

        # 1. Tài khoản Quản trị viên (ADMIN)
        self.u_admin = NguoiDung.objects.create_user(
            ten_dang_nhap='admin_test',
            email='admin_test@phongkham.vn',
            password='Password@123',
            ho_ten='Quản Trị Viên Test',
            so_dien_thoai='0901000001',
            vai_tro='ADMIN',
            is_staff=True,
            is_superuser=True,
        )

        # 2. Tài khoản Bác sĩ 1 (có đăng ký lịch trực) & Bác sĩ 2 (chưa đăng ký lịch trực)
        self.u_bacsi1 = NguoiDung.objects.create_user(
            ten_dang_nhap='bacsi1_test',
            email='bacsi1_test@phongkham.vn',
            password='Password@123',
            ho_ten='BS. Nguyễn Văn An',
            so_dien_thoai='0901000002',
            vai_tro='BAC_SI',
        )
        self.bacsi1 = BacSi.objects.create(
            nguoi_dung=self.u_bacsi1,
            ma_bac_si='BS_TEST_01',
            chuyen_khoa='Nội tổng quát',
            so_giay_phep='CCHN-001',
            trinh_do='THAC_SI',
            chuc_vu='BAC_SI_DIEU_TRI',
            is_working=True,
        )

        self.u_bacsi2 = NguoiDung.objects.create_user(
            ten_dang_nhap='bacsi2_test',
            email='bacsi2_test@phongkham.vn',
            password='Password@123',
            ho_ten='BS. Trần Thị Bình',
            so_dien_thoai='0901000003',
            vai_tro='BAC_SI',
        )
        self.bacsi2 = BacSi.objects.create(
            nguoi_dung=self.u_bacsi2,
            ma_bac_si='BS_TEST_02',
            chuyen_khoa='Nhi khoa & Tiêm chủng',
            so_giay_phep='CCHN-002',
            trinh_do='BAC_SI_CK1',
            chuc_vu='BAC_SI_DIEU_TRI',
            is_working=True,
        )

        # Đăng ký ca làm cho bác sĩ 1 (hôm nay và 2 ngày tới, cả 3 ca)
        for d in (self.today, self.today + timedelta(days=1), self.today + timedelta(days=2)):
            for ca in ('SANG', 'CHIEU', 'TOI'):
                DoctorSchedule.objects.create(
                    bac_si=self.bacsi1,
                    ngay_lam=d,
                    ca_lam=ca,
                    ghi_chu='Ca trực định kỳ',
                )

        # 3. Nhân viên Lễ tân, Bán thuốc, Kế toán
        self.u_letan = NguoiDung.objects.create_user(
            ten_dang_nhap='letan_test',
            email='letan_test@phongkham.vn',
            password='Password@123',
            ho_ten='NV Lễ Tân Lê Hoa',
            so_dien_thoai='0901000004',
            vai_tro='NHAN_VIEN',
        )
        self.nv_letan = NhanVien.objects.create(
            nguoi_dung=self.u_letan,
            ma_nhan_vien='NV_LT_01',
            chuc_vu='LE_TAN',
            phong_ban='Quầy Tiếp Đón',
            ngay_bat_dau_lam=self.today - timedelta(days=365),
            is_working=True,
        )

        self.u_banthuoc = NguoiDung.objects.create_user(
            ten_dang_nhap='banthuoc_test',
            email='banthuoc_test@phongkham.vn',
            password='Password@123',
            ho_ten='DS. Phạm Minh Dược',
            so_dien_thoai='0901000005',
            vai_tro='NHAN_VIEN',
        )
        self.nv_banthuoc = NhanVien.objects.create(
            nguoi_dung=self.u_banthuoc,
            ma_nhan_vien='NV_BT_01',
            chuc_vu='BAN_THUOC',
            phong_ban='Nhà Thuốc Phòng Khám',
            ngay_bat_dau_lam=self.today - timedelta(days=300),
            is_working=True,
        )

        self.u_ketoan = NguoiDung.objects.create_user(
            ten_dang_nhap='ketoan_test',
            email='ketoan_test@phongkham.vn',
            password='Password@123',
            ho_ten='KT. Hoàng Thị Thu',
            so_dien_thoai='0901000006',
            vai_tro='NHAN_VIEN',
        )
        self.nv_ketoan = NhanVien.objects.create(
            nguoi_dung=self.u_ketoan,
            ma_nhan_vien='NV_KT_01',
            chuc_vu='KE_TOAN',
            phong_ban='Phòng Tài Chính Kế Toán',
            ngay_bat_dau_lam=self.today - timedelta(days=400),
            is_working=True,
        )

        # 4. Bệnh nhân 1 & Bệnh nhân 2
        self.u_bn1 = NguoiDung.objects.create_user(
            ten_dang_nhap='benhnhan1_test',
            email='bn1_test@gmail.com',
            password='Password@123',
            ho_ten='Lê Văn Bệnh Nhân',
            so_dien_thoai='0901000007',
            vai_tro='BENH_NHAN',
        )
        self.bn1 = BenhNhan.objects.create(
            nguoi_dung=self.u_bn1,
            ma_benh_nhan='BN_TEST_01',
            ngay_sinh=date(1996, 5, 15),
            gioi_tinh='NAM',
            dia_chi='123 Nguyễn Văn Linh, Đà Nẵng',
            nhom_mau='O+',
            chieu_cao=Decimal('170.00'),
            can_nang=Decimal('65.00'),
            so_bao_hiem='DN4010123456789',
            ngay_het_han_bhyt=self.today + timedelta(days=180),
        )

        self.u_bn2 = NguoiDung.objects.create_user(
            ten_dang_nhap='benhnhan2_test',
            email='bn2_test@gmail.com',
            password='Password@123',
            ho_ten='Trần Thị Khách Hàng',
            so_dien_thoai='0901000008',
            vai_tro='BENH_NHAN',
        )
        self.bn2 = BenhNhan.objects.create(
            nguoi_dung=self.u_bn2,
            ma_benh_nhan='BN_TEST_02',
            ngay_sinh=date(2000, 10, 20),
            gioi_tinh='NU',
            dia_chi='456 Lê Duẩn, Đà Nẵng',
            nhom_mau='A+',
            chieu_cao=Decimal('160.00'),
            can_nang=Decimal('52.00'),
        )

        # 5. Danh mục Thuốc, Vaccine & Kho
        self.loai_thuoc = LoaiThuoc.objects.create(ten_loai='Giảm đau - Hạ sốt', mo_ta='Nhóm OTC')
        self.don_vi = DonViTinh.objects.create(ten_don_vi='Viên', ky_hieu='vien')
        self.ncc = NhaCungCap.objects.create(
            ma_ncc='NCC_TEST_01',
            ten_ncc='Công ty Dược Phẩm Trung Ương 1',
            so_dien_thoai='0243888999',
            dia_chi='Hà Nội',
            trang_thai=True,
        )

        # Thuốc OTC (không cần đơn)
        self.thuoc_otc = Thuoc.objects.create(
            ma_thuoc='TH_OTC_01',
            ten_thuoc='Paracetamol 500mg',
            loai_thuoc=self.loai_thuoc,
            don_vi=self.don_vi,
            gia_ban=Decimal('2000.00'),
            don_gia_nhap=Decimal('1200.00'),
            can_don_thuoc=False,
            can_tu_van=False,
            trang_thai=True,
        )
        self.kho_thuoc_otc_lo1 = KhoThuoc.objects.create(
            thuoc=self.thuoc_otc,
            so_luong=50,
            ngay_nhap=self.today - timedelta(days=30),
            han_su_dung=self.today + timedelta(days=60),
            lo_sx='LO-PARA-SO-1',
        )
        self.kho_thuoc_otc_lo2 = KhoThuoc.objects.create(
            thuoc=self.thuoc_otc,
            so_luong=100,
            ngay_nhap=self.today - timedelta(days=10),
            han_su_dung=self.today + timedelta(days=180),
            lo_sx='LO-PARA-SO-2',
        )

        # Thuốc kê đơn (Rx - can_don_thuoc=True)
        self.thuoc_rx = Thuoc.objects.create(
            ma_thuoc='TH_RX_01',
            ten_thuoc='Augmentin 625mg',
            loai_thuoc=self.loai_thuoc,
            don_vi=self.don_vi,
            gia_ban=Decimal('18000.00'),
            don_gia_nhap=Decimal('14000.00'),
            can_don_thuoc=True,
            can_tu_van=True,
            trang_thai=True,
        )
        self.kho_thuoc_rx = KhoThuoc.objects.create(
            thuoc=self.thuoc_rx,
            so_luong=80,
            ngay_nhap=self.today - timedelta(days=15),
            han_su_dung=self.today + timedelta(days=200),
            lo_sx='LO-AUG-01',
        )

        # Vaccine
        self.loai_vc = LoaiVaccine.objects.create(ten_loai='Vaccine Cúm mùa')
        self.vaccine = Vaccine.objects.create(
            ma_vaccine='VC_TEST_01',
            ten_vaccine='Influvac Tetra 0.5ml',
            loai_vaccine=self.loai_vc,
            nha_cung_cap=self.ncc,
            gia_tiem=Decimal('350000.00'),
            gia_nhap=Decimal('280000.00'),
            phong_benh='Cúm mùa A/B',
            do_tuoi_ap_dung='Từ 6 tháng tuổi',
            so_mui=1,
            trang_thai=True,
        )
        self.kho_vc_lo1 = KhoVaccine.objects.create(
            vaccine=self.vaccine,
            so_luong=10,
            ngay_nhap=self.today - timedelta(days=20),
            han_su_dung=self.today + timedelta(days=90),
            lo_sx='LO-VC-01',
        )

        self.api_client = APIClient()
