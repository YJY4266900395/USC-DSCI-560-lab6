DROP DATABASE IF EXISTS lab6;
CREATE DATABASE lab6 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lab6;

-- =========================
-- Table: well_info
-- =========================
CREATE TABLE well_info (
    operator VARCHAR(255),
    well_name VARCHAR(255),
    api VARCHAR(20) NOT NULL,
    enesco_job VARCHAR(100),
    job_type VARCHAR(100),
    county_state VARCHAR(255),
    shl_location VARCHAR(255),
    latitude DECIMAL(10,6),
    longitude DECIMAL(10,6),
    datum VARCHAR(50),

    -- auxiliary fields
    ndic_file_no VARCHAR(20),
    county VARCHAR(100),
    state VARCHAR(100),
    address VARCHAR(255),

    lat_raw TEXT,
    lon_raw TEXT,
    latlon_page INT,
    latlon_suspect BOOLEAN,

    fig1_pages JSON,
    raw_text TEXT,

    PRIMARY KEY (api)
);

-- =========================
-- Table: stimulation_data
-- =========================
CREATE TABLE stimulation_data (
    date_stimulated DATE,
    stimulation_formation VARCHAR(255),
    top_ft INT,
    bottom_ft INT,
    stimulation_stages INT,
    volume DECIMAL(12,2),
    volume_units VARCHAR(20),
    treatment_type VARCHAR(100),
    acid_pct DECIMAL(5,2),
    lbs_proppant INT,
    max_treatment_pressure_psi INT,
    max_treatment_rate_bbl_min DECIMAL(6,2),
    details TEXT,

    api VARCHAR(20) NOT NULL,

    stim_present BOOLEAN,
    stim_has_fields BOOLEAN,

    ndic_file_no VARCHAR(20),
    fig2_pages JSON,
    raw_text TEXT,
    raw_text_clean TEXT,

    PRIMARY KEY (api),
    CONSTRAINT fk_stim_api
        FOREIGN KEY (api)
        REFERENCES well_info(api)
        ON DELETE CASCADE
);

-- =========================
-- Table: production_data (web-scraped from DrillingEdge)
-- =========================
CREATE TABLE production_data (
    api VARCHAR(20) NOT NULL,
    well_name VARCHAR(255),
    well_status VARCHAR(100),
    well_type VARCHAR(100),
    closest_city VARCHAR(255),
    operator VARCHAR(255),
    county_state VARCHAR(255),
    first_production_date VARCHAR(50),
    most_recent_production_date VARCHAR(50),
    oil_barrels DECIMAL(14,2),
    gas_mcf DECIMAL(14,2),
    drillingedge_url TEXT,
    scrape_success BOOLEAN,

    PRIMARY KEY (api),
    CONSTRAINT fk_prod_api
        FOREIGN KEY (api)
        REFERENCES well_info(api)
        ON DELETE CASCADE
);
