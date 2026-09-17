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
U_MUAMMO_YOQ = 44        # "Учрашувда муаммо аниқланмаган оила" (teskari mantiq)

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

# "Nima uchun murojaat qilgan" katalogi.
#
# Manba faylda buning uchun alohida ustun yo'q, lekin ma'lumot ikki joyda bor:
#   * "kerakli xizmatlar" ustunlari (19-42) - fuqaroga qanday xizmat kerak;
#   * 43-ustun ("Бошқа муаммоли оилалар (Изоҳ)") - erkin matn: fuqaro nima
#     so'ragani ("Uy joyini ta'mirlash", "Nogironlik aravachasi olish"...).
#
# Har bir yozuv: (nomi, tavsifi, tartib, xizmat_kodlari, kalit_sozlar)
#   xizmat_kodlari - shu sabab qaysi `XizmatTuri.kod` larga mos keladi;
#   kalit_sozlar   - 43-ustun matnida qidiriladigan (kichik harfdagi) bo'laklar.
# Bir shaxsga bir nechta sabab tegishli bo'lishi mumkin - hammasi yoziladi.
SABAB_KATALOGI = [
    ("Ish bilan ta'minlash", 'Doimiy ish yoki bandlik masalasi', 10,
     ['doimiy_ish', 'ozini_ozi_band_qilish'],
     ['ish joyi', 'ish xakki', 'ish haqi', 'bandlik', 'ishga joylash',
      'stavka', 'ishlash istagi', 'uyushmasidan']),

    ("Tadbirkorlikni yo'lga qo'yish", 'Oilaviy tadbirkorlik, savdo', 20,
     ['tadbirkorlik'], ['dukon', 'savdo']),

    ('Mehnat migratsiyasi', "Xorijga ishga jo'natish", 30,
     ['migratsiya'], []),

    ("Kasb-hunarga o'qitish", 'Qayta tayyorlov va malaka oshirish', 40,
     ['kasb_hunarga_oqitish'], ['sertifikat', 'xamshira']),

    ('Imtiyozli kredit yoki ssuda', 'Kredit/ssuda ajratish masalasi', 50,
     ['imtiyozli_kredit', 'ssuda'], ['kredit', 'keredit', 'krelit']),

    ("Ijtimoiy daftarlardan mablag'", 'Subsidiya va ijtimoiy nafaqa', 60,
     ['ijtimoiy_daftarlar', 'yoshlar_daftari', 'ayollar_daftari',
      'infratuzilma_jamgarmasi'],
     ['subsidiya', 'moddiy', "jamg'arma", 'jamgarma', 'yangi kun']),

    ('Homiylik yordami', "Homiylar hisobidan ko'rsatiladigan yordam", 70,
     ['sahovat_jamgarmasi', 'homiylik'],
     ['xomiylik', 'homiylik', 'xomiy', 'homiy', 'tikuv moshina',
      'tikuv mashina', 'balon']),

    ('Tibbiy yordam va reabilitatsiya', "Sog'lig'ini tiklash, davolanish", 80,
     ['sogligini_tiklash'],
     ['davola', 'davolan', 'operattsiya', 'operatsiya', 'poliklinika',
      'riabilatsiya', 'reabilitatsiya', 'eshitish', 'moslama', 'miyyasi',
      'shifoxona', 'tibbiy', 'dori', 'emlash', 'kassallik', 'kasallik']),

    ('Nogironlik masalalari', 'Nogironlik guruhi, aravacha, jihozlar', 90,
     [], ['nogiron', 'nogirron', 'aravacha', 'avarachasi', 'guruxiga',
          'gruxiga']),

    ("Farzandni bog'chaga joylashtirish", 'Vaucher yoki joy masalasi', 100,
     ['bogcha_vaucheri'], ["bog'cha", 'bogcha', 'boqcha', 'ptpk']),

    ("Ta'lim, kurs va to'garaklar", "Maktab, kollej, kurs va to'garaklar", 110,
     [],
     ['kurs', 'kurrs', "to'garak", 'tugrak', 'togarak', "o'qit", 'ukitish',
      'oqitish', 'maktab', 'talim', "ta'lim", 'logoped', 'dual', 'til ',
      'ingliz', 'rus tili', 'ximiya', 'matematika', 'musiqa', 'kontrak',
      'kantrakt', "o'quv", 'oquv', 'ukuv', 'temuriylar', 'universitet',
      'imkoniyatlar olami']),

    ('Hujjat rasmiylashtirish', 'Kadastr, pasport, guvohnoma va h.k.', 120,
     ['kadastr'],
     ['pasport', 'xujjat', 'hujjat', 'rasmiylashtir', 'nikox', 'nikoh',
      'order', 'guvoxnoma', 'metirka', 'vaucher', 'xarbiy', 'armiya']),

    ('Aliment undirish', 'Aliment qarzdorligini undirib berish', 130,
     ['aliment'], []),

    ("Uy-joy va ta'mirlash", "Uy-joy olish yoki ta'mirlash masalasi", 140,
     [],
     ['uy joy', 'uy-joy', 'uyjoy', "ta'mir", 'tamir', 'shifer', 'devor',
      'uyini', 'uy olish', 'uyidan', 'uy ', 'uyi ', 'darvoza', 'xonadon']),

    ('Kommunal va infratuzilma', "Gaz, elektr, suv, yo'l masalalari", 150,
     [],
     ['gaz', 'elektor', 'elektr', 'qarzdorlik', 'karzdorlik', 'kommunal',
      "shag'al", 'shagal', "ko'chasi", 'kochasi', 'suv', 'isitish',
      'internet', "ko'mir", "yoqilg'", 'musir', 'tozalash']),

    ('Yuridik yordam', 'Sud, soliq, huquqiy maslahat', 160,
     [],
     ['yuridik', 'maslaxat olish', 'prokuror', 'sud', 'qabuliga', 'jarima',
      "solig'", 'solig', 'ozodlik', 'noqonuniy', 'er sot', 'oldisotti',
      'avtoshina', 'mashinasini', 'yatt']),

    ('Parvarish va qarovchilik', "Oila a'zosini parvarish qilish", 170,
     [],
     ['qarovchi', 'karovchi', 'karab turish', 'qarab turish', 'parvarish',
      'karab turuvchi']),

    ('Oilaviy nizo va psixologik yordam', 'Oilaviy kelishmovchilik', 180,
     [], ['psixolog', 'notinch', 'yarash', 'kelishmovchilik',
          'oilasini tiklash']),

    ('Pensiya masalasi', 'Pensiyani qayta hisoblash va h.k.', 190,
     [], ['pensiya']),

    ('Meros va ulush masalasi', 'Mulkdan ulush, meros', 200,
     [], ['ulush', 'meros']),

    ('Bolani asrab olish va vasiylik', 'Vasiylik, asrab olish', 210,
     [], ['asrab ol', 'vasiylik']),
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

        # Murojaat sabablari katalogi
        sabablar = {}
        for nomi, tavsifi, tartib, _xiz, _kal in SABAB_KATALOGI:
            sabab, _ = MurojaatSababi.objects.update_or_create(
                nomi=nomi,
                defaults={'tavsifi': tavsifi, 'tartib': tartib, 'faol': True},
            )
            sabablar[nomi] = sabab

        # Katalogda yo'q va hech bir shaxsga bog'lanmagan sabablarni
        # olib tashlaymiz (masalan katalog nomi o'zgargandan keyin qolganlar).
        ortiqcha = (
            MurojaatSababi.objects
            .exclude(nomi__in=sabablar)
            .filter(shaxslar__isnull=True)
        )
        ochirilgan = ortiqcha.count()
        if ochirilgan:
            ortiqcha.delete()
            self.stdout.write(
                f"  {ochirilgan} ta ishlatilmagan murojaat sababi o'chirildi"
            )

        return xizmat_turlari, holat_turlari, sabablar

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
            xizmat_turlari, holat_turlari, sabablar = (
                self._lugatlarni_yarat(sarlavhalar)
            )
            hisobot = self._qatorlarni_yukla(
                qatorlar, xizmat_turlari, holat_turlari, sabablar,
            )

        self.stdout.write(self.style.SUCCESS("\nImport tugadi:"))
        for kalit, qiymat in hisobot.items():
            self.stdout.write(f"  {kalit}: {qiymat}")

    def _qatorlarni_yukla(self, qatorlar, xizmat_turlari, holat_turlari,
                          sabablar):
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
                # 44-ustun "muammo aniqlanMAGAN" degani - teskarisiga olamiz
                muammo_aniqlangan=not _bayroq(qator[U_MUAMMO_YOQ]),
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

        # --- 4-qadam: tezkor hisoblar ---
        yangilanadi = []
        for shaxs in shaxs_yozuvlari:
            kerakli = kerakli_sanoq.get(shaxs.pk, 0)
            korsatilgan = korsatilgan_sanoq.get(shaxs.pk, 0)
            if kerakli or korsatilgan:
                shaxs.kerakli_xizmatlar_soni = kerakli
                shaxs.korsatilgan_xizmatlar_soni = korsatilgan
                yangilanadi.append(shaxs)
        Shaxs.objects.bulk_update(
            yangilanadi,
            ['kerakli_xizmatlar_soni', 'korsatilgan_xizmatlar_soni'],
            batch_size=TOPLAM,
        )

        # --- 5-qadam: murojaat sabablari (ko'p-ko'p bog'lanish) ---
        sabab_bogliklari = self._sabablarni_bogla(
            qatorlar, shaxs_yozuvlari, xizmatlar, sabablar,
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
            "Murojaat sabablari (lug'at)": MurojaatSababi.objects.count(),
            'Murojaat sababi bor shaxslar':
                Shaxs.objects.filter(murojaat_sabablari__isnull=False)
                .distinct().count(),
            "Murojaat sababi bog'lanishlari": sabab_bogliklari,
            "JSHSHIR nuqsonli (bo'sh qoldirildi)": buzuq_jshshir,
            "JSHSHIR takrorlangan (belgilandi)": len(takrorlangan_jshshir),
            "Oilasiz qatorlar (o'tkazib yuborildi)": oilasiz,
        }

    def _sabablarni_bogla(self, qatorlar, shaxs_yozuvlari, xizmatlar, sabablar):
        """Har bir shaxsga tegishli murojaat sabablarini bog'laydi.

        Ikki manbadan yig'iladi:
          * kerak bo'lgan xizmat turlari (`SABAB_KATALOGI` dagi xizmat kodlari);
          * 43-ustundagi erkin matn (kalit so'zlar bo'yicha).

        Bir shaxsda bir nechta sabab bo'lishi mumkin - hammasi yoziladi.
        """
        # Kod/kalit -> sabab nomlari xaritalari
        kod_xaritasi = {}
        kalit_xaritasi = []
        for nomi, _tavsifi, _tartib, xizmat_kodlari, kalit_sozlar in SABAB_KATALOGI:
            for kod in xizmat_kodlari:
                kod_xaritasi.setdefault(kod, []).append(nomi)
            for kalit in kalit_sozlar:
                kalit_xaritasi.append((kalit, nomi))

        # Shaxs -> kerak bo'lgan xizmat kodlari
        kerakli_kodlar = {}
        for xizmat in xizmatlar:
            if xizmat.holat == Xizmat.KERAKLI:
                kerakli_kodlar.setdefault(xizmat.shaxs.pk, set()).add(
                    xizmat.turi.kod
                )

        # 43-ustun matnini bir marta tahlil qilib keshlaymiz (matnlar takrorlanadi).
        matn_keshi = {}

        def matndan_sabablar(matn):
            if matn not in matn_keshi:
                past = matn.lower()
                matn_keshi[matn] = {
                    nomi for kalit, nomi in kalit_xaritasi if kalit in past
                }
            return matn_keshi[matn]

        Bogliq = Shaxs.murojaat_sabablari.through
        bogliqlar = []
        matndan_sanoq = 0
        xizmatdan_sanoq = 0

        for qator, shaxs in zip(qatorlar, shaxs_yozuvlari):
            nomlar = set()

            for kod in kerakli_kodlar.get(shaxs.pk, ()):
                nomlar.update(kod_xaritasi.get(kod, ()))
            if nomlar:
                xizmatdan_sanoq += 1

            matn = tozala(qator[U_MUROJAAT_MAZMUNI])
            if matn:
                matndan = matndan_sabablar(matn)
                if matndan:
                    matndan_sanoq += 1
                nomlar.update(matndan)

            for nomi in nomlar:
                sabab = sabablar.get(nomi)
                if sabab is not None:
                    bogliqlar.append(Bogliq(
                        shaxs_id=shaxs.pk, murojaatsababi_id=sabab.pk,
                    ))

        Bogliq.objects.bulk_create(
            bogliqlar, batch_size=TOPLAM, ignore_conflicts=True,
        )
        self.stdout.write(
            f"  {len(bogliqlar)} murojaat sababi bog'lanishi yozildi "
            f"(kerakli xizmatdan: {xizmatdan_sanoq} shaxs, "
            f"43-ustun matnidan: {matndan_sanoq} shaxs)"
        )
        return len(bogliqlar)

