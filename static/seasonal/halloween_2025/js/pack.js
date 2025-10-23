(function () {
  function handleClick(event) {
    const trigger = event.target.closest('.seasonal-optout');
    if (!trigger) {
      return;
    }
    event.preventDefault();
    const container = trigger.closest('[data-seasonal-pack]');
    if (container) {
      container.setAttribute('hidden', 'hidden');
    }
  }

  document.addEventListener('click', handleClick, true);
})();
