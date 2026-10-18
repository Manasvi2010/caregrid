const ALLOWED = {
  available: ["occupied", "reserved", "cleaning"],
  reserved: ["occupied", "available"],
  occupied: ["cleaning"],
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

let beds = [];
let currentBed = null;
let toastTimer = null;

document.getElementById("who").textContent = "Role: " + me.role.replace("_", " ");
document.getElementById("logoutBtn").addEventListener("click", logout);
document.getElementById("refreshBtn").addEventListener("click", loadBeds);
document.getElementById("cancelBtn").addEventListener("click", closeMenu);
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
    // Nurses and ward admins only see their own ward
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

function render() {
  grid.innerHTML = "";
  beds.forEach(bed => {
    const btn = document.createElement("button");
    btn.className = "bed " + bed.status;
    const name = document.createElement("strong");
    name.textContent = bed.bed_number;
    const label = document.createElement("span");
    label.textContent = LABELS[bed.status];
    btn.append(name, label);
    btn.addEventListener("click", () => openMenu(bed));
    grid.appendChild(btn);
  });
  const occupied = beds.filter(b => b.status === "occupied").length;
  summary.textContent = occupied + " of " + beds.length + " beds occupied";
}

function openMenu(bed) {
  currentBed = bed;
  document.getElementById("modalTitle").textContent = "Bed " + bed.bed_number;
  document.getElementById("modalSub").textContent = "Currently: " + LABELS[bed.status];
  const options = document.getElementById("options");
  options.innerHTML = "";
  ALLOWED[bed.status].forEach(next => {
    const b = document.createElement("button");
    b.className = "opt " + next;
    b.textContent = "Mark as " + LABELS[next];
    b.addEventListener("click", () => changeStatus(next));
    options.appendChild(b);
  });
  overlay.classList.add("show");
}

function closeMenu() {
  overlay.classList.remove("show");
  currentBed = null;
}

async function changeStatus(newStatus) {
  const bed = currentBed;
  closeMenu();
  try {
    const updated = await api("/beds/" + bed.id + "/status", {
      method: "PATCH",
      body: JSON.stringify({ status: newStatus, version: bed.version }),
    });
    const i = beds.findIndex(b => b.id === updated.id);
    if (i !== -1) beds[i] = updated;
    render();
    toast("Bed " + updated.bed_number + " is now " + LABELS[updated.status], "success");
  } catch (e) {
    toast(e.message, "error");
    if (e.status === 409) loadBeds(); // someone else changed it, so refetch
  }
}

loadWards();