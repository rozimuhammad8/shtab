# -*- coding: utf-8 -*-
"""
`MurojaatSababi` jadvalini boshlang'ich ro'yxat bilan to'ldiradi.

Bu ma'lumot `database.xlsx` faylida yo'q - u shtab xodimlari tomonidan
kiritiladi. Quyidagi ro'yxat shunchaki qulay boshlanish nuqtasi:
veb-interfeysdagi "Ma'lumotnoma -> Murojaat sabablari" bo'limida
tahrirlash, yangisini qo'shish yoki o'chirish mumkin.
"""
from django.db import migrations

SABABLAR = [
    (10, "Ish bilan ta'minlash", "Doimiy ish yoki bandlik masalasi"),
    (20, 'Imtiyozli kredit', "Tadbirkorlik uchun imtiyozli kredit so'rovi"),
    (30, 'Subsidiya yoki ijtimoiy nafaqa', 'Ijtimoiy daftarlardan mablag\' ajratish'),
    (40, 'Kasb-hunarga o\'qitish', "Qayta tayyorlov va malaka oshirish"),
    (50, 'Tibbiy yordam', "Sog'lig'ini tiklash bo'yicha yordam"),
    (60, 'Uy-joy va kommunal masalalar', 'Uy ta\'miri, elektr, gaz, suv masalalari'),
    (70, "Farzandni bog'chaga joylashtirish", 'Vaucher yoki joy masalasi'),
    (80, 'Ta\'lim masalasi', "Maktab, kollej yoki oliy ta'lim bilan bog'liq"),
    (90, 'Hujjat rasmiylashtirish', 'Kadastr, nogironlik guruhi va boshqa hujjatlar'),
    (100, 'Aliment undirish', 'Aliment qarzdorligini undirib berish'),
    (110, 'Homiylik yordami', 'Homiylar hisobidan ko\'rsatiladigan yordam'),
    (900, 'Boshqa', "Yuqoridagilarga kirmaydigan murojaat"),
]


def sabablarni_qosh(apps, schema_editor):
    MurojaatSababi = apps.get_model('registry', 'MurojaatSababi')
    for tartib, nomi, tavsifi in SABABLAR:
        MurojaatSababi.objects.update_or_create(
            nomi=nomi,
            defaults={'tavsifi': tavsifi, 'tartib': tartib, 'faol': True},
        )


def sabablarni_ochir(apps, schema_editor):
    MurojaatSababi = apps.get_model('registry', 'MurojaatSababi')
    # Faqat boshlang'ich ro'yxatdagilar o'chiriladi; qo'lda qo'shilganlar qoladi.
    # Shaxsga bog'langanlari `PROTECT` sababli o'chmaydi - ular ham qoladi.
    for _tartib, nomi, _tavsifi in SABABLAR:
        MurojaatSababi.objects.filter(nomi=nomi, shaxslar__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0003_murojaatsababi_shaxs_murojaat_izohi_and_more'),
    ]

    operations = [
        migrations.RunPython(sabablarni_qosh, sabablarni_ochir),
    ]
