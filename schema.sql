-- Drop tables (safe order because of FK)
DROP TABLE IF EXISTS stimulation_data;
DROP TABLE IF EXISTS well_info;

-- =========================
-- Table: well_info
-- =========================
CREATE TABLE well_info (
  well_id BIGINT AUTO_INCREMENT PRIMARY KEY,

  api VARCHAR(20) NULL,
  ndic_file_no VARCHAR(20) NULL,

  well_name VARCHAR(255) NULL,
  operator VARCHAR(255) NULL,
  address VARCHAR(255) NULL,
  enesco_job VARCHAR(50) NULL,
  job_type VARCHAR(100) NULL,
  county VARCHAR(100) NULL,
  state VARCHAR(100) NULL,
  shl_location VARCHAR(255) NULL,

  latitude_raw TEXT NULL,
  longitude_raw TEXT NULL,
  latitude DECIMAL(10,6) NULL,
  longitude DECIMAL(10,6) NULL,
  datum VARCHAR(50) NULL,

  source_pdf VARCHAR(255) NULL,
  relative_path VARCHAR(255) NULL,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uq_api (api),
  UNIQUE KEY uq_ndic (ndic_file_no),
  KEY idx_latlon (latitude, longitude)
);

-- =========================
-- Table: stimulation_data
-- =========================
CREATE TABLE stimulation_data (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,

  well_id BIGINT NOT NULL,
  api VARCHAR(20) NULL,

  stim_date DATE NULL,
  stimulated_formation VARCHAR(100) NULL,
  top_ft INT NULL,
  bottom_ft INT NULL,
  stimulation_stages INT NULL,

  volume DECIMAL(12,2) NULL,
  volume_units VARCHAR(50) NULL,

  type_treatment VARCHAR(100) NULL,
  acid_pct VARCHAR(50) NULL,
  lbs_proppant BIGINT NULL,

  max_treat_pressure_psi INT NULL,
  max_treat_rate DECIMAL(10,2) NULL,
  max_treat_rate_units VARCHAR(50) DEFAULT 'BBLS/Min',

  details TEXT NULL,
  raw_text TEXT NULL,
  source_pdf VARCHAR(255) NULL,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  UNIQUE KEY uq_stim_dedupe (well_id, stim_date, top_ft, bottom_ft),
  KEY idx_api (api),

  CONSTRAINT fk_stim_well
    FOREIGN KEY (well_id)
    REFERENCES well_info(well_id)
    ON DELETE CASCADE
);