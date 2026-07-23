(function () {
    if (!window.GTM_ID) {
        return;
    }

    var STORAGE_KEY = 'cookie_consent';

    function loadGTM() {
        (function (w, d, s, l, i) {
            w[l] = w[l] || [];
            w[l].push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
            var f = d.getElementsByTagName(s)[0],
                j = d.createElement(s),
                dl = l != 'dataLayer' ? '&l=' + l : '';
            j.async = true;
            j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl;
            f.parentNode.insertBefore(j, f);
        })(window, document, 'script', 'dataLayer', window.GTM_ID);
    }

    var consent = localStorage.getItem(STORAGE_KEY);
    if (consent === 'granted') {
        loadGTM();
        return;
    }
    if (consent === 'denied') {
        return;
    }

    document.addEventListener('DOMContentLoaded', function () {
        var banner = document.getElementById('cookie-consent-banner');
        if (!banner) {
            return;
        }
        banner.classList.add('cookie-consent-banner--visible');

        document.getElementById('cookie-consent-accept').addEventListener('click', function () {
            localStorage.setItem(STORAGE_KEY, 'granted');
            banner.classList.remove('cookie-consent-banner--visible');
            loadGTM();
        });

        document.getElementById('cookie-consent-decline').addEventListener('click', function () {
            localStorage.setItem(STORAGE_KEY, 'denied');
            banner.classList.remove('cookie-consent-banner--visible');
        });
    });
})();
