document.addEventListener('DOMContentLoaded', () => {
    const carousel = document.getElementById('promoCarousel');
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const items = carousel.children;

    // Розраховуємо кількість слайдів на "сторінці"
    function getItemsPerSlide() {
        return window.innerWidth >= 768 ? 3 : 1;
    }

    let currentIndex = 0;

    function updateCarousel() {
        const itemsPerSlide = getItemsPerSlide();
        const totalSlides = Math.ceil(items.length / itemsPerSlide);
        const slideWidthPercent = 100 / itemsPerSlide;
        carousel.style.transform = `translateX(-${currentIndex * 100}%)`;
    }

    nextButton.addEventListener('click', () => {
        const itemsPerSlide = getItemsPerSlide();
        const maxIndex = Math.ceil(items.length / itemsPerSlide) - 1;
        currentIndex = (currentIndex + 1) > maxIndex ? 0 : currentIndex + 1;
        updateCarousel();
    });

    prevButton.addEventListener('click', () => {
        const itemsPerSlide = getItemsPerSlide();
        const maxIndex = Math.ceil(items.length / itemsPerSlide) - 1;
        currentIndex = (currentIndex - 1 + maxIndex + 1) % (maxIndex + 1);
        updateCarousel();
    });

    // Автоперехід
    setInterval(() => {
        const itemsPerSlide = getItemsPerSlide();
        const maxIndex = Math.ceil(items.length / itemsPerSlide) - 1;
        currentIndex = (currentIndex + 1) > maxIndex ? 0 : currentIndex + 1;
        updateCarousel();
    }, 5000);

    // Оновлення при ресайзі
    window.addEventListener('resize', updateCarousel);

    updateCarousel();
});
