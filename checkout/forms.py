from django import forms
import re

class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600',
            'placeholder': "Введіть ім'я"
        }),
        label="Ім'я"
    )
    customer_last_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600',
            'placeholder': 'Введіть прізвище'
        }),
        label="Прізвище"
    )
    customer_phone_number = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600',
            'placeholder': '0XXXXXXXXX',
            'pattern': '0[0-9]{9}',
            'title': 'Введіть номер у форматі 0XXXXXXXXX'
        }),
        label="Номер телефону"
    )
    customer_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600',
            'placeholder': 'Введіть email (необов’язково)'
        }),
        label="Email"
    )
    # Added for future Nova Poshta integration
    delivery_city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600',
            'placeholder': 'Введіть місто доставки'
        }),
        label="Місто доставки"
    )
    delivery_branch = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-brown-600',
            'placeholder': 'Введіть номер або адресу відділення'
        }),
        label="Відділення Нової Пошти"
    )

    def clean_customer_phone_number(self):
        phone = self.cleaned_data['customer_phone_number']
        if not re.match(r'^0[0-9]{9}$', phone):
            raise forms.ValidationError("Введіть коректний номер телефону у форматі 0XXXXXXXXX")
        return phone