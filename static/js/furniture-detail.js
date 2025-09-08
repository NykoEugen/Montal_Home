// Furniture detail page functionality
document.addEventListener('DOMContentLoaded', function() {
    const sizeSelect = document.getElementById('size-variant');
    const fabricSelect = document.getElementById('fabric-category');
    const fabricPriceInfo = document.getElementById('fabric-price-info');
    const fabricPriceSpan = document.getElementById('fabric-price');
    const mainPriceElement = document.getElementById('main-price');
    const originalPriceElement = document.getElementById('original-price');
    const qtyInput = document.getElementById('quantity');
    
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
            isOnSale,
            originalSizePrice,
            selectedOption: selectedOption ? selectedOption.text : 'none'
        });
        
        // Use original price for comparison if on sale
        if (isOnSale && originalSizePrice > 0) {
            originalTotalPrice = originalSizePrice;
        }
        
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
            } else {
                selectedSizePrice = originalPrice;
            }
            
            // Update price display using the centralized function
            updateTotalPrice();
            
            // Update dimensions in characteristics table
            const dimensionsValue = document.getElementById('dimensions-value');
            
            if (dimensionsValue) {
                if (sizeDimensions) {
                    // Parse the dimensions string (e.g., "120x60x80 см") and format as "висота*ширина*довжина"
                    const dimensionsMatch = sizeDimensions.match(/(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)/);
                    if (dimensionsMatch) {
                        const height = dimensionsMatch[1];
                        const width = dimensionsMatch[2];
                        const length = dimensionsMatch[3];
                        dimensionsValue.textContent = `${height}x${width}x${length} см`;
                    } else {
                        dimensionsValue.textContent = sizeDimensions; // keep as-is
                    }
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
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const dotIndicators = document.querySelectorAll('.dot-indicator');
    const thumbnails = document.querySelectorAll('[data-full]');
    
    let currentImageIndex = 0;
    let totalImages = thumbnails.length;
    
    // Function to update the main image and indicators
    function updateMainImage(index) {
        if (thumbnails.length === 0) return;
        
        currentImageIndex = index;
        const thumbnail = thumbnails[currentImageIndex];
        const imageUrl = thumbnail.getAttribute('data-full');
        
        if (mainImg && imageUrl) {
            mainImg.src = imageUrl;
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

    function syncSelectionsToQuickBuy() {
        if (qbQty && qtyInput) qbQty.value = qtyInput.value || '1';
        if (qbSize && sizeSelect && sizeSelect.value) qbSize.value = sizeSelect.value;
        if (qbFabric && fabricSelect && fabricSelect.value) qbFabric.value = fabricSelect.value;
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
});
