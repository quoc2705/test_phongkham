"""Nạp dữ liệu mẫu toàn diện cho hệ thống PhòngKhám+ (người dùng, bác sĩ, nhân viên, bệnh nhân, ca trực, thuốc/vaccine, lịch hẹn, hồ sơ bệnh án, đơn hàng)."""
import sys
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management import BaseCommand, call_command
from django.db import transaction
from django.utils import timezone

from benhan.models import ChanDoan, ChiTietDonThuoc, DonThuoc, HoSoBenhAn, LichSuTiemChung, ToaThuocMau, ChiTietToaMau
from donhang.models import ChiTietDonHang, DonHang, GioHang, ThanhToan
from lichhen.models import LichHen, LichKham, LichTiem
from nguoidung.models import BacSi, BenhNhan, DoctorSchedule, NguoiDung, NhanVien, ThongBao
from thuoc.models import Thuoc, Vaccine


class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu đầy đủ cho tất cả các phân hệ (Admin, Bác sĩ, Lễ tân, Bán thuốc, Kế toán/Kho, Bệnh nhân)'

    @transaction.atomic
    def handle(self, *args, **options):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        self.stdout.write('1. Đang nạp dữ liệu thuốc, vaccine và tồn kho...')
        call_command('seed_thuoc_vaccine')

        self.stdout.write('2. Đang tạo tài khoản mẫu cho tất cả các vai trò...')
        today = date.today()
        now = timezone.now()

        # 1. Admin
        admin_user, created = NguoiDung.objects.get_or_create(
            ten_dang_nhap='admin',
            defaults={
                'email': 'admin@phongkham.vn',
                'ho_ten': 'Quản Trị Viên Hệ Thống',
                'so_dien_thoai': '0901000001',
                'vai_tro': 'ADMIN',
                'gioi_tinh': 'NAM',
                'ngay_sinh': date(1988, 5, 15),
                'dia_chi': '123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng',
                'cccd': '048088000001',
                'is_staff': True,
                'is_superuser': True,
                'is_verified': True,
            },
        )
        if created:
            admin_user.set_password('Admin@123')
            admin_user.save()

        # 2. Bác sĩ 1 (Nội tổng quát)
        bs1_user, created = NguoiDung.objects.get_or_create(
            ten_dang_nhap='bacsi',
            defaults={
                'email': 'bacsi1@phongkham.vn',
                'ho_ten': 'BS. Nguyễn Minh Tuấn',
                'so_dien_thoai': '0901000002',
                'vai_tro': 'BAC_SI',
                'gioi_tinh': 'NAM',
                'ngay_sinh': date(1985, 3, 20),
                'dia_chi': '45 Lê Duẩn, Hải Châu, Đà Nẵng',
                'cccd': '048085000002',
                'is_verified': True,
            },
        )
        if created:
            bs1_user.set_password('Bacsi@123')
            bs1_user.save()

        bs1, _ = BacSi.objects.get_or_create(
            nguoi_dung=bs1_user,
            defaults={
                'ma_bac_si': f'BS{today.year}0001',
                'chuyen_khoa': 'Nội tổng quát',
                'so_giay_phep': 'CCHN-001025/BYT',
                'trinh_do': 'BAC_SI_CK1',
                'chuc_vu': 'TRUONG_KHOA',
                'chuyen_mon': 'Khám và điều trị bệnh lý nội khoa, tim mạch, tiêu hóa',
                'khoa_phong': 'P01 - Phòng Khám Nội',
                'ngay_bat_dau_cong_tac': date(2018, 1, 10),
                'gioi_thieu': 'Hơn 12 năm kinh nghiệm khám chữa bệnh Nội tổng quát.',
                'is_working': True,
            },
        )

        # 3. Bác sĩ 2 (Nhi khoa & Tiêm chủng)
        bs2_user, created = NguoiDung.objects.get_or_create(
            ten_dang_nhap='bacsi2',
            defaults={
                'email': 'bacsi2@phongkham.vn',
                'ho_ten': 'BS. Trần Thu Hà',
                'so_dien_thoai': '0901000003',
                'vai_tro': 'BAC_SI',
                'gioi_tinh': 'NU',
                'ngay_sinh': date(1990, 8, 12),
                'dia_chi': '88 Hàm Nghi, Thanh Khê, Đà Nẵng',
                'cccd': '048090000003',
                'is_verified': True,
            },
        )
        if created:
            bs2_user.set_password('Bacsi@123')
            bs2_user.save()

        bs2, _ = BacSi.objects.get_or_create(
            nguoi_dung=bs2_user,
            defaults={
                'ma_bac_si': f'BS{today.year}0002',
                'chuyen_khoa': 'Nhi khoa - Tiêm chủng',
                'so_giay_phep': 'CCHN-002089/BYT',
                'trinh_do': 'THAC_SI',
                'chuc_vu': 'BAC_SI_DIEU_TRI',
                'chuyen_mon': 'Khám sàng lọc tiêm chủng, tư vấn dinh dưỡng và bệnh lý nhi khoa',
                'khoa_phong': 'P02 - Phòng Tiêm chủng',
                'ngay_bat_dau_cong_tac': date(2020, 6, 1),
                'gioi_thieu': 'Chuyên gia tư vấn tiêm chủng và chăm sóc sức khỏe trẻ em.',
                'is_working': True,
            },
        )

        # 4. Lễ tân
        letan_user, created = NguoiDung.objects.get_or_create(
            ten_dang_nhap='letan',
            defaults={
                'email': 'letan@phongkham.vn',
                'ho_ten': 'Lê Thị Ngọc Ánh',
                'so_dien_thoai': '0901000004',
                'vai_tro': 'NHAN_VIEN',
                'gioi_tinh': 'NU',
                'ngay_sinh': date(1998, 11, 5),
                'dia_chi': '12 Nguyễn Thị Minh Khai, Hải Châu, Đà Nẵng',
                'cccd': '048098000004',
                'is_verified': True,
            },
        )
        if created:
            letan_user.set_password('Letan@123')
            letan_user.save()

        nv_letan, _ = NhanVien.objects.get_or_create(
            nguoi_dung=letan_user,
            defaults={
                'ma_nhan_vien': f'NV{today.year}0001',
                'phong_ban': 'Quầy Tiếp đón & CSKH',
                'chuc_vu': 'LE_TAN',
                'ngay_bat_dau_lam': date(2022, 3, 1),
                'mo_ta_cong_viec': 'Đón tiếp bệnh nhân, lấy số thứ tự, điều phối phòng khám',
                'is_working': True,
            },
        )

        # 5. Nhân viên bán thuốc
        banthuoc_user, created = NguoiDung.objects.get_or_create(
            ten_dang_nhap='banthuoc',
            defaults={
                'email': 'banthuoc@phongkham.vn',
                'ho_ten': 'Phạm Quốc Bảo',
                'so_dien_thoai': '0901000005',
                'vai_tro': 'NHAN_VIEN',
                'gioi_tinh': 'NAM',
                'ngay_sinh': date(1995, 4, 25),
                'dia_chi': '56 Điện Biên Phủ, Thanh Khê, Đà Nẵng',
                'cccd': '048095000005',
                'is_verified': True,
            },
        )
        if created:
            banthuoc_user.set_password('Banthuoc@123')
            banthuoc_user.save()

        nv_banthuoc, _ = NhanVien.objects.get_or_create(
            nguoi_dung=banthuoc_user,
            defaults={
                'ma_nhan_vien': f'NV{today.year}0002',
                'phong_ban': 'Nhà thuốc Phòng khám',
                'chuc_vu': 'BAN_THUOC',
                'ngay_bat_dau_lam': date(2021, 9, 15),
                'mo_ta_cong_viec': 'Cấp phát thuốc theo đơn và bán thuốc lẻ tại quầy',
                'is_working': True,
            },
        )

        # 6. Kế toán & Quản lý kho
        ketoan_user, created = NguoiDung.objects.get_or_create(
            ten_dang_nhap='ketoan',
            defaults={
                'email': 'ketoan@phongkham.vn',
                'ho_ten': 'Hoàng Thị Mai Hương',
                'so_dien_thoai': '0901000006',
                'vai_tro': 'NHAN_VIEN',
                'gioi_tinh': 'NU',
                'ngay_sinh': date(1993, 7, 18),
                'dia_chi': '102 Hoàng Diệu, Hải Châu, Đà Nẵng',
                'cccd': '048093000006',
                'is_verified': True,
            },
        )
        if created:
            ketoan_user.set_password('Ketoan@123')
            ketoan_user.save()

        nv_ketoan, _ = NhanVien.objects.get_or_create(
            nguoi_dung=ketoan_user,
            defaults={
                'ma_nhan_vien': f'NV{today.year}0003',
                'phong_ban': 'Phòng Tài chính - Kế toán & Kho dược',
                'chuc_vu': 'KE_TOAN',
                'ngay_bat_dau_lam': date(2020, 2, 10),
                'mo_ta_cong_viec': 'Quản lý thu chi, duyệt nhập xuất kho thuốc/vaccine, báo cáo doanh thu',
                'is_working': True,
            },
        )

        # 7. Bệnh nhân 1
        bn1_user, created = NguoiDung.objects.get_or_create(
            ten_dang_nhap='benhnhan',
            defaults={
                'email': 'benhnhan1@gmail.com',
                'ho_ten': 'Võ Văn Khang',
                'so_dien_thoai': '0905123456',
                'vai_tro': 'BENH_NHAN',
                'gioi_tinh': 'NAM',
                'ngay_sinh': date(1996, 2, 14),
                'dia_chi': '210 Ngô Quyền, Sơn Trà, Đà Nẵng',
                'cccd': '048096000007',
                'is_verified': True,
            },
        )
        if created:
            bn1_user.set_password('Benhnhan@123')
            bn1_user.save()

        bn1, _ = BenhNhan.objects.get_or_create(
            nguoi_dung=bn1_user,
            defaults={
                'ma_benh_nhan': f'BN{today.year}0001',
                'ngay_sinh': date(1996, 2, 14),
                'gioi_tinh': 'NAM',
                'dia_chi': '210 Ngô Quyền, Sơn Trà, Đà Nẵng',
                'so_bao_hiem': 'DN4480123456789',
                'ngay_dang_ky_bhyt': date(2026, 1, 1),
                'ngay_het_han_bhyt': date(2026, 12, 31),
                'noi_dang_ky_kham_chua': 'Bệnh viện Đa khoa Đà Nẵng',
                'nhom_mau': 'O+',
                'chieu_cao': Decimal('172.00'),
                'can_nang': Decimal('68.50'),
                'tien_su_benh': 'Viêm dạ dày nhẹ',
                'tien_su_di_ung': 'Không',
                'nghe_nghiep': 'CAN_BO',
            },
        )
        GioHang.objects.get_or_create(benh_nhan=bn1)

        # 8. Bệnh nhân 2
        bn2_user, created = NguoiDung.objects.get_or_create(
            ten_dang_nhap='benhnhan2',
            defaults={
                'email': 'benhnhan2@gmail.com',
                'ho_ten': 'Đặng Ngọc Lan',
                'so_dien_thoai': '0905654321',
                'vai_tro': 'BENH_NHAN',
                'gioi_tinh': 'NU',
                'ngay_sinh': date(1999, 10, 22),
                'dia_chi': '35 Phan Châu Trinh, Hải Châu, Đà Nẵng',
                'cccd': '048099000008',
                'is_verified': True,
            },
        )
        if created:
            bn2_user.set_password('Benhnhan@123')
            bn2_user.save()

        bn2, _ = BenhNhan.objects.get_or_create(
            nguoi_dung=bn2_user,
            defaults={
                'ma_benh_nhan': f'BN{today.year}0002',
                'ngay_sinh': date(1999, 10, 22),
                'gioi_tinh': 'NU',
                'dia_chi': '35 Phan Châu Trinh, Hải Châu, Đà Nẵng',
                'nhom_mau': 'A+',
                'chieu_cao': Decimal('160.00'),
                'can_nang': Decimal('52.00'),
                'tien_su_benh': 'Không',
                'tien_su_di_ung': 'Không',
                'nghe_nghiep': 'KINH_DOANH',
            },
        )
        GioHang.objects.get_or_create(benh_nhan=bn2)

        self.stdout.write('3. Đang đăng ký lịch trực tuần cho các bác sĩ...')
        for offset in range(-1, 8):
            ngay = today + timedelta(days=offset)
            for ca in ('SANG', 'CHIEU', 'TOI'):
                DoctorSchedule.objects.get_or_create(
                    bac_si=bs1,
                    ngay_lam=ngay,
                    ca_lam=ca,
                    defaults={'ghi_chu': 'Trực khám Nội tổng quát'},
                )
                DoctorSchedule.objects.get_or_create(
                    bac_si=bs2,
                    ngay_lam=ngay,
                    ca_lam=ca,
                    defaults={'ghi_chu': 'Trực khám Nhi & Tiêm chủng'},
                )

        self.stdout.write('4. Đang tạo lịch hẹn, hồ sơ bệnh án, đơn thuốc và đơn hàng mẫu...')
        thuoc_para = Thuoc.objects.filter(ten_thuoc__icontains='Paracetamol').first()
        thuoc_vitc = Thuoc.objects.filter(ten_thuoc__icontains='Vitamin C').first()
        thuoc_omep = Thuoc.objects.filter(ten_thuoc__icontains='Omeprazole').first()
        vaccine_cum = Vaccine.objects.filter(ten_vaccine__icontains='Cúm').first()

        # Tạo Toa thuốc mẫu
        if thuoc_para and thuoc_vitc:
            toa_mau, _ = ToaThuocMau.objects.get_or_create(
                ma_toa='TM001',
                defaults={
                    'ten_toa': 'Toa Cảm cúm - Sốt siêu vi thông thường',
                    'chuan_doan': 'Cảm cúm cấp / Viêm đường hô hấp trên (J06)',
                    'ma_icd10': 'J06',
                    'trieu_chung': 'Sốt nhẹ, đau đầu, mỏi cơ, sổ mũi',
                    'bac_si_tao': bs1,
                    'trang_thai': True,
                },
            )
            ChiTietToaMau.objects.get_or_create(
                toa_thuoc=toa_mau,
                thuoc=thuoc_para,
                defaults={
                    'so_luong': 10,
                    'lieu_dung': '1 viên/lần',
                    'cach_dung': 'UONG',
                    'thoi_diem': 'SANG_TOI',
                    'so_ngay_dung': 5,
                },
            )
            ChiTietToaMau.objects.get_or_create(
                toa_thuoc=toa_mau,
                thuoc=thuoc_vitc,
                defaults={
                    'so_luong': 5,
                    'lieu_dung': '1 viên/lần',
                    'cach_dung': 'UONG',
                    'thoi_diem': 'SANG',
                    'so_ngay_dung': 5,
                },
            )

        # Tạo Hồ sơ bệnh án mẫu đã khám + Đơn thuốc
        if not HoSoBenhAn.objects.filter(benh_nhan=bn1).exists():
            hs1 = HoSoBenhAn.objects.create(
                benh_nhan=bn1,
                bac_si=bs1,
                ly_do_kham='Đau thượng vị, ợ chua nhiều ngày',
                trieu_chung='Đau âm ỉ vùng thượng vị sau ăn, ợ hơi, ợ chua',
                ket_qua_kham_lam_sang='Bụng mềm, ấn tức nhẹ vùng thượng vị, tim phổi bình thường',
                tien_su_benh='Viêm dạ dày nhẹ',
                can_nang=Decimal('68.5'),
                chieu_cao=Decimal('172.0'),
                huyet_ap='120/80',
                nhiet_do=Decimal('36.8'),
                mach=76,
                nhip_tho=18,
                spO2=98,
                loai_kham='KHAM_BENH',
                trang_thai='DANG_DIEU_TRI',
                ghi_chu='Kiêng đồ chua cay, ăn đúng giờ',
            )
            ChanDoan.objects.create(
                ho_so=hs1,
                ma_icd10='K29',
                ten_benh='Viêm dạ dày và tá tràng',
                loai_benh='NGOAI_TRU',
                muc_do='NHẸ',
                mo_ta='Viêm niêm mạc dạ dày cấp tính mức độ nhẹ',
                ket_luan='Viêm dạ dày cấp (K29) - Điều trị nội khoa 7 ngày',
                phuong_phap_dieu_tri='Ức chế bơm proton (PPI) kết hợp điều chỉnh chế độ ăn',
                bac_si_chan_doan=bs1,
            )
            if thuoc_omep and thuoc_vitc:
                dt1 = DonThuoc.objects.create(
                    ho_so=hs1,
                    bac_si=bs1,
                    benh_nhan=bn1,
                    chuan_doan='Viêm dạ dày cấp (K29)',
                    han_su_dung=today + timedelta(days=7),
                    trang_thai='CHO_THANH_TOAN',
                    ghi_chu='Uống thuốc đúng giờ trước bữa ăn sáng',
                )
                ChiTietDonThuoc.objects.create(
                    don_thuoc=dt1,
                    thuoc=thuoc_omep,
                    so_luong=14,
                    lieu_dung='1 viên',
                    cach_dung='UONG',
                    thoi_diem='TRUOC_AN',
                    so_ngay_dung=7,
                    tan_suat='2 lần/ngày',
                )
                ChiTietDonThuoc.objects.create(
                    don_thuoc=dt1,
                    thuoc=thuoc_vitc,
                    so_luong=7,
                    lieu_dung='1 viên',
                    cach_dung='UONG',
                    thoi_diem='SAU_AN',
                    so_ngay_dung=7,
                    tan_suat='1 lần/ngày',
                )
                dt1.tinh_tong_tien()

        # Tạo Lịch hẹn khám hôm nay (CHECKED_IN để Bác sĩ & Lễ tân thấy ngay trong hàng chờ)
        if not LichHen.objects.filter(benh_nhan=bn1, loai_lich='KHAM_BENH').exists():
            lh_kham = LichHen.objects.create(
                benh_nhan=bn1,
                bac_si=bs1,
                nhan_vien_tao=nv_letan,
                loai_lich='KHAM_BENH',
                ngay_gio_hen=now + timedelta(hours=1),
                trang_thai='CHECKED_IN',
                thoi_gian_den=now,
                so_dien_thoai_lien_he=bn1_user.so_dien_thoai,
                email_lien_he=bn1_user.email,
                gia_dich_vu=Decimal('150000'),
                da_thanh_toan=True,
                phuong_thuc_thanh_toan='TIEN_MAT',
                ma_phong='P01',
                ten_phong='Phòng Khám Nội 01',
                stt_trong_ngay=1,
                ghi_chu='Khám kiểm tra dạ dày định kỳ',
            )
            LichKham.objects.create(
                lich_hen=lh_kham,
                bac_si=bs1,
                ly_do_kham='Khám kiểm tra dạ dày',
                trieu_chung='Đau nhẹ vùng thượng vị',
            )

        # Tạo Lịch hẹn tiêm chủng hôm nay cho Bệnh nhân 2
        if vaccine_cum and not LichHen.objects.filter(benh_nhan=bn2, loai_lich='TIEM_CHUNG').exists():
            lh_tiem = LichHen.objects.create(
                benh_nhan=bn2,
                bac_si=bs2,
                nhan_vien_tao=nv_letan,
                loai_lich='TIEM_CHUNG',
                ngay_gio_hen=now + timedelta(hours=2),
                trang_thai='CHECKED_IN',
                thoi_gian_den=now,
                so_dien_thoai_lien_he=bn2_user.so_dien_thoai,
                email_lien_he=bn2_user.email,
                gia_dich_vu=vaccine_cum.gia_tiem,
                da_thanh_toan=True,
                phuong_thuc_thanh_toan='TIEN_MAT',
                ma_phong='P02',
                ten_phong='Phòng Tiêm chủng 02',
                stt_trong_ngay=2,
                ghi_chu='Đăng ký tiêm vắc xin cúm mùa',
            )
            LichTiem.objects.create(
                lich_hen=lh_tiem,
                vaccine=vaccine_cum,
                so_mui=1,
                lo_vaccine='V202603',
                han_su_dung=today + timedelta(days=365),
                nguoi_tiem=bs2,
                trang_thai_tiem='CHUA_TIEM',
                ghi_chu='Khám sàng lọc đủ điều kiện tiêm',
            )

        # Tạo Đơn hàng mẫu đã hoàn thành để Kế toán có báo cáo doanh thu
        if thuoc_para and thuoc_vitc and not DonHang.objects.filter(ma_don_hang='DH20260001').exists():
            tien_hang = thuoc_para.gia_ban * 20 + thuoc_vitc.gia_ban * 10
            dh1 = DonHang.objects.create(
                ma_don_hang='DH20260001',
                benh_nhan=bn1,
                ten_nguoi_nhan=bn1_user.ho_ten,
                so_dien_thoai_nhan=bn1_user.so_dien_thoai,
                email_nhan=bn1_user.email,
                dia_chi_giao_hang=bn1.dia_chi,
                loai_don=DonHang.LoaiDon.TAI_QUAY,
                nhan_vien_xu_ly=nv_banthuoc,
                ngay_xu_ly=now,
                tong_tien_hang=tien_hang,
                phi_ship=Decimal('0'),
                giam_gia=Decimal('0'),
                tong_tien=tien_hang,
                trang_thai=DonHang.TrangThai.HOAN_THANH,
                ghi_chu='Mua thuốc tại quầy nhà thuốc',
            )
            ChiTietDonHang.objects.create(
                don_hang=dh1,
                thuoc=thuoc_para,
                so_luong=20,
                don_gia=thuoc_para.gia_ban,
            )
            ChiTietDonHang.objects.create(
                don_hang=dh1,
                thuoc=thuoc_vitc,
                so_luong=10,
                don_gia=thuoc_vitc.gia_ban,
            )
            ThanhToan.objects.create(
                don_hang=dh1,
                so_tien=tien_hang,
                phuong_thuc=ThanhToan.PhuongThuc.TIEN_MAT,
                trang_thai=ThanhToan.TrangThai.THANH_CONG,
                ma_giao_dich='TM-DH20260001',
                noi_dung='Thanh toán tiền mặt tại quầy',
            )

        # Thông báo mẫu
        if not ThongBao.objects.filter(nguoi_nhan=bn1_user).exists():
            ThongBao.objects.create(
                nguoi_nhan=bn1_user,
                loai='LICH_HEN',
                tieu_de='Xác nhận lịch khám hôm nay',
                noi_dung='Bạn có lịch khám Nội tổng quát với BS. Nguyễn Minh Tuấn tại Phòng P01.',
            )

        self.stdout.write(self.style.SUCCESS('=== HOÀN TẤT NẠP DỮ LIỆU MẪU TOÀN HỆ THỐNG ==='))

