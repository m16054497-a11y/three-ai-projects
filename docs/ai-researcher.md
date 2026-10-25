# AI Researcher

أداة سطر أوامر للبحث والترتيب والتلخيص في مكتبة مستندات محلية. لا تحتاج إلى
Internet أو مكتبات خارجية.

## التثبيت

```bash
python -m pip install .
```

هذا يثبّت المشروعين 1 و2. إذا ثبّت الحزمة كاملة، استخدم `three-ai researcher`
مباشرة.

## الأوامر

```bash
three-ai researcher topics
three-ai researcher search "retrieval augmented generation"
three-ai researcher search "agents" --top 2
three-ai researcher summarize "efficient fine tuning" --json
three-ai researcher summarize "evaluation" --out reports/evaluation.md
```

### الخيارات العامة

| الخيار | الوصف |
|---|---|
| `--corpus PATH` | تحميل مكتبة JSON مخصصة بدل المكتبة المدمجة |
| `--version` | عرض الإصدار |
| `--help` | عرض المساعدة |

### أوامر فرعية

| الأمر | الوصف |
|---|---|
| `topics` | عرض كل المستندات في المكتبة |
| `search QUERY` | البحث وإظهار أفضل النتائج |
| `summarize QUERY` | إنشاء ملخص مع المصادر والأسئلة المفتوحة |

خيارات `search` و`summarize`:

| الخيار | الوصف |
|---|---|
| `--top N`, `-k N` | أقصى عدد نتائج، الافتراضي 3 |
| `--json` | إخراج JSON قابل للقراءة آليًا |
| `--out PATH` | كتابة الناتج إلى ملف |

## صيغة المكتبة

يقبل البرنامج شكلين: كائن يحتوي مفتاح `documents`، أو مصفوفة مباشرة.

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

## أمثلة

```bash
# المكتبة المدمجة
three-ai researcher topics

# مكتبة مخصصة
three-ai researcher --corpus examples/sample_corpus.json topics
three-ai researcher --corpus examples/sample_corpus.json search "rag"

# حفظ تقرير
three-ai researcher summarize "evaluation" --out reports/evaluation.md
```

## الاستخدام من Python

```python
from three_ai_suite.researcher import load_corpus, search, summarize

documents = load_corpus("examples/sample_corpus.json")
hits = search("retrieval augmented generation", documents, top_k=3)
result = summarize("efficient fine tuning", documents, top_k=3)

print(hits[0].document.title, hits[0].score)
print(result.summary)
```

## رموز الخروج

- `0`: نجاح، بما في ذلك البحث الذي لا يُرجع نتائج.
- `2`: خطأ في الاستخدام أو في ملف المكتبة.
