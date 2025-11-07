// Alternative furniture detail page functionality
document.addEventListener('DOMContentLoaded', () => {
    const mainImg = document.getElementById('alt-main-image');
    const thumbs = Array.from(document.querySelectorAll('.thumb-item'));
    const mainImageWrapper = document.getElementById('alt-main-image-wrapper');
    const galleryDots = Array.from(document.querySelectorAll('.gallery-dot'));
    const prevBtn = document.querySelector('.gallery-nav-prev');
    const nextBtn = document.querySelector('.gallery-nav-next');
    const thumbScroller = document.querySelector('[data-thumb-scroller]');
    const thumbPrev = document.querySelector('.thumb-nav-prev');
    const thumbNext = document.querySelector('.thumb-nav-next');
    const customOptionChips = Array.from(document.querySelectorAll('.custom-option-chip'));
    const customOptionGroup = document.querySelector('[data-custom-option-group]');
    const customOptionWarning = document.querySelector('[data-custom-option-warning]');
    const customOptionInput = document.getElementById('alt-custom-option-input');
    const CHIP_ACTIVE_CLASS = 'chip--active';
    let selectedOptionPrice = 0;

    function applyCustomOptionDefaultStyles(chip) {
        chip.classList.remove(CHIP_ACTIVE_CLASS);
    }

    function applyCustomOptionSelectedStyles(chip) {
        chip.classList.add(CHIP_ACTIVE_CLASS);
    }

    function setCustomOptionSelection(chip) {
        if (!customOptionChips.length) {
            return;
        }
        customOptionChips.forEach(applyCustomOptionDefaultStyles);
        if (!chip) {
            selectedOptionPrice = 0;
            if (customOptionInput) {
                customOptionInput.value = '';
            }
            recompute();
            return;
        }
        applyCustomOptionSelectedStyles(chip);
        const optionId = chip.dataset.optionId || '';
        selectedOptionPrice = parseFloat(chip.dataset.optionPrice || '0') || 0;
        if (customOptionInput) {
            customOptionInput.value = optionId;
        }
        if (customOptionWarning) {
            customOptionWarning.classList.add('hidden');
        }
        if (customOptionGroup) {
            customOptionGroup.classList.remove('ring-2', 'ring-red-300');
        }
        recompute();
    }

    function hasCustomOptionSelected() {
        if (!customOptionChips.length) {
            return true;
        }
        return Boolean(customOptionInput && customOptionInput.value);
    }

    function ensureCustomOptionSelection() {
        const valid = hasCustomOptionSelected();
        if (!valid) {
            if (customOptionWarning) {
                customOptionWarning.classList.remove('hidden');
            }
            if (customOptionGroup && !customOptionGroup.classList.contains('ring-2')) {
                customOptionGroup.classList.add('ring-2', 'ring-red-300');
            }
            customOptionGroup?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return valid;
    }

    customOptionChips.forEach(chip => {
        applyCustomOptionDefaultStyles(chip);
        chip.addEventListener('click', () => setCustomOptionSelection(chip));
    });

    const initialAltOptionId = customOptionInput ? customOptionInput.value : '';
    if (initialAltOptionId) {
        const initialAltChip = customOptionChips.find(chip => chip.dataset.optionId === initialAltOptionId);
        if (initialAltChip) {
            setCustomOptionSelection(initialAltChip);
        }
    }

    function setWrapperAspect(width, height) {
        if (!mainImageWrapper) {
            return;
        }

        if (width && height && Number(width) > 0 && Number(height) > 0) {
            mainImageWrapper.style.aspectRatio = `${width} / ${height}`;
        } else {
            mainImageWrapper.style.aspectRatio = '1 / 1';
        }
    }

    function syncMainImageMetadata(source) {
        if (!mainImg || !source) {
            return;
        }

        const { width, height } = source.dataset || {};
        if (width) {
            mainImg.dataset.width = width;
        }
        if (height) {
            mainImg.dataset.height = height;
        }
        setWrapperAspect(width, height);
    }

    function applyAspectFromLoadedImage() {
        if (!mainImg) return;
        const { naturalWidth, naturalHeight } = mainImg;
        if (naturalWidth && naturalHeight) {
            setWrapperAspect(naturalWidth, naturalHeight);
        }
    }

    if (mainImg) {
        if (mainImg.dataset && mainImg.dataset.width && mainImg.dataset.height) {
            setWrapperAspect(mainImg.dataset.width, mainImg.dataset.height);
        }
        if (mainImg.complete) {
            applyAspectFromLoadedImage();
        }
        mainImg.addEventListener('load', applyAspectFromLoadedImage);
        mainImg.addEventListener('error', () => setWrapperAspect());
    }

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

    let currentIndex = parseInt(mainImg?.getAttribute('data-current-index') || '0', 10);
    if (Number.isNaN(currentIndex)) {
        currentIndex = 0;
    }

    function setGalleryImage(index) {
        if (!mainImg || !thumbs.length) {
            return;
        }
        const maxIndex = thumbs.length - 1;
        const clamped = Math.max(0, Math.min(index, maxIndex));
        const thumb = thumbs[clamped];
        const url = thumb?.getAttribute('data-full');
        const thumbSrcset = thumb?.getAttribute('data-srcset');
        const thumbSizes = thumb?.getAttribute('data-sizes');
        if (!url) {
            return;
        }
        mainImg.src = url;
        if (thumbSrcset) {
            mainImg.setAttribute('srcset', thumbSrcset);
        } else {
            mainImg.removeAttribute('srcset');
        }
        if (thumbSizes) {
            mainImg.setAttribute('sizes', thumbSizes);
        } else {
            mainImg.removeAttribute('sizes');
        }
        syncMainImageMetadata(thumb);
        mainImg.setAttribute('data-current-index', String(clamped));
        currentIndex = clamped;
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
        currentIndex = -1;
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
            const baseIndex = currentIndex >= 0 ? currentIndex : 0;
            const nextIndex = (baseIndex - 1 + thumbs.length) % thumbs.length;
            setGalleryImage(nextIndex);
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (!thumbs.length || !mainImg) return;
            const baseIndex = currentIndex >= 0 ? currentIndex : 0;
            const nextIndex = (baseIndex + 1) % thumbs.length;
            setGalleryImage(nextIndex);
        });
    }

    const priceEl = document.getElementById('alt-main-price');
    const origEl = document.getElementById('alt-original-price');
    const sizeChips = document.querySelectorAll('.size-chip');
    const variantChips = document.querySelectorAll('.variant-chip');
    const stockLabel = document.getElementById('alt-stock-label');
    const stockLabelClassMap = {
        in_stock: ['bg-green-100', 'text-green-700'],
        on_order: ['bg-orange-100', 'text-orange-700']
    };
    
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
    const addToCartForm = document.querySelector('form[action*="add_to_cart_from_detail"]');

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

    function updateStockLabel(status, labelText) {
        if (!stockLabel) {
            return;
        }
        const fallbackStatus = stockLabel.dataset.baseStatus || 'in_stock';
        const fallbackText = stockLabel.dataset.baseText || '';
        const targetStatus = status || fallbackStatus;
        const targetText = labelText || fallbackText;

        stockLabel.classList.remove('bg-green-100', 'text-green-700', 'bg-orange-100', 'text-orange-700');
        const classes = stockLabelClassMap[targetStatus];
        if (classes) {
            stockLabel.classList.add(...classes);
        }
        stockLabel.textContent = targetText;
    }

    function recompute() {
        let total = selectedPrice;
        let originalTotal = selectedPrice;
        
        // Get selected size chip info for promotional pricing
        const selectedSizeChip = document.querySelector(`.size-chip.${CHIP_ACTIVE_CLASS}`);
        const isOnSale = selectedSizeChip ? selectedSizeChip.getAttribute('data-is-on-sale') === 'true' : false;
        const originalSizePrice = selectedSizeChip ? parseFloat(selectedSizeChip.getAttribute('data-original-price') || '0') : 0;
        
        // Use original price for comparison if on sale
        if (isOnSale && originalSizePrice > 0) {
            originalTotal = originalSizePrice;
        }

        total += selectedOptionPrice;
        originalTotal += selectedOptionPrice;
        
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

    if (addToCartForm) {
        addToCartForm.addEventListener('submit', (e) => {
            if (!ensureCustomOptionSelection()) {
                e.preventDefault();
            }
        });
    }

    recompute();

    // Variant chip functionality
    variantChips.forEach(b => b.addEventListener('click', () => {
        variantChips.forEach(x => x.classList.remove(CHIP_ACTIVE_CLASS));
        b.classList.add(CHIP_ACTIVE_CLASS);
        const imageUrl = b.getAttribute('data-image');
        const imageSrcset = b.getAttribute('data-srcset');
        const imageSizes = b.getAttribute('data-sizes');
        const linkUrl = b.getAttribute('data-link');
        const variantId = b.getAttribute('data-id');
        const nextStatus = b.getAttribute('data-stock-status');
        const nextStatusLabel = b.getAttribute('data-stock-label');
        
        if (imageUrl && mainImg) {
            const variantWidth = b.getAttribute('data-image-width');
            const variantHeight = b.getAttribute('data-image-height');
            if (variantWidth) {
                mainImg.dataset.width = variantWidth;
            }
            if (variantHeight) {
                mainImg.dataset.height = variantHeight;
            }
            const matchingThumb = thumbs.find(t => t.getAttribute('data-full') === imageUrl);
            if (matchingThumb) {
                syncMainImageMetadata(matchingThumb);
                const thumbSrcset = matchingThumb.getAttribute('data-srcset');
                const thumbSizes = matchingThumb.getAttribute('data-sizes');
                if (thumbSrcset) {
                    mainImg.setAttribute('srcset', thumbSrcset);
                } else if (imageSrcset) {
                    mainImg.setAttribute('srcset', imageSrcset);
                } else {
                    mainImg.removeAttribute('srcset');
                }
                if (thumbSizes) {
                    mainImg.setAttribute('sizes', thumbSizes);
                } else if (imageSizes) {
                    mainImg.setAttribute('sizes', imageSizes);
                } else {
                    mainImg.removeAttribute('sizes');
                }
            } else {
                setWrapperAspect(variantWidth, variantHeight);
                if (imageSrcset) {
                    mainImg.setAttribute('srcset', imageSrcset);
                } else {
                    mainImg.removeAttribute('srcset');
                }
                if (imageSizes) {
                    mainImg.setAttribute('sizes', imageSizes);
                } else {
                    mainImg.removeAttribute('sizes');
                }
            }
            mainImg.src = imageUrl;
            clearGallerySelection();
            if (thumbScroller) {
                thumbScroller.scrollTo({ left: 0, behavior: 'smooth' });
            }
        }

        if (variantInput) {
            variantInput.value = variantId || '';
        }

        updateStockLabel(nextStatus, nextStatusLabel);
        
        // If there's a link, you can handle it here
        if (linkUrl) {
            // You can either open in new tab or handle differently
            // window.open(linkUrl, '_blank');
        }
    }));

    sizeChips.forEach(b => b.addEventListener('click', () => {
        sizeChips.forEach(x => x.classList.remove(CHIP_ACTIVE_CLASS));
        b.classList.add(CHIP_ACTIVE_CLASS);
        
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
        recompute();
    }));

    // Ensure initial state reflects first thumbnail when available
    if (thumbs.length && mainImg) {
        const startIndex = parseInt(mainImg.getAttribute('data-current-index') || '0', 10);
        if (startIndex >= 0) {
            updateActiveThumb(startIndex);
            updateDots(startIndex);
            scrollThumbIntoView(startIndex);
            const initialThumb = thumbs[startIndex];
            if (initialThumb) {
                syncMainImageMetadata(initialThumb);
            }
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

    if (stockLabel) {
        updateStockLabel(stockLabel.dataset.defaultStatus, stockLabel.dataset.defaultText);
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
        const defaultVariant = Array.from(variantChips).find(b => b.classList.contains(CHIP_ACTIVE_CLASS));
        if (defaultVariant) {
            const variantId = defaultVariant.getAttribute('data-id');
            if (variantInput && variantId) {
                variantInput.value = variantId;
            }
            updateStockLabel(defaultVariant.getAttribute('data-stock-status'), defaultVariant.getAttribute('data-stock-label'));
        }
    }

    // Scroll stack tabs
    const scrollStack = document.querySelector('[data-scroll-stack]');
    if (scrollStack) {
        const stackTabs = Array.from(scrollStack.querySelectorAll('[data-scroll-tab]'));
        const stackCards = Array.from(scrollStack.querySelectorAll('[data-scroll-card]'));

        const activateStackSection = key => {
            stackTabs.forEach(tab => {
                const matches = tab.dataset.scrollTab === key;
                tab.classList.toggle('is-active', matches);
                if (matches) {
                    tab.setAttribute('aria-selected', 'true');
                } else {
                    tab.setAttribute('aria-selected', 'false');
                }
            });
            stackCards.forEach(card => {
                card.classList.toggle('is-active', card.dataset.scrollCard === key);
            });
        };

        stackTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.scrollTab;
                const card = scrollStack.querySelector(`[data-scroll-card="${target}"]`);
                if (card) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    activateStackSection(target);
                }
            });
        });

        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver(entries => {
                const visible = entries
                    .filter(entry => entry.isIntersecting)
                    .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
                if (visible.length) {
                    activateStackSection(visible[0].target.dataset.scrollCard);
                }
            }, {
                rootMargin: '-45% 0px -45% 0px',
                threshold: [0.1, 0.25, 0.5]
            });
            stackCards.forEach(card => observer.observe(card));
        }
    }
});
