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

   * Apache web server
   * Interactive map using Leaflet / OpenLayers
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

If using Selenium:

* ChromeDriver must match your Chrome version


# 4. Database Setup

## Step 1: Start MySQL

```
sudo service mysql start
```

## Step 2: Create Database

```
CREATE DATABASE oil_wells;
USE oil_wells;
```

## Step 3: Create Tables

Run:

```
mysql -u root -p oil_wells < schema.sql
```

Tables include:

* wells
* stimulation_data
* production_data


# 5. Running the Project

## Step 1: PDF Extraction

Place all PDF files in:

```
/data/pdfs/
```

Run:

```
python extract_pdf.py
```

This script:

* Iterates over all PDFs
* Extracts API#, well name, latitude, longitude
* Extracts stimulation data
* Inserts data into MySQL

---

## Step 2: Web Scraping

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

## Step 3: Data Preprocessing

Run:

```
python preprocess.py
```

This script:

* Removes HTML tags
* Cleans special characters
* Replaces missing values with N/A or 0
* Converts timestamps if necessary


# 6. Web Application Setup

## Step 1: Start Apache

```
sudo service apache2 start
```

## Step 2: Place Web Files

Copy contents of:

```
/web/
```

to:

```
/var/www/html/
```

## Step 3: Access Webpage

Open browser:

```
http://localhost
```

The map will:

* Display all oil wells
* Show markers at correct coordinates
* Display popup on click with:

  * Well information
  * Stimulation data
  * Production data


# 7. Testing

* Verified coordinates match database
* Verified popup displays complete data
* Verified missing values handled properly
* Tested multiple wells manually


# 8. Design Decisions

* Used OCR because PDFs were scanned images
* Used MySQL for structured relational storage
* Used web scraping to enrich missing data
* Used Leaflet/OpenLayers for lightweight mapping
* Stored cleaned data only (no raw HTML retained)
\
\
\
