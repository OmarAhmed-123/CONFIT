# CONFIT — هيكل المستودع ومسار الدمج (Architecture)

هذا المستند يربط **المخطط الاستثماري** (خدمات، بيانات، نشر) بما هو موجود فعلياً في الكود، ويوضح **لماذا يوجد ملفان للتطبيق** (`main.py` و `app.py`) وكيف تُوحَّد نقطة الدخول لاحقاً.

---

## 1. نقطة الدخول المعتمدة (Canonical entrypoint)

| العنصر | القيمة |
|--------|--------|
| **أمر التشغيل في الإنتاج** | `uvicorn main:app` |
| **الملف** | `backend/main.py` |
| **الدليل** | `backend/Dockerfile` (سطر `CMD`)، و`Dockerfile.ai` / `Dockerfile.gpu` |

تشغيل `python backend/app.py` أو `uvicorn app:app` يطلق **تطبيقاً بديلاً** (طبقة مختلفة، مسارات مختلفة) — **ليس** ما تنشره الصورة الافتراضية.

---

## 2. لماذا يوجد `main.py` و `app.py`؟

هما **تطبيقا FastAPI منفصلان** وليسا مجرد نسختين:

| الجانب | `main.py` (الافتراضي للنشر) | `app.py` (بديل / refactor) |
|--------|-----------------------------|-----------------------------|
| **طبقة البيانات** | تهيئة عبر `database.session`، بذور sync (`seed_*`) | `infrastructure.database` غير متزامن (async)، Redis، Elasticsearch في الـ lifespan |
| **المسارات** | تضمين واسع من `routers/*` + `api/style_dna` وغيرها **بدون** بادئة موحّدة `/api/v1` | وحدات `api/*` فقط تحت **`/api/v1`** (8 موجهات) |
| **الصحة والمراقبة** | `GET /api/health` | `GET /health`، `/readiness`، `/liveness`، `/metrics` |
| **الوسيطات (Middleware)** | CORS، `DevPreflightMiddleware` (تطوير)، تسجيل طلبات، slowapi | TrustedHost، GZip، Request ID، RateLimit مخصص، رؤوس أمنية، مقاييس |
| **المدفوعات** | منطق الدفع ضمن الـ routers / الطلبات | Webhook Stripe على **`POST /webhooks/stripe`** مدمج في `app.py` |
| **التغطية الوظيفية** | **كاملة تقريباً** (try-on، ستايلست، نمو، اجتماعي، أمان، …) | **جزئية** (مصادقة، منتجات، checkout، try-on، بحث بصري، خزانة، توصيات، علامات) |

**الخلاصة:** `main.py` هو **المنتج الحالي** الذي يعتمد عليه Docker. `app.py` هو **هيكل طبقي أحدث** (cleaner middleware، metrics، v1 API) لكنه **لم يُدمج** بعد مع مجموعة الـ `routers` الكاملة.

---

## 3. خارطة دمج موحّدة (مسار واحد للمستقبل)

الهدف: **عملية واحدة**، **مسارات متسقة**، **صحة/مراقبة واحدة**.

### المرحلة A — توحيد الملاحظات والعقد (بدون كسر الإنتاج)

- اعتبار **`main:app`** المصدر الوحيد للنشر حتى إشعار آخر.
- توثيق المسارات في OpenAPI للواجهة الأمامية؛ أي عميل يعتمد على `app.py` يُحدَّد صراحةً كتجريبي.

### المرحلة B — نقل القدرات من `app.py` إلى مسار الإنتاج

1. **المراقبة:** إعادة توجيه أو تكرار `/health` و `/readiness` و `/liveness` و `/metrics` من منطق `app.py` (أو مشاركة الدوال من `core/middleware/monitoring`) بحيث يعمل **`main.py`** بنفس نقاط المراقبة مع الإبقاء على **`/api/health`** كاسم مستعار (alias) للتوافق مع الـ healthcheck الحالي في Docker.
2. **الوسيطات:** دمج تدريجي لـ TrustedHost / SecurityHeaders / Metrics في `main.py` خلف أعلام بيئة (`settings`) لتجنب كسر التطوير المحلي.
3. **Webhook Stripe:** إما تضمين `POST /webhooks/stripe` في `main.py` أو جعل طبقة الدفع المشتركة تستدعي نفس الخدمة من `application.services`.

### المرحلة C — توحيد API تحت `/api/v1`

- إضافة بادئة `/api/v1` للموجهات الجديدة أو تدريجياً للموجهات القديمة مع إبقاء المسارات القديمة كـ **deprecated** لفترة.
- محاذاة `api/*` (من `app.py`) مع `routers/*` (من `main.py`) لتفادي تكرار المتحكمات — دمج في مجلد واحد (`api` أو `routers`) حسب اتفاق الفريق.

### المرحلة D — طبقة بيانات واحدة

- اختيار **نموذج واحد** (async SQLAlchemy عبر `infrastructure` أو sync عبر `database.session`) وترحيل التدفقات تدريجياً؛ هذا أضخم عمل ويُخطَّط له كمشروع مستقل.

### بعد الدمج

- تغيير `CMD` في Dockerfile إلى التطبيق الموحّد فقط عندما تختبر جميع المسارات الحرجة.
- يمكن إبقاء `app.py` كغلاف رقيق `from main import app` مؤقتاً ثم حذف الملف لتقليل الالتباس.

---

## 4. تخطيط المستودع (خريطة سريعة)

| المسار | الدور |
|--------|--------|
| `package.json`، `vite` | واجهة **React + Vite** |
| `backend/main.py` | **API الإنتاج الافتراضي** |
| `backend/app.py` | API بديل (v1 + مراقبة مركزية) |
| `backend/routers/` | معظم نقاط النهاية الميزة |
| `backend/api/` | وحدات v1 المستخدمة في `app.py` وبعضها في `main.py` |
| `backend/docker-compose.yml` | `api`، Postgres، Redis، Elasticsearch، Celery، Prometheus، Grafana، PentAGI، … |
| `docker-compose.yml` (جذر) | `include: backend/docker-compose.yml` |

---

## 5. ربط «الخدمات الاثنتي عشرة» بالكود (منطقي)

| الخدمة (مفهومية) | أين تظهر في الكود اليوم |
|------------------|-------------------------|
| Auth | `routers/auth.py`، `api/auth` (في `app.py`) |
| User Profile | `routers/profile.py`، `onboarding.py` |
| Style DNA | `api/style_dna.py`، `routers/identity_intelligence.py`، `signals.py` |
| Recommendation | `api/recommendations` (app)، منطق توصيات في الخلفية إن وُجد |
| Outfit Engine | `routers/outfits.py`، `virtual_stylist.py`، `ai_stylist.py` |
| Try-On (AI) | `routers/virtual_tryon.py`، `controllers/tryon_controller` |
| AR Processing | `routers/ar_tryon.py`، `rotation.py` |
| Social Feed | `routers/social.py`، `social_router.py`، `challenges.py` |
| Growth Engine | `routers/growth_engine.py` |
| Payment | `routers/payments.py`، `orders.py`، `commerce.py`؛ Stripe في `app.py` |
| Notification | `routers/newsletter.py` وقنوات أخرى موزعة |
| Analytics | `routers/analytics.py`، `wardrobe_analytics.py` |

لا يوجد فصل نشر لاثنتي عشرة خدمة بعد؛ هذا التقسيم **حدود دومين** لخطة التوسع لاحقاً.

---

## 6. البنية التحتية (Docker Compose — ملخص)

- **PostgreSQL** — بيانات معاملاتية.
- **Redis** — كاش / جلسات / وسيط Celery.
- **Elasticsearch** — بحث/فهرسة (حسب الاستخدام الفعلي).
- **Celery worker + beat** — مهام خلفية.
- **Prometheus + Grafana** — مراقبة.
- **PentAGI + pgvector** — أمن/ذكاء اصطناعي حسب التكوين.

تفاصيل المتغيرات: `backend/docker-compose.yml` و `backend/.env.example`.

---

## 7. ملاحظات للمستثمر / الفريق التقني

- المنصة جاهزة كـ **modular monolith** قابل للتوسع؛ المخطط متعدد الخدمات يُنفَّذ بتقسيم نشر وليس بإعادة كتابة من الصفر.
- **Cloudflare / Kubernetes** غير مُعرَّفين كملفات في الجذر؛ النشر الحالي **Compose**-محوري.
- أي SLO أو فحص صحة يجب أن يتفق مع **`/api/health`** ما دام Docker يعتمدها (حتى توحيد المسارات في المرحلة B).

---

*آخر تحديث: يعكس حالة المستودع وقت إنشاء المستند.*
