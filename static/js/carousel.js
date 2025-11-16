/**
 * Carousel functionality for promotional furniture
 * Clean implementation with consistent variable naming
 */
class PromotionalCarousel {
    constructor() {
        this.carousel = document.getElementById('promoCarousel');
        this.prevButton = document.getElementById('prevButton');
        this.nextButton = document.getElementById('nextButton');
        this.indicators = document.querySelectorAll('.carousel-indicator');
        this.items = this.carousel ? this.carousel.children : null;
        
        this.currentIndex = 0;
        this.isTransitioning = false;
        this.autoPlayInterval = null;
        this.touchStartX = 0;
        this.touchEndX = 0;
        
        this.init();
    }
    
    init() {
        console.log('=== PromotionalCarousel INIT ===');
        console.log('Carousel element:', this.carousel);
        console.log('Prev button:', this.prevButton);
        console.log('Next button:', this.nextButton);
        console.log('Indicators count:', this.indicators.length);
        console.log('Items count:', this.items ? this.items.length : 0);
        
        if (this.items && this.items.length > 0) {
            console.log('Items found:', Array.from(this.items).map((item, index) => {
                const heading = item.querySelector('h3');
                const title = heading ? heading.textContent : 'No title';
                return `${index + 1}. ${title}`;
            }));
            console.log(`Total items loaded: ${this.items.length}`);
        }
        
        if (!this.carousel || !this.items || this.items.length === 0) {
            console.error('Carousel elements not found - carousel:', !!this.carousel, 'items:', this.items ? this.items.length : 0);
            return;
        }
        
        if (!this.prevButton || !this.nextButton) {
            console.error('Navigation buttons not found - prev:', !!this.prevButton, 'next:', !!this.nextButton);
            return;
        }
        
        console.log('PromotionalCarousel initialized successfully');
        this.setupEventListeners();
        this.updateCarousel();
        this.startAutoPlay();
        this.initializeCountdownTimers();
        this.setupResponsiveHandling();
    }
    
    setupEventListeners() {
        console.log('Setting up event listeners...');
        
        // Navigation buttons
        if (this.prevButton) {
            console.log('Adding click listener to previous button');
            this.prevButton.addEventListener('click', (e) => {
                console.log('Previous button clicked!');
                e.preventDefault();
                this.prevSlide();
                this.resetAutoPlay();
            });
        } else {
            console.error('Previous button not found for event listener');
        }
        
        if (this.nextButton) {
            console.log('Adding click listener to next button');
            this.nextButton.addEventListener('click', (e) => {
                console.log('Next button clicked!');
                e.preventDefault();
                this.nextSlide();
                this.resetAutoPlay();
            });
        } else {
            console.error('Next button not found for event listener');
        }
        
        // Indicator clicks
        this.indicators.forEach((indicator, index) => {
            indicator.addEventListener('click', () => {
                this.goToSlide(index);
                this.resetAutoPlay();
            });
        });
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                this.prevSlide();
                this.resetAutoPlay();
            } else if (e.key === 'ArrowRight') {
                this.nextSlide();
                this.resetAutoPlay();
            }
        });
        
        // Touch/swipe support
        this.carousel.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
        });
        
        this.carousel.addEventListener('touchend', (e) => {
            this.touchEndX = e.changedTouches[0].clientX;
            this.handleSwipe();
        });
        
        // Auto-play pause on hover
        this.carousel.addEventListener('mouseenter', () => this.stopAutoPlay());
        this.carousel.addEventListener('mouseleave', () => this.startAutoPlay());
    }
    
    getItemsPerSlide() {
        let itemsPerSlide;
        if (window.innerWidth >= 1440) {
            itemsPerSlide = 4; // Large desktop
        } else if (window.innerWidth >= 1024) {
            itemsPerSlide = 3; // Desktop
        } else if (window.innerWidth >= 768) {
            itemsPerSlide = 2;  // Tablet
        } else {
            itemsPerSlide = 1; // Mobile
        }
        
        console.log('getItemsPerSlide:', {
            windowWidth: window.innerWidth,
            itemsPerSlide
        });
        
        return itemsPerSlide;
    }
    
    updateCarousel() {
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        const slideWidth = 100 / itemsPerSlide;
        const translateX = this.currentIndex * slideWidth;
        
        console.log('updateCarousel:', {
            itemsPerSlide,
            totalSlides,
            slideWidth,
            currentIndex: this.currentIndex,
            translateX,
            totalItems: this.items.length,
            isTransitioning: this.isTransitioning,
            itemsList: Array.from(this.items).map((item) => {
                const text = item.textContent ? item.textContent.trim() : '';
                return text.substring(0, 30);
            })
        });
        
        this.carousel.style.transform = `translateX(-${translateX}%)`;
        this.updateIndicators();
        this.updateButtonStates();
    }
    
    updateIndicators() {
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        
        // Generate indicators container if it doesn't exist
        let indicatorsContainer = document.getElementById('carousel-indicators');
        if (!indicatorsContainer) {
            console.log('Indicators container not found, creating...');
            indicatorsContainer = document.createElement('div');
            indicatorsContainer.id = 'carousel-indicators';
            indicatorsContainer.className = 'absolute bottom-4 left-1/2 transform -translate-x-1/2 flex space-x-2';
            
            const carouselWrapper = this.carousel.closest('.carousel-wrapper');
            if (carouselWrapper) {
                carouselWrapper.appendChild(indicatorsContainer);
            }
        }
        
        // Clear existing indicators
        indicatorsContainer.innerHTML = '';
        
        // Create indicators for each slide
        for (let i = 0; i < totalSlides; i++) {
            const indicator = document.createElement('div');
            indicator.className = 'carousel-indicator w-2 h-2 rounded-full bg-white/50 transition-all duration-300 cursor-pointer';
            indicator.addEventListener('click', () => {
                this.goToSlide(i);
                this.resetAutoPlay();
            });
            
            if (i === this.currentIndex) {
                indicator.classList.add('bg-white');
                indicator.classList.remove('bg-white/50');
                indicator.style.transform = 'scale(1.2)';
            }
            
            indicatorsContainer.appendChild(indicator);
        }
        
        // Update indicators reference
        this.indicators = indicatorsContainer.querySelectorAll('.carousel-indicator');
        
        console.log('Indicators updated:', {
            totalSlides,
            currentIndex: this.currentIndex,
            indicatorsCount: this.indicators.length
        });
    }
    
    updateButtonStates() {
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        
        console.log('updateButtonStates (cyclic):', {
            itemsPerSlide,
            totalSlides,
            currentIndex: this.currentIndex,
            totalItems: this.items.length,
            cyclicMode: true
        });
        
        // In cyclic mode, buttons are always enabled
        this.prevButton.disabled = false;
        this.nextButton.disabled = false;
        
        // Remove any disabled styling
        this.prevButton.classList.remove('opacity-50', 'cursor-not-allowed');
        this.nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
    }
    
    nextSlide() {
        console.log('nextSlide called, isTransitioning:', this.isTransitioning);
        if (this.isTransitioning) {
            console.log('Already transitioning, skipping');
            return;
        }
        
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        console.log('Items per slide:', itemsPerSlide, 'Total slides:', totalSlides, 'Current index:', this.currentIndex);
        
        this.isTransitioning = true;
        
        // Cyclic navigation - go to next slide or back to first
        if (this.currentIndex >= totalSlides - 1) {
            this.currentIndex = 0; // Go back to first slide
            console.log('Reached last slide, going back to first slide');
        } else {
            this.currentIndex++;
            console.log('Moving to next slide');
        }
        
        console.log('New current index:', this.currentIndex);
        this.updateCarousel();
        
        setTimeout(() => {
            this.isTransitioning = false;
            console.log('Transition completed');
        }, 700);
    }
    
    prevSlide() {
        console.log('prevSlide called, isTransitioning:', this.isTransitioning);
        if (this.isTransitioning) {
            console.log('Already transitioning, skipping');
            return;
        }
        
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        console.log('Items per slide:', itemsPerSlide, 'Total slides:', totalSlides, 'Current index:', this.currentIndex);
        
        this.isTransitioning = true;
        
        // Cyclic navigation - go to previous slide or to last
        if (this.currentIndex <= 0) {
            this.currentIndex = totalSlides - 1; // Go to last slide
            console.log('Reached first slide, going to last slide');
        } else {
            this.currentIndex--;
            console.log('Moving to previous slide');
        }
        
        console.log('New current index:', this.currentIndex);
        this.updateCarousel();
        
        setTimeout(() => {
            this.isTransitioning = false;
            console.log('Transition completed');
        }, 700);
    }
    
    goToSlide(index) {
        if (this.isTransitioning) return;
        
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        
        if (index >= 0 && index < totalSlides) {
            this.isTransitioning = true;
            this.currentIndex = index;
            
            this.updateCarousel();
            
            setTimeout(() => {
                this.isTransitioning = false;
            }, 700);
        }
    }
    
    handleSwipe() {
        const swipeThreshold = 50;
        const diff = this.touchStartX - this.touchEndX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                this.nextSlide();
            } else {
                this.prevSlide();
            }
            this.resetAutoPlay();
        }
    }
    
    startAutoPlay() {
        this.autoPlayInterval = setInterval(() => {
            this.nextSlide();
        }, 5000);
    }
    
    resetAutoPlay() {
        if (this.autoPlayInterval) {
            clearInterval(this.autoPlayInterval);
            this.startAutoPlay();
        }
    }
    
    stopAutoPlay() {
        if (this.autoPlayInterval) {
            clearInterval(this.autoPlayInterval);
        }
    }
    
    initializeCountdownTimers() {
        const timers = document.querySelectorAll('.countdown-timer');
        
        timers.forEach(timer => {
            const endDate = timer.getAttribute('data-end');
            if (endDate) {
                this.updateCountdown(timer, endDate);
                setInterval(() => this.updateCountdown(timer, endDate), 1000);
            }
        });
    }
    
    updateCountdown(timer, endDate) {
        const now = new Date().getTime();
        const end = new Date(endDate).getTime();
        const distance = end - now;

        if (distance < 0) {
            timer.textContent = '00:00:00';
            timer.parentElement.style.backgroundColor = '#ef4444';
            return;
        }

        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        timer.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    setupResponsiveHandling() {
        window.addEventListener('resize', () => {
            const newItemsPerSlide = this.getItemsPerSlide();
            const currentItemsPerSlide = Math.ceil(this.items.length / Math.max(1, this.currentIndex + 1));
            
            if (newItemsPerSlide !== currentItemsPerSlide) {
                this.currentIndex = 0;
                this.updateCarousel();
            }
        });
    }
}

// Initialize carousel when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const carouselRoot = document.getElementById('promoCarousel');

    // Skip initialization entirely if the page does not render the promo carousel.
    if (!carouselRoot) {
        console.debug('Promotional carousel skipped: root node not present on this page.');
        return;
    }

    console.log('DOM loaded, initializing promotional carousel...');
    
    // Try to initialize the carousel
    try {
        const carousel = new PromotionalCarousel();
        console.log('Carousel instance created:', carousel);
    } catch (error) {
        console.error('Error initializing carousel:', error);
        
        // Fallback: Simple button functionality
        console.log('Setting up fallback carousel functionality...');
        setupFallbackCarousel();
    }
});

// Fallback carousel functionality
function setupFallbackCarousel() {
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const carousel = document.getElementById('promoCarousel');
    
    if (!prevButton || !nextButton || !carousel) {
        console.error('Fallback: Required elements not found');
        return;
    }
    
    let currentIndex = 0;
    const items = carousel.children;
    
    if (items.length === 0) {
        console.log('Fallback: No items found');
        return;
    }
    
    function getItemsPerSlide() {
        if (window.innerWidth >= 1024) return 3;
        if (window.innerWidth >= 768) return 2;
        return 1;
    }
    
    function updateCarousel() {
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        const slideWidth = 100 / itemsPerSlide;
        const translateX = currentIndex * slideWidth;
        
        console.log('Fallback updateCarousel:', {
            itemsPerSlide,
            totalSlides,
            currentIndex,
            translateX,
            prevDisabled: currentIndex === 0,
            nextDisabled: currentIndex === totalSlides - 1
        });
        
        carousel.style.transform = `translateX(-${translateX}%)`;
        
        // In cyclic mode, buttons are always enabled
        prevButton.disabled = false;
        nextButton.disabled = false;
        
        // Remove any disabled styling
        prevButton.classList.remove('opacity-50', 'cursor-not-allowed');
        nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
        
        // Update indicators
        updateIndicators();
    }
    
    function updateIndicators() {
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        
        // Generate indicators container if it doesn't exist
        let indicatorsContainer = document.getElementById('carousel-indicators');
        if (!indicatorsContainer) {
            console.log('Fallback: Indicators container not found, creating...');
            indicatorsContainer = document.createElement('div');
            indicatorsContainer.id = 'carousel-indicators';
            indicatorsContainer.className = 'absolute bottom-4 left-1/2 transform -translate-x-1/2 flex space-x-2';
            
            const carouselWrapper = carousel.closest('.carousel-wrapper');
            if (carouselWrapper) {
                carouselWrapper.appendChild(indicatorsContainer);
            }
        }
        
        // Clear existing indicators
        indicatorsContainer.innerHTML = '';
        
        // Create indicators for each slide
        for (let i = 0; i < totalSlides; i++) {
            const indicator = document.createElement('div');
            indicator.className = 'carousel-indicator w-2 h-2 rounded-full bg-white/50 transition-all duration-300 cursor-pointer';
            indicator.addEventListener('click', () => {
                currentIndex = i;
                updateCarousel();
            });
            
            if (i === currentIndex) {
                indicator.classList.add('bg-white');
                indicator.classList.remove('bg-white/50');
                indicator.style.transform = 'scale(1.2)';
            }
            
            indicatorsContainer.appendChild(indicator);
        }
        
        console.log('Fallback indicators updated:', {
            totalSlides,
            currentIndex,
            indicatorsCount: totalSlides
        });
    }
    
    prevButton.addEventListener('click', (e) => {
        e.preventDefault();
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        
        console.log('Fallback prevButton click (cyclic):', {
            itemsPerSlide,
            totalSlides,
            currentIndex
        });
        
        // Cyclic navigation - go to previous slide or to last
        if (currentIndex <= 0) {
            currentIndex = totalSlides - 1; // Go to last slide
            console.log('Fallback: Reached first slide, going to last slide');
        } else {
            currentIndex--;
            console.log('Fallback: Moving to previous slide');
        }
        
        console.log('Fallback: Previous clicked, new index:', currentIndex);
        updateCarousel();
    });
    
    nextButton.addEventListener('click', (e) => {
        e.preventDefault();
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        
        console.log('Fallback nextButton click (cyclic):', {
            itemsPerSlide,
            totalSlides,
            currentIndex
        });
        
        // Cyclic navigation - go to next slide or back to first
        if (currentIndex >= totalSlides - 1) {
            currentIndex = 0; // Go back to first slide
            console.log('Fallback: Reached last slide, going back to first slide');
        } else {
            currentIndex++;
            console.log('Fallback: Moving to next slide');
        }
        
        console.log('Fallback: Next clicked, new index:', currentIndex);
        updateCarousel();
    });
    
    // Initial setup
    updateCarousel();
    console.log('Fallback carousel setup completed');
}
