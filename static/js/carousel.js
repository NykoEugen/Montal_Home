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
        this.items = this.carousel?.children;
        
        this.currentIndex = 0;
        this.isTransitioning = false;
        this.autoPlayInterval = null;
        this.touchStartX = 0;
        this.touchEndX = 0;
        
        this.init();
    }
    
    init() {
        if (!this.carousel || !this.items || this.items.length === 0) {
            console.log('Carousel elements not found');
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
        // Navigation buttons
        if (this.prevButton) {
            this.prevButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.prevSlide();
                this.resetAutoPlay();
            });
        }
        
        if (this.nextButton) {
            this.nextButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.nextSlide();
                this.resetAutoPlay();
            });
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
        if (window.innerWidth >= 1024) return 3; // Desktop
        if (window.innerWidth >= 768) return 2;  // Tablet
        return 1; // Mobile
    }
    
    updateCarousel() {
        if (this.isTransitioning) return;
        
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        const slideWidth = 100 / itemsPerSlide;
        
        this.carousel.style.transform = `translateX(-${this.currentIndex * slideWidth}%)`;
        this.updateIndicators();
        this.updateButtonStates();
    }
    
    updateIndicators() {
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        
        this.indicators.forEach((indicator, index) => {
            if (index < totalSlides) {
                indicator.style.display = 'block';
                if (index === this.currentIndex) {
                    indicator.classList.add('bg-white');
                    indicator.classList.remove('bg-white/50');
                    indicator.style.transform = 'scale(1.2)';
                } else {
                    indicator.classList.remove('bg-white');
                    indicator.classList.add('bg-white/50');
                    indicator.style.transform = 'scale(1)';
                }
            } else {
                indicator.style.display = 'none';
            }
        });
    }
    
    updateButtonStates() {
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        
        // Update button disabled states
        this.prevButton.disabled = this.currentIndex === 0;
        this.nextButton.disabled = this.currentIndex === totalSlides - 1;
        
        // Visual feedback for disabled state
        if (this.prevButton.disabled) {
            this.prevButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            this.prevButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
        
        if (this.nextButton.disabled) {
            this.nextButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            this.nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
    
    nextSlide() {
        if (this.isTransitioning) return;
        
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        
        this.isTransitioning = true;
        this.currentIndex = (this.currentIndex + 1) % totalSlides;
        
        this.updateCarousel();
        
        setTimeout(() => {
            this.isTransitioning = false;
        }, 700);
    }
    
    prevSlide() {
        if (this.isTransitioning) return;
        
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        
        this.isTransitioning = true;
        this.currentIndex = (this.currentIndex - 1 + totalSlides) % totalSlides;
        
        this.updateCarousel();
        
        setTimeout(() => {
            this.isTransitioning = false;
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
    console.log('DOM loaded, initializing promotional carousel...');
    new PromotionalCarousel();
});