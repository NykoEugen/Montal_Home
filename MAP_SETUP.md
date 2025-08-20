# Map Setup for "Where to Buy" Page

## Overview
I've implemented a **free map solution** using **OpenStreetMap** with **Leaflet** that doesn't require any API keys or paid services. The map shows your store location with just coordinates.

## Features
- ✅ **Completely Free** - No API keys needed
- ✅ **Interactive Map** - Users can zoom, pan, and interact
- ✅ **Custom Marker** - Branded marker with your colors
- ✅ **Store Information** - Popup with store details
- ✅ **Responsive Design** - Works on all devices
- ✅ **Fast Loading** - Uses CDN resources

## How to Customize

### 1. Change Store Coordinates
Open `templates/shop/where_to_buy.html` and find these lines:

```javascript
// Store coordinates (Kyiv, Ukraine)
const storeLat = 50.4501;
const storeLng = 30.5234;
```

Replace with your actual coordinates:
```javascript
// Your store coordinates
const storeLat = YOUR_LATITUDE;
const storeLng = YOUR_LONGITUDE;
```

### 2. Get Your Coordinates
1. Go to [Google Maps](https://maps.google.com/)
2. Search for your store address
3. Right-click on the exact location
4. Select the coordinates (e.g., 50.4501, 30.5234)
5. Use these in the template

### 3. Update Store Information
In the same file, update the store details:

```html
<h3 class="font-semibold text-brown-800">Your Store Name</h3>
<p class="text-brown-600">Your actual address</p>
```

And in the popup:
```javascript
marker.bindPopup(`
    <div style="padding: 10px; max-width: 250px;">
        <h3 style="margin: 0 0 8px 0; color: #8B4513; font-weight: bold; font-size: 16px;">
            Your Store Name
        </h3>
        <p style="margin: 0 0 5px 0; color: #666; font-size: 14px;">
            Your actual address
        </p>
        <p style="margin: 0 0 5px 0; color: #666; font-size: 14px;">
            Your working hours
        </p>
        <p style="margin: 0; color: #666; font-size: 14px;">
            Your phone number
        </p>
    </div>
`);
```

### 4. Customize Marker Style
The marker uses your brand colors (brown). To change it, find this section:

```javascript
const customIcon = L.divIcon({
    html: `
        <div style="
            width: 40px; 
            height: 40px; 
            background: #8B4513;  // Change this color
            border: 3px solid white; 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        ">
```

## Advantages of This Solution

### ✅ **No API Key Required**
- Completely free to use
- No registration needed
- No usage limits

### ✅ **OpenStreetMap Benefits**
- Community-driven map data
- Often more detailed than Google Maps
- Free for commercial use
- Regular updates

### ✅ **Leaflet Features**
- Lightweight and fast
- Mobile-friendly
- Customizable markers
- Interactive popups
- Zoom and pan controls

## Testing

1. Start your Django server
2. Navigate to the "Where to Buy" page
3. You should see:
   - Store information on the left
   - Interactive map on the right
   - Clickable marker with popup
   - Transportation information below

## Troubleshooting

### Map Not Loading
- Check internet connection (needs CDN access)
- Verify coordinates are correct
- Check browser console for errors

### Wrong Location
- Double-check coordinates format (decimal, not degrees/minutes)
- Test coordinates in Google Maps first
- Make sure latitude and longitude are in correct order

### Styling Issues
- The map uses your existing CSS classes
- Marker colors match your brown theme
- All styling is inline for compatibility

## Next Steps

1. **Update coordinates** with your actual store location
2. **Customize store information** (name, address, phone, etc.)
3. **Test on different devices** to ensure responsiveness
4. **Consider adding multiple locations** if you have multiple stores

## Alternative Map Providers

If you want to try other free options:

1. **Mapbox** - Free tier available
2. **CartoDB** - Free for basic use
3. **Here Maps** - Free tier with API key
4. **Bing Maps** - Free tier with API key

But OpenStreetMap with Leaflet is the most reliable free option!
