# GeoMeasure Studio

A production-grade geospatial file measurement platform. Upload **KML** and **zipped Shapefile** archives, inspect geometry attributes, compute accurate metric **area** and **length** measurements via automated local UTM projections, and visualize features on an interactive Leaflet map backed by OpenStreetMap.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![React](https://img.shields.io/badge/React-19-cyan)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)
![Supabase](https://img.shields.io/badge/Database-Supabase%20PostgreSQL-emerald)
![Render](https://img.shields.io/badge/Backend-Render%20Singapore-purple)
![Vercel](https://img.shields.io/badge/Frontend-Vercel-black)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Verified Live Deployments

- **Frontend Application (Vercel)**: [https://geomeasure-studio.vercel.app](https://geomeasure-studio.vercel.app)
- **Backend API (Render)**: [https://geomeasure-backend.onrender.com](https://geomeasure-backend.onrender.com)
- **Interactive API Documentation (Swagger UI)**: [https://geomeasure-backend.onrender.com/docs](https://geomeasure-backend.onrender.com/docs)
- **Production Health Check**: [https://geomeasure-backend.onrender.com/api/health/](https://geomeasure-backend.onrender.com/api/health/)
- **GitHub Repository**: [https://github.com/siva3009/geomeasure-studio](https://github.com/siva3009/geomeasure-studio)

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [CRS Methodology & Measurement Accuracy](#crs-methodology--measurement-accuracy)
- [Missing CRS Handling Policy](#missing-crs-handling-policy)
- [Verified Manual Checks & Observed Measurements](#verified-manual-checks--observed-measurements)
- [Production Database & Supabase Pooler Configuration](#production-database--supabase-pooler-configuration)
- [Setup & Local Installation](#setup--local-installation)
- [Automated Testing & Verification](#automated-testing--verification)
- [v2 Phase 1: Secure API Key Infrastructure](#v2-phase-1-secure-api-key-infrastructure)
  - [API Key Architecture & Security](#api-key-architecture--security)
  - [Database Migration & RLS](#database-migration--rls)
  - [API Key Management Endpoints](#api-key-management-endpoints)
  - [External Geometry Measurement Endpoint (v1)](#external-geometry-measurement-endpoint-v1)
  - [Authentication Error Reference](#authentication-error-reference)
- [v2 Phase 2: Developer Dashboard & API Playground](#v2-phase-2-developer-dashboard--api-playground)
  - [Authentication Flow](#developer-authentication-flow)
  - [Overview Dashboard](#overview-dashboard)
  - [API Key Management Lifecycle](#api-key-management-lifecycle)
  - [Interactive API Playground](#interactive-api-playground)
- [API Reference](#api-reference)
- [Measurement Units & Output Standards](#measurement-units--output-standards)

- [Security & Validation](#security--validation)
- [Limitations & Known Trade-offs](#limitations--known-trade-offs)
- [Learning Outcomes](#learning-outcomes)
- [Future Scope](#future-scope)
- [License](#license)

---

## Features

### Core Geospatial Engine
- **Multi-Format Ingestion**: Supports `.kml` (Keyhole Markup Language) and zipped Shapefile archives (`.zip` containing `.shp`, `.shx`, `.dbf`, and `.prj`).
- **Automated Local UTM Projection**: Detects feature centroids and reprojects geometries into their optimal transverse Mercator zone (UTM Zones $1$–$60$ North / South) to compute metric planar area and length with minimal distortion ($< 0.1\%$).
- **Separate CRS Tracking**: Records `source_crs` and `measurement_crs` independently for every feature, ensuring full traceability and data integrity.
- **Support for Multi-Part Geometries**: Accurately measures `Polygon`, `MultiPolygon`, `LineString`, and `MultiLineString` features.
- **Interactive OpenStreetMap Map**: Dark-themed Leaflet map with automatic viewport bounds fitting, vector geometry styling, hover tooltips, and click inspection popups.
- **Empty Geometry State**: Gracefully identifies datasets without displayable coordinates and renders a helpful empty state rather than misplacing markers at coordinate origins.

### Data Management & Export
- **Persistent File History**: Backed by Supabase PostgreSQL; uploaded datasets and computed measurements persist across browser refreshes and sessions.
- **CSV Export**: Downloads a detailed tabular summary of feature IDs, geometry types, source CRS, measurement CRS, area (m²), length (m), and user attributes.
- **Enhanced GeoJSON Export**: Exports standard RFC 7946 GeoJSON enriched with calculated `_area_sq_meters`, `_length_meters`, and `_measurement_crs` attributes.
- **Lifecycle Management**: Delete uploaded datasets and cascade-delete associated measurement records.

---

## Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.12, FastAPI, Pydantic v2 | High-performance asynchronous REST API, data validation, and lifecycle hooks |
| **Geospatial Processing** | GeoPandas, Shapely 2.0, PyProj, Fiona, PyOgrio | Vector geospatial manipulation, topology operations, and coordinate transformations |
| **Database** | Supabase (PostgreSQL 15+) via psycopg2 | Persistent relational storage, JSONB storage for attributes and GeoJSON |
| **Frontend Framework** | React 19, TypeScript 5, Vite 8 | Single-page application, type-safe API communication |
| **Mapping & GIS UI** | Leaflet, React-Leaflet | OpenStreetMap tile visualization, vector overlay layers, interactive popups/tooltips |
| **Styling** | Tailwind CSS, Lucide Icons | Curated dark-themed glassmorphism interface with responsive layouts |
| **Backend Hosting** | Render (Singapore Region, Docker runtime) | Python 3.11-slim container with GDAL, GEOS, and PROJ C-libraries |
| **Frontend Hosting** | Vercel (Edge Network) | Static SPA hosting with custom routing rules |

---

## System Architecture

```
┌───────────────────────────────────────────────┐
│           React 19 Frontend (Vite)            │
│       Hosted on Vercel (Edge Network)         │
│  - File Upload & Drag-and-Drop Dropzone       │
│  - Leaflet Map (OpenStreetMap TileLayer)      │
│  - Measurement Table & Unit Converter         │
│  - CSV & GeoJSON Export Trigger               │
└───────────────────────┬───────────────────────┘
                        │
                        │ HTTPS / REST (JSON)
                        ▼
┌───────────────────────────────────────────────┐
│            FastAPI Backend Service            │
│       Hosted on Render (Docker / Singapore)   │
│  - File Validation (Zip-Slip, Size Limits)    │
│  - GeoPandas & Fiona KML / Shapefile Drivers  │
│  - Dynamic Centroid UTM Calculation (PyProj)  │
│  - Shapely Planar Area & Length Computation   │
│  - Strict Production Mode Enforcement         │
└───────────────────────┬───────────────────────┘
                        │
                        │ TCP / TLS (Port 5432 / 6543 Pooler)
                        ▼
┌───────────────────────────────────────────────┐
│             Supabase PostgreSQL               │
│       Managed Cloud Relational Database       │
│  - uploaded_files (UUID PK, JSONB GeoJSON)    │
│  - measurements (Foreign Key, Cascade Delete) │
│  - Indexes on file_id and created_at          │
└───────────────────────────────────────────────┘
```

---

## Project Structure

```
GeoMeasure Studio/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS middleware, lifespan startup
│   │   ├── config.py            # Pydantic Settings with production safety rules
│   │   ├── database.py          # PostgreSQL connection management & DDL schema
│   │   ├── routers/
│   │   │   ├── upload.py        # POST /api/files/ upload & processing pipeline
│   │   │   ├── files.py         # GET, DELETE /api/files/ file management
│   │   │   ├── measurements.py  # GET /api/files/{id}/measurements/ (JSON, CSV, GeoJSON)
│   │   │   └── health.py        # GET /api/health/ database connectivity check
│   │   ├── schemas/             # Pydantic v2 schemas for files & measurements
│   │   ├── services/
│   │   │   ├── file_validator.py# Extension, MIME, path traversal, archive safety
│   │   │   ├── geo_processor.py # Geospatial parsing, UTM selection, measurement engine
│   │   │   └── db_service.py    # PostgreSQL repository with production error guards
│   │   └── utils/
│   │       ├── crs_utils.py     # Centroid-to-UTM calculations & CRS validation
│   │       └── export.py        # CSV & enriched GeoJSON generators
│   ├── tests/                   # 53 automated tests (Pytest)
│   ├── schema.sql               # Standalone Supabase PostgreSQL schema script
│   ├── Dockerfile               # Debian-slim with GDAL, GEOS, and PROJ dependencies
│   ├── requirements.txt         # Pinned Python dependencies
│   └── .env.example             # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── api/client.ts        # Axios API client
│   │   ├── components/
│   │   │   ├── FileUpload.tsx   # Drag-and-drop file upload with progress indicators
│   │   │   ├── FileHistory.tsx  # List previous uploads with status & deletion
│   │   │   ├── MapView.tsx      # Leaflet map with OpenStreetMap basemap & tooltips
│   │   │   ├── MeasurementTable.tsx # Interactive measurements table with unit toggle
│   │   │   ├── ExportButtons.tsx    # CSV and GeoJSON download actions
│   │   │   └── DiagnosticsPanel.tsx # CRS audit and file processing diagnostics
│   │   ├── types/               # TypeScript interfaces
│   │   ├── index.css            # Tailwind directives and Leaflet dark theme styling
│   │   └── App.tsx              # Application layout and state orchestration
│   ├── vercel.json              # Vercel SPA client rewrite configuration
│   ├── vite.config.ts           # Vite configuration
│   └── .env.example             # Frontend environment template
├── render.yaml                  # Render Blueprint definition (Singapore region)
├── .gitignore                   # Comprehensive rules preventing credential leaks
└── README.md                    # Project documentation
```

---

## CRS Methodology & Measurement Accuracy

### 1. The Geometric Fallacy of Measuring in EPSG:4326
Coordinates in `EPSG:4326` (WGS84) are expressed in angular degrees ($^\circ$), not linear units (meters). 
- A degree of latitude is roughly constant (~$111\text{ km}$), but a degree of longitude shrinks with the cosine of latitude:
  $$\text{Length of } 1^\circ \text{ longitude} \approx 111.320 \times \cos(\text{latitude}) \text{ km}$$
- At $60^\circ\text{ N}$, $1^\circ$ of longitude is only half its equatorial width (~$55.8\text{ km}$).
- Performing Euclidean area ($\Delta x \times \Delta y$) directly on degree coordinates yields mathematically invalid results in "square degrees" ($^\circ{}^2$), which cannot be converted to square meters by a constant multiplier.

### 2. Automated Local UTM Zone Selection
GeoMeasure Studio solves this by dynamically reprojecting features to their local **Universal Transverse Mercator (UTM)** zone:
1. The feature centroid $(\text{lon}, \text{lat})$ is computed.
2. The optimal UTM zone number ($1$ to $60$) is derived mathematically:
   $$\text{Zone} = \left\lfloor \frac{\text{lon} + 180}{6} \right\rfloor + 1$$
3. The hemisphere determines the EPSG code:
   - Northern Hemisphere ($\text{lat} \ge 0$): `EPSG:32601` through `EPSG:32660`
   - Southern Hemisphere ($\text{lat} < 0$): `EPSG:32701` through `EPSG:32760`
4. The geometry is reprojected into the target UTM projection using `pyproj` and `shapely.ops.transform`.
5. Area and length are calculated planarly in meters with distortion guaranteed below $0.1\%$.

### 3. Separation of Source and Measurement CRS
Every measurement record explicitly stores:
- `source_crs`: The original CRS declared by the dataset (e.g., `EPSG:4326`, `EPSG:32643`).
- `measurement_crs`: The projected coordinate system utilized to compute the metric measurements (e.g., `EPSG:32643`).

---

## Missing CRS Handling Policy

Shapefiles require a companion `.prj` file to define their coordinate reference system. When an uploaded Shapefile archive lacks a `.prj` file:

1. **No Silent EPSG:4326 Assumption**: Coordinates falling within the $[-180, 180]$ longitude and $[-90, 90]$ latitude range are **never** silently assumed to be `EPSG:4326`. Many local engineering coordinate systems (or localized grid systems) use small numerical coordinate values that fall inside this range without being WGS84 geographic degrees.
2. **Preservation of Geometry and Attributes**: Feature geometries, coordinate WKT strings, and all DBF table attributes are preserved in the database and output GeoJSON.
3. **Explicit Unknown Status**: The `source_crs` is set to `"Unknown (missing .prj)"`.
4. **Withholding Untrustworthy Measurements**: Because calculating metric area or length requires knowing whether coordinates are meters, feet, or degrees, metric measurements are withheld (`area_sq_meters = None`, `length_meters = None`, `measurement_crs = None`).
5. **Clear Diagnostic Warning**: Diagnostic notes are logged and attached to the feature records informing the user that area and length cannot be computed reliably without a valid `.prj` file.

---

## Verified Manual Checks & Observed Measurements

The live production deployment on Render and Vercel was manually validated against demonstrated real-world geospatial datasets:

### 1. Demonstrated KML Upload (`measurement-test.kml`)
- **Source CRS**: `EPSG:4326`
- **Features Tested**: 3 features (Point, LineString, and Polygon)
- **Observed Measurements**:
  - **Point**: Length = `None`, Area = `None`
  - **LineString**: Displayed Length = `1.0841 km`
  - **Polygon**: Displayed Area = `1.1990 ha`

### 2. Demonstrated Shapefile Upload (`GeoMeasure_Test_Shapefile_Chennai.zip`)
- **Source CRS**: `EPSG:4326`
- **Features Tested**: 3 Polygon land parcel features in Chennai, India
- **Measurement CRS**: `EPSG:32644` (UTM Zone 44N)
- **Observed Measurements**:
  - **Parcel A**: Displayed Area = `1.1990 ha`
  - **Parcel B**: Displayed Area = `6714.43 m²`
  - **Parcel C**: Displayed Area = `5035.80 m²`

### 3. Automated Backend Test Fixtures (Tested Separately in Test Suite)
The automated pytest test suite in `backend/tests/fixtures/` independently verifies:
- `sample.kml`: 3 features (Point, LineString, Polygon) in New Delhi, India ($77.2^\circ\text{ E}, 28.6^\circ\text{ N}$), reprojected to UTM Zone 43N (`EPSG:32643`), with Polygon area $\sim 1,085,000\text{ m²}$ ($\sim 1\text{ km²}$) and LineString length $\sim 1,500\text{ m}$.
- `sample_shapefile.zip`: Zipped Shapefile with `.prj` (`EPSG:4326`) defining a polygon parcel accurately measured in UTM.

### 4. Leaflet & OpenStreetMap Visualization
- Tiles served directly via `https://tile.openstreetmap.org/{z}/{x}/{y}.png`.
- Attributed with `© OpenStreetMap contributors`.
- Vector styling: emerald fill for Polygons, cyan stroke for LineStrings, indigo circle markers for Points.
- Sticky hover tooltips display feature names; clicking opens popup inspectors showing metric area and length.

### 5. Data Export & Persistence
- **CSV Export**: Verified header `feature_index,feature_id,geometry_type,source_crs,measurement_crs,area_sq_meters,length_meters,measurement_unit` with valid numeric records.
- **GeoJSON Export**: Verified valid RFC 7946 FeatureCollection with `_area_sq_meters` and `_length_meters` embedded in `properties`.
- **Persistence**: Refreshed browser; file history and past measurements loaded seamlessly from Supabase PostgreSQL.

### 6. Production Health Endpoint
A live GET request to `https://geomeasure-backend.onrender.com/api/health/` confirms:
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "connected",
  "storage": "postgresql",
  "timestamp": "2026-10-11T15:09:54.264073+00:00"
}
```

---

## Production Database & Supabase Pooler Configuration

### 1. Database Connection Guidelines
GeoMeasure Studio connects to Supabase PostgreSQL using `psycopg2`. 
- **IPv4 Compatibility via Supabase Pooler**: Render web services operate in an IPv4 environment. To connect reliably without requiring IPv6, connect via the Supabase Connection Pooler (`aws-0-[region].pooler.supabase.com`).
- **Port Selection**:
  - **Session Mode (Port 5432)**: Recommended for standard connections (`psycopg2`), supporting prepared statements and session-level locks.
  - **Transaction Mode (Port 6543)**: Designed for high-concurrency serverless connections.
- **Connection URI Format**:
  ```text
  postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@[POOLER-HOST]:5432/postgres?sslmode=require
  ```
  *(Always append `?sslmode=require` to enforce TLS encryption).*

### 2. Secret Protection
- The actual `DATABASE_URL` with database password must **never** be committed to version control.
- In `render.yaml`, `DATABASE_URL` is configured with `sync: false`. Render prompts for this value securely in the dashboard during deployment.

### 3. Production Safety Enforcement
In [config.py](file:///c:/Users/my%20pc/Downloads/GeoMeasure%20Studio/backend/app/config.py) and [main.py](file:///c:/Users/my%20pc/Downloads/GeoMeasure%20Studio/backend/app/main.py):
- When `ENVIRONMENT=production`, in-memory fallback is strictly disabled (`is_in_memory_allowed == False`).
- If PostgreSQL is unreachable during application startup, the service aborts immediately rather than accepting uploads that cannot be persisted.
- If a database failure occurs during an upload, the API immediately returns `503 Service Unavailable`.

---

## Setup & Local Installation

### Prerequisites
- Python 3.11 or 3.12 (with GDAL and GEOS binaries)
- Node.js 18+ and npm
- PostgreSQL database (local or Supabase)

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and supply your local or Supabase DATABASE_URL

# Start development server
uvicorn app.main:app --reload --port 8000
```
API runs at `http://localhost:8000` (Swagger docs at `http://localhost:8000/docs`).

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000

# Start Vite dev server
npm run dev
```
Frontend runs at `http://localhost:5173`.

---

## Automated Testing & Verification

The backend test suite contains **72 automated tests** covering end-to-end API workflows, API key infrastructure, geospatial projection logic, and production safety guards.

### Running Backend Tests
```bash
cd backend
.venv/Scripts/python -m pytest -v
```

**Test Results: 72 passed in 14.06s**
- `test_api.py` (7 tests): End-to-end API lifecycle, KML upload, Shapefile upload, invalid extension rejection, production database safety (HTTP 503 enforcement when DB is disconnected), and production health check verification.
- `test_api_keys.py` (19 tests): Cryptographic key creation, plaintext return-only-at-creation policy, SHA-256 database hashing verification, metadata isolation (no secrets or hashes in list/inspect), user ownership isolation (cross-user rejection), unauthenticated rejection (401), external v1 measurement endpoint authorization, invalid/malformed/missing key rejection (401), immediate revocation enforcement, expiration rejection, invalid geometry rejection (400), optional `Authorization: Bearer gm_live_...` support, JWT algorithm whitelist rejection (`none`/`HS384`), malformed token rejection, asymmetric RS256 JWKS verification with key rotation, Point geometry output verification, LineString with projected CRS (`EPSG:3857`), and full end-to-end sequential lifecycle QA.
- `test_crs_utils.py` (14 tests): UTM zone selection across hemispheres, Prime Meridian, Date Line, Equator, New Delhi, London, Sydney, geographic CRS detection, and CRS string normalization.
- `test_geo_processor.py` (14 tests): KML parsing and feature extraction, UTM metric measurement accuracy, handling Shapefiles missing `.prj` with coordinates in $[-180, 180]$ and projected coordinates (verifying unknown CRS status and withholding measurements), and valid projected Shapefile metric measurements.
- `test_measurements.py` (6 tests): CSV header and row formatting, GeoJSON measurement property injection, and empty dataset handling.
- `test_upload.py` (12 tests): File extension validation, uppercase extensions, path traversal stripping, file size validation, empty file rejection, and safe filename extraction.

*(Total: $7 + 19 + 14 + 14 + 6 + 12 = 72$ tests)*


### Running Frontend Production Build
```bash
cd frontend
npm run build
```
**Build Result: Built in 540ms** (`tsc -b && vite build` transformed 128 modules with 0 errors).

---

## v2 Phase 1: Secure API Key Infrastructure

GeoMeasure Studio v2 introduces secure, programmatic access via API keys. External applications can authenticate using API keys to calculate accurate metric measurements on arbitrary GeoJSON geometries without manually uploading files.

### API Key Architecture & Security
1. **Cryptographic Generation**:
   - Generated using Python's `secrets.token_urlsafe(32)` providing 256 bits of cryptographic entropy.
   - Standard prefix format: `gm_live_<secret>` (e.g. `gm_live_tJ7qK8...`).
2. **One-Time Plaintext Exposure**:
   - The plaintext API key is returned **strictly once** in the response of `POST /api/keys/`.
   - The server **never stores plaintext keys** and cannot recover them.
3. **Database Hashing**:
   - The database stores a `SHA-256` hex digest (`key_hash`) and a non-secret display prefix (`gm_live_` + first 8 characters, e.g. `gm_live_aB3dE8f2`).
   - The hash is indexed with a `UNIQUE` constraint for $O(1)$ constant-time lookup.
   - List, inspection, usage, and error endpoints never disclose the hash or the secret.
4. **User Ownership Enforcement**:
   - Key management endpoints (`/api/keys/`) require a valid Supabase Auth JWT token (`Authorization: Bearer <token>`).
   - An API key alone **cannot** access or manage the dashboard.
   - Cross-user key access is blocked: users cannot view, inspect, or revoke keys owned by other users.
5. **Immediate Revocation**:
   - Soft revocation sets `revoked_at = now()`.
   - Revocation takes effect immediately for all subsequent external API calls while preserving request counts and audit history.

---

### Database Migration & RLS

The database schema is additive and preserves all v1 tables without changes:
- Standalone migration script: [`backend/migrations/002_api_keys.sql`](file:///c:/Users/my%20pc/Downloads/GeoMeasure%20Studio/backend/migrations/002_api_keys.sql)
- Combined DDL script: [`backend/schema.sql`](file:///c:/Users/my%20pc/Downloads/GeoMeasure%20Studio/backend/schema.sql)

#### Applying the Migration
1. Open your Supabase Dashboard $\to$ **SQL Editor**.
2. Run [`backend/migrations/002_api_keys.sql`](file:///c:/Users/my%20pc/Downloads/GeoMeasure%20Studio/backend/migrations/002_api_keys.sql):
   ```sql
   CREATE TABLE IF NOT EXISTS api_keys (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       user_id UUID NOT NULL,
       name TEXT NOT NULL,
       key_hash TEXT NOT NULL UNIQUE,
       prefix TEXT NOT NULL,
       created_at TIMESTAMPTZ DEFAULT now(),
       last_used_at TIMESTAMPTZ,
       revoked_at TIMESTAMPTZ,
       expires_at TIMESTAMPTZ,
       request_count BIGINT NOT NULL DEFAULT 0
   );

   CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
   CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
   ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

   DO $$
   BEGIN
       IF NOT EXISTS (
           SELECT 1 FROM pg_policies 
           WHERE tablename = 'api_keys' AND policyname = 'Users can view and manage their own API keys'
       ) THEN
           CREATE POLICY "Users can view and manage their own API keys"
               ON api_keys FOR ALL
               USING (auth.uid() = user_id)
               WITH CHECK (auth.uid() = user_id);
       END IF;
   END
   $$;
   ```
*(Note: When the backend starts up, the `init_db()` lifespan hook in `database.py` also automatically verifies and creates the table and indexes if missing).*

---

### Environment Variables

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | Supabase PostgreSQL pooled URI | `postgresql://postgres.[ref]:[pass]@[pooler]:5432/postgres?sslmode=require` |
| `ENVIRONMENT` | Runtime environment (`production`, `development`, `test`) | `production` |
| `ALLOW_IN_MEMORY_DB` | Permits in-memory fallback in local dev/testing | `false` |
| `ALLOWED_ORIGINS` | Permitted CORS frontend origins | `http://localhost:5173,https://geomeasure-studio.vercel.app` |
| `SUPABASE_URL` | Supabase Project URL (`https://[ref].supabase.co`) | Required for fetching JWKS if using asymmetric RS256/ES256 signing |
| `SUPABASE_JWT_SECRET` | Supabase Auth JWT Secret (Project Settings $\to$ API $\to$ JWT Secret) | Required in production when using symmetric HS256 signing |
| `MAX_UPLOAD_SIZE_MB` | Maximum file upload size limit | `50` |
| `MAX_DECOMPRESSED_SIZE_MB` | Maximum uncompressed archive extraction limit | `200` |

---

### API Key Management Endpoints

All management endpoints require user authentication: `Authorization: Bearer <supabase-jwt>`.

#### 1. Create an API Key (`POST /api/keys/`)
**Request:**
```bash
curl -X POST "https://geomeasure-backend.onrender.com/api/keys/" \
  -H "Authorization: Bearer <YOUR-SUPABASE-JWT>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Production GIS Pipeline", "expires_in_days": 90}'
```
**Response (`201 Created`):**
```json
{
  "id": "e4f8b2d1-93c6-4b2e-a579-3f0a1c890e12",
  "name": "Production GIS Pipeline",
  "prefix": "gm_live_k9X2mQ7L",
  "api_key": "gm_live_k9X2mQ7L8vB4zR1pT6yW0uN5sD3eA8jF",
  "created_at": "2026-10-11T21:40:00Z",
  "expires_at": "2027-01-09T21:40:00Z"
}
```
*(Save the `api_key` now; it will never be returned again).*

#### 2. List API Keys (`GET /api/keys/`)
**Request:**
```bash
curl "https://geomeasure-backend.onrender.com/api/keys/" \
  -H "Authorization: Bearer <YOUR-SUPABASE-JWT>"
```
**Response (`200 OK`):**
```json
[
  {
    "id": "e4f8b2d1-93c6-4b2e-a579-3f0a1c890e12",
    "name": "Production GIS Pipeline",
    "prefix": "gm_live_k9X2mQ7L",
    "created_at": "2026-10-11T21:40:00Z",
    "last_used_at": "2026-10-11T21:42:15Z",
    "revoked_at": null,
    "expires_at": "2027-01-09T21:40:00Z",
    "is_active": true,
    "request_count": 42
  }
]
```

#### 3. Revoke an API Key (`DELETE /api/keys/{id}/`)
**Request:**
```bash
curl -X DELETE "https://geomeasure-backend.onrender.com/api/keys/e4f8b2d1-93c6-4b2e-a579-3f0a1c890e12/" \
  -H "Authorization: Bearer <YOUR-SUPABASE-JWT>"
```
**Response (`200 OK`):**
```json
{
  "id": "e4f8b2d1-93c6-4b2e-a579-3f0a1c890e12",
  "name": "Production GIS Pipeline",
  "prefix": "gm_live_k9X2mQ7L",
  "created_at": "2026-10-11T21:40:00Z",
  "last_used_at": "2026-10-11T21:42:15Z",
  "revoked_at": "2026-10-11T21:45:00Z",
  "expires_at": "2027-01-09T21:40:00Z",
  "is_active": false,
  "request_count": 42
}
```

---

### External Geometry Measurement Endpoint (v1)

Authenticate using header `X-API-Key: gm_live_YOUR_KEY_HERE` (or `Authorization: Bearer gm_live_YOUR_KEY_HERE`).

#### `POST /api/v1/measurements/`
Submit an arbitrary GeoJSON geometry with an explicit CRS to compute planar metric measurements.

**Request:**
```bash
curl -X POST "https://geomeasure-backend.onrender.com/api/v1/measurements/" \
  -H "X-API-Key: gm_live_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": {
      "type": "Polygon",
      "coordinates": [
        [
          [77.2090, 28.6139],
          [77.2190, 28.6139],
          [77.2190, 28.6239],
          [77.2090, 28.6239],
          [77.2090, 28.6139]
        ]
      ]
    },
    "crs": "EPSG:4326",
    "properties": {
      "parcel_name": "Block 4A"
    }
  }'
```

**Response (`200 OK`):**
```json
{
  "geometry_type": "Polygon",
  "source_crs": "EPSG:4326",
  "measurement_crs": "EPSG:32643",
  "area_sq_meters": 1085412.3012,
  "length_meters": null,
  "area_hectares": 108.5412,
  "area_sq_km": 1.0854,
  "length_km": null,
  "measurement_unit": "meters",
  "properties": {
    "parcel_name": "Block 4A"
  }
}
```

---

### Authentication Error Reference

| Status Code | Scenario | Response Body |
| :--- | :--- | :--- |
| `401 Unauthorized` | Missing `X-API-Key` | `{"detail": "Missing API key. Provide a valid key via the 'X-API-Key' header."}` |
| `401 Unauthorized` | Malformed key prefix | `{"detail": "Invalid API key format. Keys must start with 'gm_live_'."}` |
| `401 Unauthorized` | Unrecognized key | `{"detail": "Invalid or unrecognized API key."}` |
| `401 Unauthorized` | Key has been revoked | `{"detail": "API key has been revoked and can no longer be used."}` |
| `401 Unauthorized` | Key has expired | `{"detail": "API key has expired."}` |
| `400 Bad Request` | Unknown CRS submitted | `{"detail": "An explicit, valid Coordinate Reference System (CRS) is required. Unknown CRS is not permitted."}` |
| `400 Bad Request` | Malformed GeoJSON | `{"detail": "Invalid GeoJSON geometry structure: ..."}` |
| `404 Not Found` | Accessing another user's key | `{"detail": "API key not found."}` |

---

## v2 Phase 2: Developer Dashboard & API Playground

GeoMeasure Studio v2 Phase 2 introduces a dedicated developer portal at `/developer`, enabling self-service API key provisioning, real-time usage inspection, and an interactive geospatial measurement sandbox.

### Developer Authentication Flow
- **Supabase Auth Integration**: Full email/password sign-in and account registration powered by official `@supabase/supabase-js`.
- **JWT Session Synchronization**: Automatically persists session tokens in browser memory/storage and passes Bearer JWT tokens (`Authorization: Bearer <token>`) to key management endpoints.
- **Client Configuration Safety**: Requires only `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. Privileged service-role keys, JWT secrets, and database passwords are never exposed to the client.

### Overview Dashboard
- **Live Metric Counters**: Real-time cards displaying **Total Keys**, **Active Keys**, **Revoked / Expired Keys**, and **Total Programmatic Requests** aggregated directly from PostgreSQL database records.
- **Recent Credentials Activity**: Quick view of latest key prefixes, status indicators, and last-used dates.
- **Quick Actions**: One-click actions to generate new credentials, jump to the interactive playground, or read endpoint specifications.

### API Key Management Lifecycle
- **Key Generation**: Create named API keys with customizable expiration periods (30 days, 60 days, 90 days, 1 year, or never expires).
- **One-Time Plaintext Modal**: The raw secret (`gm_live_<secret>`) is presented strictly once upon creation with a one-click copy button. Plaintext keys are never stored on the server or retained in client storage.
- **Immediate Soft-Revocation**: Users can revoke keys on demand with instant confirmation. Subsequent requests with revoked keys are rejected immediately (`401 Unauthorized`) while preserving audit history.
- **Metadata Inspection**: Inspect non-sensitive key details (key ID, non-secret prefix, created timestamp, last-used timestamp, and request count).

### Interactive API Playground
- **Endpoint Sandbox**: Interactive testing interface for `POST /api/v1/measurements/`.
- **Credential Selector & Key Masking**: Test with any active account key with a password-mask toggle to prevent accidental shoulder-surfing of secrets.
- **Geometry Presets**: Instant geometry templates for **Polygon** (urban parcel), **LineString** (transit route), **Point** (validation check), and custom GeoJSON.
- **Pre-Flight JSON Validation**: Local syntax validation catches malformed coordinates before sending network requests.
- **Dynamic cURL Generator**: Generates real, ready-to-run cURL commands reflecting the exact geometry, CRS, and headers specified in the playground.
- **Live Response Inspector**: Displays HTTP status, network duration in milliseconds, computed metric measurements (area in $m^2$, hectares, $km^2$; length in meters, $km$), and formatted JSON output.

---

## API Reference


### Core File & Geometry Endpoints (v1)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/files/` | Upload `.kml` or `.zip` file | Public (v1 Web App) |
| `GET` | `/api/files/` | List all uploaded files | Public (v1 Web App) |
| `GET` | `/api/files/{id}/` | Retrieve file details & GeoJSON | Public (v1 Web App) |
| `GET` | `/api/files/{id}/measurements/` | Retrieve measurements (`json`, `csv`, `geojson`) | Public (v1 Web App) |
| `DELETE` | `/api/files/{id}/` | Delete file & measurements | Public (v1 Web App) |
| `GET` | `/api/health/` | Health & DB connectivity check | Public |
| `GET` | `/docs` | Interactive Swagger UI | Public |
| `POST` | `/api/v1/measurements/` | External programmatic geometry measurement | **`X-API-Key` Required** |

### API Key Management Endpoints (v2 Phase 1)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/keys/` | Create a new API key | **Bearer JWT (User)** |
| `GET` | `/api/keys/` | List user's active/revoked API keys | **Bearer JWT (User)** |
| `GET` | `/api/keys/{id}/` | Get non-sensitive key metadata | **Bearer JWT (User)** |
| `DELETE` | `/api/keys/{id}/` | Revoke an API key immediately | **Bearer JWT (User)** |
| `GET` | `/api/keys/{id}/usage/` | Get usage count and last-used timestamp | **Bearer JWT (User)** |

---

## Measurement Units & Output Standards

- **Length Measurements**:
  - Computed internally in meters ($m$).
  - Displayed in the UI as meters ($< 1,000\text{ m}$) or kilometers ($\ge 1,000\text{ m}$).
- **Area Measurements**:
  - Computed internally in square meters ($m^2$).
  - Displayed in the UI with dynamic unit toggles: square meters ($m^2$), hectares ($ha$, $1\text{ ha} = 10,000\text{ m}^2$), or square kilometers ($km^2$, $1\text{ km}^2 = 1,000,000\text{ m}^2$).
- **Export Units**: Exported CSV and GeoJSON files always store raw metric values in meters ($m$) and square meters ($m^2$) alongside the explicit `measurement_unit` field to prevent downstream conversion ambiguity.

---

## Security & Validation

1. **Zip-Slip & Path Traversal Prevention**: Every archive member path is resolved and validated to ensure extraction remains strictly within the isolated temporary directory. Members containing parent traversals (`../`) or absolute paths are rejected.
2. **Decompression Bomb Protection**: Archive inspection limits total decompressed size to $200\text{ MB}$, preventing zip-bomb memory exhaustion.
3. **Upload Size Limits**: Uploaded files are capped at $50\text{ MB}$.
4. **Guaranteed File Cleanup**: Temporary directories on disk are managed via context managers (`tempfile.TemporaryDirectory`) ensuring immediate cleanup upon request completion.
5. **No Tracked Secrets**: `.env`, `.venv`, and temporary artifacts are ignored by `.gitignore`. Connection secrets are managed via dashboard environment variables.

---

## Limitations & Known Trade-offs

1. **Synchronous Upload Lifecycle**: File processing occurs synchronously inside the upload handler. This provides instant feedback for files under $50\text{ MB}$, but multi-gigabyte point clouds or national datasets would require an asynchronous worker queue (e.g., Celery + Redis).
2. **Local UTM Zone Boundary Distortion**: Features spanning multiple UTM zones are projected to the UTM zone of their centroid. For extremely wide continental geometries spanning over $6^\circ$ of longitude, an equal-area projection (such as Albers Equal Area or sinusoidal projection) would be preferable to minimize edge distortion.
3. **Shapefiles Missing `.prj`**: Without coordinate reference metadata, area and length are withheld to preserve geospatial correctness. The user must supply a valid `.prj` file to calculate trustworthy metric measurements.

---

## Learning Outcomes

- Realized why calculating Euclidean area directly on geographic degree coordinates (`EPSG:4326`) produces mathematically invalid results, and how dynamic local UTM zone reprojection achieves metric accuracy.
- Gained practical experience handling ESRI Shapefile coordinate reference system quirks, particularly why coordinate ranges alone never guarantee `EPSG:4326`.
- Mastered full-stack geospatial architecture using GeoPandas, Shapely, PyProj, FastAPI, and React-Leaflet.
- Designed resilient cloud deployments pairing Render (Docker C-library container) with Supabase PostgreSQL and Vercel edge hosting.
- Implemented production fail-fast database policies that prevent silent data loss.

---

## Future Scope

1. **User-Supplied CRS Override**: Allow users to manually select or supply an EPSG code or WKT string when uploading a Shapefile that lacks a `.prj` file.
2. **Additional Vector Formats**: Expand support to GeoPackage (`.gpkg`), FlatGeobuf (`.fgb`), and DXF/DWG CAD formats.
3. **Elevation & 3D Calculations**: Integrate digital elevation models (DEM) to compute true surface area over rugged terrain.
4. **Geodesic Measurement Toggle**: Provide options to compare planar UTM calculations with ellipsoidal geodesic algorithms (Karney's method).
5. **Asynchronous Background Processing**: Transition large file uploads to asynchronous background tasks using Celery and Redis with WebSocket progress streaming.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
