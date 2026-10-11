# GeoMeasure Studio

A full-stack geospatial file measurement platform. Upload **KML** and **zipped Shapefile** files, automatically extract geometry metadata, compute accurate **area** and **length** measurements using projected coordinate systems, and visualize results on an interactive map.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![React](https://img.shields.io/badge/React-19-cyan)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Live Deployments

- **Frontend Application (Vercel)**: `[CONFIGURED_ON_DEPLOYMENT]`
- **Backend API (Render)**: `[CONFIGURED_ON_DEPLOYMENT]`
- **API Documentation (Swagger UI)**: `[CONFIGURED_ON_DEPLOYMENT]/docs`
- **Health Check Endpoint**: `[CONFIGURED_ON_DEPLOYMENT]/api/health/`

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [CRS & Measurement Methodology](#crs--measurement-methodology)
- [Production Database & Reliability](#production-database--reliability)
- [Setup & Local Installation](#setup--local-installation)
- [Running Automated Tests](#running-automated-tests)
- [API Reference](#api-reference)
- [Deployment Guide](#deployment-guide)
  - [Deploying Backend to Render](#deploying-backend-to-render)
  - [Deploying Frontend to Vercel](#deploying-frontend-to-vercel)
- [Security & Validation](#security--validation)
- [Limitations & Known Trade-offs](#limitations--known-trade-offs)
- [License](#license)

---

## Features

### Core
- **File Upload** — Accepts `.kml` and `.zip` (Shapefile) files via drag-and-drop or file browser.
- **Format Inspection** — Handles `.shp`, `.shx`, `.dbf`, `.prj` archives and Fiona GDAL KML driver layers.
- **Accurate Metric Calculations** — Calculates polygon planar area (m², hectares, km²) and LineString length (m, km) by auto-projecting to optimal local UTM zones ($32601$–$32660$ North, $32701$–$32760$ South).
- **Independent CRS Tracking** — Tracks `source_crs` and `measurement_crs` independently for complete auditability.
- **Interactive Map** — Visualizes features on a dark-themed Leaflet map with auto-bounds fitting and popup property inspectors.
- **File History & Management** — Browse previous uploads with status badges, metadata, and deletion capabilities.

### Export
- **CSV Export** — Download feature measurements with header, coordinate systems, and computed metric figures.
- **Enhanced GeoJSON Export** — Export GeoJSON enriched with calculated `_area_sq_meters`, `_length_meters`, and `_measurement_crs` in properties.

---

## Architecture

```
┌─────────────────────────────────┐           HTTP/REST           ┌───────────────────────────────────┐
│         React Frontend          │  ──────────────────────────→  │          FastAPI Backend          │
│       (Vite + TypeScript)       │  ←──────────────────────────  │         (Python 3.12 / GDAL)      │
│         Hosted on Vercel        │                               │          Hosted on Render         │
└─────────────────────────────────┘                               └─────────────────┬─────────────────┘
                                                                                    │
                                                                                    │ psycopg2 (TLS)
                                                                                    ▼
                                                                  ┌───────────────────────────────────┐
                                                                  │        Supabase PostgreSQL        │
                                                                  │     Persistent DDL & Indices      │
                                                                  └───────────────────────────────────┘
```

---

## Project Structure

```
GeoMeasure Studio/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application, CORS, lifespan hooks
│   │   ├── config.py            # Pydantic Settings with environment enforcement
│   │   ├── database.py          # PostgreSQL schema migration & connection management
│   │   ├── routers/             # API endpoints (upload, files, measurements, health)
│   │   ├── schemas/             # Pydantic v2 validation models
│   │   ├── services/            # Geospatial engine, file validator, DB repository
│   │   └── utils/               # UTM projection selection, CSV/GeoJSON serializers
│   ├── tests/                   # Pytest automated test suite (52 tests)
│   │   ├── fixtures/            # Sample KML and Shapefile archives
│   │   ├── test_api.py          # End-to-end API lifecycle & production safety tests
│   │   ├── test_crs_utils.py    # UTM calculation & CRS validation tests
│   │   ├── test_geo_processor.py# KML, Shapefile, and unknown CRS processing tests
│   │   ├── test_measurements.py # CSV/GeoJSON export format tests
│   │   └── test_upload.py       # Extension, traversal, and size validation tests
│   ├── requirements.txt         # Pinned Python dependencies
│   ├── Dockerfile               # Debian-slim container with GDAL, GEOS, and PROJ
│   └── .env.example             # Clean environment variable template
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main orchestrator component
│   │   ├── api/client.ts        # Axios client with type-safe methods
│   │   ├── components/          # Reusable UI components (MapView, FileHistory, etc.)
│   │   ├── types/               # TypeScript interfaces
│   │   └── utils/               # Formatting utilities (units, dates)
│   ├── index.html               # Semantic HTML entry with SEO metadata
│   ├── vercel.json              # Vercel SPA routing configuration
│   ├── vite.config.ts           # Vite build config
│   ├── tailwind.config.js       # Curated slate/teal color system
│   └── .env.example             # Frontend environment template
├── render.yaml                  # Render Blueprint definition
├── .gitignore                   # Comprehensive secrets & artifact ignore rules
└── README.md                    # Project documentation
```

---

## CRS & Measurement Methodology

1. **Why Not Measure in EPSG:4326?**
   - Geographic coordinate systems (such as WGS84 / EPSG:4326) define coordinates in angular degrees ($^\circ$).
   - Calculating Euclidean area or length directly on degree values produces distorted and mathematically meaningless results ($^\circ$ latitude has fixed distance, while $^\circ$ longitude varies from ~111 km at the Equator to 0 km at the poles).

2. **Automated UTM Zone Reprojection**:
   - For every geometry, the centroid coordinate is evaluated:
     $$\text{Zone} = \left\lfloor \frac{\text{lon} + 180}{6} \right\rfloor + 1$$
   - Northern hemisphere coordinates ($\text{lat} \ge 0$) map to `EPSG:32601`–`EPSG:32660`.
   - Southern hemisphere coordinates ($\text{lat} < 0$) map to `EPSG:32701`–`EPSG:32760`.
   - Geometries are dynamically projected to their optimal local UTM transverse Mercator projection, ensuring planar metric distortion is strictly minimized ($< 0.1\%$).

3. **Missing `.prj` Projection Handling**:
   - Shapefiles lacking projection metadata are evaluated before processing:
     - **Coordinates within $[-180, 180]$ longitude and $[-90, 90]$ latitude**: Assumed to be WGS84 geographic coordinates, labeled with `EPSG:4326 (assumed - missing .prj)`, and reprojected to UTM for measurement.
     - **Coordinates outside $[-180, 180]$ (e.g., $500000, 4200000$)**: Identified as projected planar coordinates. GeoMeasure Studio **never** assumes EPSG:4326 for these coordinates; it records `source_crs` as `Unknown Projected (missing .prj)` and calculates native planar area and length directly, avoiding catastrophic projection errors.

---

## Production Database & Reliability

- **Strict Production Enforcement**:
  - In `production` (`ENVIRONMENT=production`), a live, accessible PostgreSQL database is mandatory.
  - Startup fails immediately if database connection or schema migration fails.
  - Database outages result in immediate HTTP 503 errors (`Database service unavailable`) with clean error reporting. The system **never** silently accepts uploads into non-persistent memory when configured for production.
- **Configured Development Fallback**:
  - In-memory storage is only enabled when explicitly permitted via `ALLOW_IN_MEMORY_DB=true` or in automated test environments (`ENVIRONMENT=test`).
- **Health Checks**:
  - `/api/health/` runs `SELECT 1` on PostgreSQL and reports status (`healthy`, `degraded`, or `unhealthy` with HTTP 503).

---

## Setup & Local Installation

### Prerequisites
- Python 3.11 or 3.12 (with GDAL/GEOS support)
- Node.js 18+ and npm
- PostgreSQL connection string (Supabase recommended)

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv
# Activate:
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL DATABASE_URL

# Start server
uvicorn app.main:app --reload --port 8000
```
Backend API will be running at `http://localhost:8000` (docs at `http://localhost:8000/docs`).

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000

# Start development server
npm run dev
```
Frontend will be running at `http://localhost:5173`.

---

## Running Automated Tests

Run the full pytest test suite (52 automated unit, integration, and safety tests):
```bash
cd backend
.venv/Scripts/python -m pytest -v
```

Test coverage includes:
- UTM zone calculation across all quadrants, meridian boundaries, and equator boundaries.
- KML parsing and multi-geometry extraction (Point, LineString, Polygon).
- Zipped Shapefile extraction and planar calculation.
- Edge cases: missing `.prj` with projected vs geographic bounds.
- Pydantic v2 `NaT` and `NaN` serialization sanitization.
- Production database safety (HTTP 503 enforcement when DB disconnected).
- Full REST lifecycle (Upload $\to$ Retrieve $\to$ Measurements $\to$ CSV/GeoJSON Export $\to$ Delete).

---

## API Reference

| Method | Endpoint | Description | Query Parameters |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/files/` | Upload `.kml` or `.zip` file | Multipart form data (`file`) |
| `GET` | `/api/files/` | List uploaded files | — |
| `GET` | `/api/files/{id}/` | Get file metadata & GeoJSON | — |
| `GET` | `/api/files/{id}/measurements/` | Get measurements | `?format=json`, `?format=csv`, `?format=geojson` |
| `DELETE` | `/api/files/{id}/` | Delete file & measurements | — |
| `GET` | `/api/health/` | API & DB health status | — |

---

## Deployment Guide

### Deploying Backend to Render

1. **Connect Repository to Render**:
   - Create a **New Web Service** connected to your repository on [render.com](https://render.com).
   - Select **Docker** environment (or select root `render.yaml` Blueprint).
   - Root Directory: `backend` (or use root with `Dockerfile` at `backend/Dockerfile`).
2. **Environment Variables**:
   - `DATABASE_URL`: Your Supabase connection string (use port 6543 pooler mode with `?sslmode=require`).
   - `ENVIRONMENT`: `production`
   - `ALLOW_IN_MEMORY_DB`: `false`
   - `ALLOWED_ORIGINS`: `https://<YOUR-VERCEL-DOMAIN>.vercel.app`
3. **Verify Deployment**:
   - Access `https://<YOUR-RENDER-SERVICE>.onrender.com/api/health/` $\to$ verify `{"status": "healthy", "database": "connected"}`.
   - Access Swagger docs at `https://<YOUR-RENDER-SERVICE>.onrender.com/docs`.

### Deploying Frontend to Vercel

1. **Import Project into Vercel**:
   - Import your repository on [vercel.com](https://vercel.com).
   - Set **Root Directory** to `frontend`.
   - Framework Preset: **Vite**.
2. **Environment Variables**:
   - `VITE_API_URL`: Your public Render API URL (e.g., `https://geomeasure-api.onrender.com`).
3. **Deploy**:
   - Once deployed, copy your Vercel public URL and add it to `ALLOWED_ORIGINS` in Render settings.

---

## Security & Validation

- **No Secrets in Repository**: `.env` files and credentials are systematically excluded via root and frontend `.gitignore`.
- **Zip-Slip & Path Traversal Protection**: Archive member paths are sanitized; absolute paths and parent traversals (`../`) are rejected.
- **Decompression Bomb Protection**: Zip extraction checks uncompressed size against a hard 200 MB limit.
- **Guaranteed Cleanup**: Disk temporary files created during processing are purged inside `finally` blocks.
- **Production Database Integrity**: Non-persistent fallback is disabled in production to guarantee that no user data is silently lost.

---

## Limitations & Known Trade-offs

1. **Synchronous Upload Processing**: Files are processed synchronously within the upload request lifecycle. Suitable for standard files ($< 50$ MB); massive gigabyte datasets should transition to asynchronous Celery/Redis workers.
2. **Multi-Part Geometries**: MultiPolygons and MultiLineStrings calculate cumulative area and length across all sub-parts.
3. **Shapefile Projection Requirement**: Shapefiles lacking `.prj` with projected coordinates are measured in native planar units; accurate global reprojection to WGS84 requires the original projection specification.

---

## License

MIT License. Developed for GeoMeasure Studio.
