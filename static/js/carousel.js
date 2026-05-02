/**
 * Carousel functionality for promotional furniture
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
        if (!this.carousel || !this.items || this.items.length === 0) {
            console.error('Carousel elements not found - carousel:', !!this.carousel, 'items:', this.items ? this.items.length : 0);
            return;
        }

        if (!this.prevButton || !this.nextButton) {
            console.error('Navigation buttons not found - prev:', !!this.prevButton, 'next:', !!this.nextButton);
            return;
        }

        this.setupEventListeners();
        this.updateCarousel();
        this.startAutoPlay();
        this.initializeCountdownTimers();
        this.setupResponsiveHandling();
    }

    setupEventListeners() {
        if (this.prevButton) {
            this.prevButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.prevSlide();
                this.resetAutoPlay();
            });
        } else {
            console.error('Previous button not found for event listener');
        }

        if (this.nextButton) {
            this.nextButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.nextSlide();
                this.resetAutoPlay();
            });
        } else {
            console.error('Next button not found for event listener');
        }

        this.indicators.forEach((indicator, index) => {
            indicator.addEventListener('click', () => {
                this.goToSlide(index);
                this.resetAutoPlay();
            });
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                this.prevSlide();
                this.resetAutoPlay();
            } else if (e.key === 'ArrowRight') {
                this.nextSlide();
                this.resetAutoPlay();
            }
        });

        this.carousel.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
        });

        this.carousel.addEventListener('touchend', (e) => {
            this.touchEndX = e.changedTouches[0].clientX;
            this.handleSwipe();
        });

        this.carousel.addEventListener('mouseenter', () => this.stopAutoPlay());
        this.carousel.addEventListener('mouseleave', () => this.startAutoPlay());
    }

    getItemsPerSlide() {
        if (window.innerWidth >= 1440) return 4;
        if (window.innerWidth >= 1024) return 3;
        if (window.innerWidth >= 768) return 2;
        return 1;
    }

    updateCarousel() {
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);
        const slideWidth = 100 / itemsPerSlide;
        const translateX = this.currentIndex * slideWidth;

        this.carousel.style.transform = `translateX(-${translateX}%)`;
        this.updateIndicators();
        this.updateButtonStates();
    }

    updateIndicators() {
        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);

        let indicatorsContainer = document.getElementById('carousel-indicators');
        if (!indicatorsContainer) {
            indicatorsContainer = document.createElement('div');
            indicatorsContainer.id = 'carousel-indicators';
            indicatorsContainer.className = 'absolute bottom-4 left-1/2 transform -translate-x-1/2 flex space-x-2';

            const carouselWrapper = this.carousel.closest('.carousel-wrapper');
            if (carouselWrapper) {
                carouselWrapper.appendChild(indicatorsContainer);
            }
        }

        indicatorsContainer.innerHTML = '';

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

        this.indicators = indicatorsContainer.querySelectorAll('.carousel-indicator');
    }

    updateButtonStates() {
        this.prevButton.disabled = false;
        this.nextButton.disabled = false;
        this.prevButton.classList.remove('opacity-50', 'cursor-not-allowed');
        this.nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
    }

    nextSlide() {
        if (this.isTransitioning) return;

        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);

        this.isTransitioning = true;
        this.currentIndex = this.currentIndex >= totalSlides - 1 ? 0 : this.currentIndex + 1;
        this.updateCarousel();

        setTimeout(() => { this.isTransitioning = false; }, 700);
    }

    prevSlide() {
        if (this.isTransitioning) return;

        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);

        this.isTransitioning = true;
        this.currentIndex = this.currentIndex <= 0 ? totalSlides - 1 : this.currentIndex - 1;
        this.updateCarousel();

        setTimeout(() => { this.isTransitioning = false; }, 700);
    }

    goToSlide(index) {
        if (this.isTransitioning) return;

        const itemsPerSlide = this.getItemsPerSlide();
        const totalSlides = Math.ceil(this.items.length / itemsPerSlide);

        if (index >= 0 && index < totalSlides) {
            this.isTransitioning = true;
            this.currentIndex = index;
            this.updateCarousel();
            setTimeout(() => { this.isTransitioning = false; }, 700);
        }
    }

    handleSwipe() {
        const diff = this.touchStartX - this.touchEndX;
        if (Math.abs(diff) > 50) {
            diff > 0 ? this.nextSlide() : this.prevSlide();
            this.resetAutoPlay();
        }
    }

    startAutoPlay() {
        this.autoPlayInterval = setInterval(() => this.nextSlide(), 5000);
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
        document.querySelectorAll('.countdown-timer').forEach(timer => {
            const endDate = timer.getAttribute('data-end');
            if (endDate) {
                this.updateCountdown(timer, endDate);
                setInterval(() => this.updateCountdown(timer, endDate), 1000);
            }
        });
    }

    updateCountdown(timer, endDate) {
        const distance = new Date(endDate).getTime() - new Date().getTime();

        if (distance < 0) {
            timer.textContent = '00:00:00';
            timer.parentElement.style.backgroundColor = '#ef4444';
            return;
        }

        const h = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const m = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const s = Math.floor((distance % (1000 * 60)) / 1000);
        timer.textContent = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    setupResponsiveHandling() {
        window.addEventListener('resize', () => {
            this.currentIndex = 0;
            this.updateCarousel();
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const carouselRoot = document.getElementById('promoCarousel');
    if (!carouselRoot) return;

    try {
        new PromotionalCarousel();
    } catch (error) {
        console.error('Error initializing carousel:', error);
        setupFallbackCarousel();
    }
});

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
    if (items.length === 0) return;

    function getItemsPerSlide() {
        if (window.innerWidth >= 1024) return 3;
        if (window.innerWidth >= 768) return 2;
        return 1;
    }

    function updateCarousel() {
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        const translateX = currentIndex * (100 / itemsPerSlide);
        carousel.style.transform = `translateX(-${translateX}%)`;
        prevButton.disabled = false;
        nextButton.disabled = false;
        prevButton.classList.remove('opacity-50', 'cursor-not-allowed');
        nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
        updateIndicators(totalSlides);
    }

    function updateIndicators(totalSlides) {
        let container = document.getElementById('carousel-indicators');
        if (!container) {
            container = document.createElement('div');
            container.id = 'carousel-indicators';
            container.className = 'absolute bottom-4 left-1/2 transform -translate-x-1/2 flex space-x-2';
            const wrapper = carousel.closest('.carousel-wrapper');
            if (wrapper) wrapper.appendChild(container);
        }
        container.innerHTML = '';
        for (let i = 0; i < totalSlides; i++) {
            const dot = document.createElement('div');
            dot.className = 'carousel-indicator w-2 h-2 rounded-full transition-all duration-300 cursor-pointer ' + (i === currentIndex ? 'bg-white scale-125' : 'bg-white/50');
            dot.addEventListener('click', () => { currentIndex = i; updateCarousel(); });
            container.appendChild(dot);
        }
    }

    prevButton.addEventListener('click', (e) => {
        e.preventDefault();
        const totalSlides = Math.ceil(items.length / getItemsPerSlide());
        currentIndex = currentIndex <= 0 ? totalSlides - 1 : currentIndex - 1;
        updateCarousel();
    });

    nextButton.addEventListener('click', (e) => {
        e.preventDefault();
        const totalSlides = Math.ceil(items.length / getItemsPerSlide());
        currentIndex = currentIndex >= totalSlides - 1 ? 0 : currentIndex + 1;
        updateCarousel();
    });

    updateCarousel();
}
