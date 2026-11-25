import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server


class ClinicAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(server.DB_PATH):
            os.remove(server.DB_PATH)
        server.init_db()
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 5099), server.ClinicHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.2)
        cls.base = "http://127.0.0.1:5099"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _req(self, path, method="GET", body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(f"{self.base}{path}", data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def test_01_health_check(self):
        status, data = self._req("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")

    def test_02_list_and_filter_doctors(self):
        status, data = self._req("/api/doctors?specialization=Cardiology")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["doctors"]), 1)
        self.assertEqual(data["doctors"][0]["name"], "Dr. Ananya Sharma")

    def test_03_book_appointment_and_prevent_double_booking(self):
        payload = {
            "doctor_id": 2,
            "patient_name": "Hari Krishna D K",
            "patient_phone": "9988776655",
            "patient_email": "hari@example.com",
            "appointment_date": "2026-11-28",
            "time_slot": "10:30 AM",
            "reason": "Annual health checkup",
        }
        status, created = self._req("/api/appointments", method="POST", body=payload)
        self.assertEqual(status, 201)
        self.assertTrue(created["appointment"]["booking_code"].startswith("CQ-"))
        self.__class__.created_id = created["appointment"]["id"]

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._req("/api/appointments", method="POST", body=payload)
        self.assertEqual(ctx.exception.code, 409)

    def test_04_update_appointment_status(self):
        status, updated = self._req(
            f"/api/appointments/{self.__class__.created_id}",
            method="PATCH",
            body={"status": "Completed"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["appointment"]["status"], "Completed")

    def test_05_delete_appointment(self):
        status, deleted = self._req(f"/api/appointments/{self.__class__.created_id}", method="DELETE")
        self.assertEqual(status, 200)
        self.assertEqual(deleted["message"], "Appointment deleted")


if __name__ == "__main__":
    unittest.main(verbosity=2)
