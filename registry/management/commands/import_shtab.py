"""
`shtab_database.json` faylini SQL ma'lumotlar bazasiga yuklaydi.

Ishlatilishi:
    python manage.py import_shtab data/shtab_database.json
    python manage.py import_shtab data/shtab_database.json --tozalash
"""
import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from registry.models import Mahalla, Oila, Shaxs

BATCH_SIZE = 1000


def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


class Command(BaseCommand):
    help = "shtab_database.json faylidagi ma'lumotlarni SQL bazaga import qiladi"

    def add_arguments(self, parser):
        parser.add_argument(
            'json_fayl', type=str,
            help="shtab_database.json fayl yo'li",
        )
        parser.add_argument(
            '--tozalash', action='store_true',
            help="Import qilishdan oldin mavjud Mahalla/Oila/Shaxs yozuvlarini o'chirish",
        )

    def handle(self, *args, **options):
        fayl_yoli = options['json_fayl']
        try:
            with open(fayl_yoli, encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f"Fayl topilmadi: {fayl_yoli}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON o'qishda xatolik: {exc}") from exc

        yozuvlar = data.get('malumotlar', [])
        self.stdout.write(f"Jami {len(yozuvlar)} ta yozuv topildi.")

        if options['tozalash']:
            self.stdout.write("Eski yozuvlar tozalanmoqda...")
            Shaxs.objects.all().delete()
            Oila.objects.all().delete()
            Mahalla.objects.all().delete()

        with transaction.atomic():
            mahalla_cache = {}   # kodi -> Mahalla instance
            oila_cache = {}      # (mahalla_kodi, oila_unikal_id) -> Oila instance
            shaxs_buffer = []
            yaratilgan = 0

            for row in yozuvlar:
                mahalla_kodi = row.get('mfy_kodi')
                if mahalla_kodi not in mahalla_cache:
                    mahalla, _ = Mahalla.objects.get_or_create(
                        kodi=mahalla_kodi,
                        defaults={
                            'hudud': row.get('hudud', ''),
                            'nomi': row.get('mfy_nomi', ''),
                        },
                    )
                    mahalla_cache[mahalla_kodi] = mahalla
                mahalla = mahalla_cache[mahalla_kodi]

                oila_key = (mahalla_kodi, row.get('oila_unikal_id'))
                if oila_key not in oila_cache:
                    oila, _ = Oila.objects.get_or_create(
                        mahalla=mahalla,
                        oila_unikal_id=row.get('oila_unikal_id') or '',
                        defaults={'oila_azolari_soni': row.get('oila_azolari_soni')},
                    )
                    oila_cache[oila_key] = oila
                oila = oila_cache[oila_key]

                shaxs_buffer.append(Shaxs(
                    oila=oila,
                    tartib_raqami=row.get('tartib_raqami'),
                    asosiy_arizachi=bool(row.get('asosiy_arizachi')),
                    jshshir=row.get('jshshir'),
                    fio=row.get('fio') or '',
                    jinsi=row.get('jinsi') or '',
                    tugilgan_sana=parse_date(row.get('tugilgan_sana')),
                    yoshi=row.get('yoshi'),
                    ijtimoiy_toifa=row.get('ijtimoiy_toifa') or '',
                    izoh=row.get('izoh') or '',
                    reestrdan_chiqqan=bool(row.get('reestrdan_chiqqan')),
                    uchrashuv_sana=parse_date(row.get('uchrashuv_sana')),
                    uchrashuv_qatnashgan=bool(row.get('uchrashuv_qatnashgan')),
                    xizmat_sana=parse_date(row.get('xizmat_sana')),
                    xizmat_qatnashgan=bool(row.get('xizmat_qatnashgan')),
                    kerakli_xizmatlar=row.get('kerakli_xizmatlar') or {},
                    boshqa_muammo=row.get('boshqa_muammo') or {},
                    korsatilgan_xizmatlar=row.get('korsatilgan_xizmatlar') or {},
                    ijtimoiy_holat_belgilari=row.get('ijtimoiy_holat_belgilari') or {},
                ))

                if len(shaxs_buffer) >= BATCH_SIZE:
                    Shaxs.objects.bulk_create(shaxs_buffer)
                    yaratilgan += len(shaxs_buffer)
                    self.stdout.write(f"  ... {yaratilgan} ta shaxs yozildi")
                    shaxs_buffer = []

            if shaxs_buffer:
                Shaxs.objects.bulk_create(shaxs_buffer)
                yaratilgan += len(shaxs_buffer)

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {len(mahalla_cache)} mahalla, {len(oila_cache)} oila, "
            f"{yaratilgan} shaxs bazaga yozildi."
        ))
