# USC-DSCI-560-lab6
# 1. Project Overview

This project focuses on extracting oil well data from scanned PDF files, enriching the data through web scraping, preprocessing the collected information, storing it in a MySQL database, and visualizing the results on an interactive web-based map.

The system consists of two major components:

1. Backend Data Pipeline

   * PDF text extraction (OCR)
   * Data cleaning and preprocessing
   * Web scraping from drillingedge.com
   * Database storage (MySQL)

2. Web Visualization

   * Apache web server (reverse proxy to Flask)
   * Interactive map using Leaflet.js
   * Marker-based visualization with popups


# 2. System Architecture

PDF Files
→ OCR Extraction (PyTesseract / OCRMyPDF)
→ Data Cleaning
→ MySQL Database
→ Web Scraping (DrillingEdge)
→ Database Update
→ Apache + Map Frontend


# 3. Environment Requirements

## Software

* Linux (Ubuntu recommended)
* Python 3.9+
* MySQL Server
* Apache2
* pip
* Tesseract OCR

## Python Libraries

Install using:

```
pip install -r requirements.txt
```

Required packages:

* pytesseract
* pdf2image
* PyPDF2
* requests
* beautifulsoup4
* mysql-connector-python
* selenium (if dynamic scraping used)
* flask

If using Selenium:

* ChromeDriver must match your Chrome version


# 4. Database Setup

## Step 1: Start MySQL

```bash
sudo service mysql start
```

## Step 2: Create Database
```bash
sudo mysql
```

```sql
CREATE DATABASE IF NOT EXISTS dsci560_lab6;
CREATE USER IF NOT EXISTS 'labuser'@'localhost' IDENTIFIED BY 'labpass';
GRANT ALL PRIVILEGES ON dsci560_lab6.* TO 'labuser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## Step 3: Create Tables

Run:

```bash
mysql -u labuser -plabpass dsci560_lab6 < schema.sql
```

Tables include:

* well_info
* stimulation_data
* production_data


# 5. Running the Project

## Step 1: PDF Extraction

Place all PDF files in:

```
/data/pdfs/
```

Run:

```bash
python3 dump_pages_json.py \
    --pdf_dir drive-001 \
    --out_dir output \
    --do_ocr --force_ocr --try_fix_pdf --compact
```

This script:

* Iterates over all PDFs
* Extracts API#, well name, latitude, longitude
* Extracts stimulation data
* Inserts data into MySQL

Outputs JSON files with per-page OCR text to `output/texts/`.

---

## Step 2: Parse — Extract structured fields

```bash
python3 filter_and_parse.py \
    --texts_dir output/texts \
    --out_dir output/parsed
```

Outputs `well_info.jsonl` and `stimulation_data.jsonl` to `output/parsed/`.

## Step 3: Load into MySQL

```bash
python3 load_to_mysql.py
```

Reads JSONL files and inserts/updates records in MySQL.

## Step 4: Web Scraping

Run:

```
python scrape_drillingedge.py
```

This script:

* Reads each well entry from database
* Searches drillingedge.com
* Extracts well status, type, city
* Extracts oil and gas production data
* Updates database

---

## Step 5: Data Preprocessing

Run:

```
python preprocess.py
```

This script:

* Removes HTML tags
* Cleans special characters
* Replaces missing values with N/A or 0
* Converts timestamps if necessary

---

## Step 6: Web Application Setup

Run:

```bash
chmod +x ./web/setup.sh
sudo ./web/setup.sh
```
Then click to open browser: 

http://localhost

This script:

1. Installs Apache2 and enables proxy modules
2. Installs Python dependencies (Flask, mysql-connector-python)
3. Creates MySQL user and database (if not already done)
4. Configures Apache as a reverse proxy to Flask
5. Starts Flask backend on 127.0.0.1:5000
6. Restarts Apache

The map displays:

* Push-pin markers at each well's coordinates (color-coded by data availability)
* Click any marker to see a popup with:
  * **Well Information**: API#, NDIC#, well name, operator, county, state, lat/lon, surface hole location, datum, address
  * **Stimulation Data**: date, formation, top/bottom depth, stages, volume, treatment type, acid%, proppant, max pressure, max rate
  * **Production Data**: well status, well type, closest city, oil barrels, gas MCF (when available)


# 7. Testing

* Verified coordinates match database
* Verified popup displays complete data
* Verified missing values handled properly
* Tested multiple wells manually


# 8. Design Decisions

* **OCR**: Used ocrmypdf + pdfplumber because PDFs are scanned images, not text-based
* **Two-pass extraction**: dump_pages_json.py (OCR) → filter_and_parse.py (parsing) allows re-parsing without re-running OCR
* **MySQL**: Structured relational storage with foreign keys between well_info and stimulation_data
* **Apache + Flask**: Apache serves as the public-facing web server, Flask handles API logic behind a reverse proxy
* **Leaflet.js**: Lightweight, well-documented map library with easy marker/popup support
* **Dark theme**: Stadia Alidade Smooth Dark basemap with custom-styled popups for readability

