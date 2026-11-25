import json
import os
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = BASE_DIR
DB_PATH = os.path.join(BASE_DIR, "clinic.db")

TIME_SLOTS = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "02:00 PM", "02:30 PM",
    "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM",
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            qualification TEXT NOT NULL,
            experience_years INTEGER NOT NULL,
            consultation_fee INTEGER NOT NULL,
            available_days TEXT NOT NULL,
            rating REAL DEFAULT 4.8
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT UNIQUE NOT NULL,
            doctor_id INTEGER NOT NULL,
            patient_name TEXT NOT NULL,
            patient_phone TEXT NOT NULL,
            patient_email TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Confirmed',
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
        );
        """
    )
    count = cur.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
    if count == 0:
        doctors_seed = [
            ("Dr. Ananya Sharma", "Cardiology", "MD, DM (Cardiology)", 12, 700, "Mon - Sat", 4.9),
            ("Dr. Vikram Nair", "General Medicine", "MBBS, MD (Internal Med)", 9, 450, "Mon - Sat", 4.8),
            ("Dr. Priya Menon", "Dermatology", "MBBS, MD (Dermatology)", 8, 600, "Tue - Sun", 4.7),
            ("Dr. Rohan Kulkarni", "Orthopedics", "MS (Orthopedics)", 14, 650, "Mon - Fri", 4.9),
            ("Dr. Sneha Iyer", "Pediatrics", "MBBS, MD (Pediatrics)", 10, 500, "Mon - Sat", 4.8),
            ("Dr. Arjun Deshmukh", "ENT", "MBBS, MS (ENT)", 7, 500, "Mon - Sat", 4.6),
        ]
        cur.executemany(
            """
            INSERT INTO doctors (name, specialization, qualification, experience_years, consultation_fee, available_days, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            doctors_seed,
        )
        appt_seed = [
            ("CQ-1001", 1, "Aarav Patel", "9876543210", "aarav.patel@example.com", "2026-11-26", "10:00 AM", "Routine cardiac checkup", "Confirmed", "2026-11-25 10:15:00"),
            ("CQ-1002", 2, "Diya Verma", "9876501234", "diya.verma@example.com", "2026-11-26", "11:00 AM", "Seasonal fever and cough", "Confirmed", "2026-11-25 11:05:00"),
            ("CQ-1003", 3, "Karthik Rao", "9845011223", "karthik.rao@example.com", "2026-11-25", "02:00 PM", "Skin allergy consultation", "Completed", "2026-11-24 16:40:00"),
            ("CQ-1004", 5, "Meera Joshi", "9900112233", "meera.joshi@example.com", "2026-11-27", "09:30 AM", "Child vaccination follow-up", "Confirmed", "2026-11-25 12:30:00"),
        ]
        cur.executemany(
            """
            INSERT INTO appointments (booking_code, doctor_id, patient_name, patient_phone, patient_email, appointment_date, time_slot, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            appt_seed,
        )
    conn.commit()
    conn.close()


class ClinicHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/health":
            return self._send_json({"status": "ok", "service": "CareQueue Clinic API"})

        if path == "/api/doctors":
            spec = qs.get("specialization", [""])[0].strip()
            search = qs.get("q", [""])[0].strip().lower()
            conn = get_db()
            rows = conn.execute("SELECT * FROM doctors ORDER BY id ASC").fetchall()
            conn.close()
            doctors = [dict(r) for r in rows]
            if spec and spec.lower() != "all":
                doctors = [d for d in doctors if d["specialization"].lower() == spec.lower()]
            if search:
                doctors = [
                    d for d in doctors
                    if search in d["name"].lower() or search in d["specialization"].lower()
                ]
            return self._send_json({"doctors": doctors})

        if path == "/api/slots":
            doctor_id = qs.get("doctor_id", [""])[0].strip()
            date_str = qs.get("date", [""])[0].strip()
            if not doctor_id or not date_str:
                return self._send_json({"error": "doctor_id and date are required"}, HTTPStatus.BAD_REQUEST)
            conn = get_db()
            booked_rows = conn.execute(
                """
                SELECT time_slot FROM appointments
                WHERE doctor_id = ? AND appointment_date = ? AND status != 'Cancelled'
                """,
                (doctor_id, date_str),
            ).fetchall()
            conn.close()
            booked = {r["time_slot"] for r in booked_rows}
            slots = [{"time": s, "available": s not in booked} for s in TIME_SLOTS]
            return self._send_json({"doctor_id": int(doctor_id), "date": date_str, "slots": slots})

        if path == "/api/appointments":
            phone = qs.get("phone", [""])[0].strip()
            status = qs.get("status", [""])[0].strip()
            conn = get_db()
            query = """
                SELECT a.*, d.name AS doctor_name, d.specialization, d.consultation_fee
                FROM appointments a
                JOIN doctors d ON a.doctor_id = d.id
                WHERE 1=1
            """
            params = []
            if phone:
                query += " AND a.patient_phone LIKE ?"
                params.append(f"%{phone}%")
            if status and status.lower() != "all":
                query += " AND a.status = ?"
                params.append(status)
            query += " ORDER BY a.appointment_date DESC, a.id DESC"
            rows = conn.execute(query, params).fetchall()
            conn.close()
            return self._send_json({"appointments": [dict(r) for r in rows]})

        if path == "/api/stats":
            conn = get_db()
            total_doctors = conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
            total_appts = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
            confirmed = conn.execute("SELECT COUNT(*) FROM appointments WHERE status='Confirmed'").fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM appointments WHERE status='Completed'").fetchone()[0]
            cancelled = conn.execute("SELECT COUNT(*) FROM appointments WHERE status='Cancelled'").fetchone()[0]
            conn.close()
            return self._send_json({
                "total_doctors": total_doctors,
                "total_appointments": total_appts,
                "confirmed": confirmed,
                "completed": completed,
                "cancelled": cancelled,
            })

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/appointments":
            try:
                data = self._read_json()
            except json.JSONDecodeError:
                return self._send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)

            required = ["doctor_id", "patient_name", "patient_phone", "patient_email", "appointment_date", "time_slot", "reason"]
            missing = [f for f in required if not str(data.get(f, "")).strip()]
            if missing:
                return self._send_json({"error": f"Missing fields: {', '.join(missing)}"}, HTTPStatus.BAD_REQUEST)

            conn = get_db()
            doc = conn.execute("SELECT id, name FROM doctors WHERE id = ?", (data["doctor_id"],)).fetchone()
            if not doc:
                conn.close()
                return self._send_json({"error": "Doctor not found"}, HTTPStatus.NOT_FOUND)

            conflict = conn.execute(
                """
                SELECT id FROM appointments
                WHERE doctor_id = ? AND appointment_date = ? AND time_slot = ? AND status != 'Cancelled'
                """,
                (data["doctor_id"], data["appointment_date"], data["time_slot"]),
            ).fetchone()
            if conflict:
                conn.close()
                return self._send_json({"error": "Selected time slot is already booked"}, HTTPStatus.CONFLICT)

            next_num = conn.execute("SELECT COALESCE(MAX(id), 0) + 1001 FROM appointments").fetchone()[0]
            booking_code = f"CQ-{next_num}"
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO appointments (booking_code, doctor_id, patient_name, patient_phone, patient_email, appointment_date, time_slot, reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?)
                """,
                (
                    booking_code,
                    int(data["doctor_id"]),
                    data["patient_name"].strip(),
                    data["patient_phone"].strip(),
                    data["patient_email"].strip(),
                    data["appointment_date"].strip(),
                    data["time_slot"].strip(),
                    data["reason"].strip(),
                    created_at,
                ),
            )
            appt_id = cur.lastrowid
            conn.commit()
            row = conn.execute(
                """
                SELECT a.*, d.name AS doctor_name, d.specialization, d.consultation_fee
                FROM appointments a JOIN doctors d ON a.doctor_id = d.id
                WHERE a.id = ?
                """,
                (appt_id,),
            ).fetchone()
            conn.close()
            return self._send_json({"message": "Appointment booked", "appointment": dict(row)}, HTTPStatus.CREATED)

        if parsed.path == "/api/doctors":
            try:
                data = self._read_json()
            except json.JSONDecodeError:
                return self._send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)

            required = ["name", "specialization", "qualification", "experience_years", "consultation_fee", "available_days"]
            missing = [f for f in required if not str(data.get(f, "")).strip()]
            if missing:
                return self._send_json({"error": f"Missing fields: {', '.join(missing)}"}, HTTPStatus.BAD_REQUEST)

            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO doctors (name, specialization, qualification, experience_years, consultation_fee, available_days, rating)
                VALUES (?, ?, ?, ?, ?, ?, 4.8)
                """,
                (
                    data["name"].strip(),
                    data["specialization"].strip(),
                    data["qualification"].strip(),
                    int(data["experience_years"]),
                    int(data["consultation_fee"]),
                    data["available_days"].strip(),
                ),
            )
            doc_id = cur.lastrowid
            conn.commit()
            row = conn.execute("SELECT * FROM doctors WHERE id = ?", (doc_id,)).fetchone()
            conn.close()
            return self._send_json({"message": "Doctor added", "doctor": dict(row)}, HTTPStatus.CREATED)

        return self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/appointments/"):
            appt_id = parsed.path.split("/")[-1]
            try:
                data = self._read_json()
            except json.JSONDecodeError:
                return self._send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)

            status = data.get("status", "").strip()
            if status not in ("Confirmed", "Completed", "Cancelled"):
                return self._send_json({"error": "Invalid status"}, HTTPStatus.BAD_REQUEST)

            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appt_id))
            if cur.rowcount == 0:
                conn.close()
                return self._send_json({"error": "Appointment not found"}, HTTPStatus.NOT_FOUND)
            conn.commit()
            row = conn.execute(
                """
                SELECT a.*, d.name AS doctor_name, d.specialization, d.consultation_fee
                FROM appointments a JOIN doctors d ON a.doctor_id = d.id
                WHERE a.id = ?
                """,
                (appt_id,),
            ).fetchone()
            conn.close()
            return self._send_json({"message": "Status updated", "appointment": dict(row)})

        return self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/appointments/"):
            appt_id = parsed.path.split("/")[-1]
            conn = get_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
            deleted = cur.rowcount
            conn.commit()
            conn.close()
            if deleted == 0:
                return self._send_json({"error": "Appointment not found"}, HTTPStatus.NOT_FOUND)
            return self._send_json({"message": "Appointment deleted"})

        return self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)


def run_server(port=None):
    init_db()
    port = port or int(os.environ.get("PORT", 5000))
    server = ThreadingHTTPServer(("0.0.0.0", port), ClinicHandler)
    print(f"CareQueue Clinic server running on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
