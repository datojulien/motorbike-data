# MT-25 Ride

A personal, installable iPhone dashboard for the Yamaha MT-25. Built with standard HTML, CSS and JavaScript. No login, paid API key or server-side database required.

## Features in version 1.0

- Large GPS speedometer in **km/h**, plus compass heading and location accuracy.
- Live, pannable OpenStreetMap view with your position and route trace.
- Trip distance, recording duration, average and maximum GPS speeds.
- Pause/resume and saved ride in browser storage.
- Export trip track to **GPX** or **CSV** (using iOS share sheet when available).
- Open Apple Maps or Waze with a destination for voice-guided directions.
- Quick Apple Music and Spotify launchers (not native playback control).
- Day/night themes, iOS Home Screen icon, Screen Wake Lock where supported.
- Demo mode for checking the dashboard indoors, without granting GPS access.
- Offline app shell; **map imagery requires internet access**.

## GitHub deployment (datojulien/motorbike-data)

The deployable app files live in the `mt25-ride/` directory of [motorbike-data](https://github.com/datojulien/motorbike-data). The dedicated GitHub Actions workflow publishes **only this directory** to the repository's GitHub Pages site. The Python app, fuel logs and other repository files are excluded from the deployed website.

**Pages URL:** https://datojulien.github.io/motorbike-data/

One-time setup if the site is not already enabled: open **Repository Settings → Pages → Build and deployment → Source → GitHub Actions**. Then run the **MT-25 Ride Pages** workflow from the Actions tab if no successful deployment appears automatically.

## Install it on the iPhone 13

1. Open the live Pages URL above using **Safari on the iPhone 13**.
2. Tap **Share → Add to Home Screen**, and turn on **Open as Web App** if offered.
3. Open the Home Screen icon, rotate to landscape (disable Portrait Orientation Lock if needed), then tap **START RIDE** and allow Precise Location.

**Important:** The HTTPS GitHub Pages origin is necessary for geolocation. Opening `index.html` directly from the Files app is not sufficient for reliable GPS.

## Indoor test

Open the deployed site with `?demo=1` at the end of its URL. Alternatively tap Settings → **START DEMO MODE**. Demo mode is explicitly labelled and never overwrites your actual saved trip. `?preview=1` replaces online map imagery with an abstract graphic solely for offline visual previews; it is not a street map.

## Privacy

The site has **no custom backend**, accounts, analytics or telemetry. Trip points are stored in your browser's localStorage. Exported GPX/CSV files include sensitive location history, so share them carefully. OpenStreetMap receives normal map-tile requests (which reveal the approximate viewed area) when connected. Nothing is automatically synced between devices.

## How the GPS works

The speed shown is calculated from `GeolocationCoordinates.speed` when available, with a distance/time fallback. GPS readings are smoothed. Trip distance rejects very inaccurate fixes, small position jitter, implausible jumps and stale gaps. These are **estimates**, not readings from your Yamaha ECU or wheel speed sensor. Phone GPS can lag or be incorrect, especially near tall buildings and in tunnels.

The browser may suspend location and timers when you leave the dashboard, lock the phone or switch to a navigation app. Background miles are **not** reconstructed automatically. App switching also interrupts live visible speed updates. Screen Wake Lock is requested while a ride is active but can be denied, released or overridden by iOS, Low Power Mode or thermal protection.

## Limits and hardware safety

- There is no real embedded turn-by-turn navigation in v1: Apple Maps / Waze launch outside the dashboard.
- No native iOS control of Apple Music or Spotify playing in the background from an unrelated app.
- No connection to Yamaha fuel gauge, RPM, gears or other ECU data.
- The iPhone is not a certified motorcycle instrument; **never rely on it instead of the factory speedometer**.
- Don't handle the screen while moving. Use a vibration-damped, secure mount with a backup tether.
- Direct sunlight and Malaysia's heat may trigger thermal shutdown. Apple specifies an ambient operating range up to 35°C for iPhones; protect from rain, and avoid a sealed case that traps excessive heat.
- Charging over Lightning in rain can be hazardous; use weather-appropriate hardware and avoid charging when the port is wet.

## Technical notes

Everything except map imagery loads without external JavaScript libraries. The app only requests standard OpenStreetMap raster tiles at `https://tile.openstreetmap.org/{z}/{x}/{y}.png` as you view the map and displays © OpenStreetMap contributors attribution. **Do not prefetch/bulk-download** tiles; OSM's public server prohibits offline tile downloads.

The service worker caches local application files only and leaves map-tile caching to your browser's ordinary HTTP cache. For robust multi-day offline touring, use Apple Maps or another provider with authorized offline navigation/maps.

## Run on your own computer

From this directory: `python3 -m http.server 8000`, then open `http://localhost:8000/?demo=1` in a browser. Localhost is treated as a secure context by modern browsers. For iPhone access, publish over HTTPS.

---
MT-25 Ride is a personal project prototype. Test GPS, wake behavior, touch controls and visibility in a **stationary** motorcycle setup before regular use.