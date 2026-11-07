from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import *
import json
from datetime import date, timedelta

User = get_user_model()

class NguoiDungModelTest(TestCase):
    """Test models"""
    
    def setUp(self):
        self.user_data = {
            'ten_dang_nhap': 'testuser',
            'email': 'test@example.com',
            'ho_ten': 'Test User',
            'so_dien_thoai': '0123456789',
            'vai_tro': 'BENH_NHAN',
            'password': 'Test@123456'
        }
    
    def test_create_user(self):
        """Test tạo user thành công"""
        user = User.objects.create_user(
            ten_dang_nhap=self.user_data['ten_dang_nhap'],
            mat_khau=self.user_data['password'],
            **{k:v for k,v in self.user_data.items() if k not in ['ten_dang_nhap', 'password']}
        )
        
        self.assertEqual(user.ten_dang_nhap, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('Test@123456'))
        self.assertEqual(user.vai_tro, 'BENH_NHAN')
        self.assertTrue(user.is_active)
    
    def test_lock_account_after_5_failed_logins(self):
        """Test khóa tài khoản sau 5 lần đăng nhập sai"""
        user = User.objects.create_user(
            ten_dang_nhap='testuser',
            mat_khau='Test@123456',
            email='test@example.com',
            ho_ten='Test User',
            so_dien_thoai='0123456789',
            vai_tro='BENH_NHAN'
        )
        
        # Mô phỏng 5 lần đăng nhập sai
        for i in range(5):
            user.login_attempts += 1
            user.save()
        
        # Lần thứ 5 sẽ khóa
        if user.login_attempts >= 5:
            user.lock_account(30)
        
        user.refresh_from_db()
        self.assertTrue(user.is_locked)
        self.assertIsNotNone(user.locked_until)
        self.assertGreater(user.locked_until, timezone.now())
    
    def test_unlock_account(self):
        """Test mở khóa tài khoản"""
        user = User.objects.create_user(
            ten_dang_nhap='testuser',
            mat_khau='Test@123456',
            email='test@example.com',
            ho_ten='Test User',
            so_dien_thoai='0123456789',
            vai_tro='BENH_NHAN'
        )
        
        user.lock_account(30)
        user.refresh_from_db()
        self.assertTrue(user.is_locked)
        
        user.unlock_account()
        user.refresh_from_db()
        self.assertFalse(user.is_locked)
        self.assertIsNone(user.locked_until)
        self.assertEqual(user.login_attempts, 0)


class BenhNhanModelTest(TestCase):
    """Test model Bệnh nhân"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            ten_dang_nhap='benhnhan',
            mat_khau='Test@123456',
            email='benhnhan@example.com',
            ho_ten='Nguyễn Văn A',
            so_dien_thoai='0123456789',
            vai_tro='BENH_NHAN'
        )
        
        self.benh_nhan = BenhNhan.objects.create(
            nguoi_dung=self.user,
            ma_benh_nhan='BN20240001',
            ngay_sinh=date(1990, 1, 1),
            gioi_tinh='NAM',
            dia_chi='Hà Nội',
            chieu_cao=175,
            can_nang=70
        )
    
    def test_tuoi(self):
        """Test tính tuổi"""
        expected_age = date.today().year - 1990
        # Điều chỉnh nếu chưa đến sinh nhật
        today = date.today()
        if (today.month, today.day) < (1, 1):
            expected_age -= 1
        
        self.assertEqual(self.benh_nhan.tuoi(), expected_age)
    
    def test_bmi(self):
        """Test tính BMI"""
        expected_bmi = round(70 / ((175/100) ** 2), 2)
        self.assertEqual(self.benh_nhan.get_bmi(), expected_bmi)
        
        # Test phân loại BMI
        self.assertEqual(self.benh_nhan.get_bmi_phan_loai(), 'Bình thường')
    
    def test_bhyt_con_han(self):
        """Test kiểm tra BHYT còn hạn"""
        # Chưa có BHYT
        self.assertFalse(self.benh_nhan.kiem_tra_bhyt_con_han())
        
        # Có BHYT còn hạn
        self.benh_nhan.ngay_dang_ky_bhyt = date(2024, 1, 1)
        self.benh_nhan.ngay_het_han_bhyt = date.today() + timedelta(days=30)
        self.assertTrue(self.benh_nhan.kiem_tra_bhyt_con_han())
        
        # BHYT hết hạn
        self.benh_nhan.ngay_het_han_bhyt = date.today() - timedelta(days=1)
        self.assertFalse(self.benh_nhan.kiem_tra_bhyt_con_han())


class NguoiDungAPITest(APITestCase):
    """Test API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Tạo user test
        self.user = User.objects.create_user(
            ten_dang_nhap='testuser',
            mat_khau='Test@123456',
            email='test@example.com',
            ho_ten='Test User',
            so_dien_thoai='0123456789',
            vai_tro='BENH_NHAN'
        )
        
        # URL endpoints
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.profile_url = reverse('get_profile')
        self.change_password_url = reverse('change_password')
    
    def test_register_success(self):
        """Test đăng ký thành công"""
        data = {
            'ten_dang_nhap': 'newuser',
            'password': 'Test@123456',
            'password2': 'Test@123456',
            'ho_ten': 'New User',
            'email': 'newuser@example.com',
            'so_dien_thoai': '0987654321',
            'vai_tro': 'BENH_NHAN',
            'ngay_sinh': '1995-05-15',
            'gioi_tinh': 'NU',
            'dia_chi': 'TP HCM'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['ten_dang_nhap'], 'newuser')
        
        # Kiểm tra user đã được tạo trong DB
        self.assertTrue(User.objects.filter(ten_dang_nhap='newuser').exists())
    
    def test_register_password_mismatch(self):
        """Test đăng ký với mật khẩu không khớp"""
        data = {
            'ten_dang_nhap': 'newuser',
            'password': 'Test@123456',
            'password2': 'Test@1234567',  # Không khớp
            'ho_ten': 'New User',
            'email': 'newuser@example.com',
            'so_dien_thoai': '0987654321',
            'vai_tro': 'BENH_NHAN'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_login_success(self):
        """Test đăng nhập thành công"""
        data = {
            'ten_dang_nhap': 'testuser',
            'password': 'Test@123456'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
    
    def test_login_wrong_password(self):
        """Test đăng nhập sai mật khẩu"""
        data = {
            'ten_dang_nhap': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra số lần đăng nhập thất bại tăng lên
        self.user.refresh_from_db()
        self.assertEqual(self.user.login_attempts, 1)
    
    def test_get_profile_authenticated(self):
        """Test lấy profile khi đã đăng nhập"""
        # Đăng nhập
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ten_dang_nhap'], 'testuser')
        self.assertEqual(response.data['ho_ten'], 'Test User')
    
    def test_get_profile_unauthenticated(self):
        """Test lấy profile khi chưa đăng nhập"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_change_password(self):
        """Test đổi mật khẩu"""
        # Đăng nhập
        self.client.force_authenticate(user=self.user)
        
        data = {
            'old_password': 'Test@123456',
            'new_password': 'NewPass@789',
            'new_password2': 'NewPass@789'
        }
        
        response = self.client.post(self.change_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Kiểm tra có thể đăng nhập với mật khẩu mới
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass@789'))
    
    def test_change_password_wrong_old(self):
        """Test đổi mật khẩu với mật khẩu cũ sai"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'NewPass@789',
            'new_password2': 'NewPass@789'
        }
        
        response = self.client.post(self.change_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)


class BenhNhanAPITest(APITestCase):
    """Test API Bệnh nhân"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Tạo bệnh nhân
        self.benh_nhan_user = User.objects.create_user(
            ten_dang_nhap='benhnhan',
            mat_khau='Test@123456',
            email='benhnhan@example.com',
            ho_ten='Nguyễn Văn Bệnh',
            so_dien_thoai='0123456789',
            vai_tro='BENH_NHAN'
        )
        
        self.benh_nhan = BenhNhan.objects.create(
            nguoi_dung=self.benh_nhan_user,
            ma_benh_nhan='BN20240002',
            ngay_sinh=date(1985, 5, 20),
            gioi_tinh='NAM',
            dia_chi='Đà Nẵng'
        )
        
        # Tạo nhân viên
        self.nhan_vien_user = User.objects.create_user(
            ten_dang_nhap='nhanvien',
            mat_khau='Test@123456',
            email='nhanvien@example.com',
            ho_ten='Trần Văn Nhân',
            so_dien_thoai='0987654321',
            vai_tro='NHAN_VIEN'
        )
        
        self.nhan_vien = NhanVien.objects.create(
            nguoi_dung=self.nhan_vien_user,
            ma_nhan_vien='NV001',
            phong_ban='Tiếp nhận',
            chuc_vu='LE_TAN'
        )
    
    def test_benh_nhan_xem_duoc_thong_tin_cua_minh(self):
        """Test bệnh nhân xem được thông tin của mình"""
        # Bệnh nhân đăng nhập
        self.client.force_authenticate(user=self.benh_nhan_user)
        
        response = self.client.get(f'/api/benh-nhan/{self.benh_nhan.nguoi_dung_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ma_benh_nhan'], 'BN20240002')
    
    def test_benh_nhan_khong_xem_duoc_benh_nhan_khac(self):
        """Test bệnh nhân không xem được thông tin bệnh nhân khác"""
        # Tạo bệnh nhân khác
        other_user = User.objects.create_user(
            ten_dang_nhap='benhnhan2',
            mat_khau='Test@123456',
            email='benhnhan2@example.com',
            ho_ten='Lê Thị B',
            so_dien_thoai='0112233445',
            vai_tro='BENH_NHAN'
        )
        
        other_benh_nhan = BenhNhan.objects.create(
            nguoi_dung=other_user,
            ma_benh_nhan='BN20240003',
            ngay_sinh=date(1990, 1, 1),
            gioi_tinh='NU',
            dia_chi='Huế'
        )
        
        # Bệnh nhân A đăng nhập
        self.client.force_authenticate(user=self.benh_nhan_user)
        
        response = self.client.get(f'/api/benh-nhan/{other_benh_nhan.nguoi_dung_id}/')
        
        # API trả về 404 thay vì 403 để không lộ thông tin tồn tại
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_nhan_vien_xem_duoc_tat_ca_benh_nhan(self):
        """Test nhân viên xem được tất cả bệnh nhân"""
        self.client.force_authenticate(user=self.nhan_vien_user)
        
        response = self.client.get('/api/benh-nhan/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ít nhất có 1 bệnh nhân
        self.assertGreaterEqual(len(response.data), 1)
    
    def test_nhan_vien_tao_benh_nhan(self):
        """Test nhân viên tạo bệnh nhân mới"""
        self.client.force_authenticate(user=self.nhan_vien_user)
        
        data = {
            'nguoi_dung': {
                'ten_dang_nhap': 'benhnhanmoi',
                'password': 'Test@123456',
                'password2': 'Test@123456',
                'ho_ten': 'Phạm Văn Mới',
                'email': 'moi@example.com',
                'so_dien_thoai': '0999888777',
                'vai_tro': 'BENH_NHAN',
                'ngay_sinh': '1992-03-10',
                'gioi_tinh': 'NAM',
                'dia_chi': 'Cần Thơ'
            },
            'ma_benh_nhan': 'BN20240004',
            'ngay_sinh': '1992-03-10',
            'gioi_tinh': 'NAM',
            'dia_chi': 'Cần Thơ'
        }
        
        response = self.client.post('/api/benh-nhan/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(BenhNhan.objects.filter(ma_benh_nhan='BN20240004').exists())