# Shtab ma'lumotlar bazasi (Django)

Andijon tumani "Aholi bandligi va daromadlarini oshirish hamda kambag'allikka
barham berish" shtabi ma'lumotlarini SQL bazada saqlash va veb-interfeys
orqali ko'rish/qidirish uchun Django ilovasi.

Ma'lumotlar manbasi — `database.xlsx` (115 ustun, 15 959 qator). Import
vaqtida barcha kirill yozuvi lotinga o'giriladi va manba fayldagi kodirovka
nuqsonlari tuzatiladi.

## Tuzilma

```
SHTAB/
  manage.py
  requirements.txt
  database.xlsx               <- import qilinadigan manba fayl
  shtab_project/              <- loyiha sozlamalari (settings, urls)
  registry/                   <- asosiy ilova
    models.py                 <- ma'lumotlar modeli (quyida)
    translit.py               <- kirill->lotin va kodirovkani tuzatish
    views.py                  <- ro'yxat/qidiruv/detail sahifalari
    admin.py                  <- Django admin panel
    management/commands/
      import_excel.py         <- database.xlsx'ni bazaga yuklovchi buyruq
    forms.py                  <- tahrirlash formalari
    malumotnoma.py            <- ma'lumotnoma jadvallari ro'yxati (umumiy CRUD)
    templatetags/shtab.py     <- shablon filtrlari
    templates/registry/       <- HTML shablonlar
    static/registry/css/      <- CSS (dizayn tizimi)
    static/registry/js/       <- ui.js (maxsus selectlar, mavzu, formset)
```

## Interfeys

Dizayn iOS uslubida: "shisha" (glass) yuzalar, iOS tizim ranglari va
**yorug'/qorong'i mavzu** (o'ng yuqoridagi tugma bilan almashtiriladi;
tanlov `localStorage` da saqlanadi, standart holatda tizim sozlamasi olinadi).

### Maxsus ochiluvchi ro'yxatlar (custom select)

`ui.js` har bir `data-select` atributli `<select>` ni iOS uslubidagi
ro'yxatga aylantiradi:

- shisha panel, prujinali (spring) ochilish animatsiyasi, variantlar ketma-ket
  (kaskad) chiqadi, bosilganda **ripple** effekti;
- chapda doimiy yorliq (`data-label="Mahalla"`), o'ngda tanlangan qiymat;
- **ko'p tanlovli** ro'yxatda tanlovlar "chip" ko'rinishida chiqadi
  (`+N` ortiqcha hisoblagichi bilan) va "Hammasini tanlash / Tozalash" tugmalari
  bo'ladi;
- 8 dan ortiq variant bo'lsa **qidiruv** maydoni paydo bo'ladi (77 ta MFY uchun);
- to'liq klaviatura boshqaruvi (`↑ ↓ Home End Enter Space Esc Tab`), ARIA
  atributlari, `prefers-reduced-motion` hurmat qilinadi.

JavaScript o'chirilgan bo'lsa sahifalar ishlashda davom etadi - oddiy
`<select>` ko'rinishida qoladi.

## Tahrirlash (CRUD)

| Amal | Manzil |
|---|---|
| Yangi shaxs qo'shish | `/shaxslar/yangi/` |
| Shaxsni tahrirlash | `/shaxslar/<id>/tahrirlash/` |
| Shaxsni o'chirish | `/shaxslar/<id>/ochirish/` |
| MFY nomini tuzatish | `/mahallalar/<id>/tahrirlash/` |

Shaxs formasida shaxsiy ma'lumotlar, mahalla/oila, ijtimoiy reestr,
uchrashuv sanalari, ijtimoiy holat belgilari (ko'p tanlovli ro'yxat) va
**xizmatlar jadvali** (qator qo'shish/o'chirish mumkin) bir joyda tahrirlanadi.

Tekshiruvlar: JSHSHIR faqat 14 xonali raqam; oila tanlangan mahallaga tegishli
bo'lishi shart; uchrashuv sanasi tug'ilgan sanadan oldin bo'lmaydi. Mahalla
o'zgartirilsa, oilalar ro'yxati sahifani qayta yuklamasdan yangilanadi
(`/api/oilalar/`).

### Murojaat sababi (nima uchun murojaat qilgan)

Manba `database.xlsx` faylida bu ma'lumot **yo'q** - u shtab xodimlari
tomonidan kiritiladi. Shu sababli:

- `MurojaatSababi` lug'ati (`/malumotnoma/murojaat-sabablari/`) - sabablar
  ro'yxati. `0004_...` migratsiyasi 12 ta boshlang'ich sababni qo'shadi
  (ish bilan ta'minlash, imtiyozli kredit, tibbiy yordam va h.k.) - bu
  shunchaki qulay boshlanish nuqtasi, ro'yxatni to'ldirish/qisqartirish mumkin.
  `faol` belgisi olingan sabab yangi yozuvlarda ko'rinmaydi, lekin eski
  yozuvlarda saqlanib qoladi.
- `Shaxs.murojaat_sababi` (FK) va `Shaxs.murojaat_izohi` (erkin matn) -
  shaxs kartochkasidagi «Uchrashuv va xizmatlar» panelida ko'rinadi,
  shaxslar ro'yxatida esa sabab bo'yicha filtrlash mumkin.

### Ma'lumotnoma: barcha jadvallarga yozuv qo'shish

`/malumotnoma/` sahifasida bazadagi **barcha** jadvallar bor va har biriga
yozuv qo'shish / tahrirlash / o'chirish mumkin:

| Jadval | Manzil |
|---|---|
| Hududlar | `/malumotnoma/hududlar/` |
| Mahallalar (MFY) | `/malumotnoma/mahallalar/` |
| Oilalar | `/malumotnoma/oilalar/` |
| Murojaat sabablari | `/malumotnoma/murojaat-sabablari/` |
| Ijtimoiy toifalar | `/malumotnoma/ijtimoiy-toifalar/` |
| Muammo toifalari | `/malumotnoma/muammo-toifalari/` |
| Xizmat turlari | `/malumotnoma/xizmat-turlari/` |
| Ijtimoiy holat belgilari | `/malumotnoma/ijtimoiy-holatlar/` |

Bu sahifalar bitta umumiy CRUD mexanizmi bilan ishlaydi: jadval sozlamalari
`registry/malumotnoma.py` da (`JADVALLAR` ro'yxati), ko'rinishlar esa
`views.py` dagi `Jadval*View` sinflarida. **Yangi jadval qo'shish uchun
`JADVALLAR` ro'yxatiga bitta yozuv qo'shish yetarli** - alohida view yoki
shablon yozish kerak emas.

O'chirishdan oldin bog'liq yozuvlar soni ko'rsatiladi. `PROTECT` bilan
bog'langan yozuv (masalan, ishlatilayotgan ijtimoiy toifa) o'chmaydi -
tushunarli xabar chiqadi.

**Muhim:** ma'lumotlar maxfiy bo'lgani uchun tahrirlash va ma'lumotnoma
sahifalari faqat tizimga kirgan foydalanuvchiga ochiq (`/kirish/`).
Ko'rish/qidirish sahifalari hozircha ochiq - kerak bo'lsa ularga ham
`LoginRequiredMixin` qo'shing.

```bash
python manage.py createsuperuser   # tahrirlash uchun hisob
```

## Ma'lumotlar modeli

```
Hudud -> Mahalla -> Oila -> Shaxs
                              |-> Xizmat             -> XizmatTuri
                              |-> ShaxsIjtimoiyHolat -> IjtimoiyHolatTuri
                              |-> IjtimoiyToifa   (FK)
                              |-> MuammoToifasi   (FK)
                              |-> MurojaatSababi  (FK)
```

Manba fayldagi 0/1 bayroq ustunlari JSON ko'rinishida emas, **normal holatga
keltirilgan** ko'rinishda saqlanadi:

| Model | Vazifasi | Yozuvlar |
|---|---|---|
| `Hudud` | tuman/shahar | 1 |
| `Mahalla` | MFY (kodi, nomi) | 77 |
| `Oila` | oila (unikal ID bo'yicha) | 4 164 |
| `Shaxs` | jismoniy shaxs | 15 959 |
| `XizmatTuri` | xizmatlar lug'ati (ierarxik) | 17 |
| `Xizmat` | shaxsga kerak bo'lgan / ko'rsatilgan xizmat | 3 231 |
| `IjtimoiyHolatTuri` | ijtimoiy holat belgilari lug'ati | 43 |
| `ShaxsIjtimoiyHolat` | shaxsga qo'yilgan belgi | 19 160 |
| `IjtimoiyToifa` | ijtimoiy reestrdagi toifa | 3 |
| `MuammoToifasi` | "Izoh" ustunidagi muammo toifasi | 15 |
| `MurojaatSababi` | murojaat sababi (manba faylda yo'q) | 12 |

Shu sababli har qanday belgi yoki xizmat turi bo'yicha filtrlash va
hisob-kitob qilish mumkin (masalan, "Ishsiz" belgisi qo'yilgan shaxslar yoki
"imtiyozli kredit" ajratilgan summalar yig'indisi).

## O'rnatish

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Bazani tayyorlash va ma'lumotlarni yuklash

```bash
python manage.py migrate
python manage.py import_excel database.xlsx --tozalash
python manage.py createsuperuser   # admin panel uchun
```

`--tozalash` — import qilishdan oldin mavjud yozuvlarni o'chiradi (qayta
yuklash uchun). Import ~1 daqiqa vaqt oladi.

> **Diqqat:** `--tozalash` barcha `Shaxs` yozuvlarini o'chirib qaytadan
> yaratadi. Shu sababli veb-interfeys orqali qo'lda kiritilgan va manba
> faylda mavjud bo'lmagan ma'lumotlar — **murojaat sababi va murojaat
> izohi** — yo'qoladi. `MurojaatSababi` lug'atining o'zi o'chmaydi.
> Qo'lda kiritilgan ma'lumot ko'p bo'lsa, avval zaxira oling:
> `python -X utf8 manage.py dumpdata registry > zaxira.json`

Standart holatda SQLite ishlatiladi. Katta hajmda barqaror ishlash uchun
PostgreSQL tavsiya etiladi — `shtab_project/settings.py` faylida izohli
misol bor.

## Serverni ishga tushirish

```bash
python manage.py runserver
```

- `http://127.0.0.1:8000/` — bosh sahifa (statistika, xizmatlar, belgilar)
- `http://127.0.0.1:8000/shaxslar/` — qidiruv/filtr bilan shaxslar ro'yxati
- `http://127.0.0.1:8000/mahallalar/` — mahallalar ro'yxati
- `http://127.0.0.1:8000/malumotnoma/` — barcha jadvallar (yozuv qo'shish)
- `http://127.0.0.1:8000/admin/` — Django admin panel

## Kirilldan lotinga o'tkazish va kodirovka

Barcha matnli maydonlar bazada **lotin yozuvida** saqlanadi. Manba fayldagi
asl ko'rinish solishtirish uchun `*_kiril` maydonlarida (`Shaxs.fio_kiril`,
`Mahalla.nomi_kiril` va h.k.) saqlab qolinadi.

`registry/translit.py` moduli ikki ishni bajaradi:

1. **Kodirovkani tuzatish.** Manba fayl CP1251 ga o'xshash kodirovka orqali
   o'tgani sababli o'zbek kirill alifbosiga xos harflar (Қ, Ғ, Ҳ, bir joyda Ў)
   F.I.O. ustunida `?` belgisiga aylanib qolgan — jami **2 492 marta, 461 xil
   so'z shaklida** (`Ў?ЛИ` -> `ЎҒЛИ`, `?ИЗИ` -> `ҚИЗИ`, `МУ?АММАД` ->
   `МУҲАММАД` va h.k.). `QAYTA_TIKLASH` lug'atida barcha 461 shakl aniq
   ko'rsatilgan, shu sababli natija taxminga emas, ro'yxatga asoslangan.
2. **Transliteratsiya.** Kirill matni lotinga o'giriladi (`ў` -> `o'`,
   `қ` -> `q`, `ғ` -> `g'`, `ҳ` -> `h`, `ч` -> `ch`, unlidan keyin `е` ->
   `ye`: `Тешабоев` -> `Teshaboyev`). Turli tutuq belgilari (`'`, `` ` ``,
   `’`) bitta `'` ko'rinishiga keltiriladi.

Import tugagach bazada bitta ham kirill harfi yoki `?` belgisi qolmaydi
(tekshirilgan).

### MFY nomlari haqida

Manba faylda MFY nomlari kirillda, lekin `Қ`/`Ғ`/`Ў` harflaridan
foydalanmasdan yozilgan (masalan `ИТТИФОК`, `КУМ КУЧА`). To'g'ridan-to'g'ri
transliteratsiya `ITTIFOK`, `KUM KUCHA` beradi. Shu sababli
`import_excel.py` faylidagi `MFY_NOMLARI` lug'atida 77 ta MFY uchun to'g'ri
lotin yozuvi (`ITTIFOQ`, `QUM KO'CHA`) qo'lda keltirilgan. **Bu ro'yxatni
tekshirib chiqish tavsiya etiladi** — asl kirill ko'rinishi
`Mahalla.nomi_kiril` maydonida turadi.

## Manba fayldagi nuqsonlar (import hisoboti)

Import buyrug'i quyidagilarni hisoblab chiqadi va ular ma'lumot
yo'qotilmasdan bazaga o'tkaziladi:

- **6 ta qator** — JSHSHIR o'rniga `1` yozilgan; `jshshir` bo'sh qoldirilgan.
  Ularning tug'ilgan sanasi va yoshi ham `#VALUE!` bo'lib, `NULL` qilingan.
- **79 ta JSHSHIR (158 qator)** — ayni shaxs ikki xil "oila unikal ID" ostida
  ikki marta ro'yxatga olingan (F.I.O. va tug'ilgan sana bir xil). Qatorlar
  o'chirilmagan, `Shaxs.takroriy_jshshir = True` deb belgilangan. Admin
  panelda shu maydon bo'yicha filtrlab tekshirish mumkin.
- **662 ta qator** — "Izoh" ustunida toifa nomi o'rniga `1` yoki `вв`
  yozilgan; `muammo_toifasi` bo'sh (`NULL`) qoldirilgan.
- **6 ta qator** (manba faylning 3637, 3652, 3703, 3707, 3726, 3742-qatorlari)
  — "soni" ustunlariga son o'rniga summa yozilib ketgan: 29-ustun
  ("Ijtimoiy daftarlardan") va 35-ustun ("Sahovat jamg'armasidan") da `2.4`
  va `3.4` kabi kasrli qiymatlar. `Xizmat.soni` ga butun qismi olinadi
  (kamida 1), summa esa alohida `summa_mln` ustunidan olinadi.
- Manba fayldagi "jami" ustunlari (19 va 46) bazaga ko'chirilmaydi — ular
  ham shu nuqsondan aziyat chekkan. O'rniga `Shaxs.kerakli_xizmatlar_soni`
  va `Shaxs.korsatilgan_xizmatlar_soni` haqiqiy `Xizmat` yozuvlaridan
  hisoblanadi.
- **145 ta qator** — ijtimoiy holat ustunlari umuman to'ldirilmagan (bo'sh),
  shu sababli ularga birorta ham belgi qo'yilmagan.
- "Xizmat ko'rsatilgan sana" ustuni manba faylda **butunlay bo'sh**, shu
  sababli `xizmat_sana` barcha yozuvlarda `NULL`.

## Xavfsizlik bo'yicha eslatma

Ushbu ma'lumotlar bazasida F.I.O., JSHSHIR (shaxsiy identifikatsiya raqami),
ijtimoiy va sog'liq holatiga oid maxfiy ma'lumotlar mavjud. Production'ga
chiqarishdan oldin albatta quyidagilarni bajaring:

1. `settings.py`dagi `SECRET_KEY`ni maxfiy environment variable orqali bering.
2. `DEBUG = False` qiling va `ALLOWED_HOSTS`ni aniq domenlar bilan cheklang.
3. Foydalanuvchilar autentifikatsiyasini (login) joriy qiling — hozirgi holatda
   `/shaxslar/` sahifasi ochiq; kerak bo'lsa `@login_required` qo'shing.
4. HTTPS orqali joylashtiring va bazaga kirishni cheklang.
