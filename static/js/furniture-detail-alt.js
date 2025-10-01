// Alternative furniture detail page functionality
document.addEventListener('DOMContentLoaded', () => {
    const mainImg = document.getElementById('alt-main-image');
    const thumbs = Array.from(document.querySelectorAll('.thumb-item'));
    const galleryDots = Array.from(document.querySelectorAll('.gallery-dot'));
    const prevBtn = document.querySelector('.gallery-nav-prev');
    const nextBtn = document.querySelector('.gallery-nav-next');
    const thumbScroller = document.querySelector('[data-thumb-scroller]');
    const thumbPrev = document.querySelector('.thumb-nav-prev');
    const thumbNext = document.querySelector('.thumb-nav-next');

    function updateActiveThumb(index) {
        thumbs.forEach((el, i) => {
            if (i === index) {
                el.classList.add('ring-2', 'ring-brown-800');
            } else {
                el.classList.remove('ring-2', 'ring-brown-800');
            }
        });
    }

    function updateDots(index) {
        galleryDots.forEach((dot, i) => {
            if (i === index) {
                dot.classList.add('bg-brown-800');
                dot.classList.remove('bg-white/80');
            } else {
                dot.classList.remove('bg-brown-800');
                dot.classList.add('bg-white/80');
            }
        });
    }

    function setGalleryImage(index) {
        if (!mainImg || !thumbs.length) {
            return;
        }
        const maxIndex = thumbs.length - 1;
        const clamped = Math.max(0, Math.min(index, maxIndex));
        const thumb = thumbs[clamped];
        const url = thumb?.getAttribute('data-full');
        if (!url) {
            return;
        }
        mainImg.src = url;
        mainImg.setAttribute('data-current-index', String(clamped));
        updateActiveThumb(clamped);
        updateDots(clamped);
        scrollThumbIntoView(clamped);
    }

    function clearGallerySelection() {
        thumbs.forEach(el => el.classList.remove('ring-2', 'ring-brown-800'));
        galleryDots.forEach(dot => {
            dot.classList.remove('bg-brown-800');
            dot.classList.add('bg-white/80');
        });
        if (mainImg) {
            mainImg.setAttribute('data-current-index', '-1');
        }
    }

    function scrollThumbIntoView(index) {
        if (!thumbScroller || !thumbs.length) {
            return;
        }
        const thumb = thumbs[index];
        if (!thumb) {
            return;
        }
        const scrollerRect = thumbScroller.getBoundingClientRect();
        const thumbRect = thumb.getBoundingClientRect();
        const padding = 8;
        if (thumbRect.left < scrollerRect.left) {
            thumbScroller.scrollBy({ left: thumbRect.left - scrollerRect.left - padding, behavior: 'smooth' });
        } else if (thumbRect.right > scrollerRect.right) {
            thumbScroller.scrollBy({ left: thumbRect.right - scrollerRect.right + padding, behavior: 'smooth' });
        }
    }

    thumbs.forEach((t, index) => t.addEventListener('click', () => {
        setGalleryImage(index);
    }));

    if (thumbPrev && thumbScroller) {
        thumbPrev.addEventListener('click', () => {
            thumbScroller.scrollBy({ left: -(thumbScroller.clientWidth * 0.6), behavior: 'smooth' });
        });
    }

    if (thumbNext && thumbScroller) {
        thumbNext.addEventListener('click', () => {
            thumbScroller.scrollBy({ left: thumbScroller.clientWidth * 0.6, behavior: 'smooth' });
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (!thumbs.length || !mainImg) return;
            const current = parseInt(mainImg.getAttribute('data-current-index') || '0', 10);
            const nextIndex = (current - 1 + thumbs.length) % thumbs.length;
            setGalleryImage(nextIndex);
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (!thumbs.length || !mainImg) return;
            const current = parseInt(mainImg.getAttribute('data-current-index') || '0', 10);
            const nextIndex = (current + 1) % thumbs.length;
            setGalleryImage(nextIndex);
        });
    }

    const priceEl = document.getElementById('alt-main-price');
    const origEl = document.getElementById('alt-original-price');
    const sizeChips = document.querySelectorAll('.size-chip');
    const variantChips = document.querySelectorAll('.variant-chip');
    
    const parameterCells = new Map();
    document.querySelectorAll('[data-param-key]').forEach(cell => {
        const key = cell.getAttribute('data-param-key');
        if (key) {
            parameterCells.set(key, cell);
        }
    });

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

    resetVariantParameterCells();

    function resetVariantParameterCells(exceptKey = null) {
        if (!parameterCells.size) {
            return;
        }
        parameterCells.forEach((cell, key) => {
            if (key === 'dimensions' || (exceptKey && key === exceptKey)) {
                return;
            }
            const base = cell.getAttribute('data-base') || '';
            cell.textContent = base;
        });
    }

    function applyVariantParameter(key, value) {
        if (!parameterCells.size) {
            return;
        }
        if (!key) {
            resetVariantParameterCells();
            return;
        }
        const cell = parameterCells.get(key);
        resetVariantParameterCells(key);
        if (cell) {
            const base = cell.getAttribute('data-base') || '';
            cell.textContent = value || base;
        }
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
            clearGallerySelection();
            if (thumbScroller) {
                thumbScroller.scrollTo({ left: 0, behavior: 'smooth' });
            }
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
        const paramKey = b.getAttribute('data-param-key');
        const paramValue = b.getAttribute('data-param-value');


        
        selectedPrice = currentPrice > 0 ? currentPrice : basePrice;
        applyVariantParameter(paramKey, paramValue);

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
        if (mainImg) {
            // Reset gallery highlighting when switching size variants with custom visuals
            clearGallerySelection();
        }
        recompute();
    }));

    // Ensure initial state reflects first thumbnail when available
    if (thumbs.length && mainImg) {
        const startIndex = parseInt(mainImg.getAttribute('data-current-index') || '0', 10);
        if (startIndex >= 0) {
            updateActiveThumb(startIndex);
            updateDots(startIndex);
            scrollThumbIntoView(startIndex);
        }
    }

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
