# -*- coding: utf-8 -*-
"""
`muammo_aniqlanmagan` -> `muammo_aniqlangan` (qiymatlar teskarisiga).

Manba faylning 44-ustuni teskari mantiqda yozilgan: "Учрашувда муаммо
аниқланмаган оила". Interfeysda "Muammo aniqlanmagan: Yo'q" degan qo'sh inkor
chiqib, o'qish qiyin bo'lardi. Shu sababli maydon nomi ham, qiymatlari ham
to'g'ri mantiqqa o'tkaziladi: "Muammo aniqlangan: Ha / Yo'q".

Maydon o'chirilmaydi - `RenameField` ustunni saqlab qoladi, qiymatlar esa
bitta `UPDATE` bilan teskarisiga aylantiriladi.
"""
from django.db import migrations, models
from django.db.models import BooleanField, Case, Value, When


def teskarisiga(apps, schema_editor):
    """Boolean qiymatlarni teskarisiga aylantiradi (ikki yo'nalishda ham bir xil)."""
    Shaxs = apps.get_model('registry', 'Shaxs')
    Shaxs.objects.update(
        muammo_aniqlangan=Case(
            When(muammo_aniqlangan=True, then=Value(False)),
            default=Value(True),
            output_field=BooleanField(),
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0006_murojaat_kop_tanlov'),
    ]

    operations = [
        migrations.RenameField(
            model_name='shaxs',
            old_name='muammo_aniqlanmagan',
            new_name='muammo_aniqlangan',
        ),
        migrations.AlterField(
            model_name='shaxs',
            name='muammo_aniqlangan',
            field=models.BooleanField(
                db_index=True, default=False,
                verbose_name='Uchrashuvda muammo aniqlangan',
            ),
        ),
        # Nom o'zgargandan keyin mazmun ham to'g'ri bo'lishi uchun teskarisiga.
        migrations.RunPython(teskarisiga, teskarisiga),
    ]
