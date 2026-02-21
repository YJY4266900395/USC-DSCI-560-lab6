-- schema.sql
-- MySQL 5.7+ (JSON type). Charset: utf8mb4 for robust OCR text.

CREATE DATABASE IF NOT EXISTS lab6 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lab6;

-- =============== Figure 1: well_info ===============
-- Field order (after primary_id) follows Figure 1: left-to-right, top-to-bottom.

DROP TABLE IF EXISTS stimulation_data;
DROP TABLE IF EXISTS well_info;

CREATE TABLE well_info (
  -- internal/relational key
  primary_id            VARCHAR(64)  NOT NULL,

  -- Figure 1 fields (ordered)
  operator              VARCHAR(255) NULL,
  well_name             VARCHAR(255) NULL,
  api                   VARCHAR(20)  NULL,
  enesco_job            VARCHAR(64)  NULL,
  job_type              VARCHAR(120) NULL,
  county_state          VARCHAR(255) NULL,
  shl_location          VARCHAR(255) NULL,
  latitude              DECIMAL(10,6) NULL,
  longitude             DECIMAL(10,6) NULL,
  datum                 VARCHAR(80)  NULL,

  -- extras / provenance (kept after figure fields)
  ndic_file_no          VARCHAR(20)  NULL,
  county                VARCHAR(120) NULL,
  state                 VARCHAR(120) NULL,
  address               VARCHAR(255) NULL,

  lat_raw               VARCHAR(64)  NULL,
  lon_raw               VARCHAR(64)  NULL,
  latlon_page           INT          NULL,
  latlon_suspect         TINYINT(1)  NOT NULL DEFAULT 0,

  fig1_pages            JSON         NULL,

  source_pdf            TEXT         NULL,
  relative_path         VARCHAR(255) NULL,

  raw_text              MEDIUMTEXT   NULL,

  created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (primary_id),
  KEY idx_api (api),
  KEY idx_ndic (ndic_file_no),
  KEY idx_county_state (county_state(64))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============== Figure 2: stimulation_data ===============
-- Field order (after primary_id) follows Figure 2 table: left-to-right, top-to-bottom.

CREATE TABLE stimulation_data (
  id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

  -- relational key
  primary_id            VARCHAR(64)  NOT NULL,

  -- Figure 2 fields (ordered)
  date_stimulated       DATE         NULL,
  stimulation_formation VARCHAR(120) NULL,
  top_ft                INT          NULL,
  bottom_ft             INT          NULL,
  stimulation_stages    INT          NULL,
  volume                DECIMAL(14,2) NULL,
  volume_units          VARCHAR(12)  NULL,
  treatment_type        VARCHAR(120) NULL,
  acid_pct              DECIMAL(6,2) NULL,
  lbs_proppant          BIGINT       NULL,
  max_treatment_pressure_psi INT     NULL,
  max_treatment_rate_bbl_min DECIMAL(8,2) NULL,
  details               TEXT         NULL,

  -- flags (useful for QA)
  stim_present          TINYINT(1)   NOT NULL DEFAULT 0,
  stim_has_fields       TINYINT(1)   NOT NULL DEFAULT 0,

  -- extras / provenance (kept after figure fields)
  api                   VARCHAR(20)  NULL,
  ndic_file_no          VARCHAR(20)  NULL,

  fig2_pages            JSON         NULL,

  source_pdf            TEXT         NULL,
  relative_path         VARCHAR(255) NULL,

  raw_text              MEDIUMTEXT   NULL,
  raw_text_clean        MEDIUMTEXT   NULL,

  created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),

  -- allow multiple stim rows per well if later needed
  UNIQUE KEY uq_stim (primary_id, date_stimulated, top_ft, bottom_ft, volume, treatment_type),

  KEY idx_primary_id (primary_id),
  KEY idx_api (api),
  CONSTRAINT fk_stim_well FOREIGN KEY (primary_id) REFERENCES well_info(primary_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
