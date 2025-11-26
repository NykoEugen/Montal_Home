from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class PhoneLoginForm(forms.Form):
    phone_number = forms.RegexField(
        regex=r"^0\d{9}$",
        max_length=10,
        error_messages={"invalid": "Введіть номер у форматі 0XXXXXXXXX."},
        label="Номер телефону",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        label="Пароль",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone_number"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border rounded-md focus:ring-2 focus:ring-brown-500 focus:outline-none",
                "placeholder": "0XXXXXXXXX",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border rounded-md focus:ring-2 focus:ring-brown-500 focus:outline-none",
            }
        )


class PhoneRegistrationForm(forms.Form):
    first_name = forms.CharField(label="Ім'я", max_length=150)
    last_name = forms.CharField(label="Прізвище", max_length=150)
    phone_number = forms.RegexField(
        regex=r"^0\d{9}$",
        max_length=10,
        error_messages={"invalid": "Введіть номер у форматі 0XXXXXXXXX."},
        label="Номер телефону",
    )
    email = forms.EmailField(label="Email", required=False)
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Пароль",
        min_length=8,
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Повторіть пароль",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ["first_name", "last_name", "email", "password1", "password2"]:
            self.fields[name].widget.attrs.update(
                {
                    "class": "w-full px-4 py-2 border rounded-md focus:ring-2 focus:ring-brown-500 focus:outline-none",
                }
            )
        self.fields["phone_number"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border rounded-md focus:ring-2 focus:ring-brown-500 focus:outline-none",
                "placeholder": "0XXXXXXXXX",
            }
        )
        self.fields["email"].widget.attrs.setdefault("placeholder", "name@example.com")

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"]
        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError("Обліковий запис з цим номером вже існує.")
        return phone

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Паролі не співпадають.")
        return cleaned

    def save(self) -> User:
        user = User(
            username=self.cleaned_data["phone_number"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data.get("email", ""),
        )
        user.set_password(self.cleaned_data["password1"])
        user.save()
        return user


class PhonePasswordResetForm(forms.Form):
    phone_number = forms.RegexField(
        regex=r"^0\d{9}$",
        max_length=10,
        error_messages={"invalid": "Введіть номер у форматі 0XXXXXXXXX."},
        label="Номер телефону",
    )
    email = forms.EmailField(
        label="Email для отримання посилання",
        required=False,
        help_text="Має збігатися з email у замовленні або профілі.",
    )

    user: User | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone_number"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border rounded-md focus:ring-2 focus:ring-brown-500 focus:outline-none",
                "placeholder": "0XXXXXXXXX",
            }
        )
        self.fields["email"].widget.attrs.update(
            {
                "class": "w-full px-4 py-2 border rounded-md focus:ring-2 focus:ring-brown-500 focus:outline-none",
                "placeholder": "name@example.com",
            }
        )

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get("phone_number")
        email = cleaned.get("email", "")
        if not phone:
            return cleaned

        try:
            user = User.objects.get(username=phone)
        except User.DoesNotExist:
            raise forms.ValidationError("Користувача з таким номером не знайдено.")

        if email and user.email and email != user.email:
            raise forms.ValidationError("Введений email не відповідає профілю.")

        # If user has no email, try to reuse the one from their latest order
        if not user.email:
            from checkout.models import Order  # Avoid circular import at module load

            order_email = (
                Order.objects.filter(customer_phone_number=phone)
                .order_by("-created_at")
                .values_list("customer_email", flat=True)
                .first()
            )
            if order_email and email and email != order_email:
                raise forms.ValidationError("Email не співпадає з даними замовлення.")
            if email:
                user.email = email
            elif order_email:
                user.email = order_email
            else:
                raise forms.ValidationError(
                    "У профілі немає email. Додайте його, щоб отримати посилання для скидання."
                )
            user.save(update_fields=["email"])
        elif not user.email and not email:
            raise forms.ValidationError("Додайте email, щоб надіслати посилання на відновлення.")

        self.user = user
        return cleaned
