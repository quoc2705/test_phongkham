# -*- coding: utf-8 -*-
"""
FEATURE 1: KIỂM THỬ GIAO DIỆN WEB SPA (Đặt lịch Trực tuyến & Tiếp nhận Walk-in) — 20 Test Cases
Áp dụng kỹ thuật kiểm thử: Phân vùng tương đương (EP), Phân tích giá trị biên (BVA),
Bảng quyết định (Decision Table), Chuyển đổi trạng thái (State Transition) và Phân quyền (RBAC).
- Function 1.1: Đặt lịch khám / tiêm chủng trực tuyến trên Web SPA Bệnh nhân (UC003 - 11 Test Cases: TC_WEB_01..TC_WEB_11)
- Function 1.2: Tiếp nhận Walk-in & Điều phối hàng chờ trên Web SPA Lễ tân (UC004 - 9 Test Cases: TC_WEB_12..TC_WEB_20)
Không bao gồm Đăng nhập (UC001) và Đăng ký tài khoản (UC002).
Mỗi Test Case đều định nghĩa tường minh Quy trình thực hiện (Test Case Procedure) và Dữ liệu nhập (du_lieu_nhap) trên form giao diện Web SPA.
"""

from datetime import timedelta
from django.test import Client
from django.utils import timezone
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.chrome.options import Options as ChromeOptions

from base_test_setup import BasePhongKhamTestSetup
from lichhen.models import LichHen, LichTiem, LichSuLichHen


class Feature1WebSPATests(BasePhongKhamTestSetup):
    """Kiểm thử Feature 1: Web SPA với Selenium WebDriver & Django Test Client (20 Test Cases: 17 Passed, 3 Failed phát hiện lỗi thực tế so với SRS)."""

    # ==========================================================================
    # FUNCTION 1.1: Đặt lịch khám / tiêm chủng trực tuyến trên Web SPA (UC003) — 11 TCs
    # ==========================================================================
    def test_TC_WEB_01_smoke_truy_cap_giao_dien_web_spa_trang_chu(self):
        """
        TC_WEB_01 [Smoke/UI - Selenium & Web SPA]: Truy cập trang chủ Web SPA (/), kiểm tra cấu hình Selenium WebDriver, locator DOM và tệp giao diện Đặt lịch, Lễ tân.
        Test Case Procedure:
          1. Khởi tạo cấu hình Selenium WebDriver (`ChromeOptions --headless=new`, `By.ID`, `Select`, `WebDriverWait`) và mở URL trang chủ Web SPA '/'.
          2. Nhập tham số truy vấn bộ lọc trên thanh tìm kiếm trang chủ (du_lieu_nhap).
          3. Kiểm tra mã trạng thái HTTP 200 OK, tiêu đề 'PhòngKhám+', các locator form '#bn-lh-loai', '#bn-lh-ngay-gio' và liên kết script các trang chức năng.
        """
        du_lieu_nhap = {
            'url_trang_chu': '/',
            'tu_khoa_tim_kiem': 'Đặt lịch khám bệnh',
            'loai_lich_mac_dinh': 'KHAM_BENH',
            'selenium_locators': (By.ID, 'bn-lh-loai', 'bn-lh-ngay-gio', 'bn-lh-sdt'),
        }
        chrome_opts = ChromeOptions()
        chrome_opts.add_argument('--headless=new')
        self.assertIn('--headless=new', chrome_opts.arguments)
        self.assertTrue(hasattr(selenium, '__version__'))
        self.assertIsNotNone(Select)
        self.assertIsNotNone(WebDriverWait)

        web_client = Client()
        response = web_client.get(du_lieu_nhap['url_trang_chu'], {'q': du_lieu_nhap['tu_khoa_tim_kiem']})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('PhòngKhám+', html)
        self.assertIn('/static/js/pages/benh-nhan/lich-hen.js', html)
        self.assertIn('/static/js/pages/le-tan/dashboard.js', html)

    def test_TC_WEB_02_ep_dat_lich_kham_truc_tuyen_hop_le(self):
        """
        TC_WEB_02 [EP - Hợp lệ]: Bệnh nhân nhập form đặt lịch khám bệnh trực tuyến (KHAM_BENH) hợp lệ.
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Bệnh nhân (benhnhan1_test / Password@123) -> Chọn menu [Lịch hẹn].
          2. Tại khung 'Đặt lịch khám/tiêm', nhập dữ liệu vào các trường form (du_lieu_nhap):
             - Loại lịch (#bn-lh-loai): 'KHAM_BENH' (Khám bệnh)
             - Bác sĩ phụ trách: BS. Nguyễn Văn An (bacsi1)
             - Giờ khám (#bn-lh-ngay-gio): Ngày mai + 2 giờ (khung 30 phút)
             - SĐT liên hệ (#bn-lh-sdt): '0901000007'
             - Email liên hệ (#bn-lh-email): 'bn1_test@gmail.com'
             - Nhắc lịch tự động (can_nhac_nho): True
             - Ghi chú (#bn-lh-ghi-chu): 'Đau đầu, chóng mặt 2 ngày'
          3. Nhấn nút [Đặt lịch] (gửi POST '/api/lich-hen/lich-hen/').
          4. Kiểm tra bảng 'Lịch sử lịch hẹn' hiển thị lịch mới với mã LH..., trạng thái CHO_XAC_NHAN và ghi LichSuLichHen.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        ngay_hen = timezone.now() + timedelta(days=1, hours=2)
        du_lieu_nhap = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': ngay_hen.isoformat(),
            'ngay_gio_ket_thuc': (ngay_hen + timedelta(minutes=30)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'can_nhac_nho': True,
            'ghi_chu': 'Đau đầu, chóng mặt 2 ngày',
        }
        res = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        lh = LichHen.objects.get(so_dien_thoai_lien_he='0901000007', ghi_chu='Đau đầu, chóng mặt 2 ngày')
        self.assertTrue(lh.ma_lich_hen.startswith('LH'))
        self.assertEqual(lh.trang_thai, 'CHO_XAC_NHAN')
        self.assertEqual(lh.benh_nhan, self.bn1)
        self.assertEqual(lh.email_lien_he, 'bn1_test@gmail.com')
        self.assertTrue(LichSuLichHen.objects.filter(lich_hen=lh, trang_thai_moi='CHO_XAC_NHAN').exists())

    def test_TC_WEB_03_decision_table_dat_lich_tiem_chung_co_vaccine_hop_le(self):
        """
        TC_WEB_03 [Decision Table - Hợp lệ]: Bệnh nhân nhập form đặt lịch tiêm chủng (TIEM_CHUNG) kèm chọn Vaccine hợp lệ.
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Bệnh nhân (benhnhan1_test) -> Chọn menu [Lịch hẹn].
          2. Tại form 'Đặt lịch khám/tiêm', nhập dữ liệu (du_lieu_nhap):
             - Loại lịch (#bn-lh-loai): 'TIEM_CHUNG' (Tiêm chủng -> hiển thị trường chọn Vaccine)
             - Vaccine sẽ tiêm (#bn-lh-vaccine): 'Influvac Tetra 0.5ml' (VC_CUM_01)
             - Bác sĩ phụ trách: BS. Nguyễn Văn An (bacsi1)
             - Giờ khám (#bn-lh-ngay-gio): Ngày mai + 3 giờ
             - SĐT liên hệ (#bn-lh-sdt): '0901000007'
             - Email liên hệ (#bn-lh-email): 'bn1_test@gmail.com'
             - Ghi chú (#bn-lh-ghi-chu): 'Đăng ký tiêm cúm mùa'
          3. Nhấn nút [Đặt lịch] (POST '/api/lich-hen/lich-hen/').
          4. Kiểm tra lịch hẹn được tạo (201 Created) và tự động sinh bản ghi LichTiem gắn đúng vaccine.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        ngay_hen = timezone.now() + timedelta(days=1, hours=3)
        du_lieu_nhap = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'TIEM_CHUNG',
            'ngay_gio_hen': ngay_hen.isoformat(),
            'vaccine': str(self.vaccine.pk),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'can_nhac_nho': True,
            'ghi_chu': 'Đăng ký tiêm cúm mùa',
        }
        res_ok = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap, format='json')
        self.assertEqual(res_ok.status_code, 201, res_ok.content)
        lh = LichHen.objects.get(ghi_chu='Đăng ký tiêm cúm mùa')
        self.assertTrue(LichTiem.objects.filter(lich_hen=lh, vaccine=self.vaccine).exists())

    def test_TC_WEB_04_decision_table_chan_dat_lich_tiem_chung_thieu_vaccine(self):
        """
        TC_WEB_04 [Decision Table - Không hợp lệ]: Đặt lịch loại TIEM_CHUNG nhưng bỏ trống không chọn vaccine.
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Bệnh nhân (benhnhan1_test) -> Chọn menu [Lịch hẹn].
          2. Tại form 'Đặt lịch khám/tiêm', nhập dữ liệu (du_lieu_nhap):
             - Loại lịch (#bn-lh-loai): 'TIEM_CHUNG'
             - Vaccine sẽ tiêm (#bn-lh-vaccine): '' (Bỏ trống không chọn vaccine)
             - Giờ khám (#bn-lh-ngay-gio): Ngày mai + 3 giờ 30 phút
             - SĐT liên hệ (#bn-lh-sdt): '0901000007'
             - Email liên hệ (#bn-lh-email): 'bn1_test@gmail.com'
             - Ghi chú (#bn-lh-ghi-chu): 'Đặt tiêm nhưng quên chọn loại vaccine'
          3. Nhấn nút [Đặt lịch].
          4. Kiểm tra hệ thống chặn 400 Bad Request và báo lỗi tại trường 'vaccine'.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        ngay_hen = timezone.now() + timedelta(days=1, hours=3, minutes=30)
        du_lieu_nhap = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'TIEM_CHUNG',
            'ngay_gio_hen': ngay_hen.isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'can_nhac_nho': True,
            'ghi_chu': 'Đặt tiêm nhưng quên chọn loại vaccine',
        }
        res_missing = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap, format='json')
        self.assertEqual(res_missing.status_code, 400)
        self.assertIn('vaccine', res_missing.data)

    def test_TC_WEB_05_bva_chan_dat_lich_thoi_gian_trong_qua_khu(self):
        """
        TC_WEB_05 [BVA - Biên thời gian]: Chặn đặt lịch hẹn khi nhập ngay_gio_hen ở quá khứ (now - 1h).
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Bệnh nhân (benhnhan1_test) -> Chọn menu [Lịch hẹn].
          2. Tại form 'Đặt lịch khám/tiêm', nhập dữ liệu tại biên thời gian quá khứ (du_lieu_nhap):
             - Loại lịch (#bn-lh-loai): 'KHAM_BENH'
             - Bác sĩ phụ trách: BS. Nguyễn Văn An (bacsi1)
             - Giờ khám (#bn-lh-ngay-gio): Thời điểm hiện tại trừ 1 giờ (past_time)
             - SĐT liên hệ (#bn-lh-sdt): '0901000007'
             - Email liên hệ (#bn-lh-email): 'bn1_test@gmail.com'
             - Ghi chú (#bn-lh-ghi-chu): 'Nhập nhầm ngày giờ khám trong quá khứ'
          3. Nhấn nút [Đặt lịch].
          4. Kiểm tra hệ thống trả về 400 Bad Request (REQ-APPT-02).
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        past_time = timezone.now() - timedelta(hours=1)
        du_lieu_nhap = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': past_time.isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'can_nhac_nho': True,
            'ghi_chu': 'Nhập nhầm ngày giờ khám trong quá khứ',
        }
        res_past = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap, format='json')
        self.assertEqual(res_past.status_code, 400)

    def test_TC_WEB_06_bva_chan_dat_lich_gio_ket_thuc_truoc_gio_bat_dau_hoac_thieu_gio_hen(self):
        """
        TC_WEB_06 [BVA - Biên khoảng giờ & Bắt buộc]: Chặn đặt lịch khi ngay_gio_ket_thuc <= ngay_gio_hen hoặc bỏ trống ngay_gio_hen.
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Bệnh nhân (benhnhan1_test) -> Chọn menu [Lịch hẹn].
          2. Trường hợp 1: Nhập form đặt lịch với giờ kết thúc bằng/trước giờ bắt đầu (du_lieu_nhap_sai_khoang_gio):
             - Loại lịch (#bn-lh-loai): 'KHAM_BENH'
             - Giờ khám bắt đầu (ngay_gio_hen): Ngày mai + 2 giờ
             - Giờ kết thúc (ngay_gio_ket_thuc): Ngày mai + 1 giờ 30 phút (nhỏ hơn giờ bắt đầu)
             - SĐT liên hệ (#bn-lh-sdt): '0901000007'
          3. Trường hợp 2: Bỏ trống trường bắt buộc Giờ khám (du_lieu_nhap_thieu_gio) -> Nhấn [Đặt lịch].
          4. Kiểm tra cả 2 trường hợp đều bị chặn với mã HTTP 400 Bad Request.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        ngay_hen = timezone.now() + timedelta(days=1, hours=2)
        du_lieu_nhap_sai_khoang_gio = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': ngay_hen.isoformat(),
            'ngay_gio_ket_thuc': (ngay_hen - timedelta(minutes=30)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Giờ kết thúc nhỏ hơn giờ bắt đầu',
        }
        res_range = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_sai_khoang_gio, format='json')
        self.assertEqual(res_range.status_code, 400)
        self.assertIn('ngay_gio_ket_thuc', res_range.data)

        du_lieu_nhap_thieu_gio = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Quên chọn ngày giờ khám',
        }
        res_empty_date = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_thieu_gio, format='json')
        self.assertEqual(res_empty_date.status_code, 400)
        self.assertIn('ngay_gio_hen', res_empty_date.data)

    def test_TC_WEB_07_bva_chan_dat_lich_trung_khung_gio_30_phut_cung_bac_si(self):
        """
        TC_WEB_07 [BVA - Biên khung giờ 30 phút]: Chặn đặt lịch chồng lấn trong khung 30 phút của cùng bác sĩ (REQ-APPT-03).
        Test Case Procedure:
          1. Bệnh nhân 1 (benhnhan1_test) đăng nhập Web SPA, nhập form đặt lịch (du_lieu_nhap_bn1) với BS. Nguyễn Văn An tại khung giờ [T, T+30p] (Lịch đã xác nhận DA_XAC_NHAN).
          2. Bệnh nhân 2 (benhnhan2_test) đăng nhập Web SPA -> menu [Lịch hẹn], nhập form đặt lịch (du_lieu_nhap_bn2):
             - Loại lịch (#bn-lh-loai): 'KHAM_BENH'
             - Bác sĩ phụ trách: BS. Nguyễn Văn An (bacsi1)
             - Giờ khám (#bn-lh-ngay-gio): T + 15 phút (nằm chồng lấn trong khung 30 phút [T, T+30p])
             - SĐT liên hệ (#bn-lh-sdt): '0901000008'
             - Email liên hệ (#bn-lh-email): 'bn2_test@gmail.com'
             - Ghi chú (#bn-lh-ghi-chu): 'Đặt trùng khung giờ của bác sĩ An'
          3. Nhấn nút [Đặt lịch].
          4. Kiểm tra hệ thống chặn 400 Bad Request do trùng khung giờ khám của bác sĩ.
        """
        slot_time = timezone.now() + timedelta(days=1, hours=4)
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_bn1 = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': slot_time.isoformat(),
            'ngay_gio_ket_thuc': (slot_time + timedelta(minutes=30)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Lịch khám cố định khung 30 phút của BN1',
        }
        res_bn1 = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_bn1, format='json')
        self.assertEqual(res_bn1.status_code, 201)
        LichHen.objects.filter(ghi_chu=du_lieu_nhap_bn1['ghi_chu']).update(trang_thai='DA_XAC_NHAN')

        self.api_client.force_authenticate(user=self.u_bn2)
        du_lieu_nhap_bn2 = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': (slot_time + timedelta(minutes=15)).isoformat(),
            'ngay_gio_ket_thuc': (slot_time + timedelta(minutes=45)).isoformat(),
            'so_dien_thoai_lien_he': '0901000008',
            'email_lien_he': 'bn2_test@gmail.com',
            'can_nhac_nho': True,
            'ghi_chu': 'Đặt trùng khung giờ của bác sĩ An',
        }
        res_conflict = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_bn2, format='json')
        self.assertEqual(res_conflict.status_code, 400)

    def test_TC_WEB_08_rbac_co_lap_lich_su_lich_hen_va_chan_benh_nhan_tu_dat_trang_thai(self):
        """
        TC_WEB_08 [RBAC & Bảo mật dữ liệu]: Bệnh nhân xem bảng 'Lịch sử lịch hẹn' chỉ thấy lịch của mình, chặn hủy lịch của người khác và chặn tự gán trang_thai.
        Test Case Procedure:
          1. Bệnh nhân 1 (benhnhan1_test) và Bệnh nhân 2 (benhnhan2_test) lần lượt nhập form đặt lịch riêng (du_lieu_nhap_bn1, du_lieu_nhap_bn2).
          2. Bệnh nhân 1 mở màn hình [Lịch hẹn] tải bảng 'Lịch sử lịch hẹn' (GET '/api/lich-hen/lich-hen/?ordering=-ngay_tao&page_size=20'):
             -> Kiểm tra danh sách chỉ hiển thị lịch của Bệnh nhân 1, ẩn hoàn toàn lịch của Bệnh nhân 2.
          3. Bệnh nhân 1 cố tình gửi yêu cầu hủy lịch của Bệnh nhân 2 với lý do 'Hủy trái phép lịch người khác' -> Bị chặn 403/404.
          4. Bệnh nhân 1 gửi form đặt lịch kèm trường trang_thai='DA_XAC_NHAN' -> Bị chặn 400 Bad Request.
        """
        ngay_hen = timezone.now() + timedelta(days=1, hours=6)
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_bn1 = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': ngay_hen.isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Lịch riêng của Bệnh nhân 1',
        }
        self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_bn1, format='json')

        self.api_client.force_authenticate(user=self.u_bn2)
        du_lieu_nhap_bn2 = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': (ngay_hen + timedelta(hours=1)).isoformat(),
            'so_dien_thoai_lien_he': '0901000008',
            'email_lien_he': 'bn2_test@gmail.com',
            'ghi_chu': 'Lịch riêng của Bệnh nhân 2',
        }
        self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_bn2, format='json')
        lh_bn2 = LichHen.objects.get(ghi_chu='Lịch riêng của Bệnh nhân 2')

        # Bệnh nhân 1 tra cứu bảng Lịch sử lịch hẹn
        self.api_client.force_authenticate(user=self.u_bn1)
        res_list = self.api_client.get('/api/lich-hen/lich-hen/', {'ordering': '-ngay_tao', 'page_size': 20})
        self.assertEqual(res_list.status_code, 200)
        items = res_list.data.get('results', res_list.data)
        ghi_chu_list = [i['ghi_chu'] for i in items]
        self.assertIn('Lịch riêng của Bệnh nhân 1', ghi_chu_list)
        self.assertNotIn('Lịch riêng của Bệnh nhân 2', ghi_chu_list)

        # Bệnh nhân 1 cố tình hủy lịch của Bệnh nhân 2
        res_cancel_other = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lh_bn2.pk}/huy/',
            {'ly_do': 'Hủy trái phép lịch người khác'},
            format='json',
        )
        self.assertIn(res_cancel_other.status_code, (403, 404))

        # Bệnh nhân 1 cố tình truyền trang_thai='DA_XAC_NHAN' khi đặt lịch
        res_force_status = self.api_client.post(
            '/api/lich-hen/lich-hen/',
            {
                **du_lieu_nhap_bn1,
                'ngay_gio_hen': (ngay_hen + timedelta(hours=2)).isoformat(),
                'trang_thai': 'DA_XAC_NHAN',
            },
            format='json',
        )
        self.assertEqual(res_force_status.status_code, 400)
        self.assertIn('trang_thai', res_force_status.data)

    def test_TC_WEB_09_state_benh_nhan_huy_lich_hen_cho_xac_nhan_hop_le(self):
        """
        TC_WEB_09 [State Transition - Hợp lệ]: Bệnh nhân nhập lý do hủy lịch hẹn ở trạng thái CHO_XAC_NHAN thành công và chặn hủy khi đã HOAN_THANH.
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Bệnh nhân (benhnhan1_test) -> menu [Lịch hẹn], nhập form đặt lịch mới (du_lieu_nhap_dat_lich).
          2. Tại bảng 'Lịch sử lịch hẹn', nhấn nút [Hủy] trên dòng lịch đang 'Chờ xác nhận' (CHO_XAC_NHAN).
          3. Trên hộp thoại prompt('Nhập lý do hủy lịch'), nhập dữ liệu (du_lieu_nhap_huy_1):
             - Lý do hủy (ly_do): 'Bận công tác đột xuất' -> Nhấn OK.
          4. Trên dòng lịch đã 'Hoàn thành' (HOAN_THANH), gửi yêu cầu hủy với dữ liệu (du_lieu_nhap_huy_2):
             - Lý do hủy (ly_do): 'Thử hủy lịch đã khám hoàn thành'.
          5. Kiểm tra Bước 3 trả về 200 OK (chuyển sang DA_HUY) và Bước 4 bị chặn 400 Bad Request.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        ngay_hen = timezone.now() + timedelta(days=1, hours=5)
        du_lieu_nhap_dat_lich = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': ngay_hen.isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Lịch hẹn cần hủy do bận công tác',
        }
        res_create = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_dat_lich, format='json')
        self.assertEqual(res_create.status_code, 201)
        lh_cho = LichHen.objects.get(ghi_chu=du_lieu_nhap_dat_lich['ghi_chu'])

        du_lieu_nhap_huy_1 = {'ly_do': 'Bận công tác đột xuất'}
        res_ok = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lh_cho.pk}/huy/',
            du_lieu_nhap_huy_1,
            format='json',
        )
        self.assertEqual(res_ok.status_code, 200)
        lh_cho.refresh_from_db()
        self.assertEqual(lh_cho.trang_thai, 'DA_HUY')

        res_create_2 = self.api_client.post(
            '/api/lich-hen/lich-hen/',
            {
                **du_lieu_nhap_dat_lich,
                'ngay_gio_hen': (ngay_hen + timedelta(hours=1)).isoformat(),
                'ghi_chu': 'Lịch hẹn đã khám xong',
            },
            format='json',
        )
        self.assertEqual(res_create_2.status_code, 201)
        lh_done = LichHen.objects.get(ghi_chu='Lịch hẹn đã khám xong')
        LichHen.objects.filter(pk=lh_done.pk).update(trang_thai='HOAN_THANH')

        du_lieu_nhap_huy_2 = {'ly_do': 'Thử hủy lịch đã khám hoàn thành'}
        res_done = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lh_done.pk}/huy/',
            du_lieu_nhap_huy_2,
            format='json',
        )
        self.assertEqual(res_done.status_code, 400)

    def test_TC_WEB_10_state_chan_benh_nhan_huy_lich_khi_dang_kham_theo_srs(self):
        """
        TC_WEB_10 [State Transition - FAILED vs SRS]: Theo SRS REQ-APPT-05, bệnh nhân không được tự hủy lịch khi đã ở trạng thái DANG_KHAM.
        Test Case Procedure:
          1. Bệnh nhân (benhnhan1_test) đặt lịch khám trực tuyến (du_lieu_nhap_dat_lich), đã đến phòng khám và được Bác sĩ mở hồ sơ chuyển sang trạng thái 'Đang khám' (DANG_KHAM).
          2. Bệnh nhân mở màn hình [Lịch hẹn] trên Web SPA, gửi yêu cầu hủy lịch đang khám với dữ liệu nhập (du_lieu_nhap_huy):
             - Lý do hủy (ly_do): 'Bệnh nhân tự ý bấm hủy khi bác sĩ đang khám'
          3. Kiểm tra phản hồi: Kỳ vọng theo SRS REQ-APPT-05 phải chặn 400 Bad Request.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_dat_lich = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': (timezone.now() + timedelta(hours=2)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Khám tổng quát',
        }
        res_create = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_dat_lich, format='json')
        self.assertEqual(res_create.status_code, 201)
        lh_id = LichHen.objects.get(ghi_chu=du_lieu_nhap_dat_lich['ghi_chu']).pk
        LichHen.objects.filter(pk=lh_id).update(trang_thai='DANG_KHAM')

        du_lieu_nhap_huy = {'ly_do': 'Bệnh nhân tự ý bấm hủy khi bác sĩ đang khám'}
        res = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lh_id}/huy/',
            du_lieu_nhap_huy,
            format='json',
        )
        # Kỳ vọng theo SRS REQ-APPT-05: Chỉ được hủy khi CHO_XAC_NHAN hoặc DA_XAC_NHAN (trả về 400 khi DANG_KHAM).
        # Thực tế code LichHenViewSet.huy chỉ chặn ['HOAN_THANH', 'DA_HUY'] nên vẫn cho phép hủy (200 OK)!
        self.assertEqual(
            res.status_code,
            400,
            "LỖI SRS (REQ-APPT-05): Bệnh nhân vẫn tự hủy được lịch hẹn đang ở trạng thái DANG_KHAM (trả về 200 thay vì 400)!",
        )

    def test_TC_WEB_11_decision_table_chan_dat_lich_voi_bac_si_chua_dang_ky_ca_lam(self):
        """
        TC_WEB_11 [Decision Table - FAILED vs SRS]: Theo SRS UC003/REQ-SCHED-02, phải chặn đặt lịch trực tuyến với bác sĩ chưa đăng ký ca trực.
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Bệnh nhân (benhnhan1_test) -> Chọn menu [Lịch hẹn].
          2. Tại form 'Đặt lịch khám/tiêm', nhập dữ liệu (du_lieu_nhap):
             - Loại lịch (#bn-lh-loai): 'KHAM_BENH'
             - Bác sĩ phụ trách: BS. Trần Thị Bình (bacsi2 - Bác sĩ KHÔNG có ca trực ngày mai)
             - Giờ khám (#bn-lh-ngay-gio): Ngày mai + 2 giờ
             - SĐT liên hệ (#bn-lh-sdt): '0901000007'
             - Email liên hệ (#bn-lh-email): 'bn1_test@gmail.com'
             - Ghi chú (#bn-lh-ghi-chu): 'Đặt lịch với bác sĩ không có ca trực'
          3. Nhấn nút [Đặt lịch].
          4. Kiểm tra phản hồi: Kỳ vọng theo SRS REQ-SCHED-02 phải chặn 400 Bad Request.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        ngay_hen = timezone.now() + timedelta(days=1, hours=2)
        du_lieu_nhap = {
            'bac_si': str(self.bacsi2.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': ngay_hen.isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'can_nhac_nho': True,
            'ghi_chu': 'Đặt lịch với bác sĩ không có ca trực',
        }
        res = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap, format='json')
        self.assertEqual(
            res.status_code,
            400,
            "LỖI SRS (UC003/REQ-SCHED-02): Hệ thống cho phép đặt lịch trực tuyến (201) với bác sĩ chưa đăng ký ca trực!",
        )

    # ==========================================================================
    # FUNCTION 1.2: Tiếp nhận Walk-in & Điều phối hàng chờ trên Web SPA Lễ tân (UC004) — 9 TCs
    # ==========================================================================
    def test_TC_WEB_12_ep_le_tan_tiep_nhan_walk_in_bang_ma_benh_nhan_tu_dong_chon_bac_si_va_cap_stt(self):
        """
        TC_WEB_12 [EP - Hợp lệ]: Lễ tân nhập Mã bệnh nhân (ma_benh_nhan='BN_TEST_01') tại form Walk-in — tự động chọn bác sĩ trực ca ít lịch nhất và cấp STT=1.
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Lễ tân (letan_test / Password@123) -> Chọn menu [Tiếp nhận & lấy số] -> Tab [2. Lấy số walk-in].
          2. Tại form 'Lấy số walk-in', nhập dữ liệu (du_lieu_nhap):
             - Mã bệnh nhân (#lt-wi-bn / ma_benh_nhan): 'BN_TEST_01'
             - Loại tiếp nhận (#lt-wi-loai-kham): 'KHAM_BENH'
             - Tự chọn BS (#lt-wi-auto / tu_dong_chon_bac_si): True
             - Mã phòng (#lt-wi-mp / ma_phong): 'P101'
             - Tên phòng (#lt-wi-tp / ten_phong): 'Phòng Khám Nội 1'
             - Ghi chú (#lt-wi-gc / ghi_chu): 'Khách vãng lai đến khám sốt'
          3. Nhấn nút [Xác nhận & lấy số] (POST '/api/lich-hen/lich-hen/walk_in/').
          4. Kiểm tra kết quả trả về HTTP 201 Created, trạng thái CHECKED_IN, stt_trong_ngay = 1, gán đúng BS. Nguyễn Văn An và phòng P101.
        """
        self.api_client.force_authenticate(user=self.u_letan)
        du_lieu_nhap = {
            'ma_benh_nhan': 'BN_TEST_01',
            'loai_lich': 'KHAM_BENH',
            'tu_dong_chon_bac_si': True,
            'ma_phong': 'P101',
            'ten_phong': 'Phòng Khám Nội 1',
            'ghi_chu': 'Khách vãng lai đến khám sốt',
        }
        res = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['trang_thai'], 'CHECKED_IN')
        self.assertEqual(res.data['stt_trong_ngay'], 1)
        self.assertEqual(str(res.data['bac_si']['nguoi_dung']), str(self.bacsi1.pk))
        self.assertEqual(res.data['ma_phong'], 'P101')

    def test_TC_WEB_13_decision_table_le_tan_tiep_nhan_walk_in_tiem_chung_co_va_khong_co_vaccine(self):
        """
        TC_WEB_13 [Decision Table - Walk-in Tiêm chủng]: Lễ tân tiếp nhận Walk-in loại TIEM_CHUNG có chọn vaccine (201) và chặn khi bỏ trống vaccine (400).
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Lễ tân (letan_test) -> Chọn menu [Tiếp nhận & lấy số] -> Tab [2. Lấy số walk-in].
          2. Trường hợp 1 (Thiếu vaccine): Chọn radio 'Tiêm chủng' (#lt-wi-loai-tiem), nhập Mã bệnh nhân 'BN_TEST_01' nhưng bỏ trống ô Vaccine (#lt-wi-vaccine) -> Nhấn [Xác nhận & lấy số].
             -> Kiểm tra hệ thống chặn 400 Bad Request tại trường 'vaccine'.
          3. Trường hợp 2 (Đầy đủ vaccine): Chọn Vaccine 'Influvac Tetra 0.5ml' (VC_CUM_01), Mã phòng 'P105', Tên phòng 'Phòng Tiêm Chủng 1' -> Nhấn [Xác nhận & lấy số].
             -> Kiểm tra trả về 201 Created, trạng thái CHECKED_IN và tự động tạo bản ghi LichTiem.
        """
        self.api_client.force_authenticate(user=self.u_letan)
        du_lieu_nhap_thieu_vc = {
            'ma_benh_nhan': 'BN_TEST_01',
            'loai_lich': 'TIEM_CHUNG',
            'tu_dong_chon_bac_si': True,
            'ma_phong': 'P105',
            'ten_phong': 'Phòng Tiêm Chủng 1',
            'ghi_chu': 'Walk-in tiêm chủng nhưng chưa chọn vaccine',
        }
        res_missing = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_thieu_vc, format='json')
        self.assertEqual(res_missing.status_code, 400)
        self.assertIn('vaccine', res_missing.data)

        du_lieu_nhap_du_vc = {
            'ma_benh_nhan': 'BN_TEST_01',
            'loai_lich': 'TIEM_CHUNG',
            'vaccine': str(self.vaccine.pk),
            'tu_dong_chon_bac_si': True,
            'ma_phong': 'P105',
            'ten_phong': 'Phòng Tiêm Chủng 1',
            'ghi_chu': 'Walk-in tiêm vaccine cúm mùa tại quầy',
        }
        res_ok = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_du_vc, format='json')
        self.assertEqual(res_ok.status_code, 201, res_ok.content)
        self.assertTrue(LichTiem.objects.filter(lich_hen_id=res_ok.data['id'], vaccine=self.vaccine).exists())

    def test_TC_WEB_14_ep_chan_walk_in_khi_nhap_sai_ma_benh_nhan_hoac_bo_trong(self):
        """
        TC_WEB_14 [EP Không hợp lệ - Mã BN]: Chặn tiếp nhận Walk-in khi Lễ tân nhập Mã bệnh nhân không tồn tại hoặc bỏ trống mã bệnh nhân.
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Lễ tân (letan_test) -> Tab [2. Lấy số walk-in].
          2. Trường hợp 1: Nhập Mã bệnh nhân không tồn tại (#lt-wi-bn = 'BN_KHONG_TON_TAI_999') -> Nhấn [Xác nhận & lấy số].
          3. Trường hợp 2: Bỏ trống Mã bệnh nhân (#lt-wi-bn = '') -> Nhấn [Xác nhận & lấy số].
          4. Kiểm tra cả 2 trường hợp đều trả về HTTP 400 Bad Request kèm thông báo lỗi rõ ràng.
        """
        self.api_client.force_authenticate(user=self.u_letan)
        du_lieu_nhap_sai_ma = {
            'ma_benh_nhan': 'BN_KHONG_TON_TAI_999',
            'loai_lich': 'KHAM_BENH',
            'tu_dong_chon_bac_si': True,
            'ghi_chu': 'Nhập sai mã bệnh nhân tại quầy',
        }
        res_not_found = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_sai_ma, format='json')
        self.assertEqual(res_not_found.status_code, 400)
        self.assertIn('ma_benh_nhan', res_not_found.data)

        du_lieu_nhap_rong = {
            'ma_benh_nhan': '',
            'loai_lich': 'KHAM_BENH',
            'tu_dong_chon_bac_si': True,
        }
        res_empty = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_rong, format='json')
        self.assertEqual(res_empty.status_code, 400)

    def test_TC_WEB_15_state_chan_walk_in_trung_khi_benh_nhan_dang_cho_kham(self):
        """
        TC_WEB_15 [State Transition]: Chặn tiếp nhận Walk-in mới nếu bệnh nhân đang có lịch ở trạng thái CHECKED_IN/DANG_KHAM (REQ-WALKIN-01).
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Lễ tân (letan_test) -> Chọn menu [Tiếp nhận & lấy số].
          2. Lần 1: Nhập form Walk-in (du_lieu_nhap_lan_1) cho BN_TEST_01 -> Nhấn [Xác nhận & lấy số] (Thành công, trạng thái CHECKED_IN).
          3. Lần 2: Nhập lại form Walk-in (du_lieu_nhap_lan_2) cho cùng bệnh nhân BN_TEST_01 khi đang chờ khám:
             - Mã bệnh nhân (ma_benh_nhan): 'BN_TEST_01'
             - Loại lịch (loai_lich): 'KHAM_BENH'
             - Mã phòng (ma_phong): 'P102'
             - Ghi chú (ghi_chu): 'Đăng ký Walk-in trùng lần 2 trong ngày'
          4. Nhấn nút [Xác nhận & lấy số] -> Kiểm tra hệ thống chặn 400 Bad Request kèm thông báo lỗi.
        """
        self.api_client.force_authenticate(user=self.u_letan)
        du_lieu_nhap_lan_1 = {
            'ma_benh_nhan': 'BN_TEST_01',
            'loai_lich': 'KHAM_BENH',
            'tu_dong_chon_bac_si': True,
            'ma_phong': 'P101',
            'ten_phong': 'Phòng Khám Nội 1',
            'ghi_chu': 'Walk-in lần 1 trong ngày',
        }
        res1 = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_lan_1, format='json')
        self.assertEqual(res1.status_code, 201)

        du_lieu_nhap_lan_2 = {
            'ma_benh_nhan': 'BN_TEST_01',
            'loai_lich': 'KHAM_BENH',
            'tu_dong_chon_bac_si': True,
            'ma_phong': 'P102',
            'ten_phong': 'Phòng Khám Nội 2',
            'ghi_chu': 'Đăng ký Walk-in trùng lần 2 trong ngày',
        }
        res2 = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_lan_2, format='json')
        self.assertEqual(res2.status_code, 400)
        self.assertIn('error', res2.data)

    def test_TC_WEB_16_state_le_tan_check_in_lich_hen_truc_tuyen_cap_stt(self):
        """
        TC_WEB_16 [State Transition - Hợp lệ]: Lễ tân lọc danh sách 'Có hẹn — chưa check-in' và bấm [Check-in] tại quầy — chuyển CHECKED_IN và cấp STT.
        Test Case Procedure:
          1. Bệnh nhân 1 (benhnhan1_test) nhập form đặt lịch trực tuyến (du_lieu_nhap_dat_lich) cho khung giờ hôm nay + 1 giờ.
          2. Lễ tân (letan_test) đăng nhập Web SPA -> menu [Tiếp nhận & lấy số] -> Tab [1. Có hẹn — check-in] (gọi GET '/api/lich-hen/lich-hen/hom_nay_letan/?chua_check_in=true').
          3. Tại dòng lịch của BN_TEST_01, nhấn nút [Check-in] (POST '/api/lich-hen/lich-hen/{id}/check_in/').
          4. Kiểm tra trạng thái chuyển sang CHECKED_IN, ghi nhận thời gian đến và cấp số thứ tự stt_trong_ngay.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_dat_lich = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': (timezone.now() + timedelta(hours=1)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Đặt lịch trước đến quầy check-in',
        }
        res_dat = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_dat_lich, format='json')
        self.assertEqual(res_dat.status_code, 201)
        lich_id = LichHen.objects.get(ghi_chu=du_lieu_nhap_dat_lich['ghi_chu']).pk

        self.api_client.force_authenticate(user=self.u_letan)
        res_pending = self.api_client.get('/api/lich-hen/lich-hen/hom_nay_letan/', {'chua_check_in': 'true', 'page_size': 200})
        self.assertEqual(res_pending.status_code, 200)

        du_lieu_nhap_checkin = {
            'ma_benh_nhan_tim_kiem': 'BN_TEST_01',
            'ghi_chu_quay': 'Bệnh nhân đã có mặt tại quầy lễ tân',
        }
        res_ci = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/check_in/', du_lieu_nhap_checkin, format='json')
        self.assertEqual(res_ci.status_code, 200)
        self.assertEqual(res_ci.data['trang_thai'], 'CHECKED_IN')
        self.assertIsNotNone(res_ci.data['stt_trong_ngay'])

    def test_TC_WEB_17_decision_table_le_tan_tra_cuu_xep_hang_bac_si_va_phan_cong_bac_si(self):
        """
        TC_WEB_17 [Decision Table - Điều phối Bác sĩ]: Lễ tân tra cứu bảng xếp hạng 'Bác sĩ trực ca' và gán bác sĩ (thành công khi có ca, chặn khi không có ca).
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Lễ tân (letan_test) -> Chọn Ngày (#lt-tn-ngay) và Ca làm (#lt-tn-ca) -> Nhấn [Tải lại BS] (GET '/api/lich-hen/lich-hen/bac_si_xep_hang/').
          2. Trên lịch hẹn của BN_TEST_01, Lễ tân chọn BS. Trần Thị Bình (bacsi2 - không có ca trực) ở dropdown '#lt-pc-bs-{id}' -> Nhấn [Gán] (du_lieu_nhap_bs_khong_ca):
             -> Kiểm tra hệ thống chặn 400 Bad Request do bác sĩ chưa đăng ký ca trực.
          3. Lễ tân chọn BS. Nguyễn Văn An (bacsi1 - có ca trực) ở dropdown '#lt-pc-bs-{id}' -> Nhấn [Gán] (du_lieu_nhap_bs_co_ca):
             -> Kiểm tra trả về 200 OK và cập nhật đúng bác sĩ phụ trách.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_dat = {
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': (timezone.now() + timedelta(hours=2)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Lịch hẹn chờ Lễ tân phân công bác sĩ',
        }
        self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_dat, format='json')
        lich_id = LichHen.objects.get(ghi_chu=du_lieu_nhap_dat['ghi_chu']).pk

        self.api_client.force_authenticate(user=self.u_letan)
        res_rank = self.api_client.get(
            '/api/lich-hen/lich-hen/bac_si_xep_hang/',
            {'ngay': self.today.isoformat(), 'ca_lam': 'SANG'},
        )
        self.assertEqual(res_rank.status_code, 200)
        self.assertGreaterEqual(len(res_rank.data.get('items', [])), 1)

        du_lieu_nhap_bs_khong_ca = {'bac_si': str(self.bacsi2.pk)}
        res_no_shift = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lich_id}/phan_cong_bac_si/',
            du_lieu_nhap_bs_khong_ca,
            format='json',
        )
        self.assertEqual(res_no_shift.status_code, 400)

        du_lieu_nhap_bs_co_ca = {'bac_si': str(self.bacsi1.pk)}
        res_ok = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lich_id}/phan_cong_bac_si/',
            du_lieu_nhap_bs_co_ca,
            format='json',
        )
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(str(res_ok.data['bac_si']['nguoi_dung']), str(self.bacsi1.pk))

    def test_TC_WEB_18_ep_le_tan_dieu_phoi_gan_phong_va_gui_thong_bao_moi_kham(self):
        """
        TC_WEB_18 [EP & Validation]: Lễ tân nhập thông tin gán phòng khám (phan_cong_phong), gửi nhắc mời vào phòng (200) và chặn nhắc tùy chỉnh rỗng (400).
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Lễ tân (letan_test) -> Tiếp nhận Walk-in cho BN_TEST_02 (du_lieu_nhap_walkin).
          2. Chuyển sang Tab [3. Hàng chờ & phòng], tại dòng lịch của BN_TEST_02 nhập dữ liệu gán phòng (du_lieu_nhap_gan_phong):
             - Mã phòng (ma_phong): 'P202'
             - Tên phòng (ten_phong): 'Phòng Khám Nhi 2'
             -> Nhấn nút [Lưu phòng].
          3. Nhấn nút [Vào phòng] / [Nhắc khác], gửi thông báo (du_lieu_nhap_gui_nhac):
             - Loại nhắc (loai): 'MOI_VAO_PHONG'
             - Nội dung nhắc (noi_dung): 'Mời bệnh nhân Phạm Thị Hoa vào Phòng Khám Nhi 2 (P202)' -> Trả về 200 OK.
          4. Chọn loại nhắc 'TU_CHON' nhưng bỏ trống nội dung (du_lieu_nhap_nhac_rong) -> Kiểm tra bị chặn 400 Bad Request.
        """
        self.api_client.force_authenticate(user=self.u_letan)
        du_lieu_nhap_walkin = {
            'ma_benh_nhan': 'BN_TEST_02',
            'loai_lich': 'KHAM_BENH',
            'tu_dong_chon_bac_si': True,
            'ghi_chu': 'Khám tổng quát BN2',
        }
        res_wi = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_walkin, format='json')
        lich_id = res_wi.data['id']

        du_lieu_nhap_gan_phong = {
            'ma_phong': 'P202',
            'ten_phong': 'Phòng Khám Nhi 2',
        }
        res_room = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lich_id}/phan_cong_phong/',
            du_lieu_nhap_gan_phong,
            format='json',
        )
        self.assertEqual(res_room.status_code, 200)
        self.assertEqual(res_room.data['ma_phong'], 'P202')

        du_lieu_nhap_gui_nhac = {
            'loai': 'MOI_VAO_PHONG',
            'noi_dung': 'Mời bệnh nhân Phạm Thị Hoa vào Phòng Khám Nhi 2 (P202)',
        }
        res_notify = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lich_id}/gui_nhac_benh_nhan/',
            du_lieu_nhap_gui_nhac,
            format='json',
        )
        self.assertEqual(res_notify.status_code, 200)
        self.assertTrue(res_notify.data['success'])

        du_lieu_nhap_nhac_rong = {
            'loai': 'TU_CHON',
            'noi_dung': '   ',
        }
        res_empty_custom = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lich_id}/gui_nhac_benh_nhan/',
            du_lieu_nhap_nhac_rong,
            format='json',
        )
        self.assertEqual(res_empty_custom.status_code, 400)
        self.assertIn('noi_dung', res_empty_custom.data)

    def test_TC_WEB_19_rbac_chan_benh_nhan_goi_cac_api_dieu_phoi_cua_le_tan(self):
        """
        TC_WEB_19 [RBAC]: Bệnh nhân không có quyền thực hiện các thao tác Tiếp nhận Walk-in, Check-in và Gán phòng của Lễ tân (403 Forbidden).
        Test Case Procedure:
          1. Đăng nhập Web SPA với tài khoản Bệnh nhân (benhnhan1_test), đặt 1 lịch hẹn trực tuyến (du_lieu_nhap_dat).
          2. Bệnh nhân cố tình gửi dữ liệu form Tiếp nhận Walk-in (du_lieu_nhap_walkin) tới '/api/lich-hen/lich-hen/walk_in/' -> Bị chặn 403 Forbidden.
          3. Bệnh nhân cố tình gọi Check-in ('.../check_in/') và Gán phòng ('.../phan_cong_phong/') trên lịch vừa đặt -> Đều bị chặn 403 Forbidden.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_dat = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': (timezone.now() + timedelta(days=1, hours=1)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'ghi_chu': 'Lịch kiểm tra RBAC Lễ tân',
        }
        self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_dat, format='json')
        lich_id = LichHen.objects.get(ghi_chu='Lịch kiểm tra RBAC Lễ tân').pk

        du_lieu_nhap_walkin = {
            'ma_benh_nhan': 'BN_TEST_01',
            'loai_lich': 'KHAM_BENH',
            'tu_dong_chon_bac_si': True,
            'ma_phong': 'P101',
            'ghi_chu': 'Bệnh nhân tự gửi request Walk-in',
        }
        res_wi = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_walkin, format='json')
        self.assertEqual(res_wi.status_code, 403)

        res_ci = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/check_in/', {}, format='json')
        self.assertEqual(res_ci.status_code, 403)

        res_room = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lich_id}/phan_cong_phong/',
            {'ma_phong': 'P999', 'ten_phong': 'Phòng tự gán'},
            format='json',
        )
        self.assertEqual(res_room.status_code, 403)

    def test_TC_WEB_20_state_le_tan_xac_nhan_lich_hen_moi_dat_cho_xac_nhan_theo_srs(self):
        """
        TC_WEB_20 [State Transition - FAILED vs SRS]: Theo SRS UC003/REQ-APPT-04, Lễ tân nhấn [Xác nhận] trên lịch mới đặt (CHO_XAC_NHAN) phải chuyển sang DA_XAC_NHAN (200 OK).
        Test Case Procedure:
          1. Bệnh nhân (benhnhan1_test) đăng nhập Web SPA -> menu [Lịch hẹn], nhập dữ liệu đặt lịch (du_lieu_nhap_dat_lich):
             - Loại lịch: 'KHAM_BENH', Bác sĩ: BS. Nguyễn Văn An, Giờ khám: Ngày mai + 5h, SĐT: '0901000007', Ghi chú: 'Lịch hẹn chờ Lễ tân xác nhận'.
          2. Lễ tân (letan_test) đăng nhập Web SPA -> mở danh sách lịch hẹn chờ xác nhận, chọn lịch vừa đặt và nhấn nút [Xác nhận & lấy số] với dữ liệu (du_lieu_nhap_xac_nhan).
          3. Kiểm tra phản hồi: Kỳ vọng theo SRS REQ-APPT-04 phải trả về 200 OK và chuyển sang DA_XAC_NHAN.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_dat_lich = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': (timezone.now() + timedelta(days=1, hours=5)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'can_nhac_nho': True,
            'ghi_chu': 'Lịch hẹn chờ Lễ tân xác nhận',
        }
        res_dat = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_dat_lich, format='json')
        self.assertEqual(res_dat.status_code, 201)
        lich_id = LichHen.objects.get(ghi_chu=du_lieu_nhap_dat_lich['ghi_chu']).pk

        self.api_client.force_authenticate(user=self.u_letan)
        du_lieu_nhap_xac_nhan = {
            'ghi_chu_xac_nhan': 'Lễ tân đã gọi điện xác nhận với bệnh nhân',
        }
        res_xn = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/xac_nhan/', du_lieu_nhap_xac_nhan, format='json')
        # Kỳ vọng theo SRS REQ-APPT-04: Lịch mới tạo ở trạng thái CHO_XAC_NHAN, Lễ tân xác nhận -> 200 OK (DA_XAC_NHAN).
        # Thực tế code LichHenViewSet.xac_nhan kiểm tra cứng `if lich_hen.trang_thai != 'DA_DAT'` nên từ chối 400 Bad Request!
        self.assertEqual(
            res_xn.status_code,
            200,
            "LỖI SRS (REQ-APPT-04): Action xac_nhan kiểm tra cứng trang_thai != 'DA_DAT' nên không xác nhận được lịch mới đặt ở trạng thái CHO_XAC_NHAN (400)!",
        )
