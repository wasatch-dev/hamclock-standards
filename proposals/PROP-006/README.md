# Tropospheric Surface Refractivity Map Overlay (Tropo)
 
This proposal adds a global tropospheric surface refractivity map overlay to HamClock, providing VHF/UHF operators with a visual forecast of ducting and enhanced propagation conditions.
 
## Description
 
The Tropo map displays surface refractivity (N-units) derived from NOAA GFS weather model data. Surface refractivity is a function of temperature, pressure, and humidity near the ground; elevated N-unit values indicate warm, humid low-level air that promotes superrefractive and ducting propagation conditions on VHF/UHF and microwave bands.
 
The map is rendered as a full-colour global overlay using the same day/night terminator pipeline as the existing DRAP, Aurora, and Clouds overlays. It appears in the HamClock core map selection menu alongside those overlays and supports all standard map sizes and rotation sets.
 
The underlying data is sourced from the NOAA NOMADS GRIB2 filter service, which provides free, unrestricted access to the GFS 0.25° global analysis. The OHB server fetches the three required surface fields (2m temperature, 2m relative humidity, surface pressure), computes N-units using the Smith-Weintraub formula, and renders the result as compressed BMPv4 RGB565 files for each supported map size.
 
## OHB Server Component
 
The server-side generator is `update_tropo_maps.sh`. It is structured identically to `update_drap_maps.sh` and uses the same GMT / Pillow rendering pipeline.
 
### Data Source
 
| Field | GRIB2 Variable | Level |
|-------|---------------|-------|
| Temperature | TMP | 2 m above ground |
| Relative Humidity | RH | 2 m above ground |
| Surface Pressure | PRES | Surface |
 
**Source:** NOAA NOMADS GFS 0.25° global analysis  
**URL:** `https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl`  
**Download size:** ~2 MB per update (GRIB2 filter, selected fields only)
 
### Refractivity Formula
 
Surface refractivity N is computed using the Smith-Weintraub equation (ITU-R P.453):
 
```
N = 77.6 × P/T  +  3.73×10⁵ × e/T²
```
 
where P is pressure in hPa, T is temperature in Kelvin, and e is water vapour pressure in hPa derived from relative humidity via the Magnus formula.
 
### Output Files
 
Files are written to `$OUTDIR` following the standard OHB map naming convention:
 
```
map-D-{W}x{H}-Tropo.bmp      Day-side map (light haze applied)
map-N-{W}x{H}-Tropo.bmp      Night-side map (darkened for terminator visibility)
map-D-{W}x{H}-Tropo.bmp.z    zlib-compressed day map (served to HamClock)
map-N-{W}x{H}-Tropo.bmp.z    zlib-compressed night map (served to HamClock)
```
 
One set of files is generated per entry in `map_sizes.txt`. All sizes are rendered in parallel.
 
### Update Schedule
 
GFS analysis data is published four times daily. Files should be regenerated 30 minutes after each run is expected to be available on NOMADS:
 
```cron
30 5,11,17,23 * * *  /opt/hamclock-backend/scripts/update_tropo_maps.sh
```
 
| GFS Run | Data Available ~UTC | Suggested Cron |
|---------|-------------------|----------------|
| 00Z | 04:30–05:00 | 05:30 |
| 06Z | 10:30–11:00 | 11:30 |
| 12Z | 16:30–17:00 | 17:30 |
| 18Z | 22:30–23:00 | 23:30 |
 
The script automatically falls back to the previous GFS run if the most recent one is not yet available on NOMADS.
 
### Server Dependencies
 
| Dependency | Type | Purpose |
|-----------|------|---------|
| `cfgrib` | Python (pip) | GRIB2 file parsing |
| `numpy` | Python (pip) | Array computation |
| `Pillow` | Python (pip) | BMP encoding (shared with DRAP) |
| `libeccodes-dev` | System (apt) | Required by cfgrib |
| `gmt` | System | Grid processing and rendering (shared with DRAP) |
  
## Color Scale
 
The legend gradient spans the global surface refractivity range. Colour follows the same philosophy as DRAP: dark/cool tones indicate low activity, warm tones indicate significant conditions.
 
| N-units | Colour | Propagation indication |
|---------|--------|----------------------|
| < 280 | Near-black | Very dry / cold air, no enhancement |
| 280–310 | Dark blue | Below normal, subrefractive |
| 310–325 | Blue | Near normal |
| 325–340 | Cyan | Normal |
| 340–355 | Green | Slightly enhanced |
| 355–370 | Yellow-green | Superrefractive, enhancement likely |
| 370–395 | Yellow–orange | Ducting possible to probable |
| 395–420 | Orange–red | Strong ducting likely |
| 420+ | Red | Extreme conditions, trans-horizon paths |
 
## Operational Notes
 
**Most useful bands:** 144 MHz and above. Surface refractivity has negligible effect below ~50 MHz.
 
**Best paths:** Over warm ocean or large bodies of water. The map is less predictive over continental interiors where surface N largely reflects pressure patterns rather than the humidity gradients that drive ducting.
 
**Relationship to weather maps:** Surface N broadly correlates with surface pressure (higher pressure → higher N, all else equal) because the dry term in the formula tracks air density. Areas where the Tropo map diverges from the pressure map — particularly warm, humid coastlines and tropical ocean regions — are where the humidity term dominates and ducting conditions are most likely.
 
**Limitation:** Surface N is a proxy for ducting potential. The physical cause of ducting is the vertical *gradient* of N, not N itself. Elevated surface N is strongly correlated with the warm, moist boundary-layer conditions that produce inversions, but does not directly confirm a usable duct. Elevated ducts (500–2000 m) are not predicted by this map.