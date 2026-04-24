# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

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

## Документація в Obsidian

**Vault**: `~/Documents/Claude/Obsidian/montal home/`  
**MCP сервер**: `obsidian-montal` (глобальний, завантажений автоматично)

Перед тим як шукати по коду — читай відповідний файл з Obsidian:

| Тема | Файл в Obsidian |
|---|---|
| Архітектура, app map, URL namespaces | `Montal Home/Архітектура.md` |
| Моделі, зв'язки, поля | `Montal Home/Моделі та зв'язки.md` |
| Логіка ціноутворення, формула | `Montal Home/Ціноутворення.md` |
| Кошик (session key), замовлення, LiqPay | `Montal Home/Кошик та замовлення.md` |
| Price parser (3 стратегії) | `Montal Home/Парсер цін.md` |
| Nova Poshta, LiqPay, SalesDrive, R2/CDN | `Montal Home/Інтеграції.md` |
| Custom admin `/custom-admin/` | `Montal Home/Кастом адмін.md` |
| Middleware, circuit breaker | `Montal Home/Middleware.md` |
| Зображення, WebP варіанти | `Montal Home/Система зображень.md` |
| Make команди, env, management commands | `Montal Home/Команди розробки.md` |
| Пастки, неочевидні деталі | `Montal Home/Підводні камені.md` |

---

## Критичні факти (читай завжди)

- **`article_code`** — якір для price feed. Не змінюй без оновлення фіду.
- **Ключ сесії кошика** — compound string. Зміна формату ламає всі сесії.
- **`is_sale_active`** — завжди використовуй property, не `is_promotional` напряму.
- **`/custom-admin/`** — основний UI персоналу, не `/admin/`.
- **SalesDrive** — fire-and-forget. Помилки в логах, замовлення не блокує.
- **WebP варіанти** — генеруються асинхронно після upload.
