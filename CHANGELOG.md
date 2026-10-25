# Changelog

جميع التغييرات المهمة في هذا المشروع موثقة هنا. التنسيق مستوحى من
[Keep a Changelog](https://keepachangelog.com/)، والإصدارات تتبع
[Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-10-26

### Added

- حزمة قابلة للتثبيت بهيكل `src/three_ai_suite`.
- أمر موحّد `three-ai` مع أوامر فرعية للمشاريع الثلاثة.
- أوامر متوافقة: `ai-researcher`, `ai-scientist`, `ai-game`.
- أمر `three-ai game export` لإنشاء ملف HTML دون تشغيل خادم.
- مثبّتات `scripts/install.sh` و`scripts/install.ps1`.
- دليل تثبيت موسّع ودليل مستقل لكل مشروع.
- `Dockerfile` لخدمة اللعبة.
- CI على Python 3.10–3.13 مع بناء الحزمة واختبار التثبيت.
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`.

### Changed

- نقل المشاريع من ملفات في جذر المستودع إلى حزمة `src/three_ai_suite`.
- توحيد الإصدار إلى `2.0.0`.
- تحديث README ليكون نقطة بداية واضحة بدلًا من دليل ضخم.
- تحسين أوامر `Makefile` وإضافة `make install` و`make check`.

### Fixed

- أوضح رسالة عند محاولة تشغيل اللعبة دون تثبيت اعتمادياتها.
- منع تضمين `.git` والبيئات الافتراضية والذاكرة المؤقتة في حزمة التوزيع.

## [1.0.0] - 2026-10-25

### Added

- AI Researcher: بحث وتلخيص مكتبة مستندات محلية.
- AI Scientist: فرضيات وحلقة تجارب وتحديث بايزي.
- AI Game Developer: خدمة FastAPI وتصدير لعبة HTML قابلة للعب.
- 45 اختبارًا آليًا، README، LICENSE، وحزمة توزيع أولية.
