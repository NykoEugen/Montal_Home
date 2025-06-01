document.addEventListener('DOMContentLoaded', () => {
    // Функція для отримання CSRF-токена з cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Обробка кліку на кнопку "Додати до кошика"
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const furnitureId = button.getAttribute('data-id');
            const url = button.getAttribute('data-url');
            const csrftoken = getCookie('csrftoken');

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `furniture_id=${furnitureId}`
                });

                const data = await response.json();
                alert(data.message);
                const cartCountElement = document.getElementById('cart-count');
                if (cartCountElement) {
                    cartCountElement.textContent = data.cart_count;
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Сталася помилка при додаванні до кошика.');
            }
        });
    });

    // Обробка кліку на кнопку "Видалити з кошика"
    const removeFromCartButtons = document.querySelectorAll('.remove-from-cart');
    removeFromCartButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const furnitureId = button.getAttribute('data-id');
            const url = button.getAttribute('data-url');
            const csrftoken = getCookie('csrftoken');

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `furniture_id=${furnitureId}`
                });
                const data = await response.json();
                alert(data.message);
                const cartCountElement = document.getElementById('cart-count');
                if (cartCountElement) {
                    cartCountElement.textContent = data.cart_count;
                }
                // Оновлюємо сторінку кошика
                if (window.location.pathname === '/cart/') {
                    window.location.reload();
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Сталася помилка при видаленні з кошика.');
            }
        });
    });
});
