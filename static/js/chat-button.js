// Chat popup functionality
document.addEventListener('DOMContentLoaded', function() {
    const chatToggle = document.getElementById('chat-toggle');
    const chatPopup = document.getElementById('chat-popup');
    const chatClose = document.getElementById('chat-close');
    
    // Popup will only show when user clicks the button
    
    // Toggle popup on button click
    chatToggle.addEventListener('click', function() {
        chatPopup.classList.toggle('show');
    });
    
    // Close popup on close button click
    chatClose.addEventListener('click', function() {
        chatPopup.classList.remove('show');
    });
    
    // Close popup when clicking outside
    document.addEventListener('click', function(event) {
        if (!chatPopup.contains(event.target) && !chatToggle.contains(event.target)) {
            chatPopup.classList.remove('show');
        }
    });
    
    // Close popup on escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            chatPopup.classList.remove('show');
        }
    });
});
