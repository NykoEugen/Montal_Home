from categories.models import Category
from sub_categories.models import SubCategory
from params.models import Parameter
from django.db import transaction
from django.utils.text import slugify

CATEGORY_SUBCATEGORY = {
    "Стільці": ["Обідні стільці", "Барні", "Напівбарні", "Табурети"],
    "М'які меблі": ["Дивани", "Кріслa"],
    "Ліжка": ["Дерев'яні ліжка", "Ліжка з м'яким узголів'ям", "Кутові ліжка", "Дитячі ліжка", "Двоярусні ліжка", "Металеві ліжка"],
    "Комп'ютерні крісла": ["Геймерські крісла", "Дитячі крісла", "Крісла керівнмка", "Ортопедичні крісла"],
    "Столи": ["Кухонні столи", "Журнальні столи", "Комп'ютерні столи", "Барні столи"],
    "Матраци": ["Пружинні матраци", "Безпружинні матраци", "Дитячі матраци", "Топери", "Футони"],
}

SUBCATEGORY_PARAMS = {
    "Стільці": ["Матеріал покриття", "Матеріал каркасу", "Країна виробник"],
    "Столи": ["Довжина (см)", "Максимальна довжина (см)", "Ширина (см)", "Матеріал стільниці", "Вид", "Механізм розкладки", "Форма"],
    "Ліжка": ["Спальне місце", "Під'ємний механізм"],
    "Комп'ютерні крісла": ["Тип крісла", "Максимальне навантаження (кг)", "Підголовник", "Регулювання", "Країна виробник", "Гарантія"],
    "М'які меблі": ["Тип", "Механізм розкладки", "Тип наповнення", "Підлокітники", "Ширина (см)", "Висота (см)"],
    "Матраци": ["Рівень жорсткості", "Висота матрацу (см)", "Максимальне навантаження (кг)", "Країна виробник"],
}

def generate_unique_slug(base_slug, model_class):
    """Generate a unique slug by appending numbers if needed"""
    slug = base_slug
    counter = 1
    while model_class.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

def generate_unique_parameter_key(base_key):
    """Generate a unique parameter key by appending numbers if needed"""
    key = base_key
    counter = 1
    while Parameter.objects.filter(key=key).exists():
        key = f"{base_key}-{counter}"
        counter += 1
    return key

def init_furniture_taxonomy():
    # Step 1: Create categories first
    categories = {}
    for cat_name in CATEGORY_SUBCATEGORY.keys():
        # Generate unique slug for category
        base_slug = slugify(cat_name)
        unique_slug = generate_unique_slug(base_slug, Category)
        
        category, created = Category.objects.get_or_create(
            name=cat_name,
            defaults={'slug': unique_slug}
        )
        
        # If category exists but has no slug, update it
        if not created and not category.slug:
            category.slug = unique_slug
            category.save()
        
        categories[cat_name] = category
        print(f"Category '{cat_name}' {'created' if created else 'already exists'}")
    
    # Step 2: Create subcategories
    subcategories = {}
    for cat_name, subcats in CATEGORY_SUBCATEGORY.items():
        category = categories[cat_name]
        for subcat_name in subcats:
            # Generate unique slug
            base_slug = slugify(subcat_name)
            unique_slug = generate_unique_slug(base_slug, SubCategory)
            
            # Create subcategory
            subcat, created = SubCategory.objects.get_or_create(
                name=subcat_name, 
                category=category,
                defaults={'slug': unique_slug}
            )
            
            # If subcategory exists but has no slug, update it
            if not created and not subcat.slug:
                subcat.slug = unique_slug
                subcat.save()
            
            subcategories[f"{cat_name}:{subcat_name}"] = subcat
            print(f"Subcategory '{subcat_name}' {'created' if created else 'already exists'}")
    
    # Step 3: Create parameters and assign to subcategories
    for cat_name, param_labels in SUBCATEGORY_PARAMS.items():
        if cat_name in CATEGORY_SUBCATEGORY:
            # Get all subcategories for this category
            category = categories[cat_name]
            category_subcats = SubCategory.objects.filter(category=category)
            
            # Create parameters
            param_objs = []
            for label in param_labels:
                # Generate unique parameter key
                base_key = slugify(label)
                unique_key = generate_unique_parameter_key(base_key)
                
                param, created = Parameter.objects.get_or_create(
                    label=label, 
                    defaults={"key": unique_key}
                )
                
                # If parameter exists but has no key, update it
                if not created and not param.key:
                    param.key = unique_key
                    param.save()
                
                param_objs.append(param)
                print(f"Parameter '{label}' {'created' if created else 'already exists'}")
            
            # Assign parameters to all subcategories of this category
            for subcat in category_subcats:
                subcat.allowed_params.add(*param_objs)
                print(f"Assigned {len(param_objs)} parameters to subcategory '{subcat.name}'") 