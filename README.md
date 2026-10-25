# Three AI Suite

[![CI](https://github.com/m16054497-a11y/three-ai-projects/actions/workflows/ci.yml/badge.svg)](https://github.com/m16054497-a11y/three-ai-projects/actions/workflows/ci.yml)

ثلاثة مشاريع AI مستقلة، مجمّعة في حزمة واحدة قابلة للتثبيت وأوامر موحّدة. لا
تحتاج المشاريع إلى مفاتيح API أو اتصال بالإنترنت، ويمكن تشغيلها محليًا على
Linux وmacOS وWindows.

| المشروع | الأمر | الوظيفة | الاعتماديات |
|---|---|---|---|
| AI Researcher | `three-ai researcher` | بحث وتلخيص مكتبة مستندات محلية | لا شيء |
| AI Scientist | `three-ai scientist` | فرضيات وحلقة تجارب وتحديث بايزي | لا شيء |
| AI Game Developer | `three-ai game` | توليد لعبة HTML قابلة للعب وخدمة FastAPI | `[game]` |

الإصدار: `2.0.0` · Python: `3.10+` · الترخيص: MIT

---

## التثبيت السريع

الطريقة الموصى بها هي استخدام سكربت التثبيت، لأنه ينشئ بيئة افتراضية معزولة
ويثبّت كل ما تحتاجه:

```bash
git clone https://github.com/m16054497-a11y/three-ai-projects.git
cd three-ai-projects
./scripts/install.sh
source .venv/bin/activate
three-ai --help
```

على Windows (PowerShell):

```powershell
git clone https://github.com/m16054497-a11y/three-ai-projects.git
cd three-ai-projects
.\scripts\install.ps1
.\.venv\Scripts\Activate.ps1
three-ai --help
```

### التثبيت اليدوي

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[all]'
```

- لتثبيت المشروعين 1 و2 فقط: `python -m pip install .`
- لتثبيت مشروع اللعبة فقط: `python -m pip install '.[game]'`
- لتثبيت بيئة التطوير والاختبارات: `python -m pip install '.[dev]'`

> **مهم:** لا تستخدم `pip install` مباشرة على Python النظام في Kali أو
> Debian/Ubuntu الحديثة، لأنه سيرفض التثبيت بسبب `externally-managed-environment`.
> استخدم البيئة الافتراضية أو `scripts/install.sh`.

### من GitHub مباشرة دون استنساخ

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "three-ai-suite[all] @ git+https://github.com/m16054497-a11y/three-ai-projects.git@v2.0.0"
three-ai --help
```

### من ملف ZIP

نزّل الحزمة من صفحة الإصدارات، ثم:

```bash
unzip three-ai-suite-v2.0.0.zip
cd three-ai-suite
./scripts/install.sh
source .venv/bin/activate
three-ai --help
```

---

## البدء السريع

```bash
# 1. AI Researcher
three-ai researcher topics
three-ai researcher search "retrieval augmented generation"
three-ai researcher summarize "efficient fine tuning" --json

# 2. AI Scientist
three-ai scientist domains
three-ai scientist run "How do we reduce churn?" --seed 7

# 3. AI Game Developer
three-ai game themes
three-ai game export --seed 42 --theme dungeon --output dungeon.html
three-ai game serve
```

افتح `dungeon.html` في أي متصفح للعب دون خادم أو إنترنت. وعند تشغيل
`three-ai game serve`، افتح <http://127.0.0.1:8000/docs> لواجهة API التفاعلية.

يمكن أيضًا تشغيل الحزمة دون تثبيت الأوامر:

```bash
python -m three_ai_suite --help
python -m three_ai_suite researcher topics
python -m three_ai_suite scientist domains
python -m three_ai_suite game export --seed 7 --theme space -o space.html
```

---

## Docker

خدمة اللعبة جاهزة للتشغيل في حاوية:

```bash
docker build -t three-ai-game .
docker run --rm -p 8000:8000 three-ai-game
```

ثم افتح <http://127.0.0.1:8000/docs>. الصورة لا تحتاج إلى تثبيت Python محليًا.

---

## هيكل المستودع

```text
three-ai-projects/
├── src/three_ai_suite/        # الحزمة القابلة للتثبيت
│   ├── cli.py                 # الأوامر الموحّدة
│   ├── researcher.py          # المشروع 1
│   ├── scientist.py           # المشروع 2
│   └── game.py                # المشروع 3
├── docs/                      # دليل التثبيت ودليل كل مشروع
├── examples/                  # أمثلة مكتبة المستندات
├── scripts/                   # مثبّتات Linux/macOS وWindows
├── tests/                     # 53 اختبارًا آليًا
├── Dockerfile                 # خدمة اللعبة
├── pyproject.toml             # بيانات الحزمة والأوامر
├── Makefile                   # أوامر التطوير والتغليف
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

---

## المشاريع

### 1. AI Researcher

أداة سطر أوامر للبحث في مكتبة مستندات محلية، مع ترتيب النتائج وتلخيص استخلاصي
ومصادر وأسئلة مفتوحة. تعمل دون Internet أو مكتبات خارجية، وتقبل مكتبة مخصصة
بصيغة JSON.

- الدليل الكامل: [`docs/ai-researcher.md`](docs/ai-researcher.md)
- مثال مكتبة: [`examples/sample_corpus.json`](examples/sample_corpus.json)

```bash
three-ai researcher --corpus examples/sample_corpus.json search "rag"
```

### 2. AI Scientist

حلقة قرار تحاكي منهجية البحث العلمي: توليد فرضيات، اختبارها، تحديث الاحتمالات
باستخدام بايز، ثم توصية بالإجراء الأفضل. النتائج حتمية عند تثبيت `seed`.

- الدليل الكامل: [`docs/ai-scientist.md`](docs/ai-scientist.md)

```bash
three-ai scientist run "How can we improve checkout conversion?" \
  --domain conversion --rounds 6 --seed 7 --format json
```

> هذه محاكاة تعليمية وليست تجربة سببية حقيقية.

### 3. AI Game Developer

خدمة FastAPI تولّد لعبة Dungeon Crawler حتمية من `seed`، مع ثلاثة مستويات
متصلة وقتال وجمع عناصر وأبواب انتقال. يمكن تصدير كل لعبة كملف HTML واحد يعمل
دون خادم أو Internet.

- الدليل الكامل: [`docs/ai-game-developer.md`](docs/ai-game-developer.md)

```bash
three-ai game export --seed 42 --theme cyberpunk -o cyberpunk.html
three-ai game serve --host 127.0.0.1 --port 8000
```

---

## التطوير والاختبار

```bash
make install     # إنشاء .venv وتثبيت [dev]
make test        # 53 اختبارًا
make lint        # Ruff
make check       # lint + tests
make format      # تنسيق المصادر
```

لتثبيت بيئة التطوير كاملة:

```bash
python -m pip install -e '.[dev]'
```

الاختبارات تغطي البحث والتحقق من المكتبات، التحديث البايزي والحتمية، توليد
المستويات والقتال والانتقال والفوز، وواجهة API.

---

## التغليف والإصدارات

```bash
make package
```

ينتج `dist/three-ai-suite-v2.0.0.zip` مع استبعاد Git والبيئات الافتراضية
والذاكرة المؤقتة. سجل التغييرات في [`CHANGELOG.md`](CHANGELOG.md).

---

## استكشاف الأخطاء

| المشكلة | الحل |
|---|---|
| `externally-managed-environment` | استخدم `./scripts/install.sh` أو بيئة افتراضية |
| `command not found: three-ai` | فعّل البيئة: `source .venv/bin/activate` |
| `No module named fastapi` | ثبّت extras اللعبة: `python -m pip install '.[game]'` |
| `Python 3.10+ is required` | حدّث Python أو استخدم `python3.12` |
| فشل pip بسبب DNS | تحقق من الشبكة، أو استخدم `--index-url` لمصدر pip موثوق |
| لعبة لا تعمل في المتصفح | استخدم متصفحًا حديثًا وافتح ملف HTML الناتج مباشرة |

دليل تثبيت موسّع: [`docs/installation.md`](docs/installation.md).

---

## الترخيص

MIT. راجع [`LICENSE`](LICENSE). حقوق النشر (c) 2026 Adham Sabry.
