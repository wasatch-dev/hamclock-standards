# Support light strike information on maps

This proposal adds tropical cyclone tracks to maps and a summary panel. "Tropical cyclones" include cyclones hurricanes typones and like events.

## Description

An endpoint on the backend can be queried for current tropical cyclones. The return is a list of storms with location and description suitable or text summary and a map overlay.

The endpoint is:
```
/ham/HamClock/storms/storms.txt
```
The list of storms are all active and forecast. There is no "age" argument.

```
/ham/HamClock/lightning/strikes.pl?lat=28.54&lon=-81.38&radius=10000&maxage=300
```

## Endpoint
```
/ham/HamClock/storms/storms.txt
```

## GET Method Arguments

None

## Returned Results
Output format (one line per forecast point):
```
  STORMNAME,BASIN,TYPE,CATEGORY,LAT,LON,WIND_KT,FCST_HOUR,ADVISORY
```

Where:
```
  STORMNAME  = storm name e.g. HELENE, or INVEST92L if unnamed
  BASIN      = AL (Atlantic), EP (E.Pacific), CP (C.Pacific), WP (W.Pacific), IO (Indian)
  TYPE       = TD|TS|HU|TY|TC|DB|EX  (Tropical Depression/Storm/Hurricane/Typhoon/etc)
  CATEGORY   = 0-5  (0 = TD or TS, 1-5 = Saffir-Simpson)
  LAT        = decimal degrees, positive=N negative=S
  LON        = decimal degrees, positive=E negative=W
  WIND_KT    = maximum sustained winds in knots
  FCST_HOUR  = 0=current position, 12,24,36,48,72,96,120 = forecast hours
  ADVISORY   = advisory number string e.g. "24" or "24A"
```

First line is always a comment with metadata:
```
  # TROPICAL CYCLONES N storms as of YYYY-MM-DD HH:MM UTC
```

