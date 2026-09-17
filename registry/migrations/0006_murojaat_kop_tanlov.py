# -*- coding: utf-8 -*-
"""
Murojaat sababi bitta tanlovdan (`FK`) ko'p tanlovga (`M2M`) o'tkaziladi va
`murojaat_izohi` erkin matn maydoni olib tashlanadi.

Bir fuqaro bir vaqtda bir nechta sabab bilan murojaat qilishi mumkin
(masalan uy-joy ta'miri + nogironlik masalasi), shu sababli ko'p tanlov.

Eski `murojaat_sababi` qiymatlari yangi bog'lanishga ko'chiriladi, shuning
uchun qayta import qilinmasa ham ma'lumot yo'qolmaydi. To'liq (ikki manbadan
yig'ilgan) ro'yxat `import_excel` buyrug'i qayta ishga tushirilganda yoziladi.
"""
from django.db import migrations, models


def sababni_kochir(apps, schema_editor):
    """Eski bitta sababni yangi ko'p-ko'p bog'lanishga ko'chiradi."""
    Shaxs = apps.get_model('registry', 'Shaxs')
    Bogliq = Shaxs.murojaat_sabablari.through

    bogliqlar = []
    qs = (Shaxs.objects
          .filter(murojaat_sababi__isnull=False)
          .values_list('pk', 'murojaat_sababi_id'))
    for shaxs_id, sabab_id in qs.iterator(chunk_size=2000):
        bogliqlar.append(Bogliq(shaxs_id=shaxs_id, murojaatsababi_id=sabab_id))
    Bogliq.objects.bulk_create(bogliqlar, batch_size=1000, ignore_conflicts=True)


def sababni_qaytar(apps, schema_editor):
    """Teskari yo'nalish: har bir shaxsning birinchi sababini FK ga qaytaradi."""
    Shaxs = apps.get_model('registry', 'Shaxs')
    Bogliq = Shaxs.murojaat_sabablari.through

    korilgan = set()
    yangilanadi = []
    qs = Bogliq.objects.order_by('shaxs_id', 'murojaatsababi_id').values_list(
        'shaxs_id', 'murojaatsababi_id',
    )
    for shaxs_id, sabab_id in qs.iterator(chunk_size=2000):
        if shaxs_id in korilgan:
            continue
        korilgan.add(shaxs_id)
        yangilanadi.append(Shaxs(pk=shaxs_id, murojaat_sababi_id=sabab_id))
    Shaxs.objects.bulk_update(
        yangilanadi, ['murojaat_sababi'], batch_size=1000,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0005_murojaat_izohi_va_maydonlar'),
    ]

    operations = [
        # Avval yangi bog'lanish yaratiladi va ma'lumot ko'chiriladi,
        # keyingina eski maydonlar olib tashlanadi.
        migrations.AddField(
            model_name='shaxs',
            name='murojaat_sabablari',
            field=models.ManyToManyField(
                blank=True, related_name='shaxslar',
                to='registry.murojaatsababi',
                verbose_name='Nima uchun murojaat qilgan',
            ),
        ),
        migrations.RunPython(sababni_kochir, sababni_qaytar),
        migrations.RemoveField(
            model_name='shaxs',
            name='murojaat_izohi',
        ),
        migrations.RemoveField(
            model_name='shaxs',
            name='murojaat_sababi',
        ),
    ]
