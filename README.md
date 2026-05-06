# 🔮 Churn Prediction System — n8n + FastAPI

نظام تنبؤ بانسحاب العملاء (Customer Churn) يعمل عن طريق:
- **FastAPI** — API بيستقبل الأسئلة بالإنجليزي ويرجع نتائج التنبؤ
- **n8n** — workflow بيشغّل استفسارات تلقائياً كل يوم ويبعت Report بالإيميل

---

## 📁 ملفات المشروع

```
├── api.py                    ← FastAPI server (endpoint /predict و /chat)
├── llm_chatbot.py            ← LLM feature extractor (Qwen2.5-1.5B)
├── data_utils.py             ← تحميل وفلترة بيانات العملاء
├── requirements.txt          ← Python dependencies
├── churn_model.pkl           ← ← ملف الموديل (لازم يكون موجود!)
├── cleaned_data.csv          ← ← بيانات العملاء (لازم تكون موجودة!)
└── churn_n8n_workflow.json   ← n8n workflow جاهز للاستيراد
```

> ⚠️ **تأكد** إن `churn_model.pkl` و `cleaned_data.csv` موجودين في نفس الفولدر قبل ما تشغّل الـ API.

---

## ▶️ خطوة 1 — تشغيل الـ FastAPI

### تثبيت المتطلبات
```bash
pip install -r requirements.txt
```

### تشغيل السيرفر
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

افتح المتصفح على:
- **API Docs:** http://127.0.0.1:8000/docs
- **Health check:** http://127.0.0.1:8000/

> 💡 السيرفر هياخد وقت في أول تشغيل لأنه بيحمّل موديل الـ LLM (Qwen2.5-1.5B) في الذاكرة.

### اختبار الـ API يدوياً
```bash
# اختبار /chat
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "senior citizens with fiber optic internet"}'

# اختبار /predict
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "gender": 1, "Senior_Citizen": 1, "Is_Married": 0, "Dependents": 0,
    "tenure": 5, "Phone_Service": 1, "Dual": "No",
    "Internet_Service": "Fiber optic", "Online_Security": "No",
    "Online_Backup": "No", "Device_Protection": "No", "Tech_Support": "No",
    "Streaming_TV": "No", "Streaming_Movies": "No",
    "Contract": "Month-to-month", "Paperless_Billing": 1,
    "Payment_Method": "Electronic check",
    "Monthly_Charges": 85.5, "Total_Charges": 427.5
  }'
```

---

## ▶️ خطوة 2 — إعداد n8n

### تثبيت n8n (لو مش موجود)
```bash
npm install -g n8n
```

### تشغيل n8n
```bash
n8n start
```

افتح المتصفح على: **http://localhost:5678**

---

## ▶️ خطوة 3 — استيراد الـ Workflow

1. افتح n8n على `http://localhost:5678`
2. من القائمة الجانبية اختار **Workflows**
3. اضغط **Add Workflow** ← **Import from File**
4. اختار ملف `churn_n8n_workflow.json`

---

## ▶️ خطوة 4 — إعداد الإيميل (SMTP)

### إنشاء Credentials
1. اضغط على **Settings** (أيقونة الترس في الأسفل)
2. اختار **Credentials** ← **Add Credential**
3. ابحث عن **SMTP** واختاره
4. ادخل بيانات الإيميل بتاعك:

| الحقل | مثال (Gmail) |
|-------|-------------|
| Host | smtp.gmail.com |
| Port | 465 |
| SSL | ✅ نعم |
| User | your@gmail.com |
| Password | App Password (مش الباسورد الأصلي) |

> 📌 **Gmail:** لازم تفعّل "App Passwords" من إعدادات الأمان في حسابك.

### ربط الـ Credential بالـ Workflow
1. افتح **📧 Send Email Report** node
2. في حقل **Credential** اختار الـ SMTP اللي أنشأته

---

## ▶️ خطوة 5 — تعديل الـ Config

افتح **⚙️ Config** node وعدّل:

| المتغير | القيمة |
|---------|--------|
| `apiUrl` | `http://127.0.0.1:8000` (أو IP السيرفر لو مختلف) |
| `recipientEmail` | الإيميل اللي هيستقبل الـ Report |
| `senderEmail` | إيميل المُرسِل |

---

## ▶️ خطوة 6 — تشغيل الـ Workflow

### تشغيل يدوي (للتجربة)
1. افتح الـ workflow
2. اضغط **Execute Workflow** (زرار التشغيل)
3. شوف النتائج في كل node

### تشغيل تلقائي (كل يوم)
1. اضغط على **Inactive** toggle في أعلى يمين الشاشة
2. غيّره لـ **Active**
3. الـ workflow هيشتغل تلقائياً **كل يوم من الاثنين للجمعة الساعة 8 الصبح**

---

## 🔍 الـ Queries اللي الـ Workflow بيعملها

| الـ Query | الوصف |
|-----------|-------|
| Senior citizens + Fiber > $70 | عملاء كبار السن مع إنترنت fiber وشحن شهري فوق 70 |
| Low tenure < 12 months | عملاء جدد أقل من سنة |
| High charges > $80 | عملاء بشحن شهري عالي |
| Single female + Fiber | نساء غير متزوجات مع fiber |
| All at-risk customers | كل العملاء (بدون فلتر) |

---

## ❓ Troubleshooting

| المشكلة | الحل |
|---------|------|
| API مش شغال | تأكد إن `churn_model.pkl` و `cleaned_data.csv` موجودين |
| LLM بطيء | طبيعي — Qwen2.5 على CPU بياخد 10-30 ثانية لكل query |
| n8n مش وصل للـ API | تأكد إن `apiUrl` في Config صح، وإن السيرفر شغال |
| الإيميل مش بيتبعت | تأكد من SMTP credentials وإن App Password مفعّل |
| "No customers match" | الـ query مش لاقي عملاء بالمواصفات دي |
