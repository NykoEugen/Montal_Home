// Alternative furniture detail page functionality
document.addEventListener('DOMContentLoaded', () => {
    const mainImg = document.getElementById('alt-main-image');
    document.querySelectorAll('.thumb-item').forEach(t => t.addEventListener('click', () => {
        const url = t.getAttribute('data-full');
        if (url) mainImg.src = url;
    }));

    const priceEl = document.getElementById('alt-main-price');
    const origEl = document.getElementById('alt-original-price');
    const sizeChips = document.querySelectorAll('.size-chip');
    const variantChips = document.querySelectorAll('.variant-chip');
    

    const sizeInput = document.getElementById('alt-size-input');
    const variantInput = document.getElementById('alt-variant-input');
    const fabricSelect = document.getElementById('alt-fabric');
    const fabricInput = document.getElementById('alt-fabric-input');
    const fabricExtra = document.getElementById('alt-fabric-extra');
    const fabricExtraPrice = document.getElementById('alt-fabric-price');
    const dimCell = document.getElementById('alt-dimensions');
    const qty = document.getElementById('alt-qty');
    const qtyInput = document.getElementById('alt-qty-input');
    const fabricValue = parseFloat((fabricSelect?.parentElement?.getAttribute('data-fabric-value')) || '1');

    let basePrice = 0; 
    let selectedPrice = 0;
    if (priceEl) {
        basePrice = parseFloat(priceEl.textContent.replace(' грн','').trim());
        selectedPrice = basePrice;
    }

    function recompute() {
        let total = selectedPrice;
        let originalTotal = selectedPrice;
        
        // Get selected size chip info for promotional pricing
        const selectedSizeChip = document.querySelector('.size-chip.bg-beige-100');
        const isOnSale = selectedSizeChip ? selectedSizeChip.getAttribute('data-is-on-sale') === 'true' : false;
        const originalSizePrice = selectedSizeChip ? parseFloat(selectedSizeChip.getAttribute('data-original-price') || '0') : 0;
        
        // Use original price for comparison if on sale
        if (isOnSale && originalSizePrice > 0) {
            originalTotal = originalSizePrice;
        }
        
        if (fabricSelect && fabricSelect.value && fabricExtra && fabricExtraPrice) {
            const calculatedPrice = parseFloat(fabricSelect.options[fabricSelect.selectedIndex].getAttribute('data-calculated-price') || '0');
            if (calculatedPrice > 0) {
                fabricExtra.classList.remove('hidden');
                fabricExtraPrice.textContent = Math.round(calculatedPrice);
                total += calculatedPrice;
                originalTotal += calculatedPrice; // Add to original price too
            } else {
                fabricExtra.classList.add('hidden');
            }
        } else if (fabricExtra) {
            fabricExtra.classList.add('hidden');
        }
        
        const q = Math.max(1, parseInt(qty.value || '1', 10));
        if (qtyInput) qtyInput.value = String(q);
        total = total * q;
        originalTotal = originalTotal * q;
        
        if (priceEl) {
            if (isOnSale && originalTotal > total) {
                // Show promotional price and original price
                priceEl.textContent = Math.round(total) + ' грн';
                priceEl.className = 'text-3xl text-red-600 font-semibold';
                
                if (origEl) {
                    origEl.textContent = Math.round(originalTotal) + ' грн';
                    origEl.className = 'text-lg text-brown-500 line-through';
                    origEl.style.display = 'block';
                }
            } else {
                // Show regular price
                priceEl.textContent = Math.round(total) + ' грн';
                priceEl.className = 'text-3xl text-brown-800 font-semibold';
                
                if (origEl) {
                    origEl.style.display = 'none';
                }
            }
        }
    }

    // Variant chip functionality
    variantChips.forEach(b => b.addEventListener('click', () => {
        variantChips.forEach(x => x.classList.remove('bg-beige-100','ring-2','ring-brown-800'));
        b.classList.add('bg-beige-100','ring-2','ring-brown-800');
        const imageUrl = b.getAttribute('data-image');
        const linkUrl = b.getAttribute('data-link');
        const variantId = b.getAttribute('data-id');
        
        if (imageUrl && mainImg) {
            mainImg.src = imageUrl;
        }
        
        if (variantInput) {
            variantInput.value = variantId || '';
        }
        
        // If there's a link, you can handle it here
        if (linkUrl) {
            // You can either open in new tab or handle differently
            // window.open(linkUrl, '_blank');
        }
    }));

    sizeChips.forEach(b => b.addEventListener('click', () => {
        sizeChips.forEach(x => x.classList.remove('bg-beige-100','ring-2','ring-brown-800'));
        b.classList.add('bg-beige-100','ring-2','ring-brown-800');
        
        const currentPrice = parseFloat(b.getAttribute('data-price') || '0');
        const originalPrice = parseFloat(b.getAttribute('data-original-price') || '0');
        const isOnSale = b.getAttribute('data-is-on-sale') === 'true';
        

        
        selectedPrice = currentPrice > 0 ? currentPrice : basePrice;
        
        // Update price display to show promotional pricing
        if (priceEl) {
            if (isOnSale && originalPrice > currentPrice) {
                // Show promotional price and original price
                priceEl.textContent = Math.round(currentPrice) + ' грн';
                priceEl.className = 'text-3xl text-red-600 font-semibold';
                
                if (origEl) {
                    origEl.textContent = Math.round(originalPrice) + ' грн';
                    origEl.className = 'text-lg text-brown-500 line-through';
                    origEl.style.display = 'block';
                }
            } else {
                // Show regular price
                priceEl.textContent = Math.round(currentPrice) + ' грн';
                priceEl.className = 'text-3xl text-brown-800 font-semibold';
                
                if (origEl) {
                    origEl.style.display = 'none';
                }
            }
        }
        
        if (sizeInput) sizeInput.value = b.getAttribute('data-id') || '';
        const d = b.getAttribute('data-dimensions');
        if (dimCell && d) dimCell.textContent = d; else if (dimCell) dimCell.textContent = dimCell.getAttribute('data-base') || '';
        recompute();
    }));

    if (fabricSelect) {
        fabricSelect.addEventListener('change', () => {
            if (fabricInput) fabricInput.value = fabricSelect.value || '';
            recompute();
        });
    }

    if (qty) {
        qty.addEventListener('input', recompute);
    }

    // Auto-select base size if provided
    const buyCard = document.getElementById('buy-card');
    const baseIdAttr = buyCard ? buyCard.getAttribute('data-base-size-id') : '';
    const baseId = baseIdAttr ? parseInt(baseIdAttr, 10) : null;
    if (baseId !== null && !Number.isNaN(baseId)) {
        const baseBtn = Array.from(sizeChips).find(b => (b.getAttribute('data-id') || '') == String(baseId));
        if (baseBtn) {
            baseBtn.click();
        }
    } else if (sizeChips.length) {
        // fallback: select first
        sizeChips[0].click();
    }

    // Auto-select default variant if available
    if (variantChips.length) {
        const defaultVariant = Array.from(variantChips).find(b => b.classList.contains('bg-beige-100'));
        if (defaultVariant) {
            const variantId = defaultVariant.getAttribute('data-id');
            if (variantInput && variantId) {
                variantInput.value = variantId;
            }
        }
    }

    // Tabs
    const tabs = document.querySelectorAll('.tab-link');
    const panes = {
        desc: document.getElementById('tab-desc'),
        specs: document.getElementById('tab-specs'),
        shipping: document.getElementById('tab-shipping')
    };
    tabs.forEach(btn => btn.addEventListener('click', () => {
        tabs.forEach(b => b.classList.remove('active','border-brown-800'));
        Object.values(panes).forEach(p => p.classList.add('hidden'));
        const key = btn.getAttribute('data-tab');
        btn.classList.add('active','border-brown-800');
        if (panes[key]) panes[key].classList.remove('hidden');
    }));
});
