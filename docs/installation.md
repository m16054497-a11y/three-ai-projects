# دليل التثبيت

هذه الحزمة اسمها `three-ai-suite`، والمستودع اسمه `three-ai-projects`. الحزمة
غير منشورة على PyPI، لذلك ثبّتها من المستودع أو من ملف ZIP. لا تثبّتها بالأمر
`pip install three-ai-suite` لأنه سيبحث عنها في PyPI ولن يجدها.

## المتطلبات

- Python `3.10` أو أحدث.
- `git` عند التثبيت من المستودع.
- اتصال بالإنترنت أثناء تثبيت الاعتماديات.
- لا تحتاج إلى مفاتيح API أو قاعدة بيانات.

تحقق من إصدار Python:

```bash
python3 --version
```

## الطريقة 1: سكربت التثبيت (موصى بها)

```bash
git clone https://github.com/m16054497-a11y/three-ai-projects.git
cd three-ai-projects
./scripts/install.sh
source .venv/bin/activate
three-ai --help
```

على Windows PowerShell:

```powershell
git clone https://github.com/m16054497-a11y/three-ai-projects.git
cd three-ai-projects
.\scripts\install.ps1
.\.venv\Scripts\Activate.ps1
three-ai --help
```

السكربت:

1. يتحقق من إصدار Python.
2. ينشئ `.venv` معزولة.
3. يحدّث `pip`.
4. يثبّت الحزمة مع كل ميزات التشغيل `.[all]`.

## الطريقة 2: تثبيت يدوي

Linux / macOS:

```bash
git clone https://github.com/m16054497-a11y/three-ai-projects.git
cd three-ai-projects
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[all]'
```

Windows:

```powershell
git clone https://github.com/m16054497-a11y/three-ai-projects.git
cd three-ai-projects
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install ".[all]"
```

### تثبيت جزء واحد فقط

```bash
python -m pip install .              # Researcher + Scientist
python -m pip install '.[game]'      # Game + FastAPI
python -m pip install '.[dev]'       # كل شيء + أدوات الاختبار
```

## الطريقة 3: من GitHub مباشرة

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "three-ai-suite[all] @ git+https://github.com/m16054497-a11y/three-ai-projects.git@v2.0.0"
three-ai --help
```

استبدل `v2.0.0` بـ `main` إذا أردت أحدث نسخة غير مرتبطة بإصدار.

## الطريقة 4: من ملف ZIP

```bash
unzip three-ai-suite-v2.0.0.zip
cd three-ai-suite
./scripts/install.sh
source .venv/bin/activate
three-ai --help
```

## الطريقة 5: Docker (خدمة اللعبة فقط)

```bash
git clone https://github.com/m16054497-a11y/three-ai-projects.git
cd three-ai-projects
docker build -t three-ai-game .
docker run --rm -p 8000:8000 three-ai-game
```

افتح <http://127.0.0.1:8000/docs>. لا حاجة إلى Python محليًا.

## التحقق من التثبيت

```bash
three-ai --version
three-ai researcher topics
three-ai scientist domains
three-ai game themes
```

يجب أن يعرض الأمر الأخير الثيمات الأربعة: dungeon, space, forest, cyberpunk.

## مشاكل شائعة

### `externally-managed-environment`

يحدث عند محاولة التثبيت في Python النظام في Kali وDebian وUbuntu الحديثة.
الحل هو استخدام بيئة افتراضية:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[all]'
```

### `command not found: three-ai`

الأمر موجود داخل `.venv` فقط. فعّل البيئة أولًا:

```bash
source .venv/bin/activate
```

أو شغّل الحزمة مباشرة:

```bash
python -m three_ai_suite --help
```

### `No module named fastapi`

ثبّت ميزات اللعبة:

```bash
python -m pip install '.[game]'
```

أو أعد التثبيت الكامل:

```bash
python -m pip install '.[all]'
```

### فشل `pip` بسبب DNS أو الشبكة

هذه مشكلة شبكة وليست مشكلة في الحزمة. تحقق من الاتصال، أو استخدم مرآة pip
موثوقة:

```bash
python -m pip install '.[all]' --index-url https://pypi.org/simple
```

### `Python 3.10+ is required`

ثبّت Python أحدث، أو استخدم:

```bash
python3.12 -m venv .venv
```

### فشل تثبيت `setuptools` بسبب الشبكة

عند التثبيت من مصدر محلي وكان `setuptools` مثبتًا مسبقًا:

```bash
python -m pip install --no-build-isolation .
```

### تعارض مع نسخة FastAPI النظام

لا تخلط حزم النظام مع الحزمة. استخدم بيئة افتراضية جديدة، ثم:

```bash
python -m pip install --force-reinstall '.[all]'
```

## إلغاء التثبيت

إذا استخدمت بيئة افتراضية، احذفها فقط:

```bash
deactivate
rm -rf .venv
```

إذا ثبّت داخل بيئة أخرى:

```bash
python -m pip uninstall three-ai-suite
```
