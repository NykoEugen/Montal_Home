"""
Приклади конфігурацій та використання для Price Parser
"""

from price_parser.models import GoogleSheetConfig, FurniturePriceMapping
from furniture.models import Furniture


def create_example_config():
    """
    Створення прикладу конфігурації для Google таблиці "Компанія Джем"
    """
    
    # Створення конфігурації для таблиці
    config = GoogleSheetConfig.objects.create(
        name="Компанія Джем - Прайс",
        sheet_url="https://docs.google.com/spreadsheets/d/11CBbJs-KCGknFYlIguwSOz-1zveyJTx7EWBLJ48m1ek/edit?gid=0#gid=0",
        furniture_name_column="A",  # Колонка з назвами меблів
        size_columns=["B", "C"],    # Колонки з розмірами (Довжина, Ширина)
        price_columns=["E", "F"],   # Колонки з цінами (Стільниця стандарт, HPL покриття)
        start_row=4,                # Початок даних з 4-го рядка
        is_active=True
    )
    
    print(f"Створено конфігурацію: {config.name}")
    return config


def create_example_mappings():
    """
    Створення прикладів зв'язків між назвами в таблиці та меблями в БД
    """
    
    config = GoogleSheetConfig.objects.filter(name="Компанія Джем - Прайс").first()
    if not config:
        print("Спочатку створіть конфігурацію")
        return
    
    # Приклади зв'язків (потрібно адаптувати під ваші меблі)
    mappings = [
        {"sheet_name": "Maxi -1", "furniture_name": "Maxi-1"},
        {"sheet_name": "Maxi -2", "furniture_name": "Maxi-2"},
        {"sheet_name": "Boston", "furniture_name": "Boston"},
        {"sheet_name": "Boston А", "furniture_name": "Boston А"},
        {"sheet_name": "Chester", "furniture_name": "Chester"},
        {"sheet_name": "Slim", "furniture_name": "Slim"},
        {"sheet_name": "Kirk", "furniture_name": "Kirk"},
    ]
    
    created_count = 0
    for mapping_data in mappings:
        # Знаходимо меблі в базі даних
        furniture = Furniture.objects.filter(name__icontains=mapping_data["furniture_name"]).first()
        
        if furniture:
            # Створюємо зв'язок
            mapping, created = FurniturePriceMapping.objects.get_or_create(
                sheet_name=mapping_data["sheet_name"],
                config=config,
                defaults={
                    "furniture": furniture,
                    "is_active": True
                }
            )
            
            if created:
                created_count += 1
                print(f"Створено зв'язок: {mapping_data['sheet_name']} -> {furniture.name}")
            else:
                print(f"Зв'язок вже існує: {mapping_data['sheet_name']} -> {furniture.name}")
        else:
            print(f"Меблі не знайдено: {mapping_data['furniture_name']}")
    
    print(f"Створено {created_count} нових зв'язків")


def analyze_sheet_structure():
    """
    Аналіз структури Google таблиці для налаштування парсера
    """
    
    print("Аналіз структури таблиці 'Компанія Джем':")
    print()
    print("Структура таблиці:")
    print("| A (Модель) | B (Довжина) | C (Ширина) | D (Висота) | E (Стільниця стандарт) | F (HPL покриття) | G (Стільниця діамант) | ... |")
    print()
    print("Приклади даних:")
    print("- Maxi -1: 1100-1700 x 700 x 750, ціни: 7490, 7940, 8180")
    print("- Boston: 900 x 600 x 750, ціни: 4730, 5010, 5130")
    print("- Chester: 1100-1500 x 700 x 750, ціни: 8900, 10040, 9620")
    print()
    print("Рекомендовані налаштування:")
    print("- Колонка назв: A")
    print("- Колонки розмірів: B, C")
    print("- Колонки цін: E, F, G")
    print("- Початковий рядок: 4")
    print()
    print("Особливості:")
    print("- Розміри можуть бути діапазонами (1100-1700)")
    print("- Висота зазвичай фіксована (750)")
    print("- Ширина зазвичай фіксована (600-800)")
    print("- Кілька варіантів цін для різних матеріалів")


def run_example_update():
    """
    Приклад запуску оновлення цін
    """
    
    from price_parser.services import GoogleSheetsPriceUpdater
    
    config = GoogleSheetConfig.objects.filter(name="Компанія Джем - Прайс").first()
    if not config:
        print("Конфігурація не знайдена")
        return
    
    print(f"Запуск оновлення для конфігурації: {config.name}")
    
    # Тестування парсингу
    updater = GoogleSheetsPriceUpdater(config)
    test_result = updater.test_parse()
    
    if test_result['success']:
        print(f"Тест успішний: знайдено {test_result['count']} рядків")
        
        # Оновлення цін
        update_result = updater.update_prices()
        
        if update_result['success']:
            print(f"Оновлення успішне:")
            print(f"- Оброблено: {update_result['processed_count']}")
            print(f"- Оновлено: {update_result['updated_count']}")
        else:
            print(f"Помилка оновлення: {update_result['error']}")
    else:
        print(f"Помилка тесту: {test_result['error']}")


if __name__ == "__main__":
    # Розкоментуйте потрібні функції для виконання
    # create_example_config()
    # create_example_mappings()
    # analyze_sheet_structure()
    # run_example_update()
    pass 