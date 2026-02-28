(function () {
    function evaluateGroup(group) {
        const list = group.querySelector('[data-promotions-list]');
        const wrap = group.querySelector('[data-promotions-expand-wrap]');
        const button = group.querySelector('[data-promotions-toggle]');
        const label = group.querySelector('.promotions-expand-label');

        if (!list || !wrap || !button || !label) {
            return;
        }

        const cards = Array.from(list.children);
        if (cards.length < 2) {
            group.classList.remove('is-collapsed', 'is-expanded');
            wrap.hidden = true;
            button.setAttribute('aria-expanded', 'false');
            return;
        }

        const firstRowTop = cards[0].offsetTop;
        const firstRowCards = cards.filter((card) => Math.abs(card.offsetTop - firstRowTop) <= 1);
        const firstRowBottom = firstRowCards.reduce(function (maxBottom, card) {
            return Math.max(maxBottom, card.offsetTop + card.offsetHeight);
        }, firstRowTop);
        list.style.setProperty('--collapsed-height', (firstRowBottom - firstRowTop) + 'px');
        const hiddenCards = cards.filter((card) => card.offsetTop > firstRowTop + 1);
        const hasHiddenRows = hiddenCards.length > 0;

        if (!hasHiddenRows) {
            group.classList.remove('is-collapsed', 'is-expanded');
            wrap.hidden = true;
            button.setAttribute('aria-expanded', 'false');
            return;
        }

        if (!group.classList.contains('is-expanded')) {
            group.classList.add('is-collapsed');
            group.classList.remove('is-expanded');
            label.textContent = 'Показати всі пропозиції';
            button.setAttribute('aria-expanded', 'false');
        }
        wrap.hidden = false;
    }

    function initGroup(group) {
        const button = group.querySelector('[data-promotions-toggle]');
        const label = group.querySelector('.promotions-expand-label');
        if (!button || !label) {
            return;
        }

        button.addEventListener('click', function () {
            if (group.classList.contains('is-expanded')) {
                group.classList.remove('is-expanded');
                group.classList.add('is-collapsed');
                label.textContent = 'Показати всі пропозиції';
                button.setAttribute('aria-expanded', 'false');
                return;
            }

            group.classList.remove('is-collapsed');
            group.classList.add('is-expanded');
            label.textContent = 'Показати всі пропозиції';
            button.setAttribute('aria-expanded', 'true');
        });

        evaluateGroup(group);
    }

    function init() {
        const groups = Array.from(document.querySelectorAll('[data-promotions-group]'));
        if (!groups.length) {
            return;
        }

        groups.forEach(initGroup);

        const onResize = function () {
            groups.forEach(evaluateGroup);
        };

        if (typeof ResizeObserver !== 'undefined') {
            const observer = new ResizeObserver(onResize);
            groups.forEach(function (group) {
                const list = group.querySelector('[data-promotions-list]');
                if (list) {
                    observer.observe(list);
                }
            });
        }

        window.addEventListener('resize', onResize);
    }

    document.addEventListener('DOMContentLoaded', init);
})();
