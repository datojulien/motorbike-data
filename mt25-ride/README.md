# MT-25 Ride v2 — Turn-by-turn Motorcycle Navigator

An installable, landscape-first GPS dashboard for an **iPhone 13** on a Yamaha MT-25. Plain HTML, CSS and JavaScript; no account, database, app store or paid API key.

**Live address:** https://datojulien.github.io/motorbike-data/

The app is in `datojulien/motorbike-data/mt25-ride/`. GitHub Actions (`.github/workflows/mt25-ride-pages.yml`) publishes *only* this directory to the GitHub Pages root, preserving unrelated motorcycle fuel/maintenance files.

## What's new in v2

- **In-dashboard turn-by-turn navigation**: search for a place (explicit search; no background autocomplete), choose a result, or enter `latitude, longitude`.
- **Hold the map for 650 ms** to pin a destination; a confirmation appears.
- Blue/cyan **route polyline** over the existing OpenStreetMap map, destination flag, next-turn arrow, remaining metres, road name, distance remaining and ETA.
- Spoken English instructions using iOS **Web Speech** where available, with a prominent mute/unmute button. Tap voice once if Safari does not play initial instructions. Helmet audio output is controlled by iOS Bluetooth; web speech is not guaranteed on all iOS versions.
- **Off-route rerouting** after three sufficiently accurate, moving GPS fixes outside the route, with a 30-second minimum gap between routing requests. Poor GPS accuracy does not trigger reroutes.
- One-tap **Apple Maps / Waze backup** through **NAVIGATE → WAZE / APPLE MAPS** when directions aren't available.
- Continuing the existing speedometer, GPS accuracy/heading, trip tracking, pause, GPX/CSV export, and day/night mode.
- Demo-mode route simulation: **Settings → Start Demo**, **Navigate → Demo: Putrajaya**, **Resume Ride**. The route simulation uses synthetic GPS readings and does not touch saved real rides.
- Map and navigation can run while trip recording is paused; iOS foreground rules still apply.

## Install on iPhone 13

1. Open **https://datojulien.github.io/motorbike-data/** in Safari.
2. **Share → Add to Home Screen**, then open **MT-25 Ride** from your Home Screen.
3. Disable **Portrait Orientation Lock** if you want the dashboard in landscape. Give **Precise Location** permission.
4. With the motorcycle stationary, tap **NAVIGATE**. Search e.g. `Putrajaya Sentral`, tap a result, wait for the route, then tap the voice button to test Bluetooth audio.
5. Tap **START RIDE** separately if you also want to record the trip and export GPX/CSV.
6. To leave navigation, tap the **×** on the instructions or **NAVIGATE → END NAVIGATION**. This does **not** erase your recorded ride.

## Routing and search services — read before riding

Navigation depends on connectivity and these *community demo* services:

- **OSRM** `https://router.project-osrm.org` for routes and turn locations: best effort, non-commercial testing and low volume; not guaranteed, not traffic-aware. Requests happen when you select a destination or after a confirmed deviation (never more often than the 30-second rerouting cooldown). Route requests include **current GPS position and destination**. See [OSRM demo policy](https://github-wiki-see.page/m/Project-OSRM/osrm-backend/wiki/Api-usage-policy) and [API](https://project-osrm.org/docs/v26.5.0/http).
- **Photon** `https://photon.komoot.io` for *explicit* text search only; no type-ahead/autocomplete, bulk queries, or periodic lookups. Queries include search text and a nearby location bias to improve results. Low-volume personal use only, no uptime guarantees. See [Photon's demo server guidance](https://github.com/komoot/photon).
- **OpenStreetMap** `https://tile.openstreetmap.org/` for visible map tiles only, with attribution. No bulk tile downloads or offline prefetching. See [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/).

For routine or safety-critical navigation, replace demo services with a hosted provider and test reliability before relying on them. Road closures, traffic, one-way streets, and motorcycle-specific restrictions can be inaccurate or missing. Check road signage and regulations. **Waze or Apple Maps is the safer backup.**

## Privacy and persistence

GPX/CSV tracks stay in this browser's `localStorage`; the app does not upload them to a custom server. Public providers receive normal map-tile requests, search terms and limited endpoints for route requests. The service-worker cache holds the app shell only. Routes are not currently saved offline and route guidance may be interrupted without network access.

## Important iOS limitations

**Keep the iPhone unlocked and MT-25 Ride visible.** iOS can suspend geolocation updates, web speech and trip timers when locked, another app is opened, Low Power Mode intervenes or the phone overheats. Wake Lock is requested while riding or navigating if supported, but isn't guaranteed. Apple Music cannot be controlled from this site; use your helmet controls or Siri.

The displayed speed is GPS-derived and can be inaccurate; use the Yamaha factory gauges for road-legal speed/critical data. Secure the iPhone in a *vibration-damped* motorcycle mount, add a tether, avoid wet Lightning charging and be aware of Malaysia's heat/rain. Never touch or type into navigation while riding. Use Apple Maps/Waze for longer or safety-critical trips until this prototype has been tested outdoors.

## Local development and testing

Serve this directory with `python3 -m http.server 8000` and open `http://localhost:8000/` in a browser; enable Demo Mode in Settings. For an iPhone, use HTTPS (GitHub Pages) and Safari.

`navigation.js` implements geocoding, OSRM routing, route matching, next-turn/ETA display and voice/reroute state. `app.js` manages the existing display, GPS tracking, trip and map. `sw.js` caches app-shell files only.
