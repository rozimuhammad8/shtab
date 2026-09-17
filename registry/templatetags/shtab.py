# -*- coding: utf-8 -*-
"""Shablonlar uchun yordamchi filtrlar."""
from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def maydon(obj, nomi):
    """Nomi bo'yicha obyekt atributini qaytaradi.

    Ma'lumotnoma jadvallari umumiy shablon bilan chizilgani uchun ustun
    qiymatlari maydon nomi orqali olinadi:
        {{ qator|maydon:"nomi" }}
    """
    qiymat = getattr(obj, nomi, None)
    if callable(qiymat):
        qiymat = qiymat()
    return qiymat


@register.filter
def belgi(qiymat):
    """`True`/`False` ni nishon (badge) ko'rinishida chiqaradi."""
    if qiymat is True:
        return format_html('<span class="badge badge-yes">Ha</span>')
    if qiymat is False:
        return format_html('<span class="badge badge-no">Yo\'q</span>')
    return qiymat
