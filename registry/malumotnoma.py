# -*- coding: utf-8 -*-
"""
Ma'lumotnoma (lug'at) jadvallari ro'yxati.

Har bir jadval uchun bitta yozuv - model, forma, ko'rsatiladigan ustunlar va
qidiruv maydonlari. `views.py` dagi umumiy CRUD ko'rinishlari shu ro'yxatdan
foydalanadi, shuning uchun har bir jadval uchun alohida view/shablon yozilmaydi.

Yangi jadval qo'shish uchun shu yerga bitta yozuv qo'shish yetarli.
"""
from django.db.models import Count

from . import forms
from .models import (
    Hudud, IjtimoiyHolatTuri, IjtimoiyToifa, Mahalla, MuammoToifasi,
    MurojaatSababi, Oila, XizmatTuri,
)


class Jadval:
    """Bitta ma'lumotnoma jadvalining sozlamalari."""

    def __init__(self, kalit, model, form, nomi, birlik, ustunlar,
                 qidiruv=(), tartib=None, annotatsiya=None, izoh='',
                 select_related=()):
        self.kalit = kalit                  # URL dagi qism: /malumotnoma/<kalit>/
        self.model = model
        self.form = form
        self.nomi = nomi                    # ko'plik: "Mahallalar"
        self.birlik = birlik                # birlik: "Mahalla"
        self.ustunlar = ustunlar            # [(atribut, sarlavha, klass), ...]
        self.qidiruv = qidiruv              # qidiriladigan maydonlar
        self.tartib = tartib or ('pk',)
        self.annotatsiya = annotatsiya or {}
        self.izoh = izoh
        self.select_related = select_related

    def queryset(self):
        qs = self.model.objects.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.annotatsiya:
            qs = qs.annotate(**self.annotatsiya)
        return qs.order_by(*self.tartib)


# `Shaxs` bu yerda yo'q - unga alohida, boyroq forma bor (`shaxs_form.html`).
JADVALLAR = [
    Jadval(
        kalit='hududlar', model=Hudud, form=forms.HududForm,
        nomi='Hududlar', birlik='Hudud',
        ustunlar=[
            ('nomi', 'Nomi', 'cell-strong'),
            ('nomi_kiril', 'Manbadagi nomi', 'muted'),
            ('mahalla_soni', 'Mahallalar', 'num'),
        ],
        qidiruv=('nomi', 'nomi_kiril'),
        tartib=('nomi',),
        annotatsiya={'mahalla_soni': Count('mahallalar', distinct=True)},
        izoh="Tuman va shaharlar.",
    ),
    Jadval(
        kalit='mahallalar', model=Mahalla, form=forms.MahallaForm,
        nomi='Mahallalar (MFY)', birlik='Mahalla',
        ustunlar=[
            ('nomi', 'Nomi', 'cell-strong'),
            ('nomi_kiril', 'Manbadagi nomi', 'muted'),
            ('hudud', 'Hudud', ''),
            ('kodi', 'Kodi', 'mono'),
            ('oila_soni', 'Oilalar', 'num'),
            ('shaxs_soni', 'Shaxslar', 'num'),
        ],
        qidiruv=('nomi', 'nomi_kiril', 'kodi'),
        tartib=('nomi',),
        annotatsiya={
            'oila_soni': Count('oilalar', distinct=True),
            'shaxs_soni': Count('shaxslar', distinct=True),
        },
        select_related=('hudud',),
        izoh="MFY nomlari manba faylda Q/G'/O' harflarisiz yozilgan - "
             "lotin yozuvidagi nomni shu yerda tuzatish mumkin.",
    ),
    Jadval(
        kalit='oilalar', model=Oila, form=forms.OilaForm,
        nomi='Oilalar', birlik='Oila',
        ustunlar=[
            ('unikal_id', 'Oila unikal ID', 'cell-strong mono'),
            ('mahalla', 'Mahalla', ''),
            ('azolari_soni', "Manbadagi a'zolar soni", 'num'),
            ('azo_soni', "Bazadagi a'zolar", 'num'),
        ],
        qidiruv=('unikal_id',),
        tartib=('unikal_id',),
        annotatsiya={'azo_soni': Count('azolar', distinct=True)},
        select_related=('mahalla',),
        izoh="Oilani o'chirish uning barcha a'zolarini ham o'chiradi.",
    ),
    Jadval(
        kalit='murojaat-sabablari', model=MurojaatSababi,
        form=forms.MurojaatSababiForm,
        nomi='Murojaat sabablari', birlik='Murojaat sababi',
        ustunlar=[
            ('nomi', 'Sabab', 'cell-strong'),
            ('tavsifi', 'Tavsif', 'muted'),
            ('tartib', 'Tartib', 'num'),
            ('faol', 'Faol', ''),
            ('shaxs_soni', 'Shaxslar', 'num'),
        ],
        qidiruv=('nomi', 'tavsifi'),
        tartib=('tartib', 'nomi'),
        annotatsiya={'shaxs_soni': Count('shaxslar', distinct=True)},
        izoh="Shaxs nima uchun murojaat qilgani. Bu ma'lumot manba faylda yo'q - "
             "shtab xodimlari kiritadi. Ro'yxatni to'ldirib/qisqartirib olishingiz mumkin.",
    ),
    Jadval(
        kalit='ijtimoiy-toifalar', model=IjtimoiyToifa,
        form=forms.IjtimoiyToifaForm,
        nomi='Ijtimoiy toifalar', birlik='Ijtimoiy toifa',
        ustunlar=[
            ('nomi', 'Nomi', 'cell-strong'),
            ('nomi_kiril', 'Manbadagi nomi', 'muted'),
            ('shaxs_soni', 'Shaxslar', 'num'),
        ],
        qidiruv=('nomi', 'nomi_kiril'),
        tartib=('nomi',),
        annotatsiya={'shaxs_soni': Count('shaxslar', distinct=True)},
        izoh="Ijtimoiy reestrdagi toifa: Kambag'al, Davlat ta'minoti va h.k.",
    ),
    Jadval(
        kalit='muammo-toifalari', model=MuammoToifasi,
        form=forms.MuammoToifasiForm,
        nomi='Muammo toifalari', birlik='Muammo toifasi',
        ustunlar=[
            ('nomi', 'Nomi', 'cell-strong'),
            ('nomi_kiril', 'Manbadagi nomi', 'muted'),
            ('shaxs_soni', 'Shaxslar', 'num'),
        ],
        qidiruv=('nomi', 'nomi_kiril'),
        tartib=('nomi',),
        annotatsiya={'shaxs_soni': Count('shaxslar', distinct=True)},
        izoh="Manba fayldagi «Izoh» ustuni - aniqlangan muammoning toifasi.",
    ),
    Jadval(
        kalit='xizmat-turlari', model=XizmatTuri, form=forms.XizmatTuriForm,
        nomi='Xizmat turlari', birlik='Xizmat turi',
        ustunlar=[
            ('nomi', 'Nomi', 'cell-strong'),
            ('kod', 'Kod', 'mono'),
            ('ota_turi', 'Yuqori tur', 'muted'),
            ('summasi_bor', 'Summa bor', ''),
            ('tartib', 'Tartib', 'num'),
            ('xizmat_soni', 'Yozuvlar', 'num'),
        ],
        qidiruv=('nomi', 'nomi_kiril', 'kod'),
        tartib=('tartib',),
        annotatsiya={'xizmat_soni': Count('xizmatlar', distinct=True)},
        select_related=('ota_turi',),
        izoh="Kerak bo'lgan va ko'rsatilgan xizmatlar uchun umumiy lug'at.",
    ),
    Jadval(
        kalit='ijtimoiy-holatlar', model=IjtimoiyHolatTuri,
        form=forms.IjtimoiyHolatTuriForm,
        nomi='Ijtimoiy holat belgilari', birlik='Ijtimoiy holat belgisi',
        ustunlar=[
            ('nomi', 'Belgi', 'cell-strong'),
            ('kod', 'Kod', 'mono'),
            ('tartib', 'Tartib', 'num'),
            ('shaxs_soni', 'Shaxslar', 'num'),
        ],
        qidiruv=('nomi', 'nomi_kiril', 'kod'),
        tartib=('tartib',),
        annotatsiya={'shaxs_soni': Count('shaxslar', distinct=True)},
        izoh="Manba fayldagi 43 ta 0/1 belgisi.",
    ),
]

JADVAL_KALITLARI = {j.kalit: j for j in JADVALLAR}


def jadval_olish(kalit):
    """Kalit bo'yicha jadval sozlamasini qaytaradi (topilmasa `None`)."""
    return JADVAL_KALITLARI.get(kalit)
