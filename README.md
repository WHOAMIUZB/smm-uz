# SMM Xizmatlar Boti (@smm_uzb_robot)

Aiogram 3.x asosida qurilgan, SMM panel API (`smmapi.safobuilder.uz`) bilan integratsiya qilingan
to'liq funksional Telegram bot. `@shox_smmbot` botiga o'xshash menyu va oqim bilan ishlaydi.

## ✨ Imkoniyatlar

**Foydalanuvchi uchun:**
- 🧾 Buyurtma berish — **admin tuzgan katalog** bo'yicha bosqichma-bosqich tanlaydi
  (masalan: Telegram → Tekin nakrutka → Reaksiyalar → kerakli reaksiya) → link → miqdor → tasdiqlash
- 📊 Buyurtmalar — so'nggi buyurtmalar va real vaqtda holat (SMM API orqali)
- 💳 Mening hisobim — balans, buyurtmalar soni, referallar soni
- 🎙 Referal tizimi — referal havola, har bir yangi foydalanuvchi uchun bonus
- 💰 Hisob to'ldirish — ikki usul:
  - **Karta orqali** — admin qo'shgan kartalardan birini tanlaydi, karta raqami/egasi ko'rinadi, summa kiritiladi, chek (rasm/fayl) yuboriladi → admin tasdiqlaydi/rad etadi
  - **⭐️ Stars orqali** — Telegram'ning native Stars to'lov tizimi (`sendInvoice`, currency `XTR`) orqali; to'lov muvaffaqiyatli bo'lishi bilan hisob **avtomatik** to'ldiriladi, admin tasdiqlashi shart emas
- ☎️ Murojaat qilish — admin bilan bevosita yozishma (`/reply <user_id> <matn>`)
- 📚 Qo'llanmalar — foydalanish bo'yicha qo'llanma
- 📢 Majburiy obuna — bot faqat admin bo'lgan kanallarga obuna bo'lganlar uchun ishlaydi

**Admin uchun (`/admin`):**
- 📊 Statistika (foydalanuvchilar, buyurtmalar, tushum, SMM panel balansi)
- 📣 Barcha foydalanuvchilarga xabar yuborish (matn/rasm/video)
- 🗂 **Katalog (buyurtma menyu)** — cheksiz chuqurlikdagi bo'lim/quyi-bo'lim tuzilmasi:
  - Istalgan chuqurlikda yangi bo'lim ("➕ Bo'lim") yoki xizmat ("➕ Xizmat", SMM ID orqali bog'lanadi) qo'shish
  - Har bir band uchun ko'rsatiladigan nomni istalgancha o'zgartirish ("✏️ Nomini o'zgartirish")
  - Bandlarni ⬆️/⬇️ tugmalari bilan tartiblash (joyini o'zgartirish)
  - Bo'lim yoki xizmatni o'chirish (bo'lim o'chirilsa ichidagi barcha bandlar ham o'chadi, oldindan ogohlantiriladi)
  - "🔄 Xizmatlarni yangilash" bosilganda yangi xizmatlar API kategoriyasi nomi bilan katalogga **avtomatik** joylashtiriladi — allaqachon qo'lda joylashtirilganlar qayta qo'shilmaydi/dublyaj bo'lmaydi
- 💵 Har bir xizmat uchun sotuv narxini boshqarish (yoqish/o'chirish ham mumkin)
- 📢 Majburiy obuna kanallarni qo'shish/o'chirish (faqat bot admin bo'lgan kanallar; kanaldan forward yoki @username/ID orqali qo'shiladi)
- 💳 To'lov kartalarini boshqarish — istalgancha karta qo'sha oladi, foydalanuvchi to'lov paytida tanlaydi
- ⚙️ Sozlamalar: dollar kursi, ustama foizi, referal bonusi, 1 Star narxi (so'mda)

## ⚙️ Narx hisoblash mantiqi

Xizmatlarni sinxronlaganda: `sotuv_narxi = api_rate(USD) × kurs × (1 + ustama%/100)`,
so'ngra har bir xizmat narxini admin panel orqali qo'lda ham o'zgartirish mumkin.
Foydalanuvchi balansi va barcha to'lovlar **so'mda** yuritiladi (SMM panelning o'zi USD'da ishlaydi).

## 🚀 O'rnatish (lokal)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # kerakli qiymatlarni tekshiring/o'zgartiring
python main.py
```

Bot ishga tushgach, birinchi ishni admin sifatida bajaring:
1. Botga `/admin` yozing
2. "🔄 Xizmatlarni yangilash" tugmasini bosing — bot bir martalik tasdiqlash kodini ko'rsatadi, 
   shuni yozib yuborgandan keyingina haqiqiy sinxronlash boshlanadi (tasodifiy bosilib ketishning oldini olish uchun). 
   Bu **avtomatik ravishda** har bir xizmatni API kategoriyasi nomi bilan katalogga ham joylashtiradi, shunda buyurtma menyu darhol ishlay boshlaydi
3. "🗂 Katalog (buyurtma menyu)" bo'limiga kirib, kerak bo'lsa bo'limlarni qayta nomlang, guruhlang, ichma-ich joylashtiring (masalan Telegram → Tekin nakrutka → Reaksiyalar) — bu bosqichda hech narsani qo'lda qaytadan qo'shish shart emas, faqat mavjudlarini tashkil qilasiz
4. "💳 To'lov kartalari" bo'limidan kamida bitta karta qo'shing (foydalanuvchilar shundan tanlaydi)
5. "⚙️ Sozlamalar" bo'limida kerak bo'lsa kurs/ustama/referal bonus/Star narxini sozlang
6. Kerak bo'lsa "📢 Majburiy obuna kanallar" bo'limidan kanal qo'shing (bot o'sha kanalda admin bo'lishi shart — kanaldan xabar forward qilib yoki @username/ID yuborib qo'shiladi)

> ⭐️ **Stars orqali to'lov** Telegram'ning o'z native to'lov tizimidan (`currency: XTR`) foydalanadi — 
> bot tomonidan qo'shimcha sozlash talab qilinmaydi, faqat botingiz BotFather orqali to'lovlarni 
> qabul qilishga ruxsat berilgan bo'lishi kerak (odatda standart yoqilgan bo'ladi).

## ☁️ Render.com'ga deploy qilish

1. Ushbu papkani GitHub repo'siga yuklang
2. Render.com'da **New → Web Service** yarating, repo'ni ulang
3. Sozlamalar:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Environment Variables:** `.env.example` dagi barcha qiymatlarni qo'shing
     (ayniqsa `BOT_TOKEN`ni environment variable orqali berish tavsiya etiladi, kodda hardcode qilinmasin)
   - Loyihada `runtime.txt` fayli bor (`python-3.11.9`) — bu Render'ning standart eng yangi Python
     versiyasi (masalan 3.14) bilan `pydantic-core` kabi paketlarni manbadan (Rust/`maturin` orqali)
     compile qilishga urinib, `Read-only file system` xatosi bilan yiqilishining oldini oladi.
     Agar baribir shu xatolik chiqsa: Render dashboard → **Environment** → `PYTHON_VERSION` = `3.11.9`
     qo'shib, **Manual Deploy → Clear build cache & deploy** qiling.
4. Deploy bo'lgach, Render avtomatik `PORT` beradi — kod uni health-check uchun ishlatadi,
   shuning uchun bot "sleep" bo'lib qolmaydi (agar Free tarif tanlangan bo'lsa, UptimeRobot
   kabi xizmat bilan `/health` manzilini har 5 daqiqada ping qilib turish tavsiya etiladi).

> ⚠️ Ma'lumotlar bazasi SQLite fayl sifatida saqlanadi. Render'ning bepul tarifida disk
> doimiy emas — agar redeploy bo'lsa, baza tozalanishi mumkin. Uzoq muddatli loyiha uchun
> Render'da **Persistent Disk** ulashni yoki PostgreSQL'ga o'tishni tavsiya qilamiz.

## 📁 Fayl tuzilishi

```
config.py          — sozlamalar (token, API key va h.k.)
database.py         — aiosqlite bilan barcha DB funksiyalar
smm_api.py           — SMM panel API klienti
keyboards.py         — barcha reply/inline klaviaturalar
states.py            — FSM holatlari
middlewares.py        — majburiy obuna middleware
utils.py              — yordamchi funksiyalar
main.py               — bot ishga tushirish nuqtasi
handlers/user.py        — start, telefon, balans, referal, qo'llanma, murojaat
handlers/order.py        — buyurtma berish oqimi
handlers/balance.py       — hisob to'ldirish oqimi
handlers/admin.py         — to'liq admin panel
```

## 🔐 Xavfsizlik eslatmasi

`config.py` ichida token va API kalit standart qiymat sifatida yozilgan (qulaylik uchun),
lekin **production**da bularni albatta environment variable orqali bering va `config.py`dagi
qiymatlarni reponi public qilishdan oldin olib tashlang.
