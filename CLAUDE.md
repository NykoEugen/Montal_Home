# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Робота з базою даних
Викристовувати psycopg2

## Швидкі команди

```bash
make run               # Dev server → http://localhost:8000
make shell             # Django shell
make setupdb           # makemigrations + migrate
make lint              # isort + black + mypy
make autofmt           # auto-fix форматування
make test              # всі тести
python manage.py test furniture.tests   # тести одного app
make production        # clean + collectstatic + migrate
```

Settings module: `store.settings`. Env змінні: `.env` в корені проекту.

---

## Критичні факти (читай завжди)

- **`article_code`** — якір для price feed. Не змінюй без оновлення фіду.
- **Ключ сесії кошика** — compound string. Зміна формату ламає всі сесії.
- **`is_sale_active`** — завжди використовуй property, не `is_promotional` напряму.
- **`/custom-admin/`** — основний UI персоналу, не `/admin/`.
- **SalesDrive** — fire-and-forget. Помилки в логах, замовлення не блокує.
- **WebP варіанти** — генеруються асинхронно після upload.
