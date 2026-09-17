from django.db import models


class Mahalla(models.Model):
    """MFY (mahalla fuqarolar yig'ini)."""

    hudud = models.CharField("Hudud (tuman/shahar)", max_length=255)
    nomi = models.CharField("MFY nomi", max_length=255)
    kodi = models.PositiveIntegerField("MFY kodi", unique=True, db_index=True)

    class Meta:
        verbose_name = "Mahalla"
        verbose_name_plural = "Mahallalar"
        ordering = ['hudud', 'nomi']

    def __str__(self):
        return f"{self.nomi} ({self.hudud})"

    @property
    def shaxslar_soni(self):
        return Shaxs.objects.filter(oila__mahalla=self).count()


class Oila(models.Model):
    """Oila - bir nechta shaxs (oila a'zosi)ni birlashtiradi."""

    mahalla = models.ForeignKey(
        Mahalla, on_delete=models.CASCADE, related_name='oilalar',
        verbose_name="Mahalla",
    )
    oila_unikal_id = models.CharField("Oila unikal ID", max_length=64, db_index=True)
    oila_azolari_soni = models.PositiveSmallIntegerField(
        "Oila a'zolari soni", null=True, blank=True,
    )

    class Meta:
        verbose_name = "Oila"
        verbose_name_plural = "Oilalar"
        unique_together = ('mahalla', 'oila_unikal_id')

    def __str__(self):
        return f"Oila #{self.oila_unikal_id} ({self.mahalla.nomi})"

    @property
    def asosiy_arizachi(self):
        return self.azolar.filter(asosiy_arizachi=True).first()


class Shaxs(models.Model):
    """Bitta jismoniy shaxs (oila a'zosi) haqidagi yozuv."""

    JINSI_TANLOVLARI = [
        ('Эркак', 'Erkak'),
        ('Аёл', 'Ayol'),
    ]

    oila = models.ForeignKey(
        Oila, on_delete=models.CASCADE, related_name='azolar',
        verbose_name="Oila",
    )
    tartib_raqami = models.PositiveIntegerField("Tartib raqami", null=True, blank=True)
    asosiy_arizachi = models.BooleanField("Asosiy arizachi", default=False)

    jshshir = models.CharField(
        "JSHSHIR", max_length=20, blank=True, null=True, db_index=True,
    )
    fio = models.CharField("F.I.O.", max_length=255, db_index=True)
    jinsi = models.CharField("Jinsi", max_length=10, choices=JINSI_TANLOVLARI, blank=True)
    tugilgan_sana = models.DateField("Tug'ilgan sana", null=True, blank=True)
    yoshi = models.FloatField("Yoshi", null=True, blank=True)

    ijtimoiy_toifa = models.CharField(
        "Ijtimoiy reestrdagi toifasi", max_length=255, blank=True, db_index=True,
    )
    izoh = models.CharField("Izoh", max_length=500, blank=True)
    reestrdan_chiqqan = models.BooleanField(
        "O'z arizasiga ko'ra ijtimoiy reestrdan chiqqan", default=False,
    )

    uchrashuv_sana = models.DateField("Uchrashuv o'tkazilgan sana", null=True, blank=True)
    uchrashuv_qatnashgan = models.BooleanField("Uchrashuvda qatnashgan", default=False)
    xizmat_sana = models.DateField("Xizmat ko'rsatilgan sana", null=True, blank=True)
    xizmat_qatnashgan = models.BooleanField("Xizmat ko'rsatilgan", default=False)

    # Ko'p sonli (0/1) bayroq-ustunlar moslashuvchan saqlanishi uchun JSON ko'rinishida.
    kerakli_xizmatlar = models.JSONField("Kerakli xizmatlar", default=dict, blank=True)
    boshqa_muammo = models.JSONField("Boshqa muammo belgilari", default=dict, blank=True)
    korsatilgan_xizmatlar = models.JSONField("Ko'rsatilgan xizmatlar", default=dict, blank=True)
    ijtimoiy_holat_belgilari = models.JSONField(
        "Ijtimoiy holat belgilari", default=dict, blank=True,
    )

    yaratilgan_vaqt = models.DateTimeField(auto_now_add=True)
    yangilangan_vaqt = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shaxs"
        verbose_name_plural = "Shaxslar"
        ordering = ['oila', 'tartib_raqami']

    def __str__(self):
        return self.fio

    @property
    def mahalla(self):
        return self.oila.mahalla
