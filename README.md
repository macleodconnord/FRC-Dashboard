# Flask Dashboard for FRC
 
 ## Quick start (Raspberry Pi / Raspberry Pi OS)
 1. Create a `.env` file in the project root with:
 
 ```
 TEAM_NUMBER=1234
 DEFAULT_YEAR=2026
 BASE_URL=https://www.thebluealliance.com/api/v3
 API_KEY=YOUR_TBA_KEY
 ```
 
 2. Run:
  ```bash
 chmod +x ./run_dashboard_pi.sh
 ./run_dashboard_pi.sh
 ```
 
 ## Quick start (Windows)
 1. Create a `.env` file in the project root with the same variables as above.
 
 2. Run:
 ```powershell
 .\run_dashboard.ps1
 ```
 
 The scripts will install dependencies, launch the app, and open `http://127.0.0.1:5000/`.

 ## Docker (Linux container; optional Raspberry Pi/ARM emulation)
 1. Create a `.env` file in the project root with the same variables as above.

 2. Run with Docker Compose:
 ```bash
 docker compose up --build
 ```

 3. Open:
 `http://127.0.0.1:5000/`

 ### Raspberry Pi emulation notes
 To emulate a Raspberry Pi userspace on a non-ARM machine, build/run the image as `linux/arm64` (or `linux/arm/v7` for 32-bit) using Docker Buildx.

 Build and run as ARM64:
 ```bash
 docker buildx build --platform linux/arm64 -t frc-dashboard:arm64 --load .
 docker run --rm -p 5000:5000 --env-file .env frc-dashboard:arm64
 ```
