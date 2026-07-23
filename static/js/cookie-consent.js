(function () {
    if (!window.GTM_ID) {
        return;
    }

    var STORAGE_KEY = 'cookie_consent';

    function insertNoscriptFrame(id) {
        if (document.getElementById('gtm-noscript-frame')) {
            return;
        }
        var iframe = document.createElement('iframe');
        iframe.id = 'gtm-noscript-frame';
        iframe.src = 'https://www.googletagmanager.com/ns.html?id=' + id;
        iframe.height = '0';
        iframe.width = '0';
        iframe.style.display = 'none';
        iframe.style.visibility = 'hidden';
        document.body.appendChild(iframe);
    }

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
        insertNoscriptFrame(window.GTM_ID);
    }

    loadGTM();

    document.addEventListener('DOMContentLoaded', function () {
        var banner = document.getElementById('cookie-consent-banner');
        if (!banner || localStorage.getItem(STORAGE_KEY)) {
            return;
        }
        banner.classList.add('cookie-consent-banner--visible');

        document.getElementById('cookie-consent-accept').addEventListener('click', function () {
            localStorage.setItem(STORAGE_KEY, 'granted');
            banner.classList.remove('cookie-consent-banner--visible');
        });

        document.getElementById('cookie-consent-decline').addEventListener('click', function () {
            localStorage.setItem(STORAGE_KEY, 'denied');
            banner.classList.remove('cookie-consent-banner--visible');
        });
    });
})();
