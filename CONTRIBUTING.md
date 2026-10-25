# المساهمة

شكرًا لاهتمامك بالمساهمة في Three AI Suite.

## بيئة التطوير

```bash
git clone https://github.com/m16054497-a11y/three-ai-projects.git
cd three-ai-projects
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## قبل إرسال التغيير

```bash
make check
```

يجب أن ينجح:

- `ruff check src tests`
- `ruff format --check src tests`
- `python -m unittest discover -s tests -t .`

## قواعد الكود

- Python 3.10+ مع `from __future__ import annotations`.
- اتبع تنسيق Ruff وإعدادات `pyproject.toml`.
- أضف اختبارًا لكل سلوك جديد أو إصلاح خطأ.
- لا تضف أسرارًا أو مفاتيح API أو بيانات شخصية إلى المستودع.
- حافظ على المشاريع الثلاثة مستقلة؛ لا تجعل Researcher أو Scientist يعتمدان
  على FastAPI.

## رسائل الالتزام

استخدم رسائل قصيرة وواضحة، مثل:

```text
Add game export command
Fix duplicate corpus validation
Document Windows installation
```

## الإصدارات

- حدّث `version` في `pyproject.toml` و`src/three_ai_suite/__init__.py`.
- أضف مدخلًا في `CHANGELOG.md`.
- شغّل `make package`.
- أنشئ وسمًا `vX.Y.Z` وأرفق ملف ZIP في GitHub Releases.
