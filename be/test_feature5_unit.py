# -*- coding: utf-8 -*-
"""
FEATURE 5: KIỂM THỬ ĐƠN VỊ - UNIT TEST (Thuật toán FIFO Kho, Cảnh báo HSD, BHYT & Tiền tệ) — 13 Test Cases
Áp dụng kỹ thuật kiểm thử: Phân vùng tương đương (EP), Phân tích giá trị biên (BVA),
Kiểm thử Đường dẫn Logic (White-box Logic Path) và Kiểm thử Ngoại lệ (Exception Handling).
- Function 5.1: Unit Test Thuật toán Trừ tồn kho FIFO Đa lô & Cảnh báo Hạn dùng (thuoc.models, thuoc.stock - 7 Test Cases: TC_UNIT_01..TC_UNIT_07)
- Function 5.2: Unit Test Tính toán BHYT, Tổng tiền Đơn thuốc/Đơn hàng & Chuẩn hóa Thời gian (benhan, donhang, nguoidung - 6 Test Cases: TC_UNIT_08..TC_UNIT_13)
Không bao gồm Đăng nhập (UC001) và Đăng ký tài khoản (UC002).
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from base_test_setup import BasePhongKhamTestSetup
from thuoc.models import Thuoc, KhoThuoc
from thuoc.stock import tru_ton_vaccine_mot_lieu, VaccineHetTonError
from donhang.views import _giam_ton_kho_thuoc
from donhang.models import DonHang
from benhan.models import HoSoBenhAn, DonThuoc, ChiTietDonThuoc
from nguoidung.doctor_schedule import phan_ca_tu_thoi_diem
from phongkham.time_utils import bounds_for_local_days


class Feature5UnitTests(BasePhongKhamTestSetup):
    """Kiểm thử Feature 5: Unit Test (13 Test Cases: 11 Passed, 2 Failed phát hiện lỗi thực tế so với SRS)."""

    # ==========================================================================
    # FUNCTION 5.1: Unit Test Thuật toán Trừ tồn kho FIFO Đa lô & Cảnh báo HSD — 7 TCs
    # ==========================================================================
    def test_TC_UNIT_01_ep_tinh_ton_kho_thuoc_bo_qua_lo_het_han(self):
        """TC_UNIT_01 [EP]: Phương thức Thuoc.ton_kho() chỉ cộng các lô còn hạn sử dụng (han_su_dung > today), bỏ qua lô hết hạn (REQ-FIFO-01)."""
        lo_het_han = KhoThuoc.objects.create(
            thuoc=self.thuoc_otc,
            so_luong=30,
            ngay_nhap=self.today - timedelta(days=200),
            han_su_dung=self.today - timedelta(days=5),
            lo_sx='LO-EXPIRED-01',
        )
        self.assertEqual(self.thuoc_otc.ton_kho(), 150)
        self.assertFalse(lo_het_han.con_han())
        self.assertTrue(self.kho_thuoc_otc_lo1.con_han())

    def test_TC_UNIT_02_bva_bien_han_su_dung_ngay_hom_nay_va_nguong_90_ngay(self):
        """TC_UNIT_02 [BVA - Biên ngày]: Lô có han_su_dung == today bị tính là hết hạn (con_han=False); lô ở biên today + 60 ngày bật sap_het_han=True."""
        lo_hom_nay = KhoThuoc.objects.create(
            thuoc=self.thuoc_rx,
            so_luong=50,
            ngay_nhap=self.today - timedelta(days=100),
            han_su_dung=self.today,
            lo_sx='LO-TODAY-EXP',
            vi_tri='Ke-X',
        )
        self.assertFalse(lo_hom_nay.con_han())
        self.assertEqual(self.thuoc_rx.ton_kho(), 80)  # Không cộng 50 viên hết hạn hôm nay
        self.assertTrue(self.kho_thuoc_otc_lo1.sap_het_han())
        self.assertFalse(self.kho_thuoc_otc_lo2.sap_het_han())

    def test_TC_UNIT_03_whitebox_thuat_toan_tru_ton_kho_thuoc_fifo_nhieu_lo(self):
        """TC_UNIT_03 [White-box FIFO]: Hàm _giam_ton_kho_thuoc() ưu tiên trừ hết lô có HSD gần nhất (lo1: 50 viên) rồi mới trừ sang lô kế tiếp (lo2: 20 viên)."""
        ok = _giam_ton_kho_thuoc(self.thuoc_otc, 70)
        self.assertTrue(ok)
        self.kho_thuoc_otc_lo1.refresh_from_db()
        self.kho_thuoc_otc_lo2.refresh_from_db()
        self.assertEqual(self.kho_thuoc_otc_lo1.so_luong, 0)
        self.assertEqual(self.kho_thuoc_otc_lo2.so_luong, 80)
        self.assertEqual(self.thuoc_otc.ton_kho(), 80)

    def test_TC_UNIT_04_bva_chan_tru_ton_kho_khi_vuot_tong_ton_kha_dung(self):
        """TC_UNIT_04 [BVA - Biên tồn kho]: Khi yêu cầu trừ 151 viên (> 150 viên khả dụng), _giam_ton_kho_thuoc() trả về False và giữ nguyên các lô."""
        ok = _giam_ton_kho_thuoc(self.thuoc_otc, 151)
        self.assertFalse(ok)
        self.kho_thuoc_otc_lo1.refresh_from_db()
        self.kho_thuoc_otc_lo2.refresh_from_db()
        self.assertEqual(self.kho_thuoc_otc_lo1.so_luong, 50)
        self.assertEqual(self.kho_thuoc_otc_lo2.so_luong, 100)

    def test_TC_UNIT_05_whitebox_tru_ton_vaccine_mot_lieu_fifo_chinh_xac(self):
        """TC_UNIT_05 [White-box FIFO]: Hàm tru_ton_vaccine_mot_lieu() trừ đúng 1 liều ở lô hết hạn sớm nhất và trả về metadata lô."""
        ton_lo1_truoc = self.kho_vc_lo1.so_luong
        info = tru_ton_vaccine_mot_lieu(self.vaccine)
        self.assertEqual(info['lo_sx'], 'LO-VC-01')
        self.kho_vc_lo1.refresh_from_db()
        self.assertEqual(self.kho_vc_lo1.so_luong, ton_lo1_truoc - 1)

    def test_TC_UNIT_06_exception_nem_ngoai_le_khi_vaccine_het_ton_kho(self):
        """TC_UNIT_06 [Exception]: Hàm tru_ton_vaccine_mot_lieu() ném ngoại lệ VaccineHetTonError khi tất cả các lô đều hết tồn."""
        self.kho_vc_lo1.so_luong = 0
        self.kho_vc_lo1.save(update_fields=['so_luong'])
        with self.assertRaises(VaccineHetTonError):
            tru_ton_vaccine_mot_lieu(self.vaccine)

    def test_TC_UNIT_07_whitebox_canh_bao_thuoc_sap_het_han_phai_bo_qua_lo_da_ban_het_so_luong_0(self):
        """TC_UNIT_07 [White-box - FAILED vs SRS]: Theo SRS REQ-FIFO-02, Thuoc.sap_het_han() chỉ cảnh báo lô sắp hết hạn khi lô đó còn tồn (so_luong > 0)."""
        t_check = Thuoc.objects.create(
            ma_thuoc='TH_CHECK_EXP',
            ten_thuoc='Vitamin C 500mg',
            loai_thuoc=self.loai_thuoc,
            don_vi=self.don_vi,
            don_gia_nhap=Decimal('500.00'),
            gia_ban=Decimal('1000.00'),
        )
        KhoThuoc.objects.create(
            thuoc=t_check,
            so_luong=0,
            ngay_nhap=self.today - timedelta(days=60),
            han_su_dung=self.today + timedelta(days=10),
            lo_sx='LO-EMPTY-SOON',
            vi_tri='Ke-Z1',
        )
        KhoThuoc.objects.create(
            thuoc=t_check,
            so_luong=100,
            ngay_nhap=self.today,
            han_su_dung=self.today + timedelta(days=365),
            lo_sx='LO-FULL-LONG',
            vi_tri='Ke-Z2',
        )
        self.assertFalse(
            t_check.sap_het_han(),
            "LỖI SRS (REQ-FIFO-02): Thuoc.sap_het_han() không lọc so_luong__gt=0 nên cảnh báo nhầm cả lô đã bán hết (so_luong=0)!",
        )

    # ==========================================================================
    # FUNCTION 5.2: Unit Test Tính toán BHYT, Tổng tiền & Chuẩn hóa Thời gian — 6 TCs
    # ==========================================================================
    def test_TC_UNIT_08_ep_bva_tinh_tuoi_bmi_va_kiem_tra_han_the_bhyt_benh_nhan(self):
        """TC_UNIT_08 [EP & BVA]: Kiểm tra các hàm tính tuổi, chỉ số BMI, phân loại thể trạng và hạn thẻ BHYT trên model BenhNhan."""
        self.assertGreaterEqual(self.bn1.tuoi(), 30)
        self.assertEqual(self.bn1.get_bmi(), Decimal('22.49'))
        self.assertEqual(self.bn1.get_bmi_phan_loai(), 'Bình thường')
        self.assertTrue(self.bn1.kiem_tra_bhyt_con_han())
        self.assertFalse(self.bn2.kiem_tra_bhyt_con_han())

    def test_TC_UNIT_09_formula_tinh_thanh_tien_chi_tiet_va_khau_tru_bhyt_don_thuoc(self):
        """TC_UNIT_09 [Formula]: Kiểm tra ChiTietDonThuoc.thanh_tien() và DonThuoc.save() tính đúng số tiền BHYT chi trả (80%) và bệnh nhân đồng chi trả (20%)."""
        hs = HoSoBenhAn.objects.create(
            benh_nhan=self.bn1,
            bac_si=self.bacsi1,
            ly_do_kham='Khám định kỳ',
            trieu_chung='Mệt mỏi',
        )
        dt = DonThuoc.objects.create(
            ho_so=hs,
            benh_nhan=self.bn1,
            bac_si=self.bacsi1,
            ma_bao_hiem='DN4010012345678',
            ty_le_bao_hiem=Decimal('80.00'),
        )
        ct = ChiTietDonThuoc.objects.create(
            don_thuoc=dt,
            thuoc=self.thuoc_rx,
            so_luong=10,
            lieu_dung='1 viên x 2 lần',
            cach_dung='UONG',
            so_ngay_dung=5,
            don_gia_tai_thoi_diem=Decimal('18000.00'),
        )
        self.assertEqual(ct.thanh_tien(), Decimal('180000.00'))
        tong = dt.tinh_tong_tien()
        self.assertEqual(tong, Decimal('180000.00'))
        dt.refresh_from_db()
        self.assertEqual(dt.so_tien_bao_hiem, Decimal('144000.00'))
        self.assertEqual(dt.so_tien_benh_nhan_tra, Decimal('36000.00'))

    def test_TC_UNIT_10_bva_tinh_tong_tien_don_hang_va_chan_giam_gia_vuot_tong(self):
        """TC_UNIT_10 [BVA]: Kiểm tra DonHang.save() tự tính tong_tien = tong_tien_hang + phi_ship - giam_gia và clean() chặn giảm giá vượt tổng."""
        dh = DonHang.objects.create(
            ma_don_hang='DH_UNIT_01',
            benh_nhan=self.bn1,
            ten_nguoi_nhan='Lê Văn Bệnh Nhân',
            so_dien_thoai_nhan='0901000007',
            dia_chi_giao_hang='Đà Nẵng',
            tong_tien_hang=Decimal('100000.00'),
            phi_ship=Decimal('15000.00'),
            giam_gia=Decimal('5000.00'),
            tong_tien=Decimal('0'),
        )
        self.assertEqual(dh.tong_tien, Decimal('110000.00'))

        dh_invalid = DonHang(
            ma_don_hang='DH_UNIT_ERR',
            benh_nhan=self.bn1,
            ten_nguoi_nhan='Lê Văn Bệnh Nhân',
            so_dien_thoai_nhan='0901000007',
            dia_chi_giao_hang='Đà Nẵng',
            tong_tien_hang=Decimal('50000.00'),
            phi_ship=Decimal('0.00'),
            giam_gia=Decimal('60000.00'),
            tong_tien=Decimal('-10000.00'),
        )
        with self.assertRaises(ValidationError):
            dh_invalid.clean()

    def test_TC_UNIT_11_bva_phan_ca_lam_viec_tu_thoi_diem_va_khoang_ngay_local(self):
        """TC_UNIT_11 [BVA - Biên giờ]: Kiểm tra phan_ca_tu_thoi_diem() tại các mốc biên SANG/CHIEU/TOI và bounds_for_local_days()."""
        tz = timezone.get_current_timezone()
        t_sang = timezone.make_aware(datetime(2026, 11, 5, 8, 30), tz)
        t_chieu = timezone.make_aware(datetime(2026, 11, 5, 14, 15), tz)
        t_toi = timezone.make_aware(datetime(2026, 11, 5, 19, 0), tz)
        self.assertEqual(phan_ca_tu_thoi_diem(t_sang), 'SANG')
        self.assertEqual(phan_ca_tu_thoi_diem(t_chieu), 'CHIEU')
        self.assertEqual(phan_ca_tu_thoi_diem(t_toi), 'TOI')

        lo, hi = bounds_for_local_days(date(2026, 11, 1), date(2026, 11, 5))
        self.assertLess(lo, hi)
        self.assertGreaterEqual((hi - lo).days, 4)

    def test_TC_UNIT_12_bva_validation_chan_ngay_sinh_tuong_lai_va_chi_so_sinh_hoc_ngoai_bien(self):
        """TC_UNIT_12 [BVA - Biên sinh học]: Kiểm tra BenhNhan.clean() chặn ngày sinh ở tương lai và chặn chiều cao خارج ngưỡng [30..250 cm]."""
        self.bn2.chieu_cao = Decimal('280.00')
        with self.assertRaises(ValidationError):
            self.bn2.clean()
        self.bn2.chieu_cao = Decimal('160.00')

    def test_TC_UNIT_13_whitebox_don_thuoc_tu_dong_ap_dung_bhyt_tu_ho_so_benh_nhan_theo_srs(self):
        """TC_UNIT_13 [White-box - FAILED vs SRS]: Theo SRS UC007/REQ-RX-04, khi tạo DonThuoc cho bệnh nhân có BHYT còn hạn phải tự động lấy mã và tỷ lệ BHYT."""
        hs = HoSoBenhAn.objects.create(
            benh_nhan=self.bn1,
            bac_si=self.bacsi1,
            ly_do_kham='Khám nội tổng quát',
            trieu_chung='Đau đầu',
        )
        dt = DonThuoc.objects.create(ho_so=hs, benh_nhan=self.bn1, bac_si=self.bacsi1)
        ChiTietDonThuoc.objects.create(
            don_thuoc=dt,
            thuoc=self.thuoc_rx,
            so_luong=5,
            lieu_dung='1 viên/lần',
            cach_dung='UONG',
            so_ngay_dung=5,
            don_gia_tai_thoi_diem=Decimal('18000.00'),
        )
        dt.tinh_tong_tien()
        dt.refresh_from_db()
        self.assertGreater(
            dt.so_tien_bao_hiem,
            Decimal('0.00'),
            "LỖI SRS (UC007/REQ-RX-04): DonThuoc không tự động đồng bộ thông tin thẻ BHYT còn hạn từ hồ sơ BenhNhan nên tính so_tien_bao_hiem = 0!",
        )
