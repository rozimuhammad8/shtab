# -*- coding: utf-8 -*-
"""
`boshqa_muammo_izohi` -> `murojaat_izohi`.

Ikkisi ham manba faylning bir xil 43-ustunidan ("Бошқа муаммоли оилалар
(Изоҳ)") olingan - u yerda fuqaro nima so'ragani yozilgan. Maydon nomi
noto'g'ri edi, shu sababli mazmuni murojaat maydoniga ko'chiriladi va eski
maydon olib tashlanadi.
"""
from django.db import migrations, models


def izohni_kochir(apps, schema_editor):
    """Eski maydondagi matnni `murojaat_izohi` ga ko'chiradi."""
    Shaxs = apps.get_model('registry', 'Shaxs')
    yangilanadi = []
    qs = Shaxs.objects.exclude(boshqa_muammo_izohi='').only(
        'id', 'boshqa_muammo_izohi', 'murojaat_izohi',
    )
    for shaxs in qs.iterator(chunk_size=2000):
        if not shaxs.murojaat_izohi:
            shaxs.murojaat_izohi = shaxs.boshqa_muammo_izohi
            yangilanadi.append(shaxs)
    Shaxs.objects.bulk_update(yangilanadi, ['murojaat_izohi'], batch_size=1000)


def izohni_qaytar(apps, schema_editor):
    """Teskari yo'nalish: matnni qaytadan eski maydonga ko'chiradi."""
    Shaxs = apps.get_model('registry', 'Shaxs')
    yangilanadi = []
    qs = Shaxs.objects.exclude(murojaat_izohi='').only(
        'id', 'boshqa_muammo_izohi', 'murojaat_izohi',
    )
    for shaxs in qs.iterator(chunk_size=2000):
        shaxs.boshqa_muammo_izohi = shaxs.murojaat_izohi[:500]
        yangilanadi.append(shaxs)
    Shaxs.objects.bulk_update(
        yangilanadi, ['boshqa_muammo_izohi'], batch_size=1000,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0004_murojaat_sabablari_boshlangich'),
    ]

    operations = [
        # Maydon o'chirilishidan OLDIN mazmuni ko'chirib olinadi.
        migrations.AlterField(
            model_name='shaxs',
            name='murojaat_izohi',
            field=models.TextField(
                blank=True,
                help_text="Manba faylning 43-ustuni: fuqaro nima so'ragani",
                verbose_name='Murojaat mazmuni',
            ),
        ),
        migrations.RunPython(izohni_kochir, izohni_qaytar),
        migrations.RemoveField(
            model_name='shaxs',
            name='boshqa_muammo_izohi',
        ),
    ]
