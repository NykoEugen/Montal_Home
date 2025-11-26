from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.core.mail import send_mail

from checkout.models import Order

from .forms import (
    PhoneLoginForm,
    PhonePasswordResetForm,
    PhoneRegistrationForm,
)


def _attach_orders_to_user(user) -> None:
    if not user or not user.username:
        return
    Order.objects.filter(
        customer_phone_number=user.username,
        user__isnull=True,
    ).update(user=user)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("checkout:order_history")

    form = PhoneLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone_number"]
        password = form.cleaned_data["password"]
        user = authenticate(request, username=phone, password=password)
        if user is None:
            messages.error(request, "Невірний номер телефону або пароль.", extra_tags="user")
        else:
            _attach_orders_to_user(user)
            login(request, user)
            return redirect(request.GET.get("next") or "checkout:order_history")

    return render(request, "shop/auth/login.html", {"form": form})


def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("checkout:order_history")

    form = PhoneRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        _attach_orders_to_user(user)
        login(request, user)
        messages.success(
            request,
            "Обліковий запис створено! Ми прив'язали попередні замовлення за вашим номером.",
            extra_tags="user",
        )
        return redirect("checkout:order_history")

    return render(request, "shop/auth/register.html", {"form": form})


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("shop:home")


def password_reset_request(request: HttpRequest) -> HttpResponse:
    form = PhonePasswordResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.user
        if not user or not user.email:
            messages.error(
                request,
                "Не вдалося надіслати лист. Перевірте email у профілі або замовленні.",
                extra_tags="user",
            )
        else:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(
                reverse("shop:password_reset_confirm", args=[uid, token])
            )
            subject = "Скидання паролю на Montal Home"
            message = (
                "Ви отримали це повідомлення, бо запросили скидання паролю.\n\n"
                f"Перейдіть за посиланням, щоб створити новий пароль:\n{reset_link}\n\n"
                "Якщо ви не запитували скидання, просто проігноруйте цей лист."
            )
            send_mail(
                subject,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@montal.com.ua"),
                [user.email],
            )
            messages.success(
                request,
                "Ми надіслали посилання для скидання паролю на ваш email.",
                extra_tags="user",
            )
            return redirect("shop:login")

    return render(request, "shop/auth/password_reset_request.html", {"form": form})


def password_reset_confirm(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Посилання недійсне або застаріле.", extra_tags="user")
        return redirect("shop:password_reset")

    form = SetPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        _attach_orders_to_user(user)
        login(request, user)
        messages.success(request, "Пароль змінено. Ви увійшли в систему.", extra_tags="user")
        return redirect("checkout:order_history")

    return render(
        request,
        "shop/auth/password_reset_confirm.html",
        {"form": form, "user": user},
    )
