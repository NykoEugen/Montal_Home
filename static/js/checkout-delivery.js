// Checkout delivery fields functionality
document.addEventListener('DOMContentLoaded', function() {
    const deliveryTypeSelect = document.getElementById('delivery-type');
    const localDeliveryFields = document.getElementById('local-delivery-fields');
    const novaPoshtaFields = document.getElementById('nova-poshta-fields');

    function toggleDeliveryFields() {
        const selectedValue = deliveryTypeSelect.value;
        
        if (selectedValue === 'local') {
            localDeliveryFields.classList.remove('hidden');
            novaPoshtaFields.classList.add('hidden');
        } else if (selectedValue === 'nova_poshta') {
            localDeliveryFields.classList.add('hidden');
            novaPoshtaFields.classList.remove('hidden');
        } else {
            localDeliveryFields.classList.add('hidden');
            novaPoshtaFields.classList.add('hidden');
        }
    }

    // Initial state
    toggleDeliveryFields();

    // Listen for changes
    deliveryTypeSelect.addEventListener('change', toggleDeliveryFields);
});
