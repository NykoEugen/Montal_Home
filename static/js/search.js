document.addEventListener('DOMContentLoaded', function() {
    let searchTimeout;
    let currentRequest = null;
    
    // Initialize search for both desktop and mobile
    initializeSearch('desktop');
    initializeSearch('mobile');
    
    function initializeSearch(type) {
        const input = document.getElementById(`search-input-${type}`);
        const dropdown = document.getElementById(`search-dropdown-${type}`);
        const suggestionsContainer = document.getElementById(`search-suggestions-${type}`);
        
        if (!input || !dropdown || !suggestionsContainer) return;
        
        // Input event for search suggestions
        input.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            // Cancel previous request if it exists
            if (currentRequest) {
                currentRequest.abort();
            }
            
            if (query.length < 2) {
                hideDropdown(type);
                return;
            }
            
            // Debounce the search
            searchTimeout = setTimeout(() => {
                fetchSearchSuggestions(query, type);
            }, 300);
        });
        
        // Focus event
        input.addEventListener('focus', function() {
            const query = this.value.trim();
            if (query.length >= 2) {
                fetchSearchSuggestions(query, type);
            }
        });
        
        // Blur event - hide dropdown after a delay to allow clicking
        input.addEventListener('blur', function() {
            setTimeout(() => {
                hideDropdown(type);
            }, 200);
        });
        
        // Keyboard navigation
        input.addEventListener('keydown', function(e) {
            const suggestions = dropdown.querySelectorAll('.search-suggestion-item');
            const activeItem = dropdown.querySelector('.search-suggestion-item.active');
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    navigateSuggestions(suggestions, activeItem, 'next');
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    navigateSuggestions(suggestions, activeItem, 'prev');
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (activeItem) {
                        window.location.href = activeItem.dataset.url;
                    } else {
                        // Submit form if no suggestion is selected
                        const form = input.closest('form');
                        if (form) form.submit();
                    }
                    break;
                case 'Escape':
                    hideDropdown(type);
                    input.blur();
                    break;
            }
        });
        
        // Click outside to close dropdown
        document.addEventListener('click', function(e) {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                hideDropdown(type);
            }
        });
    }
    
    function fetchSearchSuggestions(query, type) {
        const url = `/search-suggestions/?q=${encodeURIComponent(query)}`;
        
        // Show loading state
        showLoading(type);
        
        // Create new AbortController for this request
        const controller = new AbortController();
        currentRequest = controller;
        
        fetch(url, {
            signal: controller.signal,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.suggestions && data.suggestions.length > 0) {
                displaySuggestions(data.suggestions, type);
            } else {
                showNoResults(type);
            }
        })
        .catch(error => {
            if (error.name !== 'AbortError') {
                console.error('Search error:', error);
                showError(type);
            }
        })
        .finally(() => {
            currentRequest = null;
        });
    }
    
    function displaySuggestions(suggestions, type) {
        const dropdown = document.getElementById(`search-dropdown-${type}`);
        const suggestionsContainer = document.getElementById(`search-suggestions-${type}`);
        
        suggestionsContainer.innerHTML = '';
        
        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'search-suggestion-item p-3 hover:bg-beige-100 cursor-pointer border-b border-beige-200 last:border-b-0';
            item.dataset.url = suggestion.url;
            item.dataset.index = index;
            
            const imageHtml = suggestion.image_url 
                ? `<img src="${suggestion.image_url}" alt="${suggestion.name}" class="w-12 h-12 object-cover rounded mr-3">`
                : `<div class="w-12 h-12 bg-beige-200 rounded mr-3 flex items-center justify-center"><i class="fas fa-image text-beige-400"></i></div>`;
            
            const priceHtml = suggestion.is_promotional && suggestion.promotional_price
                ? `<span class="text-red-600 font-semibold">${suggestion.promotional_price} грн</span><span class="text-sm text-gray-500 line-through ml-1">${suggestion.price} грн</span>`
                : `<span class="font-semibold">${suggestion.price} грн</span>`;
            
            item.innerHTML = `
                <div class="flex items-center">
                    ${imageHtml}
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-brown-800 truncate">${suggestion.name}</div>
                        <div class="text-sm text-brown-600 truncate">${suggestion.article_code}</div>
                        <div class="text-xs text-brown-500 truncate">${suggestion.category}</div>
                    </div>
                    <div class="text-right ml-2">
                        <div class="text-sm">${priceHtml}</div>
                    </div>
                </div>
            `;
            
            item.addEventListener('click', function() {
                window.location.href = suggestion.url;
            });
            
            item.addEventListener('mouseenter', function() {
                // Remove active class from all items
                dropdown.querySelectorAll('.search-suggestion-item').forEach(item => {
                    item.classList.remove('active', 'bg-brown-100');
                });
                // Add active class to current item
                this.classList.add('active', 'bg-brown-100');
            });
            
            suggestionsContainer.appendChild(item);
        });
        
        showDropdown(type);
    }
    
    function showNoResults(type) {
        const dropdown = document.getElementById(`search-dropdown-${type}`);
        const suggestionsContainer = document.getElementById(`search-suggestions-${type}`);
        
        suggestionsContainer.innerHTML = `
            <div class="p-4 text-center text-brown-600">
                <i class="fas fa-search text-2xl text-beige-400 mb-2"></i>
                <div>Нічого не знайдено</div>
                <div class="text-sm">Спробуйте інший запит</div>
            </div>
        `;
        
        showDropdown(type);
    }
    
    function showLoading(type) {
        const dropdown = document.getElementById(`search-dropdown-${type}`);
        const suggestionsContainer = document.getElementById(`search-suggestions-${type}`);
        
        suggestionsContainer.innerHTML = `
            <div class="p-4 text-center text-brown-600">
                <i class="fas fa-spinner fa-spin text-2xl mb-2"></i>
                <div>Пошук...</div>
            </div>
        `;
        
        showDropdown(type);
    }
    
    function showError(type) {
        const dropdown = document.getElementById(`search-dropdown-${type}`);
        const suggestionsContainer = document.getElementById(`search-suggestions-${type}`);
        
        suggestionsContainer.innerHTML = `
            <div class="p-4 text-center text-red-600">
                <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
                <div>Помилка пошуку</div>
                <div class="text-sm">Спробуйте ще раз</div>
            </div>
        `;
        
        showDropdown(type);
    }
    
    function showDropdown(type) {
        const dropdown = document.getElementById(`search-dropdown-${type}`);
        if (dropdown) {
            dropdown.classList.remove('hidden');
        }
    }
    
    function hideDropdown(type) {
        const dropdown = document.getElementById(`search-dropdown-${type}`);
        if (dropdown) {
            dropdown.classList.add('hidden');
        }
    }
    
    function navigateSuggestions(suggestions, activeItem, direction) {
        if (suggestions.length === 0) return;
        
        let nextIndex = 0;
        
        if (activeItem) {
            const currentIndex = parseInt(activeItem.dataset.index);
            if (direction === 'next') {
                nextIndex = (currentIndex + 1) % suggestions.length;
            } else {
                nextIndex = currentIndex === 0 ? suggestions.length - 1 : currentIndex - 1;
            }
            activeItem.classList.remove('active', 'bg-brown-100');
        }
        
        const nextItem = suggestions[nextIndex];
        if (nextItem) {
            nextItem.classList.add('active', 'bg-brown-100');
            nextItem.scrollIntoView({ block: 'nearest' });
        }
    }
    
    // Mobile menu search enhancement
    const mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenu) {
        const mobileSearchInput = mobileMenu.querySelector('#search-input-mobile');
        if (mobileSearchInput) {
            // Auto-close mobile menu after selection
            mobileSearchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    const activeItem = document.querySelector('#search-dropdown-mobile .search-suggestion-item.active');
                    if (activeItem) {
                        setTimeout(() => {
                            const mobileMenu = document.getElementById('mobile-menu');
                            if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
                                mobileMenu.classList.add('hidden');
                            }
                        }, 100);
                    }
                }
            });
        }
    }
});
