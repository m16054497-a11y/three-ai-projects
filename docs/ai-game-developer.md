# AI Game Developer

خدمة FastAPI تولّد لعبة Dungeon Crawler حتمية من `seed`، وتصدّرها كملف HTML
واحد مستقل يعمل في المتصفح دون خادم أو Internet.

## التثبيت

```bash
python -m pip install '.[game]'
```

أو ثبّت كل شيء:

```bash
python -m pip install '.[all]'
```

## الأوامر

```bash
three-ai game themes
three-ai game export --seed 42 --theme dungeon --output dungeon.html
three-ai game serve --host 127.0.0.1 --port 8000
```

### `game export`

| الخيار | الوصف |
|---|---|
| `--seed N` | بذرة اللعبة، الافتراضي 42 |
| `--theme NAME` | dungeon أو space أو forest أو cyberpunk |
| `--width N` | عرض الخريطة، من 9 إلى 60 |
| `--height N` | ارتفاع الخريطة، من 7 إلى 40 |
| `--output PATH`, `-o` | مسار ملف HTML، الافتراضي `<theme>-<seed>.html` |

### `game serve`

| الخيار | الوصف |
|---|---|
| `--host ADDR` | عنوان الاستماع، الافتراضي `127.0.0.1` |
| `--port N` | المنفذ، الافتراضي 8000 |
| `--reload` | إعادة التشغيل التلقائي أثناء التطوير |

بعد التشغيل:

- التوثيق التفاعلي: <http://127.0.0.1:8000/docs>
- فحص الصحة: <http://127.0.0.1:8000/health>
- قائمة الثيمات: <http://127.0.0.1:8000/themes>

## واجهة API

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

### إنشاء لعبة وتصديرها عبر HTTP

```bash
curl -s -X POST http://127.0.0.1:8000/games \
  -H 'Content-Type: application/json' \
  -d '{"seed": 42, "theme": "dungeon", "width": 20, "height": 12}'

# استبدل <GAME_ID> بالمعرّف الناتج
curl -OJ http://127.0.0.1:8000/games/<GAME_ID>/export
```

### تنفيذ حركة

```bash
curl -s -X POST http://127.0.0.1:8000/games/<GAME_ID>/move \
  -H 'Content-Type: application/json' \
  -d '{"direction": "e"}'
```

الاتجاهات: `n`, `s`, `e`, `w`.

## التحكم داخل ملف HTML

- `WASD` أو الأسهم للحركة.
- اصطدام بالعدو = قتال تلقائي.
- العناصر تمنح صحة ونقاطًا.
- الباب `X` ينقلك للمستوى التالي.
- إكمال المستويات الثلاثة = فوز.
- زر `Reset to new game` يعيد اللعبة من البداية بنفس البذرة.

## الاستخدام من Python

```python
from three_ai_suite.game import create_game, render_export_html

state = create_game(seed=42, theme_id="space")
html = render_export_html(state)

with open("space-game.html", "w", encoding="utf-8") as handle:
    handle.write(html)
```

## Docker

```bash
docker build -t three-ai-game .
docker run --rm -p 8000:8000 three-ai-game
```

## حدود النشر الحالية

هذه نسخة عرض جاهزة للتوزيع والتشغيل المحلي، وليست خدمة إنتاجية متعددة
المستخدمين. قبل النشر العام:

- استبدل تخزين الذاكرة بقاعدة بيانات أو Redis.
- أضف مصادقة وحدود معدل الطلبات.
- شغّل أكثر من عامل فقط بعد نقل الحالة إلى مخزن مشترك.
- راجع سياسات CORS وContent-Security-Policy حسب نطاقك.
- أضف مراقبة وتسجيلًا مركزيًا.
