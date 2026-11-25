# CareQueue Clinic — Online Appointment & Patient Booking System

Full Stack Development Minor Project by **Hari Krishna D K** (`ENG25AD0119`, Section B, AI & DS, Dayananda Sagar University).

## Features
- **Specialist Directory & Search:** Browse doctors by specialization or keyword with consultation fees, experience, and ratings.
- **Real-Time Slot Availability:** Dynamically checks booked slots in SQLite and prevents double-booking (`409 Conflict`).
- **Patient Appointment Management:** Book appointments with instant booking codes (`CQ-XXXX`), filter by phone number, and cancel visits.
- **Clinic Admin Dashboard:** View live appointment metrics, mark visits as Completed or Cancelled, delete records, and add new specialists.

## Tech Stack
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (Fetch API)
- **Backend:** Python 3 (`http.server` / `ThreadingHTTPServer` REST API)
- **Database:** SQLite3 (`clinic.db`)

## Run Locally
```bash
python3 server.py
```
Then open `http://localhost:5000` in your browser (and `http://localhost:5000/admin.html` for the admin dashboard).

## Run Automated Tests
```bash
python3 tests/test_api.py
```

## Deploy to Render (Free Tier)
1. Push this folder to a public GitHub repository.
2. On [Render](https://render.com/), create a **New Web Service** connected to your GitHub repo.
3. Set **Build Command** to `echo "No build dependencies"` and **Start Command** to `python3 server.py`.
