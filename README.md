# Montal Home - Furniture Store

A comprehensive Django web application for managing a furniture store with advanced features including product management, size variants, fabric customization, price parsing, and e-commerce functionality.

## 🏠 Project Overview

Montal Home is a full-featured furniture store management system built with Django. It provides a complete solution for managing furniture products, categories, pricing, fabric options, and online sales.

### Key Features

- **Product Management**: Complete furniture catalog with size variants and images
- **Category System**: Hierarchical categories and subcategories
- **Fabric Customization**: Fabric brands, categories, and pricing integration
- **Price Management**: Dynamic pricing with promotional offers
- **E-commerce**: Shopping cart, checkout, and order management
- **Price Parser**: Google Sheets integration for automated price updates
- **Delivery Integration**: Nova Poshta API integration
- **Responsive Design**: Modern, mobile-friendly interface

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (recommended) or SQLite
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Montal_Home
```

### 2. Install Dependencies

```bash
make install
```

### 3. Environment Setup

Create a `.env` file in the project root:

```env
SECRET_KEY=your_secret_key_here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
NOVA_POSHTA_API_KEY=your_novaposhta_api_key
DATABASE_URL=postgresql://user:password@localhost:5432/montal_home
```

#### LiqPay sandbox keys

For online payments add the LiqPay credentials that you received in Merchant Admin (sandbox keys are fine for testing):

```env
LIQPAY_PUB_KEY=your_public_key
LIQPAY_SECRET_KEY=your_private_key
# Optional overrides:
# LIQPAY_SANDBOX=true
# LIQPAY_PAYTYPES=card,privat24,applepay,googlepay
```

Without these variables the LiqPay option on checkout will stay disabled.

### 4. Database Setup

```bash
make setupdb
```

### 5. Run the Development Server

```bash
make run
```

The application will be available at http://localhost:8000

## 📁 Project Structure

```
Montal_Home/
├── categories/          # Main product categories
├── sub_categories/      # Subcategories for better organization
├── furniture/           # Core furniture management
├── fabric_category/     # Fabric brands and categories
├── params/             # Product parameters and specifications
├── shop/               # E-commerce functionality
├── checkout/           # Order processing and checkout
├── delivery/           # Delivery management
├── price_parser/       # Google Sheets price integration
├── templates/          # HTML templates
├── static/             # CSS, JS, and static assets
├── media/              # User-uploaded files
└── utils/              # Utility functions and commands
```

## 🛋️ Furniture Creation Workflow

### Step-by-Step Process for Creating Furniture Items

#### Phase 1: Basic Information (Required First)

1. **Navigate to Admin Panel**
   - Go to http://localhost:8000/admin/
   - Login with admin credentials

2. **Create Basic Furniture Entry**
   - Go to "Furniture" section
   - Click "Add Furniture"
   - Fill in **required fields only**:
     - **Name**: Product name (e.g., "Диван Монтреаль")
     - **Article Code**: Unique product code (e.g., "DM001")
     - **Sub Category**: Select appropriate subcategory
     - **Price**: Base price
     - **Description**: Basic description
   - **Save** the furniture item

#### Phase 2: Enhanced Details (After Basic Save)

3. **Add Size Variants**
   - Return to the saved furniture item
   - Go to "Size Variants" section
   - Add different size options:
     - Height, Width, Length (in cm)
     - Price for each size variant
     - Check "Foldable" if applicable
     - Add unfolded length for foldable furniture

4. **Upload Images**
   - **Main Image**: Upload primary product image
   - **Variant Images**: Add different color/material variants
   - **Gallery Images**: Additional product photos
   - Set default variant and image order

5. **Configure Fabric Options**
   - Select "Selected Fabric Brand"
   - Set "Fabric Value" (price multiplier)
   - Configure fabric categories if applicable

6. **Add Product Parameters**
   - Go to "Parameters" section
   - Add technical specifications:
     - Dimensions (height, width, length)
     - Materials
     - Features
     - Warranty information

#### Phase 3: Advanced Features

7. **Promotional Settings**
   - Enable "Is Promotional" if applicable
   - Set promotional price
   - Configure discount percentage

8. **Stock Management**
   - Set stock status (In Stock / On Order)
   - Update availability information

## 📦 Supplier Feed Import (one-off)

To rapidly create catalog items from the supplier XML feed (Matrolux-style), run the dedicated management command:

```bash
./venv/bin/python manage.py import_supplier_furniture \
  --feed-url "https://supplier.example.com/export.xml"
```

Key points:
- Only offers that belong to the catalog categories `Корпусні меблі` or `Комплекти меблів` are processed.
- The command tries to match each feed category with an existing `SubCategory` (case-insensitive). Unmatched categories are skipped and logged.
- Base product data come from `<name>`, `<model>`, `<description>`, `<price>`, `<oldprice>`, `<offer available="">`, and `<picture>` tags.
- Technical parameters `Ширина, мм`, `Висота, мм`, and `Глибина, мм` are converted to centimeters and saved into `FurnitureParameter` records (parameters are created automatically if missing).
- Multiple offers that share the same `<name>`/`<model>` pair but have different `<param name="Готові кольорові рішення">…</param>` values become color variants (`FurnitureVariantImage`) under a single furniture record. Images are downloaded and attached to both the variant and (if empty) the main product.

Optional flags:
- `--feed-file path/to/local.xml` — use a local XML copy instead of downloading it.
- `--categories "Корпусні меблі" "Комплекти меблів"` — override the default category whitelist.
- `--category-map "Корпусні меблі=Комплекти меблів"` — force-feed category names to land in specific `SubCategory` records when they differ from feed text.
 - `--category-id-map "99883424=Комплекти меблів"` — same as above but matches `categoryId` directly (and includes the category even if it isn’t in the whitelist).
   - Accepts `=Назва`, `=slug:your-slug`, or `=id:42` so you can point to the exact subcategory if names don’t match.
- `--dry-run` — preview actions without touching the database (useful for verifying category mapping).
- `--limit 10` — stop after N offers (debugging helper).

> ⚠️ The importer is intentionally designed for one-off seeding: existing furniture (matched by article code) are left untouched, and repeated runs may download the same media again. Use on a clean catalog or with caution.

9. **SEO and URLs**
   - Verify auto-generated slug
   - Customize if needed for better SEO

### Important Notes

- **Save First**: Always save the basic furniture entry before adding variants, images, or parameters
- **Size Variants**: These are crucial for furniture with multiple size options
- **Images**: Upload high-quality images with proper aspect ratios
- **Fabric Integration**: Configure fabric options for customizable furniture
- **Parameters**: Add detailed specifications for better product presentation


## 🛠️ Development Commands

### Makefile Commands

```bash
make help              # Show all available commands
make install           # Install dependencies
make run               # Start development server
make test              # Run tests
make lint              # Run code quality checks
make autofmt           # Auto-format code
make clean             # Clean up cache files
make migrate           # Apply database migrations
make makemigrations    # Create new migrations
make shell             # Open Django shell
make collectstatic     # Collect static files
make dev               # Quick setup (install + setupdb + run)
```

### Code Quality

```bash
make lint              # Run all quality checks
make autofmt           # Auto-format code
make precommit         # Pre-commit checks
```

### Database Operations

```bash
make makemigrations    # Create migrations
make migrate           # Apply migrations
make setupdb           # Setup database
```

## 🧪 Testing

```bash
make test              # Run all tests
python manage.py test furniture.tests  # Run specific app tests
```

## 🚀 Production Deployment

### Preparation

```bash
make production        # Clean, collect static, migrate
```

### Environment Variables for Production

```env
DEBUG=False
SECRET_KEY=your_secure_secret_key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=postgresql://user:password@host:5432/database
NOVA_POSHTA_API_KEY=your_production_api_key
```

## 📊 Key Models

### Furniture
- Core product information
- Pricing and promotional settings
- Fabric integration
- Size variants support

### FurnitureSizeVariant
- Multiple size options per furniture
- Individual pricing per size
- Foldable furniture support

### FabricCategory & FabricBrand
- Fabric management system
- Brand categorization
- Price calculation integration

### Order & OrderItem
- E-commerce order processing
- Cart management
- Delivery integration

## 🔧 Configuration

### Price Parser Setup

The price parser integrates with both Google Sheets and supplier XML feeds.

**Google Sheets**

```bash
python manage.py setup_jem_config    # Setup Google Sheets configuration
python manage.py update_prices       # Update prices from sheets
```

**Matroluxe XML (supplier feed)**

```bash
python manage.py setup_matroluxe_supplier_feed     # Create/update the feed config
python manage.py ensure_corpus_subcategories       # Створити підкатегорії для корпусних меблів
python manage.py ensure_mattress_subcategories     # Створити підкатегорії для матраців
```

Після цього можна:
- Запустити імпорт корпусних меблів:
  ```bash
  python manage.py import_supplier_furniture \
    --feed-file matro_korpus_mebel.xml \
    --profile furniture
  ```
- Запустити імпорт матраців (та сама логіка + власні підкатегорії):
  ```bash
  python manage.py import_supplier_furniture \
    --feed-file matro-matras.xml \
    --profile mattresses
  ```
- Відкрити `https://<домен>/custom-admin/` → **Supplier Feeds** та використати кнопки “Test parse” / “Update prices” для конфігурації “Matroluxe — корпусні меблі” (доступно також у стандартній Django адмінці).

Парсер використовує артикул `<model>` (та, за потреби, назву) для пошуку товару, оновлює ціни й повторно не завантажує медіафайли, якщо вони вже є на диску.

### Delivery Integration

Configure Nova Poshta API for delivery services:

```env
NOVA_POSHTA_API_KEY=your_api_key
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Submit a pull request

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation in the `docs/` folder

---

**Montal Home** - Professional furniture store management solution
