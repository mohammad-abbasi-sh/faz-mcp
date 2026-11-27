# faz-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/faz-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای **[FAZ.NET — فرانکفورتر آلگماینه تسایتونگ](https://www.faz.net)** — یکی از بزرگ‌ترین روزنامه‌های کیفی آلمان (تأسیس ۱۹۴۹) — از طریق فیدهای RSS رسمی (فید اصلی /rss/aktuell/ با ۱۶۹ مورد، به‌علاوه ۱۱ فید بخش‌ها) و صفحات مقاله که متن کامل آن‌ها از `articleBody` در JSON-LD NewsArticle خوانده می‌شود (پاراگراف‌های `<article>` رندرشده در سرور، جایگزین است). تازه‌ترین اخبار، جست‌وجوی کلیدواژه، مقاله‌ها بر اساس بخش و بر اساس نویسنده، بخش‌های فید امروز و متن کامل مقاله. بدون کلید، بدون ورود.

> ساخته‌شده توسط محمد عباسی در چارچوب «کارخانه MCP آلمان». وابسته به FAZ نیست.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی کلاینت MCP اضافه کنید (stdio):

```json
{
  "mcpServers": {
    "faz": {
      "command": "uvx",
      "args": ["faz-mcp==0.1.0"]
    }
  }
}
```

یا به‌صورت محلی اجرا کنید: `python -m faz_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------------|
| `faz_latest` | تازه‌ترین اخبار FAZ (فید RSS رسمی اصلی، حدود ۱۶۹ مورد)، جدیدترین اول — `limit` از ۱ تا ۵۰. هر مورد عنوان، لینک مقاله، تیزر، نویسنده (dc:creator، وقتی فید آن را دارد)، بخش، نوع (article/video/podcast)، آدرس تصویر و زمان انتشار دارد |
| `faz_search_news` | جست‌وجوی اخبار FAZ با کلیدواژه (عنوان + تیزر + نویسنده) در فید RSS رسمی اصلی — `query` (مثلاً «Rente» یا «Klimaschutz»)، `limit` از ۱ تا ۵۰ |
| `faz_by_section` | جدیدترین مقاله‌های FAZ از یک فید بخش — `section`: politik، wirtschaft، sport، feuilleton، finanzen، gesellschaft، wissen، besser-leben، rhein-main، karriere-hochschule، technik-motor؛ `limit` از ۱ تا ۵۰ |
| `faz_sections` | بخش‌های فید اصلی امروز FAZ با تعداد مقاله‌های هر یک — بیشترین اول |
| `faz_by_author` | جدیدترین مقاله‌های FAZ از یک نویسنده (dc:creator فید، مثلاً «Stephan Klenner» — به‌صورت زیررشته و بدون حساسیت به بزرگی و کوچکی حروف تطبیق داده می‌شود، نام خانوادگی کافی است) — `limit` از ۱ تا ۵۰ |
| `faz_get_article` | متن کامل یک صفحه مقاله FAZ (JSON-LD NewsArticle `articleBody`، پاراگراف‌های `<article>` به‌عنوان جایگزین) — `url`: آدرس مقاله faz.net (‎/aktuell/<section>/…-<id>.html‎). عنوان، نویسنده، زمان انتشار، بخش مقاله از BreadcrumbList صفحه (مثلاً «Politik > Inland»)، متن و تعداد کلمات را برمی‌گرداند. صفحه FAZ+ با `paywalled: true` و فقط تیزر برمی‌گردد — متن کامل نیازمند اشتراک است. صفحه ویدیو با `kind: "video"` و توضیح و مدت آن برمی‌گردد. آدرس‌های فید، صفحه اصلی و لینک‌های خارجی رد می‌شوند |
| `faz_health` | بررسی دسترسی (ok / blocked / error) — یک درخواست مؤدبانه |

نمونه خروجی (`faz_latest` با `limit` برابر ۱):

```json
{"feed_title": "Aktuell - FAZ.NET", "total_results": 169, "count": 1,
 "items": [
  {"title": "Parteitag in Dresden: „Ob ich im BSW bleibe, wird sich auf dem Parteitag entscheiden“",
   "link": "https://www.faz.net/aktuell/politik/inland/bsw-parteitag-streit-ueber-zusammenarbeit-mit-afd-accg-201721261.html",
   "description": "Auf einem Bundesparteitag in Dresden berät das BSW über seinen künftigen Kurs. Über den Umgang mit der AfD ist ein heftiger Streit entbrannt.",
   "published": "2026-11-27T09:58:08+00:00", "author": "Stephan Klenner, Dresden",
   "section": "politik", "kind": "article",
   "image_url": "https://media0.faz.net/image/514207f8116a/w3000h1687x0y2/202601/43601.0.1697382717/josephine-thyret-ko.webp"},
  ...]}
```

نکته‌ها:
- سرور **فید RSS رسمی اصلی** را می‌خواند — `https://www.faz.net/rss/aktuell/` (۱۶۹ مورد، تأیید زنده در ۲۰۲۶-۱۱-۲۷) — به‌علاوه **۱۱ فید بخش‌ها** در `/rss/aktuell/<section>/` (politik با ۴۶ مورد، wirtschaft، sport، feuilleton، finanzen، gesellschaft، wissen، besser-leben، rhein-main، karriere-hochschule، technik-motor). مسیر `/rss/<section>/` (بدون /aktuell/) همگی ۴۰۴ برمی‌گردانند و `/rss/aktuell/kultur/` هم ۴۰۴ است — فقط همین ۱۲ فید وجود دارند. فید اصلی و فیدهای بخش‌ها هم‌پوشانی زیادی دارند؛ موارد بر اساس لینک یکتا حذف تکراری می‌شوند.
- **برچسب موضوعی وجود ندارد:** فیدها مقدار `<category>` ندارند، پس ابزار موضوعی نیست — مقاله‌ها به‌جای آن بر اساس بخش گروه‌بندی می‌شوند (از مسیر لینک مقاله، مثلاً `/aktuell/politik/…`). `faz_by_section` فید همان بخش را می‌خواند.
- فید اصلی برای حدود ۸۳٪ موارد `dc:creator` (۱۴۱ از ۱۶۹) و برای هر مورد یک تصویر `media:content` (webp) دارد. نویسنده واقعی هر مقاله را `faz_get_article` از نویسنده JSON-LD گزارش می‌کند (مثلاً «Stephan Klenner»). زمان‌های `pubDate` فید به وقت GMT است.
- فید اصلی انواع مختلف را مخلوط می‌کند: ۱۶۳ مقاله، ۳ ویدیو (`/video/…`) و ۳ پادکست (`/podcasts/…`) — با `kind` مشخص‌شده برمی‌گردند و `faz_latest` هرگز آن‌ها را نمی‌خواند. همچنین ۴ مقاله FAZ+ (`/premium/…`) دارد؛ وضعیت پی‌وال آن‌ها فقط از صفحه مقاله معلوم می‌شود.
- لینک‌های فید با `-<id>.html` تمام می‌شوند و با ۳۰۱ به آدرس یکتا هدایت می‌شوند (به‌صورت خودکار دنبال می‌شود).
- **متن مقاله، صادقانه:** صفحات FAZ واقعاً `articleBody` در JSON-LD دارند (نمونه: ۴٬۹۷۱ کاراکتر / ۶۴۲ کلمه در یک مقاله رایگان). متن نرمال‌سازی فاصله می‌شود؛ پاراگراف‌های `<article>` جایگزین‌اند وقتی `articleBody` نباشد (عنوان «Zusammenfassung»، پاراگراف زیرنویس+تیزر، زیرنویس عکس‌ها «Foto:»، تبلیغ اشتراک «Zugang zu allen FAZ+ Beiträgen»، پانویس «Die F.A.Z. berichtet frei…» و تکه‌های نام نویسنده فیلتر می‌شوند).
- **پی‌وال، صادقانه (تأیید زنده):** یک مقاله نظری FAZ+ دارای `isAccessibleForFree: false` و بدون `articleBody` است — `faz_get_article` با `paywalled: true` و فقط تیزر برمی‌گردد (۳۱ کلمه در نمونه)، هرگز متن ساختگی. `<article>` سمت سرور در صفحه پولی فقط یک تیزر ناقص به‌علاوه تبلیغ اشتراک دارد — هرگز به‌عنوان متن استفاده نمی‌شود.
- **صفحه‌های ویدیو، صادقانه:** صفحه `/video/…` یک `VideoObject` در JSON-LD دارد و `NewsArticle` ندارد — `faz_get_article` با `kind: "video"` و توضیح به‌عنوان متن و مدت آن برمی‌گردد، هرگز متن ساختگی.
- داده: فیدهای RSS عمومی و صفحات مقاله FAZ.NET — بدون کلید، بدون ورود، فقط‌خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — آفلاین، دو فید واقعی ضبط‌شده (اصلی + بخش politik) به‌علاوه دو صفحه مقاله واقعی (مقاله رایگان با `articleBody` واقعی در JSON-LD، و یک صفحه واقعی پولی FAZ+) را تجزیه می‌کند؛ جایگزین SSR و شاخه ویدیو از صفحات کوچک مصنوعی استفاده می‌کنند
- `tests/test_live.py` — درخواست‌های زنده محتاطانه به faz.net

تست‌ها: ۳۴ از ۳۴ سبز (۲۷ آفلاین + ۷ زنده، ۲۰۲۶-۱۱-۲۷).

## مجوز

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — رایگان برای استفاده شخصی و غیرتجاری؛ استفاده تجاری نیازمند مجوز جداگانه است (به LICENSE مراجعه کنید).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
