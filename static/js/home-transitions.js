(() => {
    const stack = document.querySelector('.home-transition-stack');
    if (!stack) {
        return;
    }

    const sections = Array.from(stack.querySelectorAll('.home-transition-section'));
    if (!sections.length) {
        return;
    }

    const clamp = (min, max, value) => Math.min(max, Math.max(min, value));
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isSmallScreen = window.matchMedia('(max-width: 768px)').matches;
    const isCoarsePointer = window.matchMedia('(pointer:coarse)').matches;

    const setActive = (target) => {
        sections.forEach((section) => section.classList.toggle('is-active', section === target));
    };

    if (prefersReducedMotion || isSmallScreen) {
        sections.forEach((section, index) => section.classList.toggle('is-active', index === 0));
        sections.forEach((section) => section.classList.add('is-visible'));
        return;
    }

    stack.classList.add('is-ready');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                setActive(entry.target);
            } else {
                entry.target.classList.remove('is-active');
            }
        });
    }, {
        threshold: 0.35,
        rootMargin: '0px 0px -30%'
    });

    sections.forEach((section) => observer.observe(section));

    let scrollRaf = null;
    const updatePerspectiveY = () => {
        const rect = stack.getBoundingClientRect();
        const total = rect.height + window.innerHeight;
        const visibleProgress = total > 0
            ? clamp(0, 1, (window.innerHeight - rect.top) / total)
            : 0.5;
        const y = 35 + visibleProgress * 35;
        stack.style.setProperty('--home-perspective-y', `${y}%`);
    };

    const onScroll = () => {
        if (scrollRaf) {
            return;
        }
        scrollRaf = requestAnimationFrame(() => {
            scrollRaf = null;
            updatePerspectiveY();
        });
    };

    document.addEventListener('scroll', onScroll, { passive: true });
    updatePerspectiveY();

    if (!isCoarsePointer) {
        let pointerRaf = null;
        let isDragging = false;

        const updatePointer = (event) => {
            if (pointerRaf) {
                return;
            }
            pointerRaf = requestAnimationFrame(() => {
                pointerRaf = null;
                const x = clamp(25, 75, (event.clientX / window.innerWidth) * 100);
                stack.style.setProperty('--home-perspective-x', `${x}%`);

                if (isDragging) {
                    const tilt = clamp(-4, 4, (event.movementY / window.innerHeight) * 24);
                    stack.style.setProperty('--section-tilt', `${tilt}deg`);
                }
            });
        };

        const resetTilt = () => {
            stack.style.setProperty('--section-tilt', '0deg');
        };

        window.addEventListener('pointermove', updatePointer, { passive: true });
        window.addEventListener('pointerdown', () => {
            isDragging = true;
            stack.classList.add('home-transition-dragging');
        });
        window.addEventListener('pointerup', () => {
            isDragging = false;
            stack.classList.remove('home-transition-dragging');
            resetTilt();
        });
        window.addEventListener('pointerleave', () => {
            isDragging = false;
            stack.classList.remove('home-transition-dragging');
            resetTilt();
        });
    }

    window.addEventListener('resize', () => {
        stack.style.setProperty('--home-perspective-x', '50%');
        updatePerspectiveY();
    });
})();
