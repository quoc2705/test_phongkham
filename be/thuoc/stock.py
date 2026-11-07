"""Trừ tồn kho vaccine khi xác nhận đã tiêm."""
from datetime import date

from thuoc.models import KhoVaccine, Vaccine


class VaccineHetTonError(Exception):
    """Không đủ tồn hoặc không tìm thấy lô phù hợp."""


def tru_ton_vaccine_mot_lieu(vaccine, *, lo_sx=None, han_su_dung=None):
    """
    Trừ 1 liều vaccine trong kho (FIFO theo ngày nhập nếu không chỉ định lô).
    Gọi trong transaction.atomic() và sau select_for_update ở caller hoặc tại đây.

    Trả về dict: lo_sx (str), han_su_dung (date).
    """
    if isinstance(vaccine, str):
        vaccine = Vaccine.objects.get(pk=vaccine)

    today = date.today()
    qs = (
        KhoVaccine.objects.select_for_update()
        .filter(vaccine=vaccine, so_luong__gt=0, han_su_dung__gt=today)
    )
    if lo_sx and han_su_dung:
        kho = qs.filter(lo_sx=lo_sx, han_su_dung=han_su_dung).first()
        if kho is None:
            raise VaccineHetTonError(
                'Không tìm thấy tồn kho cho vaccine/lô/hạn sử dụng này hoặc số lượng đã hết.'
            )
    else:
        kho = qs.order_by('ngay_nhap').first()
        if kho is None:
            raise VaccineHetTonError(
                'Vaccine không còn tồn kho còn hạn. Vui lòng nhập kho trước khi xác nhận tiêm.'
            )

    kho.so_luong -= 1
    kho.save(update_fields=['so_luong'])
    return {'lo_sx': (kho.lo_sx or '').strip(), 'han_su_dung': kho.han_su_dung}
