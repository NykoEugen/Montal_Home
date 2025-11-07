(() => {
    const stack = document.querySelector('.home-transition-stack');
    if (!stack) {
        return;
    }

    const sections = Array.from(stack.querySelectorAll('.home-transition-section'));
    if (!sections.length) {
        return;
    }

    const hasGSAP = typeof window.gsap !== 'undefined'
        && typeof window.ScrollTrigger !== 'undefined'
        && typeof window.Observer !== 'undefined';

    if (!hasGSAP) {
        sections[0].classList.add('is-active');
        return;
    }

    const { gsap, ScrollTrigger, Observer } = window;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isSmallScreen = window.matchMedia('(max-width: 768px)').matches;

    gsap.registerPlugin(ScrollTrigger, Observer);

    const clamp = gsap.utils.clamp;
    const setActive = (target) => {
        sections.forEach((section) => section.classList.toggle('is-active', section === target));
    };

    if (prefersReducedMotion || isSmallScreen) {
        setActive(sections[0]);
        return;
    }

    gsap.set(sections, {
        transformOrigin: 'center top',
        autoAlpha: 0,
        y: 120,
        rotateX: -6
    });

    gsap.to(sections, {
        autoAlpha: 1,
        y: 0,
        rotateX: 0,
        duration: 1.1,
        ease: 'expo.out',
        stagger: 0.18,
        delay: 0.45
    });

    sections.forEach((section) => {
        const card = section.querySelector('.home-transition-card');
        const innerTargets = section.querySelectorAll('.home-transition-card__header, .home-transition-content > *, .home-transition-category');

        gsap.fromTo(card, {
            autoAlpha: 0.9,
            y: 80,
            rotateX: -6
        }, {
            autoAlpha: 1,
            y: 0,
            rotateX: 0,
            duration: 1,
            ease: 'power3.out',
            scrollTrigger: {
                trigger: section,
                start: 'top 85%',
                toggleActions: 'play none none reverse'
            }
        });

        if (innerTargets.length) {
            gsap.from(innerTargets, {
                autoAlpha: 0,
                y: 32,
                duration: 0.8,
                ease: 'power2.out',
                stagger: 0.12,
                scrollTrigger: {
                    trigger: section,
                    start: 'top 75%',
                    once: true
                }
            });
        }

        ScrollTrigger.create({
            trigger: section,
            start: 'top center',
            end: 'bottom center',
            onEnter: () => setActive(section),
            onEnterBack: () => setActive(section),
            onLeave: () => section.classList.remove('is-active'),
            onLeaveBack: () => section.classList.remove('is-active'),
            onUpdate: (self) => {
                if (ScrollTrigger.isTouch === 1) {
                    return;
                }
                const tiltValue = self.direction > 0 ? '-3.6deg' : '3.6deg';
                gsap.to(stack, {
                    '--section-tilt': tiltValue,
                    duration: 0.45,
                    ease: 'power2.out',
                    overwrite: 'auto'
                });
                gsap.to(stack, {
                    '--section-tilt': '0deg',
                    duration: 0.6,
                    ease: 'power3.out',
                    delay: 0.1,
                    overwrite: 'auto'
                });
            }
        });
    });

    ScrollTrigger.create({
        trigger: stack,
        start: 'top top',
        end: 'bottom bottom',
        onUpdate: (self) => {
            const y = clamp(30, 70, 35 + self.progress * 40);
            stack.style.setProperty('--home-perspective-y', `${y}%`);
        }
    });

    if (ScrollTrigger.isTouch !== 1) {
        Observer.create({
            target: window,
            type: 'pointer',
            tolerance: 12,
            onPress: () => stack.classList.add('home-transition-dragging'),
            onRelease: () => {
                stack.classList.remove('home-transition-dragging');
                gsap.to(stack, {
                    '--section-tilt': '0deg',
                    duration: 0.5,
                    ease: 'power3.out'
                });
            },
            onMove: (self) => {
                const x = clamp(20, 80, (self.x / window.innerWidth) * 100);
                stack.style.setProperty('--home-perspective-x', `${x}%`);

                if (stack.classList.contains('home-transition-dragging')) {
                    const tilt = clamp(-6, 6, (self.deltaY / window.innerHeight) * 22);
                    gsap.to(stack, {
                        '--section-tilt': `${tilt}deg`,
                        duration: 0.2,
                        ease: 'power2.out',
                        overwrite: true
                    });
                }
            }
        });
    }

    window.addEventListener('resize', () => {
        stack.style.setProperty('--home-perspective-x', '50%');
        ScrollTrigger.refresh();
    });
})();
