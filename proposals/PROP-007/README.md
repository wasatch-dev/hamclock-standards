# Active Nets Display (NetLogger)

This proposal adds an Active Nets pane to HamClock, giving operators an at-a-glance, continuously updated list of amateur radio nets that are currently on the air, sourced from the NetLogger network.

## Description

The Active Nets pane displays the nets that are live on NetLogger right now: the net name, operating frequency, band, mode, net control station, and the current number of stations checked in. It is presented as a scrolling pane in the same family as the existing Contests, On-The-Air, and DX Peditions panes, and it appears in the HamClock pane-selection menu alongside them. It supports all standard map sizes and rotation sets and may be assigned to any rotating pane or to the large PANE_0 slot.

Each net is drawn with its name in a large font and a smaller supporting line beneath it. The pane refreshes once per minute while it is on screen. Because net names are frequently wider than the narrow pane, the pane offers two display modes toggled by tapping the pane body: a default mode that wraps long names onto a second large line so the full name is visible, and a compact mode that keeps each net on a single line so more nets are visible at once.

The underlying data is sourced from the public NetLogger XML Data Service. The OHB server polls NetLogger once per minute for the list of active nets, reduces the response to the fields HamClock needs, and writes a single small CSV file that HamClock retrieves through the standard backend cached-file pipeline.

## OHB Server Component

The server-side generator is `poll_activenets.py`. Unlike the map overlays, it produces a small text file rather than rendered imagery, and it has no third-party dependencies. It is intended to run once per minute from cron.

### Data Source

| Field | NetLogger XML Element | Used For |
|-------|----------------------|----------|
| Net name | `NetName` | Primary display line |
| Frequency | `Frequency` | Supporting line |
| Band | `Band` | Supporting line |
| Mode | `Mode` | Supporting line |
| Net control | `NetControl` | Supporting line ("NCS") |
| Check-in count | `SubscriberCount` | Supporting line ("ckins") |
| Logger | `Logger` | Carried in CSV, **not displayed** |
| Opened/updated | `Date` | Carried in CSV as "Started" |

**Source:** NetLogger XML Data Service — `GetActiveNets`
**URL:** `https://www.netlogger.org/api/GetActiveNets.php`
**Download size:** a few KB per poll (one XML document listing all active nets)

The poller sends a `ClientName` parameter (`HamClock-OHB`) so NetLogger can identify the client, per the service's usage guidelines. No server name is supplied, so nets from all NetLogger servers are returned.

### Data Transformation

The script parses the XML defensively: it locates each net record by the presence of a `NetName` child element rather than assuming a fixed container tag, so it tolerates element-name variation and forward-compatible additions. For each net it emits one CSV row in a fixed column order. The `Logger` column is retained in the file for completeness but is deliberately omitted from the HamClock display. An empty result or an API error is treated as "no active nets" and produces a header-only file so HamClock can distinguish "no nets right now" from stale data.

### Output File

A single file is written, following the OHB htdocs convention so it is served under the standard `/ham/HamClock/` path:

```
/opt/hamclock-backend/htdocs/ham/HamClock/activenets/activenets.txt
```

Served to HamClock at:

```
<backend>/ham/HamClock/activenets/activenets.txt
```

The file is written atomically (temporary file in the same directory, then `os.replace`) so HamClock never reads a half-written file. CSV format:

```
# NetLogger active nets - updated <UTC timestamp> - <N> net(s)
NetName,Frequency,Band,Mode,NetControl,Checkins,Logger,Started
<one row per active net>
```

The leading comment line carries the update time so freshness can be judged; HamClock skips it and the column header when parsing. Fields containing commas are double-quoted in the standard CSV manner and are handled by the client parser.

### Update Schedule

NetLogger's active-net list changes continuously, so the file is regenerated once per minute. This matches the cadence NetLogger asks of polling clients (no more frequently than once per minute) and is enforced by the one-minute cron granularity:

```cron
* * * * *  /opt/hamclock-backend/scripts/poll_activenets.py
```

The client side independently rate-limits its own fetches to no more than once per minute via the backend cached-file age check, so a single backend file comfortably serves any number of HamClock instances.

### Server Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `python3` | System | Runs the poller (standard library only) |
| `urllib` | Python (stdlib) | HTTP GET to the NetLogger API |
| `xml.etree` | Python (stdlib) | Parse the GetActiveNets response |
| `csv` | Python (stdlib) | Emit the CSV snapshot |
| `cron` | System | One-minute scheduling |

No `pip` or `apt` packages are required.

## HamClock Client Component

The client side is a single new source file, `activenets.cpp`, wired into the pane system as plot choice `PLOT_CH_ACTIVENETS`. It follows the structure of `contests.cpp`.

| Aspect | Value |
|--------|-------|
| Plot choice | `PLOT_CH_ACTIVENETS` (added at end of the `PLOT_CH` list to preserve saved rotation indices) |
| Fetch path | `/activenets/activenets.txt` (relative to the `/ham/HamClock` root that `httpHCGET` prepends) |
| Pane update interval | 60 s (`ACTIVENETS_INTERVAL`) |
| Cache max age | 30 s (`ACTIVENETS_MAXAGE`) — bounds network fetches to once per minute |
| Retrieval | `openCachedFile()` from the configured backend host |
| Touched files | `activenets.cpp` (new), `HamClock.h`, `plotmgmnt.cpp`, `wifi.cpp`, `Makefile` |

Net retrieval reuses the backend cached-file path, so the pane requires HamClock to be pointed at the OHB backend (for example with `-b host:port`) that serves the file.

## Pane Layout

The pane renders each net as a large name line with a smaller supporting line beneath. Row geometry is computed from live font metrics in logical coordinates, so it is correct at every build resolution (800×480 through 3200×1920). The accent colour follows the DRAP-style philosophy of a single distinctive hue per overlay.

| Element | Font | Notes |
|---------|------|-------|
| Title "Active Nets" | Large (16 pt) | Accent colour |
| Subtitle | Small | Count of active nets |
| Net name | Large (16 pt), white | One line (compact) or wrapped to two lines (full names) |
| Supporting line | Small, light grey | `freq band mode - NCS <call> - <n> ckins` |
| Scroll controls | — | Up/down arrows with counts in the title row when the list overflows |

| Display Mode | Behaviour | Visible per top pane | Visible in PANE_0 |
|--------------|-----------|----------------------|-------------------|
| Full names (default) | Name wraps to two large lines | ~1 | ~3 |
| Compact | Name on one line, truncated if needed | ~2 | ~5 |

Tapping the pane body toggles the mode; tapping the title row scrolls or switches the pane.

## Operational Notes

**Most useful for:** operators looking for a net to join or net control stations monitoring activity across the NetLogger community. The pane is mode- and band-agnostic; it shows whatever is currently logged on NetLogger, predominantly HF SSB nets with a mix of VHF/UHF FM, digital, and D-STAR reflectors.

**Refresh behaviour:** the displayed list reflects NetLogger at the time of the last successful poll, stamped in UTC on the first line of the file. Nets opening and closing between polls is normal churn, not an error; the count in the subtitle and the scroll arrows update each minute.

**Failure behaviour:** on a network or HTTP failure the client leaves the previous file in place and keeps showing the last known list rather than going blank. An empty or error response from NetLogger produces a header-only file and the pane shows "No active nets," which is distinct from a stale display because the timestamp continues to advance.

**Backend requirement:** the file is fetched from the configured HamClock backend, not from NetLogger directly. The client must be pointed at the OHB instance that runs `poll_activenets.py`; otherwise the path returns 404 from a backend that does not host it.

**Display limitation:** at 16 pt in a ~160 px-wide pane roughly ten characters fit per line, so two wrapped lines accommodate names up to about twenty characters. The longest four- and five-word net names still clip their final word in full-names mode, as a third large line would leave less than one net visible. Compact mode, the large PANE_0 slot, or backend-side abbreviation of net names are the available mitigations.
