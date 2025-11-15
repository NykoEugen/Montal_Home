// Furniture detail page functionality
document.addEventListener('DOMContentLoaded', function() {
    const sizeSelect = document.getElementById('size-variant');
    const fabricSelect = document.getElementById('fabric-category');
    const fabricPriceInfo = document.getElementById('fabric-price-info');
    const fabricPriceSpan = document.getElementById('fabric-price');
    const mainPriceElement = document.getElementById('main-price');
    const originalPriceElement = document.getElementById('original-price');
    const qtyInput = document.getElementById('quantity');
    const customOptionChips = Array.from(document.querySelectorAll('.custom-option-chip'));
    const customOptionGroup = document.querySelector('[data-custom-option-group]');
    const customOptionWarning = document.querySelector('[data-custom-option-warning]');
    const selectedCustomOptionInput = document.getElementById('selected-custom-option');
    const qbCustomOptionInput = document.getElementById('qb-custom-option');
    const colorSwatches = Array.from(document.querySelectorAll('[data-color-swatch]'));
    const selectedColorInput = document.getElementById('selected-color-id');
    const qbColorInput = document.getElementById('qb-color-id');
    const selectedColorLabel = document.querySelector('[data-selected-color-label]');
    
    const CHIP_ACTIVE_CLASS = 'chip--active';
    let selectedOptionPrice = 0;
    let activeColorSwatch = null;

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
            if (selectedCustomOptionInput) selectedCustomOptionInput.value = '';
            if (qbCustomOptionInput) qbCustomOptionInput.value = '';
            updateTotalPrice();
            return;
        }
        applyCustomOptionSelectedStyles(chip);
        const optionId = chip.dataset.optionId || '';
        selectedOptionPrice = parseFloat(chip.dataset.optionPrice || '0') || 0;
        if (selectedCustomOptionInput) {
            selectedCustomOptionInput.value = optionId;
        }
        if (qbCustomOptionInput) {
            qbCustomOptionInput.value = optionId;
        }
        if (customOptionWarning) {
            customOptionWarning.classList.add('hidden');
        }
        if (customOptionGroup) {
            customOptionGroup.classList.remove('ring-2', 'ring-red-300');
        }
        updateTotalPrice();
    }

    function hasCustomOptionSelected() {
        if (!customOptionChips.length) {
            return true;
        }
        const selectedValue =
            (selectedCustomOptionInput && selectedCustomOptionInput.value) ||
            (qbCustomOptionInput && qbCustomOptionInput.value) ||
            '';
        return Boolean(selectedValue);
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

    function updateSelectedColorLabel(text) {
        if (!selectedColorLabel) return;
        selectedColorLabel.textContent = text || 'Колір не обрано';
    }

    function clearColorSelection() {
        if (!colorSwatches.length) return;
        colorSwatches.forEach(swatch => {
            swatch.classList.remove('ring-2', 'ring-brown-600', 'bg-white');
            swatch.setAttribute('aria-pressed', 'false');
        });
        activeColorSwatch = null;
        if (selectedColorInput) selectedColorInput.value = '';
        if (qbColorInput) qbColorInput.value = '';
        updateSelectedColorLabel('Колір не обрано');
    }

    function setColorSelection(target) {
        if (!colorSwatches.length || !target) {
            clearColorSelection();
            return;
        }
        if (activeColorSwatch === target) {
            clearColorSelection();
            return;
        }
        colorSwatches.forEach(swatch => {
            swatch.classList.remove('ring-2', 'ring-brown-600', 'bg-white');
            swatch.setAttribute('aria-pressed', 'false');
        });
        target.classList.add('ring-2', 'ring-brown-600', 'bg-white');
        target.setAttribute('aria-pressed', 'true');
        activeColorSwatch = target;
        const colorId = target.dataset.colorId || '';
        const colorName = target.dataset.colorName || '';
        const paletteName = target.dataset.paletteName || '';
        const label = colorName;
        if (selectedColorInput) selectedColorInput.value = colorId;
        if (qbColorInput) qbColorInput.value = colorId;
        updateSelectedColorLabel(label || 'Колір не обрано');
    }

    colorSwatches.forEach(swatch => {
        swatch.addEventListener('click', () => setColorSelection(swatch));
    });

    customOptionChips.forEach(chip => {
        applyCustomOptionDefaultStyles(chip);
        chip.addEventListener('click', () => {
            setCustomOptionSelection(chip);
        });
    });

    const initialOptionId = selectedCustomOptionInput ? selectedCustomOptionInput.value : '';
    if (initialOptionId) {
        const initialChip = customOptionChips.find(chip => chip.dataset.optionId === initialOptionId);
        if (initialChip) {
            setCustomOptionSelection(initialChip);
        }
    }

    // Get the base furniture price
    let basePrice = 0;
    let originalPrice = 0;
    let selectedSizePrice = 0;
    let isPromotional = false;
    
    if (mainPriceElement) {
        basePrice = parseFloat(mainPriceElement.textContent.replace(' грн', '').trim());
        selectedSizePrice = basePrice;
        
        // Check if furniture is promotional
        if (originalPriceElement && originalPriceElement.style.display !== 'none') {
            originalPrice = parseFloat(originalPriceElement.textContent.replace(' грн', '').trim());
            isPromotional = true;
        } else {
            originalPrice = basePrice;
            isPromotional = false;
        }
    }
    
    // Get fabric_value from the data attribute
    const fabricValueElement = document.querySelector('[data-fabric-value]');
    const fabricValue = fabricValueElement ? parseFloat(fabricValueElement.getAttribute('data-fabric-value')) : 1.0;
    
    // Function to update total price
    function updateTotalPrice() {
        let totalPrice = selectedSizePrice;
        let originalTotalPrice = selectedSizePrice;
        
        // Get selected option info
        const selectedOption = sizeSelect ? sizeSelect.options[sizeSelect.selectedIndex] : null;
        const isOnSale = selectedOption ? selectedOption.getAttribute('data-is-on-sale') === 'true' : false;
        const originalSizePrice = selectedOption ? parseFloat(selectedOption.getAttribute('data-original-price') || 0) : 0;
        
        // Debug logging
        console.log('updateTotalPrice:', {
            selectedSizePrice,
            selectedOptionPrice,
            isOnSale,
            originalSizePrice,
            selectedOption: selectedOption ? selectedOption.text : 'none'
        });
        
        // Use original price for comparison if on sale
        if (isOnSale && originalSizePrice > 0) {
            originalTotalPrice = originalSizePrice;
        }

        totalPrice += selectedOptionPrice;
        originalTotalPrice += selectedOptionPrice;
        
        // Add fabric cost if fabric is selected
        if (fabricSelect && fabricSelect.value) {
            const selectedFabricOption = fabricSelect.options[fabricSelect.selectedIndex];
            const fabricPrice = parseFloat(selectedFabricOption.getAttribute('data-price') || 0);
            if (fabricPrice > 0) {
                const fabricCost = fabricPrice * fabricValue;
                totalPrice += fabricCost;
                originalTotalPrice += fabricCost; // Add to original price too
                fabricPriceSpan.textContent = Math.round(fabricCost);
                fabricPriceInfo.classList.remove('hidden');
            } else {
                fabricPriceInfo.classList.add('hidden');
            }
        } else {
            fabricPriceInfo.classList.add('hidden');
        }
        
        // Multiply by quantity for display only
        const qty = qtyInput ? Math.max(1, parseInt(qtyInput.value || '1', 10)) : 1;
        totalPrice = totalPrice * qty;
        originalTotalPrice = originalTotalPrice * qty;
        
        // Debug logging
        console.log('Final prices:', {
            totalPrice,
            originalTotalPrice,
            selectedOptionPrice,
            isOnSale,
            shouldShowPromo: isOnSale && originalTotalPrice > totalPrice
        });
        
        // Update the displayed price
        if (mainPriceElement) {
            if (isOnSale && originalTotalPrice > totalPrice) {
                // Show promotional price and original price
                mainPriceElement.textContent = Math.round(totalPrice) + ' грн';
                mainPriceElement.className = 'text-3xl text-red-600 font-semibold';
                
                if (originalPriceElement) {
                    originalPriceElement.textContent = Math.round(originalTotalPrice) + ' грн';
                    originalPriceElement.className = 'text-lg text-brown-500 line-through';
                    originalPriceElement.style.display = 'block';
                }
            } else {
                // Show regular price
                mainPriceElement.textContent = Math.round(totalPrice) + ' грн';
                mainPriceElement.className = 'text-3xl text-brown-800 font-semibold';
                
                if (originalPriceElement) {
                    originalPriceElement.style.display = 'none';
                }
            }
        }
    }
    
    // Handle size variant selection
    if (sizeSelect) {
        console.log('Adding change listener to size select');
        
        // Test click handler
        sizeSelect.addEventListener('click', function() {
            console.log('Size select clicked!');
        });
        
        sizeSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const sizePrice = parseFloat(selectedOption.getAttribute('data-price') || 0);
            const originalSizePrice = parseFloat(selectedOption.getAttribute('data-original-price') || 0);
            const isOnSale = selectedOption.getAttribute('data-is-on-sale') === 'true';
            const sizeDimensions = selectedOption.getAttribute('data-dimensions');
            
            // Debug logging
            console.log('Size variant selected:', {
                sizePrice,
                originalSizePrice,
                isOnSale,
                sizeDimensions,
                optionText: selectedOption.text
            });
            
            if (sizePrice > 0) {
                selectedSizePrice = sizePrice;
            } else if (originalSizePrice > 0) {
                selectedSizePrice = originalSizePrice;
            } else {
                selectedSizePrice = basePrice;
            }
            
            // Update price display using the centralized function
            // Update dimensions in characteristics table
            const dimensionsValue = document.getElementById('dimensions-value');
            
            if (dimensionsValue) {
                if (sizeDimensions) {
                    dimensionsValue.textContent = sizeDimensions;
                } else {
                    // If no size selected, revert to base size (from server-rendered value)
                    dimensionsValue.textContent = dimensionsValue.getAttribute('data-base');
                }
            }
            
            updateTotalPrice();
        });
    }
    
    // Handle fabric selection
    if (fabricSelect) {
        fabricSelect.addEventListener('change', function() {
            updateTotalPrice();
        });
    }

    if (qtyInput) {
        qtyInput.addEventListener('input', function() {
            updateTotalPrice();
        });
    }
    
    // Handle form submission
    const addToCartForm = document.getElementById('add-to-cart-form');
    const selectedSizeVariantInput = document.getElementById('selected-size-variant');
    const selectedFabricCategoryInput = document.getElementById('selected-fabric-category');
    const selectedVariantImageInput = document.getElementById('selected-variant-image');
    
    if (addToCartForm) {
        addToCartForm.addEventListener('submit', function(e) {
            if (!ensureCustomOptionSelection()) {
                e.preventDefault();
                return;
            }
            // Let browser validation handle required fields
            
            // Update hidden fields with current selections
            if (sizeSelect && sizeSelect.value) {
                selectedSizeVariantInput.value = sizeSelect.value;
            }
            
            if (fabricSelect && fabricSelect.value) {
                selectedFabricCategoryInput.value = fabricSelect.value;
            }

            // no manual submit needed; default form submit proceeds
        });
    }

    // Photo gallery navigation functionality
    const mainImg = document.getElementById('main-image');
    const mainImageWrapper = document.getElementById('main-image-wrapper');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const dotIndicators = document.querySelectorAll('.dot-indicator');
    const thumbnails = document.querySelectorAll('[data-full]');
    
    let currentImageIndex = 0;
    let totalImages = thumbnails.length;
    
    function setWrapperAspect(width, height) {
        if (!mainImageWrapper) return;

        if (width && height && Number(width) > 0 && Number(height) > 0) {
            mainImageWrapper.style.aspectRatio = `${width} / ${height}`;
        } else {
            mainImageWrapper.style.aspectRatio = '1 / 1';
        }
    }

    function syncMainImageMetadata(source) {
        if (!mainImg || !source) return;

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

    // Function to update the main image and indicators
    function updateMainImage(index) {
        if (thumbnails.length === 0) return;
        
        currentImageIndex = index;
        const thumbnail = thumbnails[currentImageIndex];
        const imageUrl = thumbnail.getAttribute('data-full');
        const srcset = thumbnail.getAttribute('data-srcset');
        const sizes = thumbnail.getAttribute('data-sizes');
        
        if (mainImg && imageUrl) {
            mainImg.src = imageUrl;
            if (srcset) {
                mainImg.setAttribute('srcset', srcset);
            } else {
                mainImg.removeAttribute('srcset');
            }
            if (sizes) {
                mainImg.setAttribute('sizes', sizes);
            } else {
                mainImg.removeAttribute('sizes');
            }
            syncMainImageMetadata(thumbnail);
        }
        
        // Update dot indicators
        dotIndicators.forEach((dot, i) => {
            if (i === currentImageIndex) {
                dot.classList.remove('bg-brown-300');
                dot.classList.add('bg-brown-600');
            } else {
                dot.classList.remove('bg-brown-600');
                dot.classList.add('bg-brown-300');
            }
        });
        
        // Update thumbnail active state
        thumbnails.forEach((thumb, i) => {
            if (i === currentImageIndex) {
                thumb.classList.add('ring-2', 'ring-brown-500');
            } else {
                thumb.classList.remove('ring-2', 'ring-brown-500');
            }
        });
    }
    
    // Function to go to previous image
    function goToPrevious() {
        if (totalImages === 0) return;
        const newIndex = currentImageIndex === 0 ? totalImages - 1 : currentImageIndex - 1;
        updateMainImage(newIndex);
    }
    
    // Function to go to next image
    function goToNext() {
        if (totalImages === 0) return;
        const newIndex = currentImageIndex === totalImages - 1 ? 0 : currentImageIndex + 1;
        updateMainImage(newIndex);
    }
    
    // Navigation button event listeners
    if (prevBtn) {
        prevBtn.addEventListener('click', goToPrevious);
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', goToNext);
    }
    
    // Dot indicator event listeners
    dotIndicators.forEach((dot, index) => {
        dot.addEventListener('click', () => {
            updateMainImage(index);
        });
    });
    
    // Thumbnail click to swap main image
    thumbnails.forEach(function(thumb, index){
        thumb.addEventListener('click', function(){
            updateMainImage(index);
        });
    });
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (totalImages <= 1) return;
        
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            goToPrevious();
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            goToNext();
        }
    });
    
    // Show/hide navigation buttons on hover
    const galleryContainer = document.querySelector('.relative');
    if (galleryContainer && totalImages > 1) {
        galleryContainer.addEventListener('mouseenter', function() {
            if (prevBtn) prevBtn.style.opacity = '1';
            if (nextBtn) nextBtn.style.opacity = '1';
        });
        
        galleryContainer.addEventListener('mouseleave', function() {
            if (prevBtn) prevBtn.style.opacity = '0';
            if (nextBtn) nextBtn.style.opacity = '0';
        });
    }

    // Quick buy modal logic
    const qbBtn = document.getElementById('quick-buy-btn');
    const qbModal = document.getElementById('quick-buy-modal');
    const qbClose = document.getElementById('quick-buy-close');
    const qbQty = document.getElementById('qb-quantity');
    const qbSize = document.getElementById('qb-size-variant');
    const qbFabric = document.getElementById('qb-fabric-category');
    const qbVariantImage = document.getElementById('qb-variant-image');
    const quickBuyForm = qbModal ? qbModal.querySelector('form') : null;

    function syncSelectionsToQuickBuy() {
        if (qbQty && qtyInput) qbQty.value = qtyInput.value || '1';
        if (qbSize && sizeSelect && sizeSelect.value) qbSize.value = sizeSelect.value;
        if (qbFabric && fabricSelect && fabricSelect.value) qbFabric.value = fabricSelect.value;
        if (qbCustomOptionInput && selectedCustomOptionInput) {
            qbCustomOptionInput.value = selectedCustomOptionInput.value;
        }
        if (qbColorInput && selectedColorInput) {
            qbColorInput.value = selectedColorInput.value || '';
        }
    }

    if (qbBtn && qbModal && qbClose) {
        qbBtn.addEventListener('click', () => {
            syncSelectionsToQuickBuy();
            qbModal.classList.remove('hidden');
            qbModal.classList.add('flex');
        });
        qbClose.addEventListener('click', () => {
            qbModal.classList.add('hidden');
            qbModal.classList.remove('flex');
        });
        qbModal.addEventListener('click', (e) => {
            if (e.target === qbModal) {
                qbModal.classList.add('hidden');
                qbModal.classList.remove('flex');
            }
        });
    }

    if (quickBuyForm) {
        quickBuyForm.addEventListener('submit', (e) => {
            if (!ensureCustomOptionSelection()) {
                e.preventDefault();
                alert('Оберіть варіант перед додаванням у кошик.');
                if (qbModal) {
                    qbModal.classList.add('hidden');
                    qbModal.classList.remove('flex');
                }
            }
        });
    }

    updateTotalPrice();
});
