# AI Scientist

حلقة قرار تحاكي منهجية البحث العلمي: توليد فرضيات، اختبارها، تحديث الاحتمالات
باستخدام بايز، ثم اقتراح الإجراء الأفضل.

## التثبيت

```bash
python -m pip install .
```

## الأوامر

```bash
three-ai scientist domains
three-ai scientist run "How can we improve checkout conversion?"
three-ai scientist run "How do we reduce churn?" \
  --domain retention --rounds 6 --seed 7 --threshold 0.9
three-ai scientist run "How do we cut latency?" --format json
three-ai scientist run "How do we improve reliability?" --out reports/reliability.md
```

### الخيارات

| الخيار | الوصف |
|---|---|
| `--n N` | عدد الفرضيات، الافتراضي 4 |
| `--rounds N` | أقصى عدد جولات، الافتراضي 8 |
| `--seed N` | بذرة عشوائية للحتمية |
| `--sigma F` | ضوضاء المشاهدة |
| `--domain NAME` | فرض المجال بدل استنتاجه |
| `--threshold P` | عتبة التقارب في `(0, 1]` |
| `--format {markdown,json}` | صيغة الخرج |
| `--out PATH` | كتابة التقرير إلى ملف |

## المجالات

- `conversion`: التحويل والمبيعات والاشتراك.
- `retention`: الاحتفاظ والعودة والانسحاب.
- `performance`: الأداء والزمن واستجابة الموقع.
- `reliability`: الموثوقية والتوفر والأعطال.
- `satisfaction`: الرضا والدعم وتجربة المستخدم.

## المنهجية

1. كل فرضية تتنبأ بقيمة `claim` عند اختبارها، وبقيمة `0.0` عند عدم اختبارها.
2. يتم توليد مشاهدة من توزيع Gaussian حول التنبؤ، مع ضوضاء `sigma`.
3. يتم تحديث الاحتمالات باستخدام بايز.
4. تُختبر كل فرضية مرة واحدة، ثم تُختبر الفرضية الأعلى احتمالًا حتى الوصول إلى
   عتبة التقارب.

> هذه محاكاة تعليمية وليست تجربة سببية حقيقية. قيم `claim` افتراضية قابلة
> للتعديل، والنتائج لا تُغني عن قياس أثر فعلي في الإنتاج.

## الاستخدام من Python

```python
from three_ai_suite.scientist import render_markdown, run_loop

result = run_loop(
    "How do we reduce churn?",
    n_hypotheses=4,
    rounds=8,
    seed=7,
    domain="retention",
)
print(render_markdown(result))
```

`run_loop` حتمية عند تثبيت `seed`، وتعيد كائن `Result` يحتوي الفرضيات
والجولات والاحتمالات والتوصية النهائية.
