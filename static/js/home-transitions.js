(() => {
    const stack = document.querySelector('.home-transition-stack');
    if (!stack) return;

    const sections = Array.from(stack.querySelectorAll('.home-transition-section'));
    if (!sections.length) return;

    const supportsMatchMedia = typeof window.matchMedia === 'function';
    const media = (query, fallback = false) => supportsMatchMedia
        ? window.matchMedia(query).matches
        : fallback;

    const prefersReducedMotion = media('(prefers-reduced-motion: reduce)');
    const supportsIntersectionObserver = typeof window.IntersectionObserver === 'function';

    if (prefersReducedMotion || !supportsIntersectionObserver) {
        sections.forEach(s => s.classList.add('is-visible'));
        return;
    }

    stack.classList.add('is-ready');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    sections.forEach(s => observer.observe(s));
})();
