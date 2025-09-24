/**
 * Carousel debugging and testing utilities
 * This file is only loaded in DEBUG mode
 */

console.log('Carousel test file loaded');

// Test if DOM elements exist
document.addEventListener('DOMContentLoaded', () => {
    console.log('=== CAROUSEL DEBUG TEST ===');
    
    // Check if carousel container exists
    const carousel = document.getElementById('promoCarousel');
    console.log('Carousel container:', carousel);
    
    // Check if navigation buttons exist
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    console.log('Previous button:', prevButton);
    console.log('Next button:', nextButton);
    
    // Check if indicators exist
    const indicators = document.querySelectorAll('.carousel-indicator');
    console.log('Indicators count:', indicators.length);
    console.log('Indicators:', indicators);
    
    // Check if carousel items exist
    const items = carousel?.children;
    console.log('Carousel items count:', items?.length);
    console.log('Carousel items:', items);
    
    // Test button click events
    if (prevButton) {
        console.log('Testing previous button click...');
        prevButton.addEventListener('click', (e) => {
            console.log('Previous button clicked!', e);
        });
    }
    
    if (nextButton) {
        console.log('Testing next button click...');
        nextButton.addEventListener('click', (e) => {
            console.log('Next button clicked!', e);
        });
    }
    
    // Check if PromotionalCarousel class exists
    console.log('PromotionalCarousel class:', typeof PromotionalCarousel);
    
    console.log('=== END CAROUSEL DEBUG TEST ===');
});
