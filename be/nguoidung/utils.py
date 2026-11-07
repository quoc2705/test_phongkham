import re
import logging
from django.core.exceptions import ValidationError
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_password_strength(password):
    """
    Validate độ mạnh của mật khẩu
    Returns: (is_valid, message)
    """
    if len(password) < 8:
        return False, "Mật khẩu phải có ít nhất 8 ký tự"
    
    if not re.search(r'[A-Z]', password):
        return False, "Mật khẩu phải có ít nhất 1 chữ hoa"
    
    if not re.search(r'[a-z]', password):
        return False, "Mật khẩu phải có ít nhất 1 chữ thường"
    
    if not re.search(r'[0-9]', password):
        return False, "Mật khẩu phải có ít nhất 1 chữ số"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        return False, "Mật khẩu phải có ít nhất 1 ký tự đặc biệt"
    
    return True, "Mật khẩu hợp lệ"

def generate_ma_benh_nhan():
    """Tạo mã BN theo format BN + YYYY + 0001 tăng dần"""
    from .models import BenhNhan
    nam_hien_tai = datetime.now().year
    prefix = f"BN{nam_hien_tai}"

    ma_moi_nhat = (
        BenhNhan.objects
        .filter(ma_benh_nhan__startswith=prefix)
        .order_by('-ma_benh_nhan')
        .values_list('ma_benh_nhan', flat=True)
        .first()
    )

    if not ma_moi_nhat:
        return f"{prefix}0001"

    try:
        so_hien_tai = int(ma_moi_nhat[-4:])
    except (TypeError, ValueError):
        so_hien_tai = 0

    so_tiep_theo = so_hien_tai + 1
    return f"{prefix}{so_tiep_theo:04d}"

def generate_ma_bac_si():
    """Tạo mã bác sĩ tự động — BS{YYYY}{0001} (đồng bộ với BacSi.generate_next_ma_bac_si)."""
    from .models import BacSi
    return BacSi.generate_next_ma_bac_si()

def chuan_hoa_so_dien_thoai_vietnam(value):
    """
    Chuẩn hóa SĐT VN về dạng 0 + 9–10 chữ số (khớp RegexValidator NguoiDung).
    Xử lý: +84 / 84 đầu số, thiếu số 0 (912345678), bỏ khoảng trắng và dấu gạch.
    """
    if value is None:
        return value
    raw = str(value).strip()
    if not raw:
        return raw
    digits = ''.join(c for c in raw if c.isdigit())
    if not digits:
        return raw
    if digits.startswith('84') and len(digits) >= 11 and digits[2] == '9':
        digits = '0' + digits[2:]
        if len(digits) > 11:
            digits = digits[:11]
    elif len(digits) == 9 and digits[0] == '9':
        digits = '0' + digits
    return digits


def log_user_activity(user, action, object_type, object_id=None, old_data=None, new_data=None, request=None):
    """Ghi nhật ký hoạt động người dùng"""
    from .models import NhatKyHoatDong
    
    ip_address = None
    user_agent = None
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    
    NhatKyHoatDong.objects.create(
        nguoi_dung=user,
        hanh_dong=action,
        doi_tuong=object_type,
        doi_tuong_id=str(object_id) if object_id else '',
        du_lieu_cu=old_data or {},
        du_lieu_moi=new_data or {},
        ip_address=ip_address,
        user_agent=user_agent
    )