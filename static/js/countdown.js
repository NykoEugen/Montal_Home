document.addEventListener('DOMContentLoaded', () => {
    // Initialize countdown timers
    initializeCountdownTimers();

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
});
