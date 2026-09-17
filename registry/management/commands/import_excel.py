# -*- coding: utf-8 -*-
"""
`database.xlsx` faylidagi ma'lumotlarni SQL bazaga ko'chiradi.

Manba fayl tuzilishi:
  * 1-3   qatorlar  - hujjat sarlavhasi
  * 4-8   qatorlar  - ko'p qatlamli (birlashtirilgan) jadval sarlavhasi
  * 9     qator     - "jami" qatori (import qilinmaydi)
  * 10+   qatorlar  - ma'lumotlar, har bir qator = bitta shaxs

Ishlatilishi:
    python manage.py import_excel database.xlsx
    python manage.py import_excel database.xlsx --tozalash
"""
import datetime
from collections import Counter
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from registry.models import (
    Hudud, IjtimoiyHolatTuri, IjtimoiyToifa, Mahalla, MuammoToifasi,
    MurojaatSababi, Oila, Shaxs, ShaxsIjtimoiyHolat, Xizmat, XizmatTuri,
)
from registry.translit import tozala

BIRINCHI_QATOR = 10          # ma'lumotlar shu qatordan boshlanadi
SARLAVHA_QATORLARI = (4, 8)  # birlashtirilgan sarlavha qatorlari oralig'i
TOPLAM = 2000                # bulk_create uchun to'plam hajmi

# --- ustun indekslari (0 dan boshlanadi) -----------------------------------
U_TARTIB = 0
U_HUDUD = 1
U_MFY_NOMI = 2
U_MFY_KODI = 3
U_OILA_ID = 4
U_ASOSIY_ARIZACHI = 5
U_JSHSHIR = 6
U_FIO = 7
U_JINSI = 8
U_TUGILGAN = 9
U_YOSHI = 10
U_OILA_SONI = 11
U_TOIFA = 12
U_IZOH = 13
U_REESTRDAN_CHIQQAN = 14
U_UCHRASHUV_SANA = 15
U_UCHRASHUV = 16
U_XIZMAT_SANA = 17
U_XIZMAT = 18
U_MUROJAAT_MAZMUNI = 43   # "Бошқа муаммоли оилалар (Изоҳ)" - fuqaro nima so'ragani
U_MUAMMO_YOQ = 44

# Xizmat turlari katalogi.
# (kod, kerakli_ustun, kerakli_summa_ustuni, korsatilgan_ustun,
#  korsatilgan_summa_ustuni, nomi olinadigan ustun, ota_kodi)
# `nomi` ustuni - nomni manba fayl sarlavhasidan olish uchun; shu sababli
# nomlar qo'lda yozilmaydi va fayl bilan bir joyda turadi.
XIZMAT_KATALOGI = [
    ('doimiy_ish',              20, None, 47, None, 20, None),
    ('imtiyozli_kredit',        21, 22,   48, 49,   21, None),
    ('ssuda',                   23, 24,   50, 51,   23, None),
    ('tadbirkorlik',            25, None, 52, None, 25, None),
    ('migratsiya',              26, None, 53, None, 26, None),
    ('ozini_ozi_band_qilish',   27, None, 54, None, 27, None),
    ('kasb_hunarga_oqitish',    28, None, 55, None, 28, None),
    ('ijtimoiy_daftarlar',      29, 30,   56, 57,   29, None),
    ('yoshlar_daftari',         31, 32,   58, 59,   31, 'ijtimoiy_daftarlar'),
    ('ayollar_daftari',         33, 34,   60, 61,   33, 'ijtimoiy_daftarlar'),
    ('sahovat_jamgarmasi',      35, 36,   62, 63,   35, 'ijtimoiy_daftarlar'),
    ('infratuzilma_jamgarmasi', 37, 38,   64, 65,   37, 'ijtimoiy_daftarlar'),
    ('homiylik',                None, None, 66, None, 66, None),
    ('sogligini_tiklash',       39, None, 67, None, 39, None),
    ('aliment',                 40, None, 68, None, 40, None),
    ('kadastr',                 41, None, 69, None, 41, None),
    ('bogcha_vaucheri',         42, None, 70, None, 42, None),
]

# Ijtimoiy holat belgilari: (kod, ustun indeksi). Nomlari sarlavhadan olinadi.
IJTIMOIY_HOLAT_KATALOGI = [
    ('nogiron_bola_onasi', 72),
    ('ish_bilan_band', 73),
    ('ishsiz', 74),
    ('uch_yoshgacha_bola_parvarishi', 75),
    ('ozgalar_parvarishi', 76),
    ('tomorqada_band', 77),
    ('oilaviy_tadbirkorlik', 78),
    ('ishlamaydigan_pensioner', 79),
    ('nogironligi_bor', 80),
    ('oliy_talim_talabasi', 81),
    ('kollej_litsey_oquvchisi', 82),
    ('maktab_oquvchisi', 83),
    ('maktabgacha_tarbiya', 84),
    ('toliq_davlat_taminotida', 85),
    ('muddatli_harbiy_xizmat', 86),
    ('jazoni_ijro_etish_joyida', 87),
    ('xorijda_mehnat_faoliyati', 88),
    ('qayta_tayyorlov', 89),
    ('maqbul_ish_qidirish', 90),
    ('jamoat_ishlari', 91),
    ('rasman_ishsiz', 92),
    ('oiv_bilan_farzand_qarovchisi', 93),
    ('ozini_ozi_band_qilgan', 94),
    ('yakka_tartibdagi_tadbirkor', 95),
    ('subsidiya_uchun_band', 96),
    ('yoshlar_daftari_subsidiyasi', 97),
    ('mehnat_organlari_konsultatsiyasi', 98),
    ('harbiy_talim_muassasasida', 99),
    ('chet_el_oliy_talimida', 100),
    ('tort_va_undan_ortiq_farzand', 101),
    ('yolgiz_ona_ota', 102),
    ('temir_daftarda', 103),
    ('korxona_tasischisi', 104),
    ('kuch_organlari_xodimi', 105),
    ('ruhiy_dispanser_hisobida', 106),
    ('boquvchisini_yoqotgan', 107),
    ('yakka_yolgiz', 108),
    ('ishsiz_uch_oy_band_bolmagan', 109),
    ('yammtdan_otkazilmagan', 110),
    ('chet_elda_jazoni_ijro_etish', 111),
    ('kambagallik_reestrida', 112),
    ('norasmiy_band', 113),
    ('ogir_kasalligi_bor', 114),
]

JINSI_MOSLIGI = {'эркак': Shaxs.ERKAK, 'аёл': Shaxs.AYOL}

# "Nima uchun murojaat qilgan" - manba faylda alohida ustun yo'q, lekin
# "kerakli xizmatlar" ustunlari (19-42) fuqaro nima so'raganini ko'rsatadi.
# Shu sababli murojaat sababi kerakli xizmat turidan keltirib chiqariladi.
# Bir shaxsda bir nechta kerakli xizmat bo'lishi mumkin, shuning uchun
# ro'yxat tartibi = ustuvorlik: eng aniq sabab yuqorida turadi.
SABAB_USTUVORLIGI = [
    ('sogligini_tiklash',       'Tibbiy yordam'),
    ('bogcha_vaucheri',         "Farzandni bog'chaga joylashtirish"),
    ('aliment',                 'Aliment undirish'),
    ('kadastr',                 'Hujjat rasmiylashtirish'),
    ('kasb_hunarga_oqitish',    "Kasb-hunarga o'qitish"),
    ('imtiyozli_kredit',        'Imtiyozli kredit'),
    ('ssuda',                   'Imtiyozli kredit'),
    ('yoshlar_daftari',         'Subsidiya yoki ijtimoiy nafaqa'),
    ('ayollar_daftari',         'Subsidiya yoki ijtimoiy nafaqa'),
    ('sahovat_jamgarmasi',      'Homiylik yordami'),
    ('infratuzilma_jamgarmasi', 'Subsidiya yoki ijtimoiy nafaqa'),
    ('ijtimoiy_daftarlar',      'Subsidiya yoki ijtimoiy nafaqa'),
    ('doimiy_ish',              "Ish bilan ta'minlash"),
    ('tadbirkorlik',            "Ish bilan ta'minlash"),
    ('ozini_ozi_band_qilish',   "Ish bilan ta'minlash"),
    ('migratsiya',              "Ish bilan ta'minlash"),
]


def _matn(qiymat):
    """Yacheyka qiymatini `#VALUE!` kabi xatoliklardan tozalab matnga aylantiradi."""
    if qiymat is None:
        return ''
    matn = str(qiymat).strip()
    return '' if matn.startswith('#') else matn


def _sana(qiymat):
    if isinstance(qiymat, datetime.datetime):
        return qiymat.date()
    if isinstance(qiymat, datetime.date):
        return qiymat
    matn = _matn(qiymat)
    if not matn:
        return None
    try:
        return datetime.date.fromisoformat(matn[:10])
    except ValueError:
        return None


def _son(qiymat):
    """Sonli qiymatni qaytaradi, aks holda None."""
    if isinstance(qiymat, bool):
        return int(qiymat)
    if isinstance(qiymat, (int, float)):
        return qiymat
    matn = _matn(qiymat).replace(',', '.')
    if not matn:
        return None
    try:
        return float(matn)
    except ValueError:
        return None


def _bayroq(qiymat):
    son = _son(qiymat)
    return bool(son and son > 0)


def _kasr(qiymat, xona=2):
    son = _son(qiymat)
    if son is None:
        return None
    try:
        return round(Decimal(str(son)), xona)
    except (InvalidOperation, ValueError):
        return None


def _jshshir(qiymat):
    """JSHSHIR ni tozalaydi; manba faylda "1" kabi nuqsonli qiymatlar ham bor."""
    matn = _matn(qiymat)
    if matn.endswith('.0'):
        matn = matn[:-2]
    return matn if len(matn) == 14 and matn.isdigit() else ''


# MFY nomlari manba faylda o'zbek kirill alifbosining Q/G'/O' harflaridan
# foydalanmasdan yozilgan (masalan "ИТТИФОК", "КУМ КУЧА"). To'g'ridan-to'g'ri
# transliteratsiya "ITTIFOK", "KUM KUCHA" beradi, shu sababli 78 ta MFY nomi
# uchun to'g'ri lotin yozuvi shu jadvalda keltirilgan. Asl kirill ko'rinishi
# `Mahalla.nomi_kiril` maydonida saqlanadi.
MFY_NOMLARI = {
    307001: 'EKIN-TIKIN',      307002: 'SAYDILOBOD',    307004: 'NAMUNA',
    307005: 'SADDATAGI',       307006: 'HAQIQAT',       307007: 'KENGASH',
    307008: 'GULISTON',        307009: 'OTCHOPAR',      307010: 'DARXON',
    307011: 'INTILISH',        307012: 'NURAFSHON',     307013: 'QORATUT',
    307014: 'MIROBOD',         307015: 'GUMBAZ',        307016: 'GUZAR',
    307017: "YANGI TO'LQIN",   307018: 'CHILON',        307019: 'KATTA GUZAR',
    307020: "YANGI YO'L",      307021: 'QURAMA',        307022: 'NAVRUZ',
    307023: 'BEKOBOD',         307024: 'DUDIR',         307025: 'NUXATAK',
    307026: 'ZANGIBOBO',       307027: 'TOSHLOQ',       307028: 'DARYOBUYI',
    307029: 'ZAVROQ',          307031: 'DEHQON',        307032: 'SANOAT',
    307033: 'BESHPAHLAVON',    307034: 'ISLOMOBOD',     307035: "OG'ULLIK",
    307036: 'CHEM',            307037: 'TOLMOZOR',      307039: "QUM KO'CHA",
    307040: "CHUNGBOG'ICH",    307041: 'JEVACHI',       307042: 'OYJAMOL',
    307043: 'MUSTAQILLIK',     307044: 'NAYMANOBOD',    307045: 'CHAVQANDARYO',
    307046: 'GULOBOD',         307047: 'POLOSON',       307049: 'ROVVOT',
    307050: 'MART',            307051: 'SULTONOBOD',    307052: 'JANNATMAKON',
    307053: 'ITTIFOQ',         307054: "DO'STLIK",      307055: "BESHBO'YNOQ",
    307056: 'TERAKTAGI',       307057: 'JAHONOBOD',     307058: 'YUKSALISH',
    307059: "QO'SHCHINOR",     307060: 'BUYUK TURON',   307061: "DO'NG QISHLOQ",
    307062: "CHORBOG'",        307063: 'OROL',          307064: "QO'SHARIQ",
    307065: 'ROHAT',           307066: 'AYLANPA',       307067: 'OQ ROVVOT',
    307068: "QO'QONLIK",       307069: "XO'JA",         307070: 'ISTIQLOL',
    307071: "BOBOG'OZI",       307072: 'SHARQ YULDUZI', 307073: 'BAXT',
    307074: "O'RIKZOR",        307075: 'QORAQALPOQ',    307076: 'YANGIOBOD',
    307077: "MINGO'RIK",       307078: 'BAHOR',         307079: 'OBI-HAYOT',
    307080: "O'RIKZOR-2",      307081: 'YANGI ANDIJON',
}


class Command(BaseCommand):
    help = "database.xlsx faylidagi ma'lumotlarni SQL bazaga import qiladi"

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_fayl', nargs='?', default='database.xlsx',
            help="Manba Excel fayl yo'li (standart: database.xlsx)",
        )
        parser.add_argument(
            '--tozalash', action='store_true',
            help="Import qilishdan oldin mavjud yozuvlarni o'chirish",
        )
        parser.add_argument(
            '--varaq', default=None,
            help="Varaq nomi (standart: birinchi varaq)",
        )

    # -- sarlavha -----------------------------------------------------------
    def _sarlavhalarni_oqi(self, ws):
        """Birlashtirilgan yacheykalarni yoyib, har bir ustunning nomini qaytaradi."""
        boshi, oxiri = SARLAVHA_QATORLARI
        panjara = {
            (r, c): ws.cell(row=r, column=c).value
            for r in range(boshi, oxiri + 1)
            for c in range(1, ws.max_column + 1)
        }
        for oraliq in ws.merged_cells.ranges:
            if oraliq.min_row > oxiri or oraliq.max_row < boshi:
                continue
            qiymat = ws.cell(row=oraliq.min_row, column=oraliq.min_col).value
            for r in range(max(boshi, oraliq.min_row), min(oxiri, oraliq.max_row) + 1):
                for c in range(oraliq.min_col, oraliq.max_col + 1):
                    panjara[(r, c)] = qiymat

        nomlar = {}
        for c in range(1, ws.max_column + 1):
            # Ustun nomi sifatida eng quyi (eng aniq) sarlavha olinadi.
            for r in range(oxiri, boshi - 1, -1):
                qiymat = panjara.get((r, c))
                matn = ' '.join(str(qiymat).split()) if qiymat else ''
                if matn and matn.rstrip(':,').lower() not in ('шундан', 'шундан,'):
                    nomlar[c - 1] = matn
                    break
            else:
                nomlar[c - 1] = ''
        return nomlar

    # -- lug'atlar ----------------------------------------------------------
    def _lugatlarni_yarat(self, sarlavhalar):
        xizmat_turlari = {}
        for tartib, (kod, k_ust, _ks, ko_ust, _kos, nom_ust, ota) in enumerate(
                XIZMAT_KATALOGI, start=1):
            kiril = sarlavhalar.get(nom_ust, kod)
            turi, _ = XizmatTuri.objects.update_or_create(
                kod=kod,
                defaults={
                    'nomi': tozala(kiril) or kod,
                    'nomi_kiril': kiril,
                    'summasi_bor': _ks is not None or _kos is not None,
                    'tartib': tartib,
                },
            )
            xizmat_turlari[kod] = turi
        # Ota-bola bog'lanishi lug'at to'liq yaratilgandan keyin o'rnatiladi.
        for kod, _k, _ks, _ko, _kos, _n, ota in XIZMAT_KATALOGI:
            if ota:
                turi = xizmat_turlari[kod]
                turi.ota_turi = xizmat_turlari[ota]
                turi.save(update_fields=['ota_turi'])

        holat_turlari = {}
        for tartib, (kod, ustun) in enumerate(IJTIMOIY_HOLAT_KATALOGI, start=1):
            kiril = sarlavhalar.get(ustun, kod)
            turi, _ = IjtimoiyHolatTuri.objects.update_or_create(
                kod=kod,
                defaults={
                    'nomi': tozala(kiril) or kod,
                    'nomi_kiril': kiril,
                    'tartib': tartib,
                },
            )
            holat_turlari[kod] = turi
        return xizmat_turlari, holat_turlari

    # -- asosiy ish ---------------------------------------------------------
    def handle(self, *args, **options):
        try:
            import openpyxl
        except ImportError as xato:
            raise CommandError(
                "openpyxl kutubxonasi kerak: pip install openpyxl"
            ) from xato

        fayl = options['excel_fayl']
        self.stdout.write(f"Fayl o'qilmoqda: {fayl}")
        try:
            kitob = openpyxl.load_workbook(fayl, data_only=True)
        except FileNotFoundError as xato:
            raise CommandError(f"Fayl topilmadi: {fayl}") from xato

        ws = kitob[options['varaq']] if options['varaq'] else kitob.worksheets[0]
        sarlavhalar = self._sarlavhalarni_oqi(ws)
        qatorlar = [
            q for q in ws.iter_rows(min_row=BIRINCHI_QATOR, values_only=True)
            if q[U_TARTIB] is not None
        ]
        kitob.close()
        self.stdout.write(f"Varaq: {ws.title!r}, ma'lumot qatorlari: {len(qatorlar)}")

        if options['tozalash']:
            self.stdout.write("Eski yozuvlar tozalanmoqda...")
            ShaxsIjtimoiyHolat.objects.all().delete()
            Xizmat.objects.all().delete()
            Shaxs.objects.all().delete()
            Oila.objects.all().delete()
            Mahalla.objects.all().delete()
            Hudud.objects.all().delete()
            IjtimoiyToifa.objects.all().delete()
            MuammoToifasi.objects.all().delete()

        with transaction.atomic():
            xizmat_turlari, holat_turlari = self._lugatlarni_yarat(sarlavhalar)
            hisobot = self._qatorlarni_yukla(
                qatorlar, xizmat_turlari, holat_turlari,
            )

        self.stdout.write(self.style.SUCCESS("\nImport tugadi:"))
        for kalit, qiymat in hisobot.items():
            self.stdout.write(f"  {kalit}: {qiymat}")

    def _qatorlarni_yukla(self, qatorlar, xizmat_turlari, holat_turlari):
        hududlar, mahallalar, toifalar, muammolar = {}, {}, {}, {}
        oilalar = {}

        def _hudud(kiril):
            if kiril not in hududlar:
                hududlar[kiril], _ = Hudud.objects.get_or_create(
                    nomi=tozala(kiril) or 'Aniqlanmagan',
                    defaults={'nomi_kiril': kiril},
                )
            return hududlar[kiril]

        def _toifa(kiril, model, saqlanma):
            """Lug'at yozuvini oladi yoki yaratadi; nuqsonli qiymatlar chetlab o'tiladi."""
            matn = _matn(kiril)
            # Manba faylda "Izoh" ustunida 1 va "вв" kabi nuqsonli qiymatlar bor.
            if not matn or matn.isdigit() or len(matn) < 3:
                return None
            if matn not in saqlanma:
                saqlanma[matn], _ = model.objects.get_or_create(
                    nomi=tozala(matn), defaults={'nomi_kiril': matn},
                )
            return saqlanma[matn]

        # --- 1-qadam: mahallalar va oilalar ---
        for qator in qatorlar:
            kodi = int(qator[U_MFY_KODI])
            if kodi not in mahallalar:
                kiril_nomi = _matn(qator[U_MFY_NOMI])
                mahallalar[kodi], _ = Mahalla.objects.update_or_create(
                    kodi=kodi,
                    defaults={
                        'hudud': _hudud(_matn(qator[U_HUDUD])),
                        'nomi': MFY_NOMLARI.get(kodi) or tozala(kiril_nomi, True),
                        'nomi_kiril': kiril_nomi,
                    },
                )

        oila_yozuvlari = {}
        for qator in qatorlar:
            unikal = _matn(qator[U_OILA_ID])
            if not unikal or unikal in oila_yozuvlari:
                continue
            soni = _son(qator[U_OILA_SONI])
            oila_yozuvlari[unikal] = Oila(
                mahalla=mahallalar[int(qator[U_MFY_KODI])],
                unikal_id=unikal,
                azolari_soni=int(soni) if soni else None,
            )
        Oila.objects.bulk_create(list(oila_yozuvlari.values()), batch_size=TOPLAM)
        oilalar = {o.unikal_id: o for o in Oila.objects.all()}
        self.stdout.write(
            f"  {len(mahallalar)} mahalla, {len(oilalar)} oila yozildi"
        )

        # --- 2-qadam: shaxslar ---
        # Manba faylda bir xil JSHSHIR bir necha qatorda uchraydi (ayni shaxs
        # ikki xil "oila unikal ID" ostida ro'yxatga olingan). Qatorlar
        # yo'qotilmaydi, faqat belgilab qo'yiladi.
        jshshir_sanogi = Counter(
            j for j in (_jshshir(q[U_JSHSHIR]) for q in qatorlar) if j
        )
        takrorlangan_jshshir = {j for j, n in jshshir_sanogi.items() if n > 1}

        shaxs_yozuvlari = []
        buzuq_jshshir = 0
        oilasiz = 0
        for qator in qatorlar:
            unikal = _matn(qator[U_OILA_ID])
            oila = oilalar.get(unikal)
            if oila is None:
                oilasiz += 1
                continue

            jshshir = _jshshir(qator[U_JSHSHIR])
            if not jshshir and _matn(qator[U_JSHSHIR]):
                buzuq_jshshir += 1

            fio_manba = _matn(qator[U_FIO])
            tartib = _son(qator[U_TARTIB])
            shaxs_yozuvlari.append(Shaxs(
                oila=oila,
                mahalla=oila.mahalla,
                tartib_raqami=int(tartib) if tartib else None,
                asosiy_arizachi=_bayroq(qator[U_ASOSIY_ARIZACHI]),
                fio=tozala(fio_manba, bosh_harf=True),
                fio_kiril=fio_manba,
                jshshir=jshshir,
                takroriy_jshshir=jshshir in takrorlangan_jshshir,
                jinsi=JINSI_MOSLIGI.get(_matn(qator[U_JINSI]).lower(), ''),
                tugilgan_sana=_sana(qator[U_TUGILGAN]),
                yoshi=_kasr(qator[U_YOSHI]),
                ijtimoiy_toifa=_toifa(qator[U_TOIFA], IjtimoiyToifa, toifalar),
                muammo_toifasi=_toifa(qator[U_IZOH], MuammoToifasi, muammolar),
                reestrdan_chiqqan=_bayroq(qator[U_REESTRDAN_CHIQQAN]),
                uchrashuv_sana=_sana(qator[U_UCHRASHUV_SANA]),
                uchrashuvda_qatnashgan=_bayroq(qator[U_UCHRASHUV]),
                xizmat_sana=_sana(qator[U_XIZMAT_SANA]),
                xizmat_korsatilgan=_bayroq(qator[U_XIZMAT]),
                murojaat_izohi=tozala(qator[U_MUROJAAT_MAZMUNI]),
                muammo_aniqlanmagan=_bayroq(qator[U_MUAMMO_YOQ]),
            ))
        Shaxs.objects.bulk_create(shaxs_yozuvlari, batch_size=TOPLAM)
        self.stdout.write(f"  {len(shaxs_yozuvlari)} shaxs yozildi")

        # --- 3-qadam: xizmatlar va ijtimoiy holatlar ---
        # `bulk_create` SQLite'da ham `id` ni to'ldiradi, shu sababli
        # qatorlar bilan yozuvlar tartibi bir xil bo'ladi.
        xizmatlar, holatlar = [], []
        kerakli_sanoq = {}
        korsatilgan_sanoq = {}
        for qator, shaxs in zip(qatorlar, shaxs_yozuvlari):
            for kod, k_ust, k_summa, ko_ust, ko_summa, _n, _o in XIZMAT_KATALOGI:
                turi = xizmat_turlari[kod]
                for holat, ustun, summa_ustuni in (
                    (Xizmat.KERAKLI, k_ust, k_summa),
                    (Xizmat.KORSATILGAN, ko_ust, ko_summa),
                ):
                    if ustun is None:
                        continue
                    soni = _son(qator[ustun])
                    summa = _kasr(qator[summa_ustuni], 3) if summa_ustuni else None
                    if not soni and not summa:
                        continue
                    xizmatlar.append(Xizmat(
                        shaxs=shaxs, turi=turi, holat=holat,
                        # Manba faylda 6 qatorda "soni" ustuniga summa yozilib
                        # ketgan (masalan 3.4), shu sababli kamida 1 qilinadi.
                        soni=max(1, int(soni)) if soni else 1,
                        summa_mln=summa,
                    ))
                    if holat == Xizmat.KERAKLI:
                        kerakli_sanoq[shaxs.pk] = kerakli_sanoq.get(shaxs.pk, 0) + 1
                    else:
                        korsatilgan_sanoq[shaxs.pk] = (
                            korsatilgan_sanoq.get(shaxs.pk, 0) + 1
                        )

            for kod, ustun in IJTIMOIY_HOLAT_KATALOGI:
                if _bayroq(qator[ustun]):
                    holatlar.append(ShaxsIjtimoiyHolat(
                        shaxs=shaxs, turi=holat_turlari[kod],
                    ))

        Xizmat.objects.bulk_create(xizmatlar, batch_size=TOPLAM)
        ShaxsIjtimoiyHolat.objects.bulk_create(holatlar, batch_size=TOPLAM)
        self.stdout.write(
            f"  {len(xizmatlar)} xizmat, {len(holatlar)} ijtimoiy holat yozildi"
        )

        # --- 4-qadam: tezkor hisoblar va murojaat sababi ---
        # Murojaat sababi kerakli xizmat turidan keltirib chiqariladi
        # (`SABAB_USTUVORLIGI` tartibida - eng aniq sabab birinchi bo'ladi).
        sabab_obyektlari = {
            s.nomi: s for s in MurojaatSababi.objects.all()
        }
        kerakli_kodlar = {}
        for xizmat in xizmatlar:
            if xizmat.holat == Xizmat.KERAKLI:
                kerakli_kodlar.setdefault(xizmat.shaxs.pk, set()).add(xizmat.turi.kod)

        sabab_sanogi = 0
        yangilanadi = []
        for shaxs in shaxs_yozuvlari:
            kerakli = kerakli_sanoq.get(shaxs.pk, 0)
            korsatilgan = korsatilgan_sanoq.get(shaxs.pk, 0)
            ozgardi = False

            if kerakli or korsatilgan:
                shaxs.kerakli_xizmatlar_soni = kerakli
                shaxs.korsatilgan_xizmatlar_soni = korsatilgan
                ozgardi = True

            kodlar = kerakli_kodlar.get(shaxs.pk)
            if kodlar:
                for kod, sabab_nomi in SABAB_USTUVORLIGI:
                    if kod in kodlar and sabab_nomi in sabab_obyektlari:
                        shaxs.murojaat_sababi = sabab_obyektlari[sabab_nomi]
                        sabab_sanogi += 1
                        ozgardi = True
                        break

            if ozgardi:
                yangilanadi.append(shaxs)

        Shaxs.objects.bulk_update(
            yangilanadi,
            [
                'kerakli_xizmatlar_soni', 'korsatilgan_xizmatlar_soni',
                'murojaat_sababi',
            ],
            batch_size=TOPLAM,
        )
        self.stdout.write(
            f"  {sabab_sanogi} shaxsga murojaat sababi qo'yildi, "
            f"{Shaxs.objects.exclude(murojaat_izohi='').count()} ta murojaat mazmuni"
        )

        return {
            'Hududlar': Hudud.objects.count(),
            'Mahallalar': Mahalla.objects.count(),
            'Oilalar': Oila.objects.count(),
            'Shaxslar': Shaxs.objects.count(),
            'Xizmat turlari': XizmatTuri.objects.count(),
            'Xizmat yozuvlari': Xizmat.objects.count(),
            'Ijtimoiy holat turlari': IjtimoiyHolatTuri.objects.count(),
            'Ijtimoiy holat yozuvlari': ShaxsIjtimoiyHolat.objects.count(),
            'Ijtimoiy toifalar': IjtimoiyToifa.objects.count(),
            'Muammo toifalari': MuammoToifasi.objects.count(),
            "Murojaat sababi qo'yilgan shaxslar":
                Shaxs.objects.filter(murojaat_sababi__isnull=False).count(),
            "Murojaat mazmuni yozilgan shaxslar":
                Shaxs.objects.exclude(murojaat_izohi='').count(),
            "JSHSHIR nuqsonli (bo'sh qoldirildi)": buzuq_jshshir,
            "JSHSHIR takrorlangan (belgilandi)": len(takrorlangan_jshshir),
            "Oilasiz qatorlar (o'tkazib yuborildi)": oilasiz,
        }
