# Satellite Transmitter Frequencies and Live Doppler (SatNOGS)

This proposal adds satellite transmitter frequency and mode information to HamClock, sourced from the SatNOGS database, together with two new full-screen views: a paginated frequency/mode table and a live, self-updating Doppler screen. It gives operators the actual uplink/downlink frequencies, modes, FM access tones, and real-time Doppler-corrected tuning for any satellite HamClock is already tracking.

## Description

HamClock already predicts satellite passes and plots ground tracks, but it does not know a satellite's radios. This proposal supplies that missing layer. For each satellite in HamClock's active list, the operator can open a frequency/mode table listing every known transmitter — mode, uplink and downlink frequencies, baud, operational status, and CTCSS/PL tone — and from there drill into a live Doppler screen for a chosen transmitter.

Both views are reached from the existing DX satellite menu (a new "Show freq/modes" item), not from the pane-selection menu, because they are modal full-screen displays rather than rotating panes. They support all standard build resolutions (800×480 through 3200×1920); every position is derived from live screen and font metrics rather than fixed pixels.

The frequency/mode table is paginated, since busy satellites such as the ISS expose dozens of transmitters. Status is colour-coded (active green, inactive grey, future yellow), transponder passbands are shown as a low–high range with an inverting flag, and tapping a row selects that transmitter and opens the Doppler screen for it.

The Doppler screen is the operational centrepiece. It shows the transmitter's nominal downlink and uplink, its FM access tone if any, the next pass summary (AOS, time of closest approach, LOS, and duration), a live az/el/range/range-rate line that turns green when the satellite is above the horizon, and the Doppler-corrected RX tune and TX transmit frequencies updated roughly once per second. A sky-dome pass plot in the upper right — the same renderer HamClock uses for its standalone "Show pass here" view — draws the pass arc with a live marker that crawls along it as the pass progresses. Local weather (temperature in the user's configured units, plus a drawn condition glyph) is shown in the header.

The underlying data is sourced from the public SatNOGS database. The OHB server queries SatNOGS once per satellite during the existing TLE refresh, reduces each response to the fields HamClock needs, and writes a single small CSV file that HamClock retrieves through the standard backend cached-file pipeline.

## OHB Server Component

The server-side generator is `fetch_sat_freq.sh`. Like the TLE tooling and unlike the map overlays, it produces a small text file rather than rendered imagery. It runs as a continuation of the existing TLE refresh chain — immediately after `filter_amsat_active.pl` has produced the active satellite list — so it never needs its own satellite roster and always agrees with the set of satellites HamClock is tracking.

### Data Source

For each satellite, the NORAD catalog id is read from the first line of its TLE block in `esats.txt` and used to query the SatNOGS transmitter list. The fields consumed from each transmitter record:

| Field            | SatNOGS JSON          | Used For                                          |
| ---------------- | --------------------- | ------------------------------------------------- |
| NORAD id         | (from `esats.txt` TLE)| Join key to the displayed satellite               |
| Name             | (satellite name)      | Display / grouping                                |
| Status           | `status`              | Colour coding; rows with `invalid` are dropped    |
| Type             | `type`                | Transmitter / Transceiver / Transponder           |
| Mode             | `mode`                | FM, AFSK, LSB, etc.                                |
| Uplink low/high  | `uplink_low/high`     | Nominal and Doppler-corrected TX                  |
| Downlink low/high| `downlink_low/high`   | Nominal and Doppler-corrected RX                  |
| Baud             | `baud`                | Supporting detail (e.g. `9k6`)                    |
| Invert           | `invert`              | Transponder inverting flag                        |
| CTCSS / PL tone  | (parsed from `description`) | FM access tone, in Hz                       |
| Description      | `description`         | Free-text supporting line (last column)           |

**Source:** SatNOGS DB Transmitters API
**URL:** `https://db.satnogs.org/api/transmitters/?satellite__norad_cat_id=<NORAD>&format=json`
**Download size:** a small JSON document per satellite (one query per active satellite per refresh).

SatNOGS does not expose a structured tone field, so the CTCSS/PL access tone is extracted from the free-text `description` with a case-insensitive pattern matching `CTCSS` or `PL` followed by a number. DCS codes and split access/decode tones are intentionally not matched; a satellite with no recognised tone simply carries a blank `ctcss` field.

### Data Transformation

The script issues one query per NORAD id and emits one CSV row per transmitter, grouped by satellite. Transmitters of every status except `invalid` are written, so the client can show or filter active, inactive, and future transmitters as it chooses. Frequencies are passed through in Hz exactly as SatNOGS reports them; the `*_high` columns are blank for single-frequency (non-transponder) transmitters and carry the passband edge only for transponders.

The `description` is the last column and is sanitised so a naive split on `,` stays correct: embedded commas become semicolons, and pipes and newlines become spaces. The column header is emitted as a `# fields:` comment line, which makes the format self-describing — the client maps columns by name, so the column order may change and new columns (such as `ctcss`) may be appended without breaking older or newer clients. An empty result or an API error for a given satellite yields no rows for it rather than aborting the file.

### Output File

A single file is written, following the OHB htdocs convention so it is served under the standard `/ham/HamClock/` path, alongside `esats.txt`:

```
/opt/hamclock-backend/htdocs/ham/HamClock/esats/esats-freq.txt
```

Served to HamClock at:

```
<backend>/ham/HamClock/esats/esats-freq.txt
```

CSV format:

```
# SatNOGS transmitter frequencies/modes - updated <UTC timestamp>
# fields: norad,name,status,type,mode,uplink_low,uplink_high,downlink_low,downlink_high,baud,invert,ctcss,description
<one row per transmitter, grouped by NORAD>
```

The leading comment lines carry the update time (so freshness can be judged) and the self-describing field list. HamClock skips any line beginning with `#` except that it reads the `# fields:` line to build its column map. Writing the file atomically (temporary file in the same directory, then rename) is recommended so HamClock never reads a half-written file.

### Update Schedule

Unlike continuously changing data such as active nets, a satellite's transmitter list changes rarely. The frequency file is therefore regenerated as part of the existing TLE refresh rather than on its own fast cadence — it is wired in by adding one call to `fetch_sat_freq.sh` immediately after the active-satellite filter in `fetch_tle.sh`:

```
# in fetch_tle.sh, after filter_amsat_active.pl produces esats.txt
/opt/hamclock-backend/scripts/fetch_sat_freq.sh
```

This piggybacks on whatever schedule the site already uses for TLE updates (typically daily) and guarantees the frequency file and the TLE list are always generated from the same satellite roster. A single backend file serves any number of HamClock instances through the client's cached-file age check.

### Server Dependencies

| Dependency        | Type   | Purpose                                                  |
| ----------------- | ------ | -------------------------------------------------------- |
| `curl`            | System | HTTPS GET to the SatNOGS transmitters API               |
| `jq`              | System | Parse the JSON response and emit CSV rows / extract tone |
| `fetch_tle.sh`    | OHB    | Host chain; supplies `esats.txt` and invokes the script |
| `cron`            | System | Scheduling (inherited from the TLE refresh job)         |

No Python or additional packages are required.

## HamClock Client Component

The client side adds no new pane. It extends the existing satellite feature with a parser and two full-screen views, plus a web-endpoint addition.

| Aspect             | Value                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------- |
| Entry point        | DX satellite menu item "Show freq/modes" (per displayed satellite)                    |
| Fetch path         | `/esats/esats-freq.txt` (relative to the `/ham/HamClock` root that the fetch prepends)|
| Parser             | `getSatFreqs()` — header-driven, maps columns by name from the `# fields:` line       |
| Data structure     | `SatFreq` (status, type, mode, ctcss, description, up/down low/high, baud, invert)     |
| Frequency table    | `showSatFreqs()` — paginated full-screen list, tap a row to open Doppler              |
| Doppler screen     | `showSatDoppler()` — live tuning view with sky dome, refreshed ~1 s                   |
| Web endpoint       | `/get_satellite.txt` gains per-active-transmitter Doppler-corrected frequency lines   |
| Retrieval          | Standard backend cached-file path from the configured backend host                    |
| Touched files      | `HamClock.h`, `earthsat.cpp`, `webserver.cpp`                                          |

The parser is deliberately header-driven: it reads the `# fields:` line and resolves each column by name, defaulting absent columns sensibly (for example, a file without a `status` column is treated as all-active, and one without `ctcss` simply shows no tone). This makes the client tolerant of both the original column layout and later additions, so a backend that has not yet been regenerated with the newer format continues to work.

Frequency retrieval reuses the backend cached-file path, so the views require HamClock to be pointed at the OHB backend (for example with `-b host:port`) that serves the file.

## Screen Layout

### Frequency / Mode Table

A paginated full-screen table. Columns: Mode, Up MHz, Dn MHz, Baud, Status, Description. Status is colour-coded (active green, inactive grey, future yellow). Mode and description are clipped to their columns to prevent wrap. Transponder passbands display as `low-high` with a trailing `i` when inverting, and baud is shown compactly (e.g. `9600` as `9k6`). A "More" control appears when the list exceeds one page; Ok, Enter, or Esc dismisses. Tapping a row highlights it (not persisted) and Ok then opens the Doppler screen for that transmitter.

### Live Doppler Screen

A proportional layout, all positions derived from screen height (`P = height/16`) and font metrics, verified to stay on-screen at every build resolution.

| Element              | Position            | Notes                                                              |
| -------------------- | ------------------- | ------------------------------------------------------------------ |
| Title                | Top left            | `<name> Doppler`, accent colour                                    |
| Mode / Type          | Left                | From `SatFreq`                                                     |
| Local weather        | Left (gap row)      | Temperature in the user's units (`showTempC`) + drawn condition glyph |
| Nominal downlink/uplink | Left, grey       | Published centre frequencies (reference)                          |
| CTCSS tone           | Left, grey          | Shown only when a tone was parsed; does not Doppler-shift          |
| AOS / TCA / LOS / dur| Left                | Next-pass summary in local time                                    |
| Az/El/Range/Rate     | Full width, below dome | Live; green when elevation ≥ 0, grey below the horizon          |
| RX tune / TX xmit    | Full width          | Live, Doppler-corrected (`%.5f MHz` plus kHz shift), white         |
| Sky dome             | Upper right         | Pass arc + live marker; reuses the existing pass-dome renderer     |
| Ok button            | Bottom right        | Clear of the dome                                                  |

The Doppler correction uses `dop = range_rate / c`: the received downlink is `downlink × (1 − dop)` and the uplink to transmit is `uplink × (1 + dop)`. AOS and LOS come from HamClock's existing pass finder; duration is their difference; TCA (time of closest approach) is found by stepping the prediction across the pass to its minimum range. The sky dome is drawn by the same routine as the standalone pass view, parameterised by a target circle so there is one implementation shared by both screens. The pass arc is fixed for a given pass while the now-marker is redrawn each refresh, so it crawls along the arc in step with the live tuning digits, and is plotted only while the satellite is above the horizon.

### Web Endpoint

`/get_satellite.txt` gains a block of per-active-transmitter lines giving the transmitter mode and its current Doppler-corrected RX and TX frequencies (with passband variants for transponders), using the same key/value format as the rest of the endpoint, so headless and scripted clients get the same live tuning data as the on-screen view.

## Operational Notes

**Most useful for:** satellite operators who want the actual radios for a bird — which transmitter is active, what mode and access tone it uses, and where to set RX and TX right now given Doppler — without leaving HamClock or consulting an external chart.

**Units:** temperature on the Doppler screen follows the user's HamClock units setting via `showTempC()` — Celsius for Metric and British, Fahrenheit for Imperial — with no separate configuration. Frequencies are displayed in MHz and tones in Hz.

**Refresh behaviour:** the frequency list reflects SatNOGS at the time of the last backend regeneration, which is tied to the TLE refresh; transmitter data changes rarely, so a daily cadence is appropriate. The Doppler screen's live numbers and dome marker update roughly once per second from HamClock's own orbital model; the pass summary and weather are computed when the screen opens.

**Failure behaviour:** the header-driven parser tolerates an older `esats-freq.txt` that lacks the `status` or `ctcss` columns — those simply default rather than corrupting the display, so status colours and the tone line appear automatically once the backend is regenerated with the newer script. A satellite with no frequency rows shows an empty table rather than an error.

**Backend requirement:** the file is fetched from the configured HamClock backend, not from SatNOGS directly. The client must be pointed at the OHB instance that runs `fetch_sat_freq.sh`; otherwise the path returns 404 from a backend that does not host it.

**Display limitations:** HamClock's embedded fonts are ASCII-only, so the temperature uses a plain unit letter (for example `72 F`) rather than a degree symbol, and condition icons are drawn from primitives rather than loaded from image files. The CTCSS/PL extraction is a regex over free text, so it covers the common `CTCSS <n> Hz` and `PL <n>` forms but does not decode DCS codes or distinguish separate access and decode tones; an unrecognised tone is shown as no tone rather than a wrong one.
