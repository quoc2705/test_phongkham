from celery import shared_task
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)


def _sms_da_cau_hinh():
    if not getattr(settings, 'SMS_ENABLED', False):
        return False
    key = getattr(settings, 'SMS_API_KEY', '') or ''
    if key in ('', 'your-sms-api-key'):
        return False
    return True


@shared_task
def gui_sms(so_dien_thoai, noi_dung):
    """
    Gửi SMS (ESMS.vn). Chỉ gọi API khi SMS_ENABLED=true và đã cấu khóa;
    nếu không, ghi log (dev / chưa cấu hình).
    """
    try:
        if not _sms_da_cau_hinh():
            logger.info(
                "[SMS skipped] To=%s msg=%s",
                so_dien_thoai,
                (noi_dung or '')[:200],
            )
            return {'success': True, 'skipped': True}

        api_key = settings.SMS_API_KEY
        secret_key = settings.SMS_SECRET_KEY
        brand_name = settings.SMS_BRAND_NAME

        so_dien_thoai = (so_dien_thoai or '').strip()
        if not so_dien_thoai:
            return {'success': False, 'error': 'Thiếu số điện thoại'}

        # Format số điện thoại
        if so_dien_thoai.startswith('0'):
            so_dien_thoai = '84' + so_dien_thoai[1:]
        
        # Gửi request đến ESMS API
        url = 'http://rest.esms.vn/MainService.svc/json/SendMultipleMessage_V4_post_json/'
        
        data = {
            'ApiKey': api_key,
            'SecretKey': secret_key,
            'Phone': so_dien_thoai,
            'Content': noi_dung,
            'Brandname': brand_name,
            'SmsType': '2',  # 2: SMS Brandname
        }
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('CodeResult') == '100':
            logger.info(f"Gửi SMS thành công đến {so_dien_thoai}")
            return {'success': True, 'message': 'SMS đã được gửi'}
        else:
            logger.error(f"Lỗi gửi SMS: {result.get('ErrorMessage')}")
            return {'success': False, 'error': result.get('ErrorMessage')}
            
    except Exception as e:
        logger.error(f"Lỗi gửi SMS: {str(e)}")
        return {'success': False, 'error': str(e)}

@shared_task
def gui_thong_bao_lich_hen(lich_hen_id):
    """Gửi thông báo khi có lịch hẹn mới"""
    from lichhen.models import LichHen
    
    try:
        lich_hen = LichHen.objects.get(id=lich_hen_id)
        benh_nhan = lich_hen.benh_nhan
        
        # Tạo nội dung SMS
        ngay_gio = lich_hen.ngay_gio_hen.strftime('%d/%m/%Y %H:%M')
        noi_dung = f"[Phong Kham] Lich hen {lich_hen.get_loai_lich_display()} cua ban vao {ngay_gio}. Ma BN: {benh_nhan.ma_benh_nhan}"
        
        # Gửi SMS
        gui_sms.delay(benh_nhan.nguoi_dung.so_dien_thoai, noi_dung)
        
        logger.info(f"Đã lên lịch gửi SMS cho lịch hẹn {lich_hen_id}")
        
    except LichHen.DoesNotExist:
        logger.error(f"Không tìm thấy lịch hẹn {lich_hen_id}")
    except Exception as e:
        logger.error(f"Lỗi gửi thông báo lịch hẹn: {str(e)}")

@shared_task
def gui_thong_bao_don_hang(don_hang_id):
    """Gửi thông báo khi có đơn hàng mới"""
    from donhang.models import DonHang
    
    try:
        don_hang = DonHang.objects.get(id=don_hang_id)
        benh_nhan = don_hang.benh_nhan
        
        noi_dung = f"[Phong Kham] Don hang {don_hang.ma_don_hang} cua ban da duoc tao thanh cong. Tong tien: {don_hang.tong_tien:,.0f}d"
        
        gui_sms.delay(benh_nhan.nguoi_dung.so_dien_thoai, noi_dung)
        
    except DonHang.DoesNotExist:
        logger.error(f"Không tìm thấy đơn hàng {don_hang_id}")
    except Exception as e:
        logger.error(f"Lỗi gửi thông báo đơn hàng: {str(e)}")


@shared_task
def xu_ly_nhac_lich_hen_truoc_moc():
    """
    Quét NhacNhoLichHen (đã lên lịch tại thời điểm tạo/sửa lịch: trước 1 ngày so với giờ khám).
    Với mỗi bản ghi đến hạn: tạo ThongBao trong tài khoản + gửi SMS tới SĐT liên hệ lịch hoặc SĐT đăng ký.
    """
    from django.utils import timezone
    from django.db import transaction
    from lichhen.models import NhacNhoLichHen
    from nguoidung.models import ThongBao

    now = timezone.now()
    ids = list(
        NhacNhoLichHen.objects.filter(
            trang_thai='CHO_GUI',
            thoi_gian_nhac__lte=now,
        ).values_list('id', flat=True)[:250]
    )
    sent = 0
    for nid in ids:
        try:
            with transaction.atomic():
                nh = (
                    NhacNhoLichHen.objects.select_for_update()
                    .filter(pk=nid, trang_thai='CHO_GUI')
                    .select_related('lich_hen__benh_nhan__nguoi_dung')
                    .first()
                )
                if not nh:
                    continue
                lh = nh.lich_hen
                if lh.trang_thai in ('HOAN_THANH', 'DA_HUY', 'VANG_MAT'):
                    nh.delete()
                    continue

                nguoi = lh.benh_nhan.nguoi_dung
                tieu_de = 'Nhắc lịch hẹn (ngày mai)'
                noi_dung_tb = nh.noi_dung or (
                    f"Bạn có lịch {lh.get_loai_lich_display()} "
                    f"vào {lh.ngay_gio_hen.strftime('%H:%M ngày %d/%m/%Y')}."
                )
                ThongBao.objects.create(
                    nguoi_nhan=nguoi,
                    loai='LICH_HEN',
                    tieu_de=tieu_de,
                    noi_dung=noi_dung_tb,
                    du_lieu_lien_quan={
                        'lich_hen_id': str(lh.pk),
                        'ma_lich_hen': lh.ma_lich_hen or '',
                        'loai': 'nhac_truoc_1_ngay',
                    },
                )

                sdt = (lh.so_dien_thoai_lien_he or '').strip() or (nguoi.so_dien_thoai or '').strip()
                brand = getattr(settings, 'SMS_BRAND_NAME', 'PhongKham')
                if sdt:
                    sms = (
                        f"[{brand}] Ban co lich {lh.get_loai_lich_display()} "
                        f"luc {lh.ngay_gio_hen.strftime('%H:%M %d/%m/%Y')}. "
                        f"Ma: {lh.ma_lich_hen or str(lh.pk)[:8]}"
                    )
                    transaction.on_commit(
                        lambda s=sdt, m=sms[:480]: gui_sms.delay(s, m)
                    )

                nh.trang_thai = 'DA_GUI'
                nh.sent_at = now
                nh.chi_tiet_phan_hoi = {'sms_queued': bool(sdt), 'thong_bao_app': True}
                nh.save()

                lh.da_nhac_nho = True
                lh.ngay_nhac_nho = now
                lh.save()
                sent += 1
        except Exception as e:
            logger.exception('xu_ly_nhac_lich_hen_truoc_moc id=%s: %s', nid, e)

    if sent:
        logger.info('xu_ly_nhac_lich_hen_truoc_moc: đã xử lý %s nhắc', sent)


@shared_task
def nhan_lich_hen_sap_toi():
    """
    (Tuỳ chọn) Nhắc SMS lịch trong ngày — không bật trong beat mặc định.
    """
    from lichhen.models import LichHen
    from django.utils import timezone
    from datetime import timedelta

    try:
        hom_nay = timezone.now().date()

        lich_hen_hom_nay = LichHen.objects.filter(
            ngay_gio_hen__date=hom_nay,
            trang_thai__in=['DA_DAT', 'DA_XAC_NHAN']
        )

        for lich in lich_hen_hom_nay:
            benh_nhan = lich.benh_nhan
            ngay_gio = lich.ngay_gio_hen.strftime('%H:%M')
            noi_dung = (
                f"[Phong Kham] Nho lich hen {lich.get_loai_lich_display()} "
                f"cua ban hom nay luc {ngay_gio}. Ma BN: {benh_nhan.ma_benh_nhan}"
            )
            gui_sms.delay(benh_nhan.nguoi_dung.so_dien_thoai, noi_dung)

        logger.info('nhan_lich_hen_sap_toi: %s lịch', lich_hen_hom_nay.count())

    except Exception as e:
        logger.error(f"Lỗi task nhắc lịch hẹn: {str(e)}")

@shared_task
def kiem_tra_thuoc_het_han():
    """
    Task chạy định kỳ (mỗi tuần)
    Kiểm tra thuốc sắp hết hạn và gửi cảnh báo
    """
    from thuoc.models import KhoThuoc
    from nguoidung.models import NguoiDung
    from thongbao.models import ThongBao
    from datetime import date, timedelta
    
    try:
        # Thuốc hết hạn trong 30 ngày
        ngay_kiem_tra = date.today() + timedelta(days=30)
        
        thuoc_sap_het = KhoThuoc.objects.filter(
            han_su_dung__lte=ngay_kiem_tra,
            han_su_dung__gt=date.today(),
            so_luong__gt=0
        )
        
        if thuoc_sap_het.exists():
            # Gửi thông báo cho nhân viên
            nhan_vien = NguoiDung.objects.filter(vai_tro='NHAN_VIEN')
            
            for nv in nhan_vien:
                ThongBao.objects.create(
                    nguoi_nhan=nv,
                    loai='HE_THONG',
                    tieu_de='Cảnh báo thuốc sắp hết hạn',
                    noi_dung=f'Có {thuoc_sap_het.count()} loại thuốc sắp hết hạn trong vòng 30 ngày',
                )
        
        logger.info(f"Đã kiểm tra {thuoc_sap_het.count()} thuốc sắp hết hạn")
        
    except Exception as e:
        logger.error(f"Lỗi task kiểm tra thuốc hết hạn: {str(e)}")