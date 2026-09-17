# Shtab ma'lumotlar bazasi (Django)

Andijon tumani "Aholi bandligi va daromadlarini oshirish hamda kambag'allikka
barham berish" shtabi ma'lumotlarini SQL bazada saqlash va veb-interfeys
orqali ko'rish/qidirish uchun Django ilovasi.

## Tuzilma

```
shtab_project/
  manage.py
  requirements.txt
  data/
    shtab_database.json      <- import qilinadigan manba fayl
  shtab_project/              <- loyiha sozlamalari (settings, urls)
  registry/                   <- asosiy ilova
    models.py                 <- Mahalla, Oila, Shaxs modellari
    views.py                  <- ro'yxat/qidiruv/detail sahifalari
    admin.py                  <- Django admin panel
    management/commands/
      import_shtab.py         <- JSON'ni bazaga yuklovchi buyruq
    templates/registry/       <- HTML shablonlar
    static/registry/css/      <- CSS
```

## O'rnatish

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Ma'lumotlar bazasini tayyorlash

Standart holatda SQLite ishlatiladi (kichik/o'rtacha hajm uchun yetarli).
Katta hajmda barqaror ishlash uchun PostgreSQL'ga o'tish tavsiya etiladi —
`shtab_project/settings.py` faylida izohli misol bor.

```bash
python manage.py migrate
python manage.py createsuperuser   # admin panel uchun (ixtiyoriy)
```

## Ma'lumotlarni JSON'dan bazaga yuklash

```bash
python manage.py import_shtab data/shtab_database.json
```

Agar qayta yuklash kerak bo'lsa (avvalgi yozuvlarni tozalab):

```bash
python manage.py import_shtab data/shtab_database.json --tozalash
```

~16 000 yozuv uchun import bir necha soniyadan bir necha daqiqagacha vaqt olishi
mumkin (baza turiga qarab).

## Serverni ishga tushirish

```bash
python manage.py runserver
```

So'ng brauzerda oching:

- `http://127.0.0.1:8000/` — bosh sahifa (statistika)
- `http://127.0.0.1:8000/shaxslar/` — qidiruv/filtr bilan shaxslar ro'yxati
- `http://127.0.0.1:8000/mahallalar/` — mahallalar ro'yxati
- `http://127.0.0.1:8000/admin/` — Django admin panel

## Xavfsizlik bo'yicha eslatma

Ushbu ma'lumotlar bazasida F.I.O., JSHSHIR (shaxsiy identifikatsiya raqami),
ijtimoiy va sog'liq holatiga oid maxfiy ma'lumotlar mavjud. Production'ga
chiqarishdan oldin albatta quyidagilarni bajaring:

1. `settings.py`dagi `SECRET_KEY`ni maxfiy environment variable orqali bering.
2. `DEBUG = False` qiling va `ALLOWED_HOSTS`ni aniq domenlar bilan cheklang.
3. Foydalanuvchilar autentifikatsiyasini (login) joriy qiling — hozirgi holatda
   `/shaxslar/` sahifasi ochiq; kerak bo'lsa `@login_required` qo'shing.
4. HTTPS orqali joylashtiring va bazaga kirishni cheklang.
