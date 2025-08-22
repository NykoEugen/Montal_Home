// Map functionality for where_to_buy page
document.addEventListener('DOMContentLoaded', function() {
    // Store coordinates (Dnipro, Ukraine)
    const storeLat = 48.428674138280584; 
    const storeLng = 35.014744300000004;
    
    // Initialize map
    const map = L.map('map').setView([storeLat, storeLng], 15);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Create custom icon
    const customIcon = L.divIcon({
        html: `
            <div style="
                width: 40px; 
                height: 40px; 
                background: #8B4513; 
                border: 3px solid white; 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            ">
                <div style="
                    width: 16px; 
                    height: 16px; 
                    background: white; 
                    border-radius: 50%;
                "></div>
            </div>
        `,
        className: 'custom-marker',
        iconSize: [40, 40],
        iconAnchor: [20, 40],
        popupAnchor: [0, -40]
    });
    
    // Add marker
    const marker = L.marker([storeLat, storeLng], { icon: customIcon }).addTo(map);
    
    // Add popup
    marker.bindPopup(`
        <div style="padding: 10px; max-width: 250px;">
            <h3 style="margin: 0 0 8px 0; color: #8B4513; font-weight: bold; font-size: 16px;">
                Montal Home - Меблевий магазин
            </h3>
            <p style="margin: 0 0 5px 0; color: #666; font-size: 14px;">
                м. Дніпро, проспект Богдана Хмельницького, 31Д
            </p>
            <p style="margin: 0 0 5px 0; color: #666; font-size: 14px;">
                Пн-Пт, 10:00-19:00 <br>
                Субота - 10:00-18:00 <br>
                Неділя - Вихідний
            </p>
            <p style="margin: 0; color: #666; font-size: 14px;">
                +380 67 841 62 72
            </p>
        </div>
    `);
    
    // Open popup by default
    marker.openPopup();
});
