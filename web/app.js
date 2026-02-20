/* Oil Wells Dashboard - Frontend */

const fmt = (v, fallback = "N/A") =>
    v !== null && v !== undefined && v !== "" ? v : fallback;

const fmtNum = (v) => {
    if (v === null || v === undefined || v === "") return "N/A";
    return Number(v).toLocaleString("en-US");
};

const fmtDate = (v) => {
    if (!v) return "N/A";
    try { return new Date(v).toLocaleDateString("en-US"); } catch { return v; }
};

function makeIcon(hasStim) {
    const c = hasStim ? "#34d399" : "#6b7280";
    return L.divIcon({
        className: "",
        iconSize: [18, 18],
        iconAnchor: [9, 9],
        popupAnchor: [0, -12],
        html: `<svg width="18" height="18" viewBox="0 0 18 18">
                 <circle cx="9" cy="9" r="8" fill="${c}" fill-opacity="0.25" stroke="${c}" stroke-width="1.5"/>
                 <circle cx="9" cy="9" r="4" fill="${c}"/>
               </svg>`,
    });
}

// Popup ───────────────────────────────────────────────────

function buildPopup(w) {
    return `
    <div class="popup">

        <div class="popup__header">
            <div class="popup__well-name">${fmt(w.well_name, "Unnamed Well")}</div>
            <span class="popup__api">API# ${fmt(w.api)}</span>
            ${w.ndic_file_no ? `<span class="popup__api" style="margin-left:8px">NDIC# ${w.ndic_file_no}</span>` : ""}
        </div>

        <div class="popup__section">
            <div class="popup__section-title">Well Information</div>
            <div class="popup__grid">
                <div class="popup__field popup__field--full">
                    <span class="popup__key">Operator</span>
                    <span class="popup__val">${fmt(w.operator)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">County</span>
                    <span class="popup__val">${fmt(w.county)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">State</span>
                    <span class="popup__val">${fmt(w.state)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Latitude</span>
                    <span class="popup__val popup__val--mono">${fmt(w.latitude)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Longitude</span>
                    <span class="popup__val popup__val--mono">${fmt(w.longitude)}</span>
                </div>
                <div class="popup__field popup__field--full">
                    <span class="popup__key">Surface Hole Location</span>
                    <span class="popup__val">${fmt(w.shl_location)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Datum</span>
                    <span class="popup__val">${fmt(w.datum)}</span>
                </div>
            </div>
        </div>

        <div class="popup__section">
            <div class="popup__section-title">Stimulation Data</div>
            <div class="popup__grid">
                <div class="popup__field">
                    <span class="popup__key">Date Stimulated</span>
                    <span class="popup__val">${fmtDate(w.stim_date)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Formation</span>
                    <span class="popup__val">${fmt(w.stimulated_formation)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Top (ft)</span>
                    <span class="popup__val popup__val--mono">${fmtNum(w.top_ft)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Bottom (ft)</span>
                    <span class="popup__val popup__val--mono">${fmtNum(w.bottom_ft)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Stages</span>
                    <span class="popup__val popup__val--mono">${fmtNum(w.stimulation_stages)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Volume</span>
                    <span class="popup__val popup__val--mono">${fmtNum(w.volume)} ${fmt(w.volume_units, "")}</span>
                </div>
                <div class="popup__field popup__field--full">
                    <span class="popup__key">Treatment Type</span>
                    <span class="popup__val">${fmt(w.type_treatment)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Acid %</span>
                    <span class="popup__val popup__val--mono">${fmt(w.acid_pct)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Proppant (lbs)</span>
                    <span class="popup__val popup__val--mono popup__val--highlight">${fmtNum(w.lbs_proppant)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Max Pressure (PSI)</span>
                    <span class="popup__val popup__val--mono popup__val--highlight">${fmtNum(w.max_treat_pressure_psi)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Max Rate</span>
                    <span class="popup__val popup__val--mono">${fmtNum(w.max_treat_rate)} ${fmt(w.max_treat_rate_units, "")}</span>
                </div>
            </div>
        </div>

    </div>`;
}

// Map ─────────────────────────────────────────────────────

const map = L.map("map", { center: [48.065, -103.65], zoom: 11 });

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19,
}).addTo(map);

// Load & Render ───────────────────────────────────────────

fetch("/api/wells")
    .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
    })
    .then((wells) => {
        document.getElementById("stat-total").textContent = wells.length;

        const withCoords = wells.filter(w => w.latitude != null && w.longitude != null);
        document.getElementById("stat-active").textContent = withCoords.length;

        const withStim = wells.filter(w => w.type_treatment || w.stim_date).length;
        document.getElementById("stat-oil").textContent = withStim;

        const group = L.featureGroup();

        wells.forEach((w) => {
            if (w.latitude == null || w.longitude == null) return;
            const hasStim = !!(w.type_treatment || w.lbs_proppant || w.max_treat_pressure_psi || w.stim_date);
            const marker = L.marker([w.latitude, w.longitude], { icon: makeIcon(hasStim) });
            marker.bindPopup(buildPopup(w), { maxWidth: 420, minWidth: 340 });
            group.addLayer(marker);
        });

        group.addTo(map);
        if (group.getLayers().length) map.fitBounds(group.getBounds().pad(0.15));
    })
    .catch((err) => {
        console.error("Failed to load wells:", err);
        document.getElementById("stat-total").textContent = "ERR";
    });