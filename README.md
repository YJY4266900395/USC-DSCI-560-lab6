# USC DSCI 560 Lab 6

Oil well data extraction, web scraping, preprocessing, MySQL storage, and interactive map visualization.

## File Structure

```
lab6/
├── dump_pages_json.py          # Step 1: OCR
├── filter_and_parse.py         # Step 2: Parse
├── scrape_production.py        # Step 3: Scrape
├── preprocess.py               # Step 4: Clean
├── load_to_mysql.py            # Step 5: Load
├── schema.sql                  # Database schema
├── requirements.txt
├── README.md
├── drive-001/                  # Input PDFs
├── output/parsed/              # JSONL outputs
│   ├── well_info.jsonl
│   ├── stimulation_data.jsonl
│   └── production_data.jsonl
└── web/
    ├── app.py                  # Flask backend
    ├── index.html              # Map page
    ├── app.js                  # Frontend logic
    ├── style.css               # Dark theme styles
    └── setup.sh                # One command deployment
```

## Requirements

* Ubuntu Linux
* Python 3.9+, pip
* MySQL Server
* Apache2
* Tesseract OCR
* Google Chrome + ChromeDriver (for Selenium scraping)

Install Python dependencies:

```
pip install -r requirements.txt
```

## Database Setup

```bash
sudo service mysql start
sudo mysql < schema.sql
sudo mysql -e "CREATE USER IF NOT EXISTS 'labuser'@'localhost' IDENTIFIED BY 'labpass'; GRANT ALL ON lab6.* TO 'labuser'@'localhost'; FLUSH PRIVILEGES;"
```

This creates database `lab6` with three tables: `well_info`, `stimulation_data`, `production_data`.

## Pipeline

### Step 1: OCR Extraction

```bash
python3 dump_pages_json.py \
    --pdf_dir drive-001 \
    --out_dir output \
    --do_ocr --force_ocr --try_fix_pdf --compact
```

Reads scanned PDFs from `drive-001/`, runs OCR via ocrmypdf + pytesseract, outputs per page JSON to `output/texts/`.

### Step 2: Field Parsing

```bash
python3 filter_and_parse.py \
    --texts_dir output/texts \
    --out_dir output/parsed
```

Extracts structured fields (API#, well name, operator, coordinates, stimulation details) from OCR text using regex. Outputs `well_info.jsonl` and `stimulation_data.jsonl`.

### Step 3: Web Scraping

```bash
python3 scrape_production.py \
    --well_jsonl output/parsed/well_info.jsonl \
    --out_jsonl output/parsed/production_data.jsonl \
    --delay 2.0
```

Uses Selenium to search each well on drillingedge.com by API#, navigates to the detail page, and extracts: well status, well type, closest city, operator, county, oil/gas production, and production date ranges. Supports `--resume` for interrupted runs and `--headless` for no browser window.

### Step 4: Preprocessing

```bash
python3 preprocess.py --data_dir output/parsed
```

Cleans all three JSONL files in place (originals backed up as `.bak`):

* Strips HTML tags, control characters, OCR artifacts
* Normalizes state abbreviations ("ND" to "North Dakota")
* Fixes positive longitudes (North Dakota is western hemisphere)
* Standardizes date formats
* Ensures numeric fields are proper numbers

### Step 5: Load into MySQL

```bash
python3 load_to_mysql.py \
    --user labuser --password labpass --database lab6 \
    --well_jsonl output/parsed/well_info.jsonl \
    --stim_jsonl output/parsed/stimulation_data.jsonl \
    --prod_jsonl output/parsed/production_data.jsonl \
    --truncate
```

Loads all three JSONL files into MySQL. Uses `ON DUPLICATE KEY UPDATE` for safe re-runs.

### Step 6: Web Visualization

```bash
chmod +x web/setup.sh
sudo web/setup.sh
```

Then open http://localhost in your browser.

The setup script installs Apache2, enables reverse proxy modules, starts Flask on port 5000, and configures Apache to proxy traffic to Flask.

## Web Application

The map displays all wells as color coded markers:

* Green: Active
* Orange: Inactive
* Red: Plugged and Abandoned
* Gray: Unknown or no data

Clicking a marker opens a popup with three sections:

1. **Well Information** (from OCR): operator, job type, county/state, coordinates, surface hole location, datum, address
2. **Stimulation Data** (from OCR): date, formation, depth interval, stages, volume, treatment type, acid%, proppant, max pressure, max rate
3. **Production Data** (from web scraping): well status, well type, closest city, oil barrels, gas MCF, production dates, DrillingEdge source link

The Flask backend performs a three table LEFT JOIN with `COALESCE` on overlapping fields (well_name, operator, county_state) to prefer web scraped values over OCR when available.

