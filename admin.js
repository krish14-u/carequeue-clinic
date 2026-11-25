async function refreshAdmin() {
  const statsRes = await fetch("/api/stats");
  const stats = await statsRes.json();
  document.getElementById("stat-total").textContent = stats.total_appointments;
  document.getElementById("stat-confirmed").textContent = stats.confirmed;
  document.getElementById("stat-completed").textContent = stats.completed;
  document.getElementById("stat-doctors").textContent = stats.total_doctors;

  const status = document.getElementById("status-filter").value;
  const apptsRes = await fetch(`/api/appointments?status=${encodeURIComponent(status)}`);
  const apptsData = await apptsRes.json();
  const tbody = document.getElementById("admin-appts-tbody");

  tbody.innerHTML = apptsData.appointments
    .map(
      (a) => `
      <tr>
        <td><strong>${a.booking_code}</strong></td>
        <td>${a.patient_name}<br><small style="color:var(--muted);">${a.patient_phone}</small></td>
        <td>${a.doctor_name}<br><small style="color:var(--muted);">${a.specialization}</small></td>
        <td>${a.appointment_date} · ${a.time_slot}</td>
        <td>${a.reason}</td>
        <td><span class="badge badge-${a.status}">${a.status}</span></td>
        <td style="display:flex;gap:6px;">
          ${a.status === "Confirmed" ? `<button class="btn btn-success btn-sm" onclick="updateStatus(${a.id}, 'Completed')">Complete</button>` : ""}
          ${a.status === "Confirmed" ? `<button class="btn btn-danger btn-sm" onclick="updateStatus(${a.id}, 'Cancelled')">Cancel</button>` : ""}
          <button class="btn btn-outline btn-sm" onclick="deleteAppt(${a.id})">Delete</button>
        </td>
      </tr>`
    )
    .join("");
}

async function updateStatus(id, status) {
  await fetch(`/api/appointments/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  refreshAdmin();
}

async function deleteAppt(id) {
  await fetch(`/api/appointments/${id}`, { method: "DELETE" });
  refreshAdmin();
}

document.getElementById("status-filter").addEventListener("change", refreshAdmin);

document.getElementById("add-doctor-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById("doc-name").value,
    specialization: document.getElementById("doc-spec").value,
    qualification: document.getElementById("doc-qual").value,
    experience_years: document.getElementById("doc-exp").value,
    consultation_fee: document.getElementById("doc-fee").value,
    available_days: document.getElementById("doc-days").value,
  };
  const res = await fetch("/api/doctors", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const alertBox = document.getElementById("doc-alert");
  if (res.ok) {
    alertBox.innerHTML = `<div class="alert alert-success">Doctor added to directory!</div>`;
    document.getElementById("add-doctor-form").reset();
    refreshAdmin();
  } else {
    alertBox.innerHTML = `<div class="alert alert-error">Failed to add doctor.</div>`;
  }
});

refreshAdmin();
