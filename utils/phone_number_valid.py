import re


def clean_phone(phone_number):
    clean_number = phone_number.replace(" ", "")

    if not re.match(r"^(05[0-9]|06[0-9]|07[0-3]|09[3-9])\d{7}$", clean_number):
        return False
    return clean_number
