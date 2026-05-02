import re

from django import forms

FIELD_CLASS = "w-full px-4 py-3 border border-beige-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-brown-500 transition bg-white text-brown-800 placeholder-brown-400"


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": FIELD_CLASS,
                "placeholder": "Введіть ім'я",
                "autocomplete": "given-name",
            }
        ),
        label="Ім'я",
    )
    customer_last_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": FIELD_CLASS,
                "placeholder": "Введіть прізвище",
                "autocomplete": "family-name",
            }
        ),
        label="Прізвище",
    )
    customer_phone_number = forms.CharField(
        max_length=13,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": FIELD_CLASS,
                "placeholder": "0XXXXXXXXX",
                "autocomplete": "tel",
                "inputmode": "tel",
            }
        ),
        label="Номер телефону",
    )
    customer_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": FIELD_CLASS,
                "placeholder": "email@example.com (необов'язково)",
                "autocomplete": "email",
            }
        ),
        label="Email",
    )
    customer_comment = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": FIELD_CLASS,
                "placeholder": "Побажання щодо замовлення, зручний час дзвінка тощо",
                "rows": "3",
            }
        ),
        label="Коментар",
    )

    def clean_customer_phone_number(self):
        phone = self.cleaned_data["customer_phone_number"].strip()
        if not re.match(r"^0[0-9]{9}$", phone):
            raise forms.ValidationError(
                "Введіть коректний номер телефону у форматі 0XXXXXXXXX"
            )
        return phone
