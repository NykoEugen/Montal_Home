// ── Cart-added modal — глобальна функція, доступна на всіх сторінках ──
function showCartAddedModal(productName, cartCount, cartUrl) {
    const modal = document.getElementById('cart-added-modal');
    if (!modal) return;
    const nameEl = document.getElementById('cart-modal-product-name');
    const gotoEl = document.getElementById('cart-modal-goto');
    if (nameEl) nameEl.textContent = productName;
    if (gotoEl && cartUrl) gotoEl.setAttribute('href', cartUrl);

    ['cart-count-mobile', 'cart-count-desktop'].forEach(id => {
        const el = document.getElementById(id);
        if (el && cartCount != null) el.textContent = cartCount;
    });

    modal.classList.remove('hidden');
    modal.classList.add('flex');

    const backdrop      = document.getElementById('cart-modal-backdrop');
    const closeXBtn     = document.getElementById('cart-modal-continue');
    const continueBtn   = document.getElementById('cart-modal-continue-btn');

    function closeModal() {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }

    if (closeXBtn)   closeXBtn.onclick   = closeModal;
    if (continueBtn) continueBtn.onclick = closeModal;
    if (backdrop)    backdrop.onclick    = closeModal;
    document.addEventListener('keydown', function onEsc(ev) {
        if (ev.key === 'Escape') { closeModal(); document.removeEventListener('keydown', onEsc); }
    }, { once: true });
}

document.addEventListener('DOMContentLoaded', () => {
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

    function updateCartBadge(count) {
        ['cart-count-mobile', 'cart-count-desktop'].forEach(id => {
            const el = document.getElementById(id);
            if (el && count != null) el.textContent = count;
        });
    }

    // Legacy .add-to-cart buttons (catalog listing)
    document.querySelectorAll('.add-to-cart').forEach(button => {
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
                    body: `furniture_id=${furnitureId}`,
                });
                const data = await response.json();
                updateCartBadge(data.cart_count);
                if (typeof showCartAddedModal === 'function') {
                    showCartAddedModal(data.name || 'Товар', data.cart_count, '/cart/');
                }
            } catch (error) {
                console.error('Cart add error:', error);
            }
        });
    });

    // Remove-from-cart buttons
    document.querySelectorAll('.remove-from-cart').forEach(button => {
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
                    body: `furniture_id=${furnitureId}`,
                });
                const data = await response.json();
                updateCartBadge(data.cart_count);
                if (window.location.pathname.includes('/cart')) {
                    window.location.reload();
                }
            } catch (error) {
                console.error('Cart remove error:', error);
            }
        });
    });

    // Phone search form validation
    const phoneForm = document.getElementById('phone-search-form');
    if (phoneForm) {
        phoneForm.addEventListener('submit', function(e) {
            const phoneInput = phoneForm.querySelector('input[name="phone_number"]');
            if (!phoneInput) return;
            if (!/^0[0-9]{9}$/.test(phoneInput.value)) {
                e.preventDefault();
                phoneInput.classList.add('border-red-500');
                phoneInput.focus();
            } else {
                phoneInput.classList.remove('border-red-500');
            }
        });
    }
});
