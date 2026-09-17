# -*- coding: utf-8 -*-
"""
Shtab ma'lumotlar bazasi modellari.

Manba `database.xlsx` faylida 115 ta ustun bor va ularning katta qismi
0/1 bayroqlari hamda summalardan iborat. Ular JSON ko'rinishida saqlanmaydi,
balki normal holatga keltirilgan: har bir bayroq alohida yozuv bo'lib,
lug'at jadvallariga (`XizmatTuri`, `IjtimoiyHolatTuri`) bog'lanadi. Shu
sababli har qanday belgi bo'yicha filtrlash va hisoblash mumkin.

Tuzilma:

    Hudud -> Mahalla -> Oila -> Shaxs
                                  |-> Xizmat            (XizmatTuri)
                                  |-> ShaxsIjtimoiyHolat (IjtimoiyHolatTuri)

Barcha matnli maydonlar lotin yozuvida saqlanadi; manba faylidagi kirill
ko'rinishi solishtirish uchun `*_kiril` maydonlarida saqlanadi.
"""
from django.db import models


class Hudud(models.Model):
    """Tuman yoki shahar."""

    nomi = models.CharField("Hudud nomi", max_length=255, unique=True)
    nomi_kiril = models.CharField(
        "Hudud nomi (kirill)", max_length=255, blank=True,
        help_text="Manba fayldagi asl ko'rinishi",
    )

    class Meta:
        verbose_name = "Hudud"
        verbose_name_plural = "Hududlar"
        ordering = ['nomi']

    def __str__(self):
        return self.nomi


class Mahalla(models.Model):
    """MFY - mahalla fuqarolar yig'ini."""

    hudud = models.ForeignKey(
        Hudud, on_delete=models.PROTECT, related_name='mahallalar',
        verbose_name="Hudud",
    )
    kodi = models.PositiveIntegerField("MFY kodi", unique=True, db_index=True)
    nomi = models.CharField("MFY nomi", max_length=255, db_index=True)
    nomi_kiril = models.CharField(
        "MFY nomi (kirill)", max_length=255, blank=True,
        help_text="Manba fayldagi asl ko'rinishi",
    )

    class Meta:
        verbose_name = "Mahalla (MFY)"
        verbose_name_plural = "Mahallalar (MFY)"
        ordering = ['nomi']

    def __str__(self):
        return f"{self.nomi} ({self.kodi})"


class IjtimoiyToifa(models.Model):
    """Ijtimoiy reestrdagi toifa: Kambag'al, Davlat ta'minoti va h.k."""

    nomi = models.CharField("Toifa nomi", max_length=255, unique=True)
    nomi_kiril = models.CharField("Toifa nomi (kirill)", max_length=255, blank=True)

    class Meta:
        verbose_name = "Ijtimoiy toifa"
        verbose_name_plural = "Ijtimoiy toifalar"
        ordering = ['nomi']

    def __str__(self):
        return self.nomi


class MuammoToifasi(models.Model):
    """Manba fayldagi "Izoh" ustuni - aniqlangan muammoning toifasi."""

    nomi = models.CharField("Muammo toifasi", max_length=255, unique=True)
    nomi_kiril = models.CharField("Muammo toifasi (kirill)", max_length=255, blank=True)

    class Meta:
        verbose_name = "Muammo toifasi"
        verbose_name_plural = "Muammo toifalari"
        ordering = ['nomi']

    def __str__(self):
        return self.nomi


class MurojaatSababi(models.Model):
    """Shaxs nima uchun murojaat qilgani (murojaat sababi) lug'ati.

    Import vaqtida har bir shaxsning sababi manba faylning "kerakli xizmatlar"
    ustunlaridan (19-42) keltirib chiqariladi - ular fuqaro nima so'raganini
    ko'rsatadi. Murojaat mazmuni esa 43-ustundan olinadi.
    Ro'yxatni veb-interfeysda tahrirlash/to'ldirish mumkin.
    """

    nomi = models.CharField("Murojaat sababi", max_length=255, unique=True)
    tavsifi = models.CharField("Qisqa tavsif", max_length=500, blank=True)
    tartib = models.PositiveSmallIntegerField(
        "Tartib", default=100,
        help_text="Ro'yxatda kichik raqam yuqorida turadi",
    )
    faol = models.BooleanField(
        "Faol", default=True,
        help_text="Belgi olinsa, yangi yozuvlarda tanlash uchun ko'rinmaydi",
    )

    class Meta:
        verbose_name = "Murojaat sababi"
        verbose_name_plural = "Murojaat sabablari"
        ordering = ['tartib', 'nomi']

    def __str__(self):
        return self.nomi


class Oila(models.Model):
    """Oila - bir nechta shaxsni (oila a'zolarini) birlashtiradi."""

    mahalla = models.ForeignKey(
        Mahalla, on_delete=models.CASCADE, related_name='oilalar',
        verbose_name="Mahalla",
    )
    unikal_id = models.CharField(
        "Oila unikal ID", max_length=64, unique=True, db_index=True,
    )
    azolari_soni = models.PositiveSmallIntegerField(
        "Oila a'zolari soni", null=True, blank=True,
        help_text="Manba faylda ko'rsatilgan son",
    )

    class Meta:
        verbose_name = "Oila"
        verbose_name_plural = "Oilalar"
        ordering = ['unikal_id']

    def __str__(self):
        return f"Oila #{self.unikal_id}"

    @property
    def asosiy_arizachi(self):
        return self.azolar.filter(asosiy_arizachi=True).first()


class XizmatTuri(models.Model):
    """Ko'rsatiladigan/ko'rsatilgan xizmat turlari lug'ati.

    Manba faylda "kerak bo'lgan" va "ko'rsatilgan" xizmatlar ikkita alohida
    ustunlar guruhi bo'lib, ro'yxati deyarli bir xil. Shu sababli lug'at bitta
    bo'ladi, holat esa `Xizmat.holat` maydonida saqlanadi.
    """

    kod = models.SlugField("Kod", max_length=64, unique=True)
    nomi = models.CharField("Xizmat nomi", max_length=255)
    nomi_kiril = models.CharField("Xizmat nomi (kirill)", max_length=255, blank=True)
    ota_turi = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='quyi_turlari', verbose_name="Yuqori turdagi xizmat",
        help_text="Masalan, 'Yoshlar daftaridan' - 'Ijtimoiy daftarlar'ning quyi turi",
    )
    summasi_bor = models.BooleanField(
        "Summa ko'rsatiladi", default=False,
        help_text="Manba faylda bu xizmat uchun mln so'mdagi summa ustuni bor",
    )
    tartib = models.PositiveSmallIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "Xizmat turi"
        verbose_name_plural = "Xizmat turlari"
        ordering = ['tartib', 'nomi']

    def __str__(self):
        return self.nomi


class IjtimoiyHolatTuri(models.Model):
    """Shaxsning ijtimoiy holatini bildiruvchi belgilar lug'ati (43 ta belgi)."""

    kod = models.SlugField("Kod", max_length=80, unique=True)
    nomi = models.CharField("Ijtimoiy holat belgisi", max_length=255)
    nomi_kiril = models.CharField(
        "Ijtimoiy holat belgisi (kirill)", max_length=255, blank=True,
    )
    tartib = models.PositiveSmallIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "Ijtimoiy holat turi"
        verbose_name_plural = "Ijtimoiy holat turlari"
        ordering = ['tartib']

    def __str__(self):
        return self.nomi


class Shaxs(models.Model):
    """Bitta jismoniy shaxs (oila a'zosi) haqidagi yozuv."""

    ERKAK = 'erkak'
    AYOL = 'ayol'
    JINSI_TANLOVLARI = [
        (ERKAK, 'Erkak'),
        (AYOL, 'Ayol'),
    ]

    oila = models.ForeignKey(
        Oila, on_delete=models.CASCADE, related_name='azolar',
        verbose_name="Oila",
    )
    mahalla = models.ForeignKey(
        Mahalla, on_delete=models.CASCADE, related_name='shaxslar',
        verbose_name="Mahalla",
        help_text="Oilaning mahallasi; filtrlashni tezlashtirish uchun takrorlanadi",
    )
    tartib_raqami = models.PositiveIntegerField(
        "Manba fayldagi tartib raqami", null=True, blank=True, db_index=True,
    )
    asosiy_arizachi = models.BooleanField("Asosiy arizachi", default=False)

    # --- shaxsiy ma'lumotlar ---
    fio = models.CharField("F.I.O.", max_length=255, db_index=True)
    fio_kiril = models.CharField(
        "F.I.O. (manbadagi ko'rinishi)", max_length=255, blank=True,
        help_text="Manba fayldagi asl yozuv (kirill yoki nuqsonli kodirovka bilan)",
    )
    jshshir = models.CharField(
        "JSHSHIR", max_length=20, blank=True, db_index=True,
        help_text="14 xonali shaxsiy identifikatsiya raqami",
    )
    takroriy_jshshir = models.BooleanField(
        "JSHSHIR takrorlangan", default=False, db_index=True,
        help_text="Manba faylda bu JSHSHIR bir necha qatorda uchraydi - "
                  "tekshirish talab etiladi",
    )
    jinsi = models.CharField(
        "Jinsi", max_length=10, choices=JINSI_TANLOVLARI, blank=True, db_index=True,
    )
    tugilgan_sana = models.DateField("Tug'ilgan sana", null=True, blank=True)
    yoshi = models.DecimalField(
        "Yoshi", max_digits=5, decimal_places=2, null=True, blank=True,
    )

    # Formalarda qulay bo'lishi uchun `ShaxsIjtimoiyHolat` orqali o'tuvchi
    # ko'p-ko'p bog'lanish. O'tish jadvalida qo'shimcha maydon yo'q, shuning
    # uchun `.set()` / `.add()` to'g'ridan-to'g'ri ishlaydi.
    ijtimoiy_holatlar = models.ManyToManyField(
        IjtimoiyHolatTuri, through='ShaxsIjtimoiyHolat', blank=True,
        related_name='belgilangan_shaxslar',
        verbose_name="Ijtimoiy holat belgilari",
    )

    # --- ijtimoiy reestr ---
    ijtimoiy_toifa = models.ForeignKey(
        IjtimoiyToifa, on_delete=models.PROTECT, null=True, blank=True,
        related_name='shaxslar', verbose_name="Ijtimoiy reestrdagi toifasi",
    )
    muammo_toifasi = models.ForeignKey(
        MuammoToifasi, on_delete=models.PROTECT, null=True, blank=True,
        related_name='shaxslar', verbose_name="Izoh (muammo toifasi)",
    )
    reestrdan_chiqqan = models.BooleanField(
        "O'z arizasiga ko'ra ijtimoiy reestrdan chiqqan", default=False,
    )

    # --- uchrashuv va xizmat ko'rsatish ---
    uchrashuv_sana = models.DateField(
        "Uchrashuv o'tkazilgan sana", null=True, blank=True,
    )
    uchrashuvda_qatnashgan = models.BooleanField(
        "Uchrashuv o'tkazilgan", default=False,
    )
    xizmat_sana = models.DateField(
        "Xizmat ko'rsatilgan sana", null=True, blank=True,
    )
    xizmat_korsatilgan = models.BooleanField("Xizmat ko'rsatilgan", default=False)

    # --- murojaat (nima uchun murojaat qilgan) ---
    # Manba faylning 43-ustuni ("Бошқа муаммоли оилалар (Изоҳ)") aynan
    # murojaat mazmunini saqlaydi, sabab esa kerakli xizmatlardan keltirib
    # chiqariladi - ikkisi ham `import_excel` buyrug'ida to'ldiriladi.
    murojaat_sababi = models.ForeignKey(
        MurojaatSababi, on_delete=models.PROTECT, null=True, blank=True,
        related_name='shaxslar', verbose_name="Nima uchun murojaat qilgan",
    )
    murojaat_izohi = models.TextField(
        "Murojaat mazmuni", blank=True,
        help_text="Manba faylning 43-ustuni: fuqaro nima so'ragani",
    )

    # --- muammo tavsifi ---
    muammo_aniqlanmagan = models.BooleanField(
        "Uchrashuvda muammo aniqlanmagan", default=False,
    )

    # --- tezkor hisoblar (import vaqtida to'ldiriladi) ---
    kerakli_xizmatlar_soni = models.PositiveSmallIntegerField(
        "Kerakli xizmatlar soni", default=0,
    )
    korsatilgan_xizmatlar_soni = models.PositiveSmallIntegerField(
        "Ko'rsatilgan xizmatlar soni", default=0,
    )

    yaratilgan_vaqt = models.DateTimeField("Yaratilgan vaqt", auto_now_add=True)
    yangilangan_vaqt = models.DateTimeField("Yangilangan vaqt", auto_now=True)

    class Meta:
        verbose_name = "Shaxs"
        verbose_name_plural = "Shaxslar"
        ordering = ['oila__unikal_id', '-asosiy_arizachi', 'fio']
        indexes = [
            models.Index(fields=['mahalla', 'jinsi']),
            models.Index(fields=['mahalla', 'ijtimoiy_toifa']),
        ]
        # JSHSHIR ga unikallik cheklovi qo'yilmagan: manba faylda 79 ta shaxs
        # (158 qator) ikki xil "oila unikal ID" ostida ikki marta ro'yxatga
        # olingan. Ma'lumot yo'qotilmasligi uchun barcha qatorlar saqlanadi,
        # takrorlanishlar esa `takroriy_jshshir` maydoni orqali belgilanadi.

    def __str__(self):
        return self.fio

    @property
    def yoshi_butun(self):
        return int(self.yoshi) if self.yoshi is not None else None


class Xizmat(models.Model):
    """Shaxsga kerak bo'lgan yoki ko'rsatilgan bitta xizmat."""

    KERAKLI = 'kerakli'
    KORSATILGAN = 'korsatilgan'
    HOLAT_TANLOVLARI = [
        (KERAKLI, "Kerak bo'lgan (xatlov holati)"),
        (KORSATILGAN, "Ko'rsatilgan (ijro holati)"),
    ]

    shaxs = models.ForeignKey(
        Shaxs, on_delete=models.CASCADE, related_name='xizmatlar',
        verbose_name="Shaxs",
    )
    turi = models.ForeignKey(
        XizmatTuri, on_delete=models.PROTECT, related_name='xizmatlar',
        verbose_name="Xizmat turi",
    )
    holat = models.CharField(
        "Holat", max_length=12, choices=HOLAT_TANLOVLARI, db_index=True,
    )
    soni = models.PositiveSmallIntegerField("Soni", default=1)
    summa_mln = models.DecimalField(
        "Summa (mln so'm)", max_digits=12, decimal_places=3, null=True, blank=True,
    )

    class Meta:
        verbose_name = "Xizmat"
        verbose_name_plural = "Xizmatlar"
        ordering = ['turi__tartib']
        constraints = [
            models.UniqueConstraint(
                fields=['shaxs', 'turi', 'holat'], name='xizmat_shaxs_turi_holat',
            ),
        ]

    def __str__(self):
        return f"{self.shaxs.fio} - {self.turi.nomi} ({self.get_holat_display()})"


class ShaxsIjtimoiyHolat(models.Model):
    """Shaxsga qo'yilgan bitta ijtimoiy holat belgisi."""

    shaxs = models.ForeignKey(
        Shaxs, on_delete=models.CASCADE, related_name='ijtimoiy_holatlari',
        verbose_name="Shaxs",
    )
    turi = models.ForeignKey(
        IjtimoiyHolatTuri, on_delete=models.PROTECT, related_name='shaxslar',
        verbose_name="Ijtimoiy holat turi",
    )

    class Meta:
        verbose_name = "Shaxsning ijtimoiy holati"
        verbose_name_plural = "Shaxslarning ijtimoiy holatlari"
        ordering = ['turi__tartib']
        constraints = [
            models.UniqueConstraint(
                fields=['shaxs', 'turi'], name='ijtimoiy_holat_shaxs_turi',
            ),
        ]

    def __str__(self):
        return f"{self.shaxs.fio} - {self.turi.nomi}"
