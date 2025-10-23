/**
 * Seasonal UI controls: handles opt-out interactions and motion preferences.
 *
 * - Listens for clicks on elements with `.seasonal-optout` to set the
 *   `seasonal_opt_out` cookie (30 days) and strip animated elements.
 * - Removes animations immediately when the user has opted out previously or
 *   when `prefers-reduced-motion: reduce` is active.
 */
(function () {
  var COOKIE_NAME = "seasonal_opt_out";
  var COOKIE_VALUE = "1";
  var COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // 30 days
  var MOTION_QUERY = "(prefers-reduced-motion: reduce)";

  function setCookie(name, value, maxAgeSeconds) {
    document.cookie = name + "=" + value + "; path=/; max-age=" + maxAgeSeconds;
  }

  function hasOptedOut() {
    return document.cookie.indexOf(COOKIE_NAME + "=" + COOKIE_VALUE) !== -1;
  }

  function removeAnimations() {
    var animated = document.querySelectorAll("[data-seasonal-animated]");
    animated.forEach(function (el) {
      el.removeAttribute("data-seasonal-animated");
      el.classList.add("seasonal-no-motion");
      el.style.animation = "none";
      el.style.transition = "none";
    });
  }

  function handleOptOut(event) {
    var trigger = event.target.closest(".seasonal-optout");
    if (!trigger) {
      return;
    }
    event.preventDefault();
    setCookie(COOKIE_NAME, COOKIE_VALUE, COOKIE_MAX_AGE);
    removeAnimations();
    var container = trigger.closest("[data-seasonal-pack]");
    if (container) {
      container.setAttribute("hidden", "hidden");
    }
  }

  if (typeof window === "undefined") {
    return;
  }

  if (window.matchMedia && window.matchMedia(MOTION_QUERY).matches) {
    removeAnimations();
  } else if (hasOptedOut()) {
    removeAnimations();
  }

  document.addEventListener("click", handleOptOut, true);
})();

