document.addEventListener('DOMContentLoaded', () => {
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    const removeFromCartButtons = document.querySelectorAll('.remove-from-cart');

    addToCartButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const furnitureId = button.getAttribute('data-id');
            const response = await fetch(`/add-to-cart/${furnitureId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            alert(data.message);
            document.getElementById('cart-count').textContent = data.cart_count;
        });
    });

    removeFromCartButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const furnitureId = button.getAttribute('data-id');
            const response = await fetch(`/remove-from-cart/${furnitureId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            alert(data.message);
            document.getElementById('cart-count').textContent = data.cart_count;
            // Оновлюємо сторінку кошика
            if (window.location.pathname === '/cart/') {
                window.location.reload();
            }
        });
    });
});

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
