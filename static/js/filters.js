// Toggle filter sections
function toggleFilterSection(headerElement) {
    const content = headerElement.nextElementSibling;
    const icon = headerElement.querySelector('svg');
    
    if (content.style.display === "none" || content.style.display === "") {
        content.style.display = "block";
        icon.style.transform = "rotate(180deg)";
    } else {
        content.style.display = "none";
        icon.style.transform = "rotate(0deg)";
    }
}

// Clear all filters
function clearAllFilters() {
    // Clear all form inputs
    const form = document.getElementById('filterForm');
    if (form) {
        const inputs = form.querySelectorAll('input[type="text"], input[type="number"], input[type="radio"], input[type="checkbox"]');
        inputs.forEach(input => {
            if (input.type === 'radio' || input.type === 'checkbox') {
                input.checked = false;
            } else {
                input.value = '';
            }
        });
        
        // Submit the form to apply cleared filters
        form.submit();
    }
}

// Auto-submit form when radio buttons change
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('filterForm');
    if (form) {
        const radioButtons = form.querySelectorAll('input[type="radio"]');
        radioButtons.forEach(radio => {
            radio.addEventListener('change', function() {
                // Small delay to ensure the change is registered
                setTimeout(() => {
                    form.submit();
                }, 100);
            });
        });
    }
    
    // Initialize filter sections
    const filterHeaders = document.querySelectorAll('.filter-header');
    filterHeaders.forEach(header => {
        const content = header.nextElementSibling;
        // Start with all sections expanded
        content.style.display = "block";
        const icon = header.querySelector('svg');
        if (icon) {
            icon.style.transform = "rotate(180deg)";
        }
    });
});

// Price range validation
function validatePriceRange() {
    const minPrice = document.querySelector('input[name="min_price"]');
    const maxPrice = document.querySelector('input[name="max_price"]');
    
    if (minPrice && maxPrice && minPrice.value && maxPrice.value) {
        const min = parseFloat(minPrice.value);
        const max = parseFloat(maxPrice.value);
        
        if (min > max) {
            alert('Мінімальна ціна не може бути більшою за максимальну');
            return false;
        }
    }
    
    return true;
}

// Add price range validation to form submission
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('filterForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validatePriceRange()) {
                e.preventDefault();
            }
        });
    }
});