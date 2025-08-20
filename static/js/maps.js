// Google Maps functionality for store location
function initMap(storeData) {
    // Store location coordinates
    const storeLocation = {
        lat: parseFloat(storeData.latitude),
        lng: parseFloat(storeData.longitude)
    };
    
    // Create map
    const map = new google.maps.Map(document.getElementById('map'), {
        zoom: 15,
        center: storeLocation,
        styles: [
            {
                "featureType": "all",
                "elementType": "geometry",
                "stylers": [{"color": "#f5f5f5"}]
            },
            {
                "featureType": "all",
                "elementType": "labels.text.fill",
                "stylers": [{"color": "#9e9e9e"}]
            },
            {
                "featureType": "all",
                "elementType": "labels.text.stroke",
                "stylers": [{"color": "#ffffff"}]
            },
            {
                "featureType": "landscape",
                "elementType": "geometry",
                "stylers": [{"color": "#f5f5f5"}]
            },
            {
                "featureType": "poi",
                "elementType": "geometry",
                "stylers": [{"color": "#e5e5e5"}]
            },
            {
                "featureType": "road",
                "elementType": "geometry",
                "stylers": [{"color": "#ffffff"}]
            },
            {
                "featureType": "transit",
                "elementType": "geometry",
                "stylers": [{"color": "#e5e5e5"}]
            },
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{"color": "#c9c9c9"}]
            }
        ]
    });
    
    // Create custom marker icon
    const markerIcon = {
        url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(
            '<svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">' +
            '<circle cx="20" cy="20" r="18" fill="#8B4513" stroke="#fff" stroke-width="2"/>' +
            '<circle cx="20" cy="20" r="8" fill="#fff"/>' +
            '<circle cx="20" cy="20" r="4" fill="#8B4513"/>' +
            '</svg>'
        ),
        scaledSize: new google.maps.Size(40, 40),
        anchor: new google.maps.Point(20, 20)
    };
    
    // Create marker
    const marker = new google.maps.Marker({
        position: storeLocation,
        map: map,
        title: storeData.name,
        icon: markerIcon
    });
    
    // Create info window content
    const infoWindowContent = 
        '<div style="padding: 10px; max-width: 250px;">' +
        '<h3 style="margin: 0 0 8px 0; color: #8B4513; font-weight: bold;">' + storeData.name + '</h3>' +
        '<p style="margin: 0 0 5px 0; color: #666;">' + storeData.address + '</p>' +
        '<p style="margin: 0 0 5px 0; color: #666;">' + storeData.working_hours + '</p>' +
        '<p style="margin: 0; color: #666;">' + storeData.phone + '</p>' +
        '</div>';
    
    // Create info window
    const infoWindow = new google.maps.InfoWindow({
        content: infoWindowContent
    });
    
    // Add click listener to marker
    marker.addListener('click', () => {
        infoWindow.open(map, marker);
    });
    
    // Open info window by default
    infoWindow.open(map, marker);
}

// Load Google Maps API
function loadGoogleMapsAPI(storeData, apiKey) {
    const script = document.createElement('script');
    script.src = 'https://maps.googleapis.com/maps/api/js?key=' + apiKey + '&callback=function(){initMap(' + JSON.stringify(storeData) + ')}';
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the where to buy page
    if (document.getElementById('map')) {
        // Store data will be passed from the template
        if (typeof window.storeData !== 'undefined' && typeof window.googleMapsApiKey !== 'undefined') {
            loadGoogleMapsAPI(window.storeData, window.googleMapsApiKey);
        }
    }
});
