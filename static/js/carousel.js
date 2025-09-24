document.addEventListener('DOMContentLoaded', () => {
    const carousel = document.getElementById('promoCarousel');
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const items = carousel?.children;
    const indicators = document.querySelectorAll('.carousel-indicator');
    
    if (!carousel) return;
    
    if (!items || items.length === 0) return;

    // Calculate items per slide based on screen size
    function getItemsPerSlide() {
        if (window.innerWidth >= 1024) return 3; // Desktop
        if (window.innerWidth >= 768) return 2;  // Tablet
        return 1; // Mobile
    }

    let currentIndex = 0;
    let isTransitioning = false;
    let autoPlayInterval;

    function updateCarousel() {
        if (isTransitioning) return;
        
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        const slideWidth = 100 / itemsPerSlide;
        
        carousel.style.transform = `translateX(-${currentIndex * slideWidth}%)`;
        
        // Update indicators
        updateIndicators();
        
        // Update button states
        updateButtonStates();
    }

    function updateIndicators() {
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        
        indicators.forEach((indicator, index) => {
            if (index < totalSlides) {
                indicator.style.display = 'block';
                if (index === currentIndex) {
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

    function updateButtonStates() {
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        
        // Add/remove disabled states
        prevButton.disabled = currentIndex === 0;
        nextButton.disabled = currentIndex === totalSlides - 1;
        
        // Visual feedback for disabled state
        if (prevButton.disabled) {
            prevButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            prevButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
        
        if (nextButton.disabled) {
            nextButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }

    function nextSlide() {
        if (isTransitioning) return;
        
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        
        isTransitioning = true;
        currentIndex = (currentIndex + 1) % totalSlides;
        
        updateCarousel();
        
        setTimeout(() => {
            isTransitioning = false;
        }, 700);
    }

    function prevSlide() {
        if (isTransitioning) return;
        
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        
        isTransitioning = true;
        currentIndex = (currentIndex - 1 + totalSlides) % totalSlides;
        
        updateCarousel();
        
        setTimeout(() => {
            isTransitioning = false;
        }, 700);
    }

    function goToSlide(index) {
        if (isTransitioning) return;
        
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        
        if (index >= 0 && index < totalSlides) {
            isTransitioning = true;
            currentIndex = index;
            
            updateCarousel();
            
            setTimeout(() => {
                isTransitioning = false;
            }, 700);
        }
    }

    // Event listeners
    nextButton?.addEventListener('click', (e) => {
        e.preventDefault();
        nextSlide();
        resetAutoPlay();
    });

    prevButton?.addEventListener('click', (e) => {
        e.preventDefault();
        prevSlide();
        resetAutoPlay();
    });

    // Indicator clicks
    indicators.forEach((indicator, index) => {
        indicator.addEventListener('click', () => {
            goToSlide(index);
            resetAutoPlay();
        });
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
            prevSlide();
            resetAutoPlay();
        } else if (e.key === 'ArrowRight') {
            nextSlide();
            resetAutoPlay();
        }
    });

    // Touch/swipe support
    let startX = 0;
    let endX = 0;

    carousel.addEventListener('touchstart', (e) => {
        startX = e.touches[0].clientX;
    });

    carousel.addEventListener('touchend', (e) => {
        endX = e.changedTouches[0].clientX;
        handleSwipe();
    });

    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = startX - endX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                nextSlide();
            } else {
                prevSlide();
            }
            resetAutoPlay();
        }
    }

    // Auto-play functionality
    function startAutoPlay() {
        autoPlayInterval = setInterval(() => {
            nextSlide();
        }, 5000);
    }

    function resetAutoPlay() {
        if (autoPlayInterval) {
            clearInterval(autoPlayInterval);
            startAutoPlay();
        }
    }

    function stopAutoPlay() {
        if (autoPlayInterval) {
            clearInterval(autoPlayInterval);
        }
    }

    // Pause auto-play on hover
    carousel.addEventListener('mouseenter', stopAutoPlay);
    carousel.addEventListener('mouseleave', startAutoPlay);

    // Initialize countdown timers
    function initializeCountdownTimers() {
        const timers = document.querySelectorAll('.countdown-timer');
        
        timers.forEach(timer => {
            const endDate = timer.getAttribute('data-end');
            if (endDate) {
                updateCountdown(timer, endDate);
                setInterval(() => updateCountdown(timer, endDate), 1000);
            }
        });
    }

    function updateCountdown(timer, endDate) {
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

    // Responsive handling
    function handleResize() {
        const newItemsPerSlide = getItemsPerSlide();
        const currentItemsPerSlide = Math.ceil(items.length / Math.max(1, currentIndex + 1));
        
        if (newItemsPerSlide !== currentItemsPerSlide) {
            currentIndex = 0;
            updateCarousel();
        }
    }

    window.addEventListener('resize', handleResize);

    // Initialize
    updateCarousel();
    startAutoPlay();
    
    // Initialize countdown timers
    initializeCountdownTimers();

    // Add loading animation
    carousel.style.opacity = '0';
    setTimeout(() => {
        carousel.style.transition = 'opacity 0.5s ease-in-out';
        carousel.style.opacity = '1';
    }, 100);
});
