# Order Pipeline Lab — GitFlow + .NET 10 + GitHub Actions + Docker

پروژه آموزشی واقعی برای **Pull Request → Unit Tests → SemVer → Git Tag → Docker Image → GHCR**.

- بدون Jenkins و بدون GitLab
- نیازی به نصب .NET روی Ubuntu نیست؛ کامپایل و Unit Test روی GitHub-hosted runners انجام می‌شود.
- تنها دو شاخه دائمی: `main` (نسخه رسمی) و `develop` (نسخه توسعه‌ای).
- شاخه‌های موقت: `feature/*`, `bugfix/*`, `release/*`, `hotfix/*`.
- **برای هر Merge/Push به `develop` یک نسخه پیش‌انتشار `-dev.N` ثبت می‌شود؛ انتشار رسمی فقط از PR مربوط به Release/Hotfix به `main` می‌آید.**

> این ریپو یک Lab برای آموزش CI/CD است، نه یک سیستم Production با استقرار مستقیم روی اینترنت.

## 1) شروع سریع — چگونه ZIP را داخل ریپوی فعلی بگذارم؟

[Repository](https://github.com/MaedehShahcheraghi/order-pipeline-lab)

اگر Repo از قبل `main` و `develop` دارد، فایل‌های این ZIP را **داخل ریشه آن** کپی کن و یک Feature Branch بساز؛ به `main` مستقیم Push نکن.

**راه راحت‌تر:** بعد از Extract کردن ZIP، روی دستگاهی که Git و دسترسی به GitHub دارد، از داخل پوشه استخراج‌شده اجرا کن: `bash scripts/push-project.sh`؛ این اسکریپت خودش `develop` را Clone، شاخه `feature/bootstrap-ci` را ایجاد و Push می‌کند (هرگز مستقیم به main/develop Push نمی‌کند).

```bash
# از داخل یک clone از ریپو (یک بار clone کرده باش)
git switch develop
git pull origin develop
git switch -c feature/bootstrap-ci

# فایل‌های ZIP را در همین پوشه (کنار .git) کپی/Extract کن
# سپس:
git add .
git commit -m "feat: bootstrap .NET API, tests and automation"
git push -u origin feature/bootstrap-ci
```

در GitHub یک PR به **`develop`** با عنوان زیر باز کن:

```text
feat: bootstrap .NET API, tests and automation
```

بگذار Workflow **Unit Tests** سبز شود و سپس **Squash and merge** بزن. یک Push به `develop` Workflow دوم را اجرا می‌کند و اگر همه مراحل موفق شوند:

```text
Git tag: v0.1.0-dev.1
GHCR image: ghcr.io/maedehshahcheraghi/order-pipeline-lab:0.1.0-dev.1
```

اگر Workflow اجازه Push Tag یا Package نداشت، بخش «تنظیمات GitHub» را بررسی کن.

## 2) تنظیمات ضروری GitHub

در `Settings → General → Pull Requests`:
- **Allow squash merging** را برای PRهای معمولی فعال نگه دار.
- پیام پیش‌فرض Squash را روی **Pull request title** قرار بده؛ چون نسخه `develop` از عنوان Conventional Commit آن Merge خوانده می‌شود.
- **Allow merge commits** را هم فعال کن، چون **Release/Hotfix به `main` باید با Create a merge commit** انجام شود؛ نه Squash. دلیلش تضمین اینکه Commit تأییدشده RC واقعاً در تاریخچه Commit انتشار وجود دارد.

در `Settings → Actions → General`:
- مطمئن شو GitHub Actions مجازه اجرا بشه.
- برای انتشار Tag و Package، `GITHUB_TOKEN` باید امکان `contents: write` و `packages: write` داشته باشه. این مجوزها داخل Workflow درخواست شده‌اند؛ محدودیت سطح ریپو/سازمان ممکنه اجازه نده.

در Rulesets/Branch protection (در صورت پشتیبانی پلن):
- برای `main` و `develop` ورود کد را از طریق PR انجام بده.
- Required check: **Build and Unit Tests** (پس از اولین اجرا ظاهر می‌شود).
- برای `main` فقط انتشار از شاخه‌های `release/*` و `hotfix/*` مجاز است؛ Workflow PR هم این سیاست را چک می‌کند.
- اگر فقط یک حساب داری، الزام به approval یک نفر دیگر نگذار، چون بدون کاربر دوم Merge را مسدود می‌کند.

**مهم:** فایل‌های Workflow را روی PRهایی از Fork ناشناس با سطح دسترسی نوشتن اجرا نکن؛ Workflow تست فقط read دارد و Workflow انتشار تنها برای Merge شده‌های داخل همین Repository منتشر می‌کند.

## 3) اولین Release رسمی از صفر

پس از Merge پروژه به `develop`، آخرین Build توسعه‌ای `0.1.0-dev.1` یا جدیدتره.

از `develop` یک Release Branch بساز:

```bash
git switch develop
git pull origin develop
git switch -c release/0.1.0
git push -u origin release/0.1.0
```

Push این Branch به‌طور خودکار Workflow **Version, Build and Publish** را فعال می‌کند:

```text
v0.1.0-rc.1              Git Tag روی Commit شاخه Release
ghcr.io/...:0.1.0-rc.1   Docker Image آماده آزمایش Staging
```

بعد از تست، PR با **Source `release/0.1.0` → Target `main`** و عنوان زیر ایجاد کن:

```text
release: 0.1.0
```

تست‌ها باید Pass شوند. **این PR را با گزینه `Create a merge commit` مرج کن، نه Squash.** پس از Merge موفق، Workflow انتشار روی Commit نهایی `main` این Tag را می‌سازد:

```text
v0.1.0
```

و Image نسخه رسمی را به GHCR می‌فرستد:

```text
ghcr.io/maedehshahcheraghi/order-pipeline-lab:0.1.0
```

Tag توسط خود Merge ساخته نمی‌شود؛ Workflow اتوماتیک بعد از Merge آن را ایجاد می‌کند.

**نکته درباره RC و Production:** Git Tag نهایی روی Merge Commit در `main` قرار می‌گیرد و بنابراین SHA آن از RC متفاوت است. Workflow نسخه نهایی را از همان Commit نهایی دوباره Build و Test می‌کند. در پروژه واقعی با حساسیت بالا باید Promotion یک Artifact دارای Digest یکسان را پیاده‌سازی و تأیید کرد. در این Lab، برای سادگی، نسخه نهایی پس از تست مجدداً Build می‌شود.

## 4) قوانین Versioning

| رویداد | نتیجه |
|---|---|
| PR معمولی باز شد | Build و Test، هنوز Tag ندارد |
| `feat:` با Squash وارد `develop` شد | افزایش Minor هدف، مثل `0.2.0-dev.1` |
| `fix:` وارد `develop` شد در حالی که Minor منتشرنشده داریم | افزایش dev counter، مثل `0.2.0-dev.2` |
| `fix:` وارد `develop` شد و نسخه منتشرنشده نداریم | Patch هدف، مثل `0.1.1-dev.1` |
| `feat!:` / `BREAKING CHANGE:` وارد `develop` شد | افزایش Major هدف |
| Push به `release/0.2.0` | `v0.2.0-rc.1`, بعد `rc.2` و ... |
| PR `release/0.2.0 → main` Merge شد | `v0.2.0`، و Image رسمی |
| PR `hotfix/0.1.1 → main` Merge شد | `v0.1.1`، و Image رسمی |
| `release/*` یا `hotfix/*` به `develop` برگردد | build و `-dev` جدید، **بدون تغییر نسخه پایدار main** |

اگر نسخه رسمی `0.1.0` و نسخه توسعه‌ای `0.2.0-dev.3` باشد، Hotfix `0.1.1` روی main منتشر می‌شود و سپس اصلاح آن به develop می‌رود، نسخه develop می‌تواند `0.2.0-dev.4` شود؛ به `0.1.1` برنمی‌گردد.

`main` نسخه پایدار Git Tag دارد؛ `develop` نسخه پیش‌انتشار Git Tag دارد. `release/*` با `-rc.N` مشخص می‌شود. Docker Imageها علاوه بر نسخه، Tag `sha-<commit>` نیز دارند.

**محدودیت آگاهانه این Lab:** تشخیص نوع تغییر `develop` از پیام Commit نهایی (عنوان Squash PR) است؛ پس برای Feature PRها باید Squash Merge انجام دهی و عنوان Conventional Commit را حفظ کنی. Mergeهای sync از release/hotfix با عنوان `chore:` یا `fix:` بر اساس قواعد ساده نسخه‌گذاری می‌شوند. اجرای هم‌زمان Workflow انتشار با `concurrency` سریالی شده، ولی برای تیم‌های بزرگ بهتر است Release Automation تخصصی و حفاظت پیشرفته از Branch/Tag هم اضافه شود.

## 5) دو Workflow

- `.github/workflows/unit-tests.yml`: بررسی Policy عنوان PR، Restore، Build، xUnit، تست محاسبه نسخه. هیچ Tag یا Image منتشر نمی‌کند.
- `.github/workflows/build-release.yml`: روی Push به `develop` یا `release/*` و PR Merge‌شده `release/*`/`hotfix/*` به `main` اجرا می‌شود. مجدداً Test می‌کند، Version را حساب می‌کند، Image می‌سازد، به GHCR Push می‌کند، و **فقط پس از موفقیت انتشار Image** Git Tag را ثبت می‌کند.

تنها با تغییر GitHub Repo، GitHub Actions کار می‌کند؛ Jenkins و Webhook سفارشی لازم نیست.

## 6) API و تست محلی

اگر .NET 10 داری:

```bash
dotnet restore OrderPipelineLab.sln
dotnet test OrderPipelineLab.sln
dotnet run --project src/OrderPipeline.Api
```

بدون .NET روی Ubuntu، با Docker:

```bash
docker build -t order-pipeline-lab:local --build-arg APP_VERSION=0.0.0-local .
docker run --rm -p 8080:8080 order-pipeline-lab:local
```

(ساخت Docker روی VM ضعیف ممکنه سنگین باشه؛ بهتره Build روی GitHub انجام بشه.)

تست Endpoint:

```bash
curl -X POST http://localhost:8080/orders/calculate \
  -H 'Content-Type: application/json' \
  -d '{"unitPrice":100,"quantity":2,"discountPercent":10}'
# {"total":180}

curl http://localhost:8080/health
curl http://localhost:8080/version
```

## 7) Deploy روی Ubuntu کم‌منبع

GHCR بسته به تنظیمات Visibility می‌تواند Private باشد. برای Image خصوصی باید با یک توکن با مجوز `read:packages` لاگین کنی؛ توکن را داخل Repository یا فایل Compose قرار نده.

```bash
cd deploy
cp .env.example .env
# DEV_TAG را مطابق آخرین نسخه واقعی موجود در GHCR تنظیم کن.
docker compose --profile dev pull
docker compose --profile dev up -d
docker compose --profile dev ps
curl http://127.0.0.1:8081/health
```

همین الگو برای `--profile staging` و `--profile prod` با پورت‌های 8082 و 8083 است. چون VM خصوصی تو از GitHub قابل دسترسی نیست، **Deploy به Ubuntu در این نسخه دستی است**؛ تست، Versioning، Tag و Docker Build/Push کاملاً خودکارند. برای خودکار شدن Deploy روی Ubuntu بعداً می‌شود یک Runner امن محلی، شبکه امن یا مکانیزم Pull-based کنترل‌شده اضافه کرد.

Compose این Lab برای مصرف کم منابع روی localhost، non-root runtime، حذف Capabilities، filesystem فقط‌خواندنی، `tmpfs` و محدودیت حافظه تنظیم شده.

## 8) Hotfix

```bash
git switch main
git pull origin main
git switch -c hotfix/0.1.1
# Fix code + test, commit, push
```

PR با عنوان `fix: repair production bug` از `hotfix/0.1.1` به `main` بزن، با **Create a merge commit** ادغام کن؛ Workflow `v0.1.1` و Image رسمی را ایجاد می‌کند. سپس PR دیگری از `hotfix/0.1.1` به `develop` با عنوان `fix: sync production hotfix` باز کن تا کد اصلاح‌شده به توسعه برگردد. Merge به develop نسخه پایدار جدید نمی‌سازد.

## 9) ساختار فایل‌ها

```text
.
├── .github/workflows/
│   ├── unit-tests.yml
│   └── build-release.yml
├── src/OrderPipeline.Api/
│   ├── Services/OrderCalculator.cs
│   ├── Program.cs
│   └── OrderPipeline.Api.csproj
├── tests/OrderPipeline.UnitTests/
│   ├── OrderCalculatorTests.cs
│   └── OrderPipeline.UnitTests.csproj
├── build/
│   ├── versioning.py
│   ├── validate_pr.py
│   └── tests/test_versioning.py
├── deploy/
│   ├── compose.yaml
│   └── .env.example
├── scripts/push-project.sh
├── Dockerfile
├── .dockerignore
├── .gitignore
└── OrderPipelineLab.sln
```

## 10) نکته‌ها و محدودیت‌ها

- ریپوی GitHub شما از محیط ساخت این ZIP قابل مشاهده نبود؛ این فایل‌ها یک پروژه مستقل و آماده کپی هستند و هنوز روی Repository شما Push یا اجرا نشده‌اند.
- نسخه Packageهای Unit Test و .NET 10 در Runner به اینترنت دسترسی نیاز دارند؛ تست واقعی .NET/Docker فقط بعد از اجرای GitHub Actions مشخص می‌شود.
- Git Tag با دستور `git push origin v0.1.0` به GitHub فرستاده می‌شود؛ این دستور Branch را Push نمی‌کند.
- Pipeline انتشار PRهای Merge‌شده از `release/*` و `hotfix/*` را روی `main` می‌پذیرد و از `GITHUB_TOKEN` استفاده می‌کند، نه PAT شخصی.
