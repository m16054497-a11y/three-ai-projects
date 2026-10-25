# Three AI Suite

حزمة من ثلاثة مشاريع برمجية مستقلة، جاهزة للتشغيل والنشر والتوزيع، مبنية على
المشاريع الثلاثة الموجودة في ملف `Three.PDF` مع إعادة كتابة كاملة للكود
وإصلاح الأخطاء وإضافة الاختبارات والتوثيق وحزمة التوزيع.

- **AI Researcher**: أداة سطر أوامر للبحث والتلخيص في مكتبة مستندات محلية.
- **AI Scientist**: حلقة فرضيات وتجارب محاكاة مع تحديث بايزي وتوصية نهائية.
- **AI Game Developer**: خدمة FastAPI لتوليد لعبة Dungeon Crawler قابلة للعب
  وتصديرها كملف HTML واحد يعمل دون إنترنت.

الإصدار: `1.0.0`  
الترخيص: MIT  
Python: `3.10+`

---

## المحتويات

```text
three-ai-suite/
├── ai_researcher.py          # المشروع 1: CLI بدون اعتماديات خارجية
├── ai_scientist.py           # المشروع 2: CLI بدون اعتماديات خارجية
├── ai_game_developer.py      # المشروع 3: FastAPI + تصدير HTML مستقل
├── examples/
│   └── sample_corpus.json    # مثال لمكتبة مستندات مخصصة
├── tests/                    # 45 اختبارًا آليًا
├── requirements.txt          # اعتماديات مشروع اللعبة
├── requirements-dev.txt      # اعتماديات التطوير والاختبار
├── pyproject.toml            # حزمة قابلة للتثبيت + إعدادات Ruff
├── Makefile                  # أوامر التشغيل والاختبار والتغليف
├── LICENSE
└── README.md
```

---

## التثبيت السريع

المشروعان 1 و2 يعملان مباشرة دون تثبيت أي مكتبة:

```bash
python3 ai_researcher.py topics
python3 ai_scientist.py domains
```

لتشغيل المشروع الثالث والاختبارات، يُفضّل إنشاء بيئة افتراضية:

```bash
cd three-ai-suite
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make test
```

> ملاحظة توافق: المشروع مختبر مع `fastapi 0.162` و`starlette 1.10`.
> إذا كانت لديك نسخة قديمة من FastAPI، فإن `pip install -r requirements.txt`
> سيحدّثها إلى نسخة متوافقة.

---

## 1. AI Researcher

أداة بحث واسترجاع وتلخيص تعمل بالكامل من سطر الأوامر. لا تحتاج إلى Internet أو
مكتبات خارجية.

### الميزات

- مكتبة مدمجة من 10 مستندات حول موضوعات AI.
- تحميل مكتبة مخصصة من JSON.
- ترتيب نتائج البحث بأوزان مختلفة: العنوان 4، الوسوم 2، المحتوى 1، مع مكافأة
  للعبارة المطابقة في العنوان أو المحتوى.
- تلخيص استخلاصي مع المصادر والأسئلة المفتوحة.
- مخرجات نصية أو JSON قابلة للكتابة إلى ملف.

### أمثلة

```bash
# عرض كل المستندات
python3 ai_researcher.py topics

# بحث
python3 ai_researcher.py search "retrieval augmented generation"

# تحديد عدد النتائج
python3 ai_researcher.py search "agents" --top 2

# تلخيص بصيغة JSON
python3 ai_researcher.py summarize "efficient fine tuning" --json

# استخدام مكتبة مخصصة
python3 ai_researcher.py --corpus examples/sample_corpus.json topics
python3 ai_researcher.py --corpus examples/sample_corpus.json search "rag"

# كتابة التقرير إلى ملف
python3 ai_researcher.py summarize "evaluation" --out reports/evaluation.md
```

### صيغة المكتبة المخصصة

يُقبل شكلان: كائن يحتوي مفتاح `documents`، أو مصفوفة مباشرة.

```json
{
  "documents": [
    {
      "id": "d1",
      "title": "Document title",
      "tags": ["ai", "retrieval"],
      "content": "A paragraph of searchable text."
    }
  ]
}
```

يتم التحقق من الحقول، ورفض المعرّفات المكررة، وإظهار رسالة خطأ واضحة عند وجود
ملف غير صالح.

### رموز الخروج

- `0`: نجاح، بما في ذلك البحث الذي لا يُرجع نتائج.
- `2`: خطأ في الاستخدام أو في ملف المكتبة.

---

## 2. AI Scientist

حلقة قرار تحاكي منهجية البحث العلمي: توليد فرضيات، اختبارها، تحديث
الاحتمالات، ثم اقتراح الإجراء الأفضل.

### الميزات

- خمسة مجالات: conversion, retention, performance, reliability, satisfaction.
- استنتاج المجال تلقائيًا من نص السؤال، أو فرضه يدويًا.
- تحديث بايزي مستقر عدديًا باستخدام log-likelihood.
- حلقة اختبار حتمية بالاعتماد على `seed`.
- تقرير Markdown أو JSON مع سجل كامل للجولات.
- إمكانية حفظ التقرير في ملف.

### أمثلة

```bash
# عرض المجالات
python3 ai_scientist.py domains

# تشغيل كامل
python3 ai_scientist.py run "How can we improve checkout conversion?"

# تحديد المجال والمعاملات
python3 ai_scientist.py run "How do we reduce churn?" \
  --domain retention --rounds 6 --seed 7 --threshold 0.9

# مخرجات JSON
python3 ai_scientist.py run "How do we cut latency?" --format json

# حفظ التقرير
python3 ai_scientist.py run "How do we improve reliability?" --out reports/reliability.md
```

### المنهجية

1. كل فرضية تتنبأ بقيمة `claim` عند اختبارها، وبقيمة `0.0` عند عدم اختبارها.
2. يتم توليد مشاهدة من توزيع Gaussian حول التنبؤ، مع ضوضاء `sigma`.
3. يتم تحديث الاحتمالات باستخدام بايز.
4. تُختبر كل فرضية مرة واحدة، ثم تُختبر الفرضية الأعلى احتمالًا حتى الوصول إلى
   عتبة التقارب.

> هذه محاكاة تعليمية وليست تجربة سببية حقيقية. قيم `claim` افتراضية قابلة
> للتعديل، والنتائج لا تُغني عن قياس أثر فعلي في الإنتاج.

---

## 3. AI Game Developer

خدمة FastAPI تولّد لعبة Dungeon Crawler حتمية من `seed`، وتصدّرها كملف HTML
واحد مستقل يعمل في المتصفح دون خادم أو Internet.

### الميزات

- ثلاثة مستويات متصلة فعليًا (غرف + ممرات) لكل لعبة.
- أربعة themes: dungeon, space, forest, cyberpunk.
- قتال وجمع عناصر وأبواب انتقال بين المستويات.
- حالة لعبة محفوظة في الذاكرة مع قفل thread-safe.
- تصدير HTML مستقل يحتوي على المحرك كاملًا بلغة JavaScript.
- واجهة API موثقة تلقائيًا عبر Swagger UI.

### التشغيل

```bash
pip install -r requirements.txt
uvicorn ai_game_developer:app --reload
# أو
make run-game
```

- التوثيق التفاعلي: <http://127.0.0.1:8000/docs>
- فحص الصحة: <http://127.0.0.1:8000/health>

### واجهة API

| الطريقة | المسار | الوصف |
|---|---|---|
| GET | `/` | معلومات الخدمة |
| GET | `/health` | الحالة وعدد الألعاب النشطة |
| GET | `/themes` | الثيمات وإحصاءاتها |
| POST | `/games` | إنشاء لعبة جديدة |
| GET | `/games/{id}` | حالة اللعبة |
| POST | `/games/{id}/move` | تنفيذ حركة |
| DELETE | `/games/{id}` | حذف اللعبة |
| GET | `/games/{id}/export` | تنزيل ملف HTML قابل للعب |
| GET | `/games/{id}/export?download=false` | عرض HTML مباشرة |

### إنشاء لعبة وتصديرها

```bash
curl -s -X POST http://127.0.0.1:8000/games \
  -H 'Content-Type: application/json' \
  -d '{"seed": 42, "theme": "dungeon", "width": 20, "height": 12}'

# استبدل <GAME_ID> بالمعرّف الناتج
curl -OJ http://127.0.0.1:8000/games/<GAME_ID>/export
```

أو باستخدام Python:

```python
from ai_game_developer import create_game, render_export_html

state = create_game(seed=42, theme_id="space")
html = render_export_html(state)
with open("space-game.html", "w", encoding="utf-8") as handle:
    handle.write(html)
```

### التحكم داخل ملف HTML

- `WASD` أو الأسهم للحركة.
- اصطدام بالعدو = قتال تلقائي.
- العناصر تمنح صحة ونقاطًا.
- الباب `X` ينقلك للمستوى التالي.
- إكمال المستويات الثلاثة = فوز.
- زر `Reset to new game` يعيد اللعبة من البداية بنفس البذرة.

### حدود النشر الحالية

هذه نسخة عرض جاهزة للتوزيع والتشغيل المحلي، وليست خدمة إنتاجية متعددة
المستخدمين. قبل النشر العام:

- استبدل تخزين الذاكرة بقاعدة بيانات أو Redis.
- أضف مصادقة وحدود معدل الطلبات.
- شغّل أكثر من عامل فقط بعد نقل الحالة إلى مخزن مشترك.
- راجع سياسات CORS وContent-Security-Policy حسب نطاقك.
- أضف مراقبة وتسجيلًا مركزيًا.

---

## التثبيت كحزمة

يمكن تثبيت الحزمة واستخدام أوامر مختصرة:

```bash
pip install .
ai-researcher topics
ai-scientist domains

# لعبة + أمر التشغيل
pip install '.[game]'
ai-game
```

أو تثبيت بيئة التطوير كاملة:

```bash
pip install -r requirements-dev.txt
```

---

## الاختبارات والجودة

```bash
make test
make lint
```

- 45 اختبارًا آليًا باستخدام `unittest` القياسي.
- اختبارات توليد المستويات، القتال، الجمع، الانتقال، الفوز، وواجهة API.
- اختبارات البحث، التحقق من المكتبات، التحديث البايزي، والحتمية.
- `ruff` لفحص الأسلوب والأخطاء الشائعة.

---

## التغليف والتوزيع

```bash
make package
```

ينتج ملف `dist/three-ai-suite-v1.0.0.zip` داخل المشروع، مع استبعاد ملفات
الذاكرة المؤقتة. الملفات الثلاثة الأساسية يمكن نسخها وتشغيلها منفردة:

- `ai_researcher.py`: ملف واحد، بدون اعتماديات.
- `ai_scientist.py`: ملف واحد، بدون اعتماديات.
- `ai_game_developer.py`: ملف واحد + `requirements.txt`.

---

## ما تم إصلاحه مقارنة بالنسخة الأولى في PDF

- إزالة اعتماد `click` من المشروعين 1 و2 واستبداله بـ `argparse` القياسي.
- إصلاح خطأ منطقي في القتال: اللاعب كان يقتل العدو دون أن ينتقل إلى خانته.
- استبدال توليد الخرائط العشوائي غير المضمون بمولد غرف وممرات متصل.
- استكمال تصدير اللعبة: النسخة السابقة كانت تعرض الخريطة دون منطق لعب فعلي.
- إضافة تحقق شامل من المدخلات وأخطاء واضحة بدلًا من الانهيار.
- إضافة اختبارات آلية وتوثيق وحزمة تثبيت وترخيص.
- إزالة الأسرار وعدم إضافة أي اتصالات شبكية غير ضرورية.

---

## الترخيص

MIT. راجع ملف [LICENSE](LICENSE).

Copyright (c) 2026 Adham Sabry.
