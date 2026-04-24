# Аналіз: модель товару, варіанти та формування ціни

Документ фіксує, як у проєкті формується сторінка одного товару, які є варіанти вибору (колір/розмір/опції) і як рахується ціна на різних етапах.

## 1) Доменна модель товару

### Основна модель `Furniture`
- Файл: `furniture/models.py`
- Ключові поля:
  - `price` — базова ціна товару.
  - `is_promotional`, `promotional_price`, `sale_end_date` — акційна ціна та активність акції.
  - `selected_fabric_brand`, `fabric_value` — бренд тканин + множник на доплату за тканину.
  - `color_palettes` (M2M до `FabricColorPalette`) — доступні палітри кольорів для товару.
  - `custom_option_name` + звʼязані `custom_options` — додатковий параметр з надбавкою.
- Важливо:
  - `current_price` повертає акційну ціну, якщо товар акційний; інакше базову.
  - Якщо вимкнути `is_promotional`, у `save()` очищається `promotional_price` у size-варіантів.

### Розмірні варіанти `FurnitureSizeVariant`
- Файл: `furniture/models.py`
- Привʼязка: `ForeignKey` до `Furniture` (`related_name="size_variants"`).
- Ключові поля:
  - Геометрія: `length`, `width`, `height`, + `is_foldable`/`unfolded_length`.
  - Ціна: `price`, `promotional_price`, `is_promotional`, `sale_end_date`.
  - `parameter` + `parameter_value` — дозволяє змінювати конкретний параметр у таблиці характеристик при виборі розміру.
- Логіка ціни:
  - `current_price`:
    1. якщо сам варіант акційний і акція активна -> `variant.promotional_price`;
    2. інакше якщо батьківський `Furniture` акційний і активний -> `furniture.promotional_price`;
    3. інакше -> `variant.price`.
  - Тобто size-варіант може наслідувати акцію від основного товару.

### Кольорові варіанти

У проєкті є два різні механізми "кольору":

1. `FurnitureVariantImage` (файл: `furniture/models.py`)
   - Це візуальні "варіанти товару" (кнопки-чіпи з фото), з полями `name`, `image`, `is_default`, `stock_status`.
   - Впливають на відображення фото/статусу наявності.
   - На ціну **не впливають**.

2. `FabricColorPalette` / `FabricColor` (файл: `fabric_category/models.py`)
   - Це палітри оббивки/покриттів (`color_palettes` у `Furniture`).
   - Обраний `color_id` зберігається у кошику/замовленні як атрибут.
   - На ціну **не впливає**.

### Параметри товару
- Файл: `params/models.py`
- `FurnitureParameter` зберігає базові характеристики (напр. `length`, `width`, `height`, інші ключі).
- На сторінці товару `height/width/length` агрегуються в один параметр "Розмір (ДхШхВ)".

### Додаткові опції з доплатою
- Модель: `FurnitureCustomOption` (файл: `furniture/models.py`).
- Кожна опція має `price_delta` (надбавка до ціни).

## 2) Як формується сторінка одного товару

### View `furniture_detail`
- Файл: `furniture/views.py`
- URL: `furniture/<slug>/`
- Основні кроки:
  1. Завантажує `Furniture`, `parameters`, `size_variants`, `variant_images`, галерею.
  2. Формує `parameters` для таблиці характеристик (окремо збирає `dimensions`).
  3. Підтягує `fabric_categories` (якщо задано `selected_fabric_brand`).
  4. Підтягує активні `color_palettes` + `colors`.
  5. Визначає `base_size_variant_id` (якщо один із size-варіантів збігається з базовими dimensions).
  6. Віддає в шаблон `furniture/furniture_detail_alt.html` (v2, за замовчуванням).

### Дані, що віддаються у шаблон для вибору користувачем
- `size_variants` — розміри + дата-атрибути цін.
- `variant_images` — візуальні варіанти (зображення + stock status).
- `fabric_categories` — категорії тканини з доплатою.
- `color_palettes` — палітри/кольори для фіксації у замовленні.
- `custom_options` — опції з `price_delta`.

## 3) Як рахується ціна на сторінці (frontend)

### Джерело
- Шаблон: `templates/furniture/furniture_detail_alt.html`
- JS: `static/js/furniture-detail-alt.js`

### Базовий алгоритм у JS (`recompute()`)
Поточна ціна на екрані:
1. стартує з `selectedPrice` (база або обраний size),
2. додає `selectedOptionPrice` (custom option),
3. додає доплату за тканину (`data-calculated-price`),
4. множить на кількість.

Окремо ведеться `originalTotal` для відображення закресленої ціни (коли є акція).

### Важливо про вибір розміру
- Кожен `size-chip` має:
  - `data-price`
  - `data-original-price`
  - `data-is-on-sale`
- Після кліку на chip:
  - змінюється `selectedPrice`,
  - оновлюються параметри (якщо у варіанта є `parameter`/`parameter_value`),
  - перераховується загальна ціна.

### Що реально йде в форму на бекенд
У `hidden` поля відправляються:
- `size_variant_id`
- `fabric_category_id`
- `variant_image_id`
- `custom_option_id`
- `color_id`
- `quantity`

Тобто фронт передає **ідентифікатори виборів**, а не "фінальну суму".

## 4) Де формується фактична ціна (бекенд)

### Кошик (перегляд)
- Файл: `shop/views.py`, `CartView.get_context_data`
- Для кожної позиції:
  1. Бере базу: `size_variant.current_price` (або `furniture.current_price`).
  2. Додає тканину: `fabric_category.price * furniture.fabric_value`.
  3. Додає `custom_option_price`.
  4. Множить на `quantity`.

### Checkout (створення `OrderItem`)
- Файл: `checkout/views.py`
- Рахує ціну аналогічно кошику і записує в `OrderItem.price`.
- Також зберігає snapshot атрибутів:
  - `size_variant_id`, `fabric_category_id`, `variant_image_id`,
  - `custom_option_*`,
  - `color_*`.

### Модель `OrderItem`
- Файл: `checkout/models.py`
- Зберігає:
  - фінальну ціну рядка `price`,
  - `original_price`,
  - технічні поля про обрану модифікацію.

## 5) Звідки потрапляють базові ціни в БД

### Google Sheets / XLSX мапінг
- Файли: `price_parser/models.py`, `price_parser/services.py`
- `FurniturePriceCellMapping` може бути:
  - або для `furniture` (основна ціна),
  - або для `size_variant` (ціна конкретного розміру).
- Сервіс оновлення:
  - читає комірку,
  - парсить/множить на `price_multiplier`,
  - пише або в `mapping.furniture.price`, або в `mapping.size_variant.price`.

### Supplier feed (XML/YML)
- Файл: `price_parser/services.py` (`SupplierFeedPriceUpdater`)
- Оновлює **лише `Furniture`**:
  - `price`,
  - `promotional_price`,
  - `is_promotional`.
- Size-варіанти цим шляхом не оновлюються.

## 6) Повний ланцюг ціноутворення (коротко)

1. БД містить базову ціну товару та/або розмірів.
2. `furniture_detail` віддає всі варіанти в шаблон.
3. JS на сторінці рахує "превʼю" ціни для користувача.
4. У форму відправляються ID обраних модифікацій.
5. Бекенд у кошику/checkout перераховує ціну з нуля за правилами моделей.
6. `OrderItem.price` стає фінальною ціною позиції.

## 7) Важливі технічні нюанси (для майбутніх змін)

1. У `Furniture` є дубльований property `current_price` (друга дефініція перекриває першу). Це не ламає роботу, але створює ризик плутанини.

2. Потенційна неузгодженість у шаблоні `furniture_detail_alt.html`:
   - для `size-chip` використовується `variant.is_sale_active` у `data-price` та `data-is-on-sale`,
   - але `FurnitureSizeVariant.current_price` враховує ще й акцію батьківського `Furniture`.
   - Наслідок: якщо акція задана на рівні товару, UI може показувати неакційну ціну для size-chip, тоді як кошик/checkout порахують акційну.

3. Колір (`color_id`) не впливає на ціну, лише фіксується як атрибут замовлення.

4. `variant_image_id` (візуальний варіант) теж не впливає на ціну.

5. Фінальний source of truth по сумі: бекенд-розрахунок у `shop/views.py` + `checkout/views.py`, а не цифра в DOM.

