// Plain status changes. Occupying and freeing go through Admit / Discharge.
const ALLOWED = {
  available: ["reserved", "cleaning"],
  reserved: ["available"],
  occupied: [],
  cleaning: ["available"],
};
const LABELS = {
  available: "Available",
  occupied: "Occupied",
  cleaning: "Cleaning",
  reserved: "Reserved",
};

const me = parseToken();
if (!me) logout();

const grid = document.getElementById("grid");
const wardSelect = document.getElementById("wardSelect");
const summary = document.getElementById("summary");
const overlay = document.getElementById("overlay");
const toastBox = document.getElementById("toast");
const optionsBox = document.getElementById("options");
const admitForm = document.getElementById("admitForm");
const transferForm = document.getElementById("transferForm");

let beds = [];
let currentBed = null;
let toastTimer = null;

document.getElementById("who").textContent = "Role: " + me.role.replace("_", " ");
document.getElementById("logoutBtn").addEventListener("click", logout);
document.getElementById("refreshBtn").addEventListener("click", loadBeds);
document.getElementById("cancelBtn").addEventListener("click", closeMenu);
document.getElementById("admitBtn").addEventListener("click", admitPatient);
document.getElementById("transferBtn").addEventListener("click", transferPatient);
wardSelect.addEventListener("change", loadBeds);
overlay.addEventListener("click", e => { if (e.target === overlay) closeMenu(); });

function toast(message, type) {
  toastBox.textContent = message;
  toastBox.className = "show " + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastBox.className = ""; }, 3500);
}

async function loadWards() {
  try {
    let wards = await api("/wards");
    if (me.role !== "hospital_admin") {
      wards = wards.filter(w => w.id === me.ward);
    }
    wardSelect.innerHTML = "";
    wards.forEach(w => {
      const opt = document.createElement("option");
      opt.value = w.id;
      opt.textContent = w.name + " (floor " + w.floor + ")";
      wardSelect.appendChild(opt);
    });
    if (wards.length) await loadBeds();
    else grid.textContent = "No ward assigned to this user.";
  } catch (e) {
    toast(e.message, "error");
  }
}

async function loadBeds() {
  try {
    beds = await api("/wards/" + wardSelect.value + "/beds");
    render();
  } catch (e) {
    toast(e.message, "error");
  }
}

function upsert(bed) {
  if (String(bed.ward_id) !== wardSelect.value) return;
  const i = beds.findIndex(b => b.id === bed.id);
  if (i !== -1) beds[i] = bed;
}

function render() {
  grid.innerHTML = "";
  beds.forEach(bed => {
    const btn = document.createElement("button");
    btn.className = "bed " + bed.status;
    const name = document.createElement("strong");
    name.textContent = bed.bed_number;
    const label = document.createElement("span");
    label.className = "pname";
    label.textContent =
      bed.status === "occupied" && bed.patient_name ? bed.patient_name : LABELS[bed.status];
    btn.append(name, label);
    btn.addEventListener("click", () => openMenu(bed));
    grid.appendChild(btn);
  });
  const occupied = beds.filter(b => b.status === "occupied").length;
  summary.textContent = occupied + " of " + beds.length + " beds occupied";
}

function addOption(text, cls, handler) {
  const b = document.createElement("button");
  b.className = "opt " + cls;
  b.textContent = text;
  b.addEventListener("click", handler);
  optionsBox.appendChild(b);
}

function openMenu(bed) {
  currentBed = bed;
  admitForm.classList.add("hidden");
  transferForm.classList.add("hidden");
  optionsBox.innerHTML = "";
  document.getElementById("modalTitle").textContent = "Bed " + bed.bed_number;

  if (bed.status === "occupied") {
    if (!bed.admission_id) {
      document.getElementById("modalSub").textContent = "Occupied, but no patient record.";
    } else {
      document.getElementById("modalSub").textContent = "Patient: " + bed.patient_name;
      addOption("Transfer patient", "reserved", showTransfer);
      addOption("Discharge patient", "cleaning", dischargePatient);
    }
  } else {
    document.getElementById("modalSub").textContent = "Currently: " + LABELS[bed.status];
    if (bed.status === "available" || bed.status === "reserved") {
      addOption("Admit patient", "occupied", showAdmit);
    }
    ALLOWED[bed.status].forEach(next => {
      addOption("Mark as " + LABELS[next], next, () => changeStatus(next));
    });
  }
  overlay.classList.add("show");
}

function closeMenu() {
  overlay.classList.remove("show");
  currentBed = null;
}

function showAdmit() {
  optionsBox.innerHTML = "";
  document.getElementById("pName").value = "";
  document.getElementById("pAge").value = "";
  document.getElementById("pGender").value = "";
  admitForm.classList.remove("hidden");
  document.getElementById("pName").focus();
}

function showTransfer() {
  optionsBox.innerHTML = "";
  const select = document.getElementById("targetBed");
  select.innerHTML = "";
  beds
    .filter(b => b.id !== currentBed.id && (b.status === "available" || b.status === "reserved"))
    .forEach(b => {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = "Bed " + b.bed_number + " (" + LABELS[b.status] + ")";
      select.appendChild(opt);
    });
  if (!select.options.length) {
    toast("No free beds in this ward to transfer to.", "error");
    closeMenu();
    return;
  }
  transferForm.classList.remove("hidden");
}

async function changeStatus(newStatus) {
  const bed = currentBed;
  closeMenu();
  try {
    const updated = await api("/beds/" + bed.id + "/status", {
      method: "PATCH",
      body: JSON.stringify({ status: newStatus, version: bed.version }),
    });
    upsert(updated);
    render();
    toast("Bed " + updated.bed_number + " is now " + LABELS[updated.status], "success");
  } catch (e) {
    toast(e.message, "error");
    if (e.status === 409) loadBeds();
  }
}

async function admitPatient() {
  const bed = currentBed;
  const name = document.getElementById("pName").value.trim();
  const ageText = document.getElementById("pAge").value;
  if (!name) { toast("Enter the patient name.", "error"); return; }
  const payload = {
    patient_name: name,
    age: ageText === "" ? null : Number(ageText),
    gender: document.getElementById("pGender").value || null,
    bed_id: bed.id,
    version: bed.version,
  };
  closeMenu();
  try {
    const updated = await api("/admissions", { method: "POST", body: JSON.stringify(payload) });
    upsert(updated);
    render();
    toast(name + " admitted to bed " + updated.bed_number, "success");
  } catch (e) {
    toast(e.message, "error");
    if (e.status === 409) loadBeds();
  }
}

async function transferPatient() {
  const bed = currentBed;
  const targetId = Number(document.getElementById("targetBed").value);
  const target = beds.find(b => b.id === targetId);
  closeMenu();
  try {
    const res = await api("/admissions/" + bed.admission_id + "/transfer", {
      method: "POST",
      body: JSON.stringify({ to_bed_id: target.id, to_version: target.version }),
    });
    upsert(res.from);
    upsert(res.to);
    render();
    toast("Moved to bed " + res.to.bed_number + ". Bed " + res.from.bed_number + " is being cleaned.", "success");
  } catch (e) {
    toast(e.message, "error");
    if (e.status === 409 || e.status === 400) loadBeds();
  }
}

async function dischargePatient() {
  const bed = currentBed;
  closeMenu();
  try {
    const updated = await api("/admissions/" + bed.admission_id + "/discharge", {
      method: "POST",
      body: JSON.stringify({ version: bed.version }),
    });
    upsert(updated);
    render();
    toast("Patient discharged. Bed " + updated.bed_number + " is being cleaned.", "success");
  } catch (e) {
    toast(e.message, "error");
    if (e.status === 409) loadBeds();
  }
}

loadWards();