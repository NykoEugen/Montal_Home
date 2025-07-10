import re

from django import forms


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600",
                "placeholder": "Введіть ім'я",
            }
        ),
        label="Ім'я",
    )
    customer_last_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600",
                "placeholder": "Введіть прізвище",
            }
        ),
        label="Прізвище",
    )
    customer_phone_number = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600",
                "placeholder": "0XXXXXXXXX",
                "pattern": "0[0-9]{9}",
                "title": "Введіть номер у форматі 0XXXXXXXXX",
            }
        ),
        label="Номер телефону",
    )
    customer_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600",
                "placeholder": "Введіть email (необов'язково)",
            }
        ),
        label="Email",
    )
    
    # Delivery type selection
    delivery_type = forms.ChoiceField(
        choices=[
            ('local', 'Локальна доставка'),
            ('nova_poshta', 'Нова Пошта'),
        ],
        required=True,
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600",
                "id": "delivery-type",
            }
        ),
        label="Тип доставки",
    )
    
    # Payment type selection
    payment_type = forms.ChoiceField(
        choices=[
            ('iban', 'IBAN'),
            ('liqupay', 'LiquPay'),
        ],
        required=True,
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600",
                "id": "payment-type",
            }
        ),
        label="Тип оплати",
    )
    
    # Address field for local delivery
    delivery_address = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600",
                "placeholder": "Введіть повну адресу доставки",
                "rows": "3",
                "id": "delivery-address",
            }
        ),
        label="Адреса доставки",
    )
    
    # Nova Poshta fields (existing)
    delivery_city = forms.CharField(
        max_length=200,
        required=False,
        label="Місто доставки",
        widget=forms.HiddenInput(),
    )

    delivery_city_label = forms.CharField(
        required=False,
        label="Місто доставки",
        widget=forms.TextInput(
            attrs={
                "id": "city-input",
                "autocomplete": "off",
                "placeholder": "Введіть місто доставки",
                "class": "w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600",
            }
        ),
    )
    delivery_branch = forms.CharField(
        max_length=200,
        required=False,
        label="Відділення Нової Пошти",
        widget=forms.HiddenInput(),
    )

    delivery_branch_label = forms.CharField(
        required=False,
        label="Оберіть відділення",
        widget=forms.Select(
            attrs={"id": "warehouse-select", "class": "border p-2 w-full"}
        ),
    )

    delivery_branch_name = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_customer_phone_number(self):
        phone = self.cleaned_data["customer_phone_number"]
        if not re.match(r"^0[0-9]{9}$", phone):
            raise forms.ValidationError(
                "Введіть коректний номер телефону у форматі 0XXXXXXXXX"
            )
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        delivery_type = cleaned_data.get('delivery_type')
        
        if delivery_type == 'local':
            # For local delivery, address is required
            if not cleaned_data.get('delivery_address'):
                raise forms.ValidationError(
                    "Для локальної доставки необхідно вказати адресу"
                )
        elif delivery_type == 'nova_poshta':
            # For Nova Poshta, city and branch are required
            if not cleaned_data.get('delivery_city_label'):
                raise forms.ValidationError(
                    "Для доставки Новою Поштою необхідно вказати місто"
                )
            if not cleaned_data.get('delivery_branch_name'):
                raise forms.ValidationError(
                    "Для доставки Новою Поштою необхідно вибрати відділення"
                )
        
        return cleaned_data
