/**
 * Oil Wells Dashboard – Frontend
 * Fetches well + stimulation + production data from /api/wells,
 * renders colour-coded markers on Leaflet map,
 * popups show all three tables' data.
 */

const fmt = (v, fallback = "N/A") =>
    v !== null && v !== undefined && v !== "" ? v : fallback;

const fmtNum = (v) => {
    if (v === null || v === undefined || v === "") return "N/A";
    return Number(v).toLocaleString("en-US");
};

//  Status classification 

function statusClass(w) {
    const s = (w.well_status || "").toLowerCase();
    if (s.includes("active") && !s.includes("inactive")) return "active";
    if (s.includes("inactive"))                           return "inactive";
    if (s.includes("plug") || s.includes("abandon"))      return "plugged";
    return "unknown";
}

function statusLabel(w) {
    if (w.well_status && w.well_status.length > 1) return w.well_status;
    const labels = { active: "Active", inactive: "Inactive", plugged: "Plugged & Abandoned", unknown: "Unknown" };
    return labels[statusClass(w)];
}

//  Marker icons 

function makeIcon(cls) {
    const colours = {
        active:   "#34d399",
        inactive: "#f97316",
        plugged:  "#ef4444",
        unknown:  "#6b7280",
    };
    const c = colours[cls] || colours.unknown;
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

//  Popup 

function buildPopup(w) {
    const cls = statusClass(w);

    return `
    <div class="popup">

        <div class="popup__header">
            <div class="popup__well-name">${fmt(w.well_name, "Unnamed Well")}</div>
            <span class="popup__api">API# ${fmt(w.api)}</span>
            ${w.ndic_file_no ? `<span class="popup__api" style="margin-left:8px">NDIC# ${w.ndic_file_no}</span>` : ""}
            <span class="popup__status-badge popup__status-badge--${cls}">${statusLabel(w)}</span>
        </div>

        <!--  Well Information (from well_info)  -->
        <div class="popup__section">
            <div class="popup__section-title">Well Information</div>
            <div class="popup__grid">
                <div class="popup__field popup__field--full">
                    <span class="popup__key">Operator</span>
                    <span class="popup__val">${fmt(w.operator)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Job Type</span>
                    <span class="popup__val">${fmt(w.job_type)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Well Type</span>
                    <span class="popup__val">${fmt(w.well_type)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">County / State</span>
                    <span class="popup__val">${fmt(w.county_state)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Closest City</span>
                    <span class="popup__val">${fmt(w.closest_city)}</span>
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
                <div class="popup__field">
                    <span class="popup__key">Address</span>
                    <span class="popup__val">${fmt(w.address)}</span>
                </div>
            </div>
        </div>

        <!--  Stimulation Data (from stimulation_data)  -->
        <div class="popup__section">
            <div class="popup__section-title">Stimulation Data</div>
            <div class="popup__grid">
                <div class="popup__field">
                    <span class="popup__key">Date Stimulated</span>
                    <span class="popup__val">${fmt(w.date_stimulated)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Formation</span>
                    <span class="popup__val">${fmt(w.stimulation_formation)}</span>
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
                    <span class="popup__val">${fmt(w.treatment_type)}</span>
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
                    <span class="popup__val popup__val--mono popup__val--highlight">${fmtNum(w.max_treatment_pressure_psi)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Max Rate (BBL/Min)</span>
                    <span class="popup__val popup__val--mono">${fmtNum(w.max_treatment_rate_bbl_min)}</span>
                </div>
                <div class="popup__field popup__field--full">
                    <span class="popup__key">Details</span>
                    <span class="popup__val">${fmt(w.details)}</span>
                </div>
            </div>
        </div>

        <!--  Production Data (from production_data, web-scraped)  -->
        <div class="popup__section">
            <div class="popup__section-title">Production Data (Web-Scraped)</div>
            <div class="popup__grid">
                <div class="popup__field">
                    <span class="popup__key">Oil Produced (bbl)</span>
                    <span class="popup__val popup__val--mono popup__val--highlight">${fmtNum(w.oil_barrels)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Gas Produced (MCF)</span>
                    <span class="popup__val popup__val--mono popup__val--highlight">${fmtNum(w.gas_mcf)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">First Production</span>
                    <span class="popup__val">${fmt(w.first_production_date)}</span>
                </div>
                <div class="popup__field">
                    <span class="popup__key">Most Recent</span>
                    <span class="popup__val">${fmt(w.most_recent_production_date)}</span>
                </div>
                ${w.drillingedge_url ? `
                <div class="popup__field popup__field--full">
                    <span class="popup__key">Source</span>
                    <span class="popup__val"><a href="${w.drillingedge_url}" target="_blank" style="color:#60a5fa">DrillingEdge ↗</a></span>
                </div>` : ""}
            </div>
        </div>

    </div>`;
}

//  Map 

const map = L.map("map", { center: [48.065, -103.65], zoom: 11 });

L.tileLayer("https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://stadiamaps.com/">Stadia</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
    maxZoom: 19,
    subdomains: 'abcd',
}).addTo(map);

//  Load & Render 

fetch("/api/wells")
    .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
    })
    .then((wells) => {
        // Header stats
        document.getElementById("stat-total").textContent = wells.length;

        const activeCount = wells.filter(w => statusClass(w) === "active").length;
        document.getElementById("stat-active").textContent = activeCount;

        const totalOil = wells.reduce((s, w) => s + (Number(w.oil_barrels) || 0), 0);
        document.getElementById("stat-oil").textContent = totalOil.toLocaleString("en-US");

        // Markers
        const group = L.featureGroup();

        wells.forEach((w) => {
            if (w.latitude == null || w.longitude == null) return;
            const cls = statusClass(w);
            const marker = L.marker([w.latitude, w.longitude], { icon: makeIcon(cls) });
            marker.bindPopup(buildPopup(w), { maxWidth: 440, minWidth: 340 });
            group.addLayer(marker);
        });

        group.addTo(map);
        if (group.getLayers().length) map.fitBounds(group.getBounds().pad(0.15));
    })
    .catch((err) => {
        console.error("Failed to load wells:", err);
        document.getElementById("stat-total").textContent = "ERR";
    });