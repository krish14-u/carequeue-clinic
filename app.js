let selectedSlot = "";

async function loadStats() {
  const res = await fetch("/api/stats");
  const data = await res.json();
  document.getElementById("hero-doctors").textContent = data.total_doctors;
  document.getElementById("hero-appts").textContent = data.total_appointments;
}

async function loadDoctors() {
  const q = document.getElementById("search-input").value.trim();
  const spec = document.getElementById("spec-filter").value;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (spec) params.set("specialization", spec);

  const res = await fetch(`/api/doctors?${params.toString()}`);
  const data = await res.json();
  const grid = document.getElementById("doctors-grid");

  if (!data.doctors.length) {
    grid.innerHTML = `<p style="color:var(--muted);">No doctors match your search.</p>`;
    return;
  }

  grid.innerHTML = data.doctors
    .map(
      (d) => `
      <div class="doc-card">
        <div>
          <div class="doc-top">
            <div>
              <span class="doc-spec">${d.specialization}</span>
              <div class="doc-name">${d.name}</div>
              <div class="doc-qual">${d.qualification} &middot; ${d.experience_years} yrs exp</div>
            </div>
            <span class="doc-rating">&#9733; ${d.rating}</span>
          </div>
        </div>
        <div class="doc-meta">
          <div>
            <div>Available: <strong>${d.available_days}</strong></div>
            <div class="doc-fee">&#8377;${d.consultation_fee} consultation</div>
          </div>
          <button class="btn btn-primary btn-sm" onclick='openBookingModal(${JSON.stringify(d)})'>
            Book Slot
          </button>
        </div>
      </div>`
    )
    .join("");
}

async function loadAppointments() {
  const phone = document.getElementById("phone-search").value.trim();
  const params = new URLSearchParams();
  if (phone) params.set("phone", phone);

  const res = await fetch(`/api/appointments?${params.toString()}`);
  const data = await res.json();
  const tbody = document.getElementById("appointments-tbody");

  if (!data.appointments.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--muted);">No appointments found.</td></tr>`;
    return;
  }

  tbody.innerHTML = data.appointments
    .map(
      (a) => `
      <tr>
        <td><strong>${a.booking_code}</strong></td>
        <td>${a.patient_name}<br><small style="color:var(--muted);">${a.patient_phone}</small></td>
        <td>${a.doctor_name}<br><small style="color:var(--muted);">${a.specialization}</small></td>
        <td>${a.appointment_date}<br><small style="color:var(--muted);">${a.time_slot}</small></td>
        <td>${a.reason}</td>
        <td><span class="badge badge-${a.status}">${a.status}</span></td>
        <td>
          ${
            a.status === "Confirmed"
              ? `<button class="btn btn-danger btn-sm" onclick="cancelAppointment(${a.id})">Cancel</button>`
              : `<span style="color:var(--muted);font-size:0.82rem;">—</span>`
          }
        </td>
      </tr>`
    )
    .join("");
}

async function loadSlots() {
  const doctorId = document.getElementById("book-doctor-id").value;
  const dateVal = document.getElementById("appointment-date").value;
  const grid = document.getElementById("slots-grid");
  selectedSlot = "";

  if (!doctorId || !dateVal) {
    grid.innerHTML = "";
    return;
  }

  const res = await fetch(`/api/slots?doctor_id=${doctorId}&date=${dateVal}`);
  const data = await res.json();
  grid.innerHTML = data.slots
    .map(
      (s) => `
      <button type="button" class="slot-btn" ${s.available ? "" : "disabled"}
        onclick="selectSlot(this, '${s.time}')">${s.time}</button>`
    )
    .join("");
}

function selectSlot(btn, time) {
  document.querySelectorAll(".slot-btn").forEach((b) => b.classList.remove("selected"));
  btn.classList.add("selected");
  selectedSlot = time;
}

function openBookingModal(doctor) {
  document.getElementById("book-doctor-id").value = doctor.id;
  document.getElementById("modal-doc-name").textContent = `Book with ${doctor.name}`;
  document.getElementById("modal-doc-spec").textContent = `${doctor.specialization} · ₹${doctor.consultation_fee}`;
  document.getElementById("modal-alert").innerHTML = "";

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById("appointment-date").value = tomorrow.toISOString().split("T")[0];

  document.getElementById("booking-modal").classList.add("open");
  loadSlots();
}

async function cancelAppointment(id) {
  const res = await fetch(`/api/appointments/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "Cancelled" }),
  });
  if (res.ok) {
    loadAppointments();
    loadStats();
  }
}

document.getElementById("close-modal").addEventListener("click", () => {
  document.getElementById("booking-modal").classList.remove("open");
});

document.getElementById("appointment-date").addEventListener("change", loadSlots);
document.getElementById("search-input").addEventListener("input", loadDoctors);
document.getElementById("spec-filter").addEventListener("change", loadDoctors);
document.getElementById("btn-filter-phone").addEventListener("click", loadAppointments);

document.getElementById("booking-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const alertBox = document.getElementById("modal-alert");

  if (!selectedSlot) {
    alertBox.innerHTML = `<div class="alert alert-error">Please select an available time slot.</div>`;
    return;
  }

  const payload = {
    doctor_id: document.getElementById("book-doctor-id").value,
    patient_name: document.getElementById("patient-name").value,
    patient_phone: document.getElementById("patient-phone").value,
    patient_email: document.getElementById("patient-email").value,
    appointment_date: document.getElementById("appointment-date").value,
    time_slot: selectedSlot,
    reason: document.getElementById("visit-reason").value,
  };

  const res = await fetch("/api/appointments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();

  if (!res.ok) {
    alertBox.innerHTML = `<div class="alert alert-error">${data.error || "Booking failed"}</div>`;
    return;
  }

  alertBox.innerHTML = `<div class="alert alert-success">Confirmed! Booking Code: <strong>${data.appointment.booking_code}</strong></div>`;
  document.getElementById("booking-form").reset();
  loadSlots();
  loadAppointments();
  loadStats();
});

loadStats();
loadDoctors();
loadAppointments();
