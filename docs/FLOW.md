# فلو به زبان علی، سارا و رضا

1. **علی** `feature/discount` را از `develop` می‌سازد، کد می‌زند و PR با عنوان `feat: add discount` به `develop` می‌فرستد.
2. **GitHub Actions: Unit Tests** از رویداد PR باخبر می‌شود؛ کد و Policy عنوان را بررسی می‌کند. **هنوز Tag نداریم.**
3. **سارا** PR را تأیید می‌کند؛ علی با **Squash merge** آن را در `develop` ادغام می‌کند.
4. رویداد **push to develop**، Workflow انتشار را اجرا می‌کند. Build و Test، سپس Version مثل `0.1.0-dev.1`، Docker Image در GHCR و Git Tag `v0.1.0-dev.1` ایجاد می‌شود.
5. **رضا** از `develop`، Branch `release/0.1.0` می‌سازد و Push می‌کند؛ GitHub Actions پس از تست، `v0.1.0-rc.1` و Image Staging می‌سازد.
6. **سارا** روی Staging تست می‌کند. اگر باگ پیدا کرد، علی Branch `bugfix/rounding` را از `release/0.1.0` ساخته و با PR به همان Release برمی‌گرداند. RC بعدی `v0.1.0-rc.2` می‌شود.
7. **رضا** PR از `release/0.1.0` به `main` باز می‌کند. این PR فقط با **Create a merge commit** ادغام می‌شود. Workflow نسخه نهایی `v0.1.0` را روی همان Merge Commit ایجاد می‌کند و Image رسمی را منتشر می‌کند.
8. اگر روی Release تغییراتی انجام شده بود، **رضا** آن تغییرات را با PR `release/0.1.0 → develop` برمی‌گرداند. نسخه develop ممکن است به `0.1.1-dev.1` برسد؛ main هنوز `0.1.0` است.
9. در Hotfix، علی از آخرین نسخه main `hotfix/0.1.1` می‌سازد، PR به main می‌دهد، Stable Tag `v0.1.1` منتشر می‌شود و سپس اصلاح با PR به develop هم منتقل می‌شود.

**یادآوری:** GitHub Actions با `pull_request` و `push` فعال می‌شود، نه با پیش‌بینی نوع تغییر! نسخه توسعه‌ای از پیام Commitهای Squash و نسخه RC/Stable از نام Branch انتشار محاسبه می‌شود.
