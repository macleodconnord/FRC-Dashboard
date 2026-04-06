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
