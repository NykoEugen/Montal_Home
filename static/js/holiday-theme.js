(() => {
    const SPAWN_INTERVAL = 900;
    const MAX_OFFSET = 40;

    const createContainer = () => {
        let container = document.getElementById('holiday-snow-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'holiday-snow-container';
            container.setAttribute('aria-hidden', 'true');
            document.body.appendChild(container);
        }
        return container;
    };

    const spawnSnowflake = container => {
        const snowflake = document.createElement('span');
        const duration = 10 + Math.random() * 8;
        const size = 10 + Math.random() * 8;
        const drift = Math.random() * MAX_OFFSET * (Math.random() > 0.5 ? 1 : -1);

        snowflake.className = 'holiday-snowflake';
        snowflake.style.left = `${Math.random() * 100}%`;
        snowflake.style.animationDelay = `${Math.random() * 4}s`;
        snowflake.style.setProperty('--fall-duration', `${duration}s`);
        snowflake.style.setProperty('--flake-size', `${size}px`);
        snowflake.style.setProperty('--x-drift', `${drift}px`);

        container.appendChild(snowflake);

        const removalDelay = (duration + 5) * 1000;
        window.setTimeout(() => {
            snowflake.remove();
        }, removalDelay);
    };

    const initSnow = () => {
        const container = createContainer();
        for (let i = 0; i < 20; i += 1) {
            spawnSnowflake(container);
        }
        return container;
    };

    document.addEventListener('DOMContentLoaded', () => {
        const body = document.body;
        const toggle = document.getElementById('holiday-decor-toggle');
        const toggleIcon = toggle ? toggle.querySelector('.holiday-toggle__icon') : null;
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        let container = null;
        let spawnTimer = null;
        let decorEnabled = !prefersReducedMotion;

        const updateToggleVisual = enabled => {
            if (!toggle) {
                return;
            }
            toggle.classList.toggle('holiday-toggle--off', !enabled);
            toggle.setAttribute('aria-pressed', enabled ? 'true' : 'false');
            toggle.setAttribute('aria-label', enabled ? 'Вимкнути святкові ефекти' : 'Увімкнути святкові ефекти');
            if (toggleIcon) {
                toggleIcon.textContent = enabled ? '❄️' : '🌙';
            }
        };

        const stopSnow = () => {
            if (spawnTimer) {
                window.clearInterval(spawnTimer);
                spawnTimer = null;
            }
            if (container) {
                container.innerHTML = '';
                container.classList.add('hidden');
            }
        };

        const startSnow = () => {
            if (!container) {
                container = initSnow();
            } else {
                container.classList.remove('hidden');
            }
            if (!spawnTimer) {
                spawnTimer = window.setInterval(() => {
                    spawnSnowflake(container);
                }, SPAWN_INTERVAL);
            }
        };

        const applyDecorState = enabled => {
            if (enabled) {
                body.classList.remove('holiday-decor-disabled');
                startSnow();
            } else {
                body.classList.add('holiday-decor-disabled');
                stopSnow();
            }
            updateToggleVisual(enabled);
        };

        if (!body.classList.contains('holiday-mode')) {
            body.classList.add('holiday-mode');
        }

        applyDecorState(decorEnabled);

        if (toggle) {
            toggle.addEventListener('click', () => {
                decorEnabled = !decorEnabled;
                applyDecorState(decorEnabled);
            });
        }
    });
})();
