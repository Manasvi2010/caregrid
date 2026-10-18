const me = parseToken();
if (!me) logout();
if (me.role === "nurse") location.href = "/dashboard.html";

const rowsBox = document.getElementById("rows");
const toastBox = document.getElementById("toast");
let page = 1;
let pages = 1;
let toastTimer = null;

document.getElementById("logoutBtn").addEventListener("click", logout);
document.getElementById("applyBtn").addEventListener("click", () => { page = 1; load(); });
document.getElementById("clearBtn").addEventListener("click", clearFilters);
document.getElementById("prevBtn").addEventListener("click", () => { if (page > 1) { page--; load(); } });
document.getElementById("nextBtn").addEventListener("click", () => { if (page < pages) { page++; load(); } });

if (me.role !== "hospital_admin") {
  document.getElementById("wardField").classList.add("hidden"); // ward admins see their own ward only
}

function toast(message) {
  toastBox.textContent = message;
  toastBox.className = "show error";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastBox.className = ""; }, 3500);
}

function fillSelect(id, items) {
  const select = document.getElementById(id);
  items.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = item.name;
    select.appendChild(opt);
  });
}

function clearFilters() {
  ["fWard", "fUser", "fStatus", "fFrom", "fTo"].forEach(id => { document.getElementById(id).value = ""; });
  page = 1;
  load();
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

async function load() {
  const params = new URLSearchParams({ page: page, page_size: 15 });
  const map = { fWard: "ward_id", fUser: "user_id", fStatus: "new_status", fFrom: "date_from", fTo: "date_to" };
  Object.entries(map).forEach(([id, key]) => {
    const value = document.getElementById(id).value;
    if (value) params.set(key, value);
  });

  try {
    const data = await api("/audit?" + params.toString());
    pages = data.pages;
    rowsBox.innerHTML = "";
    if (!data.items.length) {
      const tr = document.createElement("tr");
      const td = cell("No events match these filters.");
      td.colSpan = 5;
      tr.appendChild(td);
      rowsBox.appendChild(tr);
    }
    data.items.forEach(e => {
      const tr = document.createElement("tr");
      tr.append(
        cell(new Date(e.changed_at).toLocaleString()),
        cell(e.ward),
        cell(e.bed_number),
        cell((e.old_status || "-") + " \u2192 " + e.new_status),
        cell(e.user_name)
      );
      rowsBox.appendChild(tr);
    });
    document.getElementById("count").textContent = data.total + " events";
    document.getElementById("pageInfo").textContent = "Page " + data.page + " of " + data.pages;
    document.getElementById("prevBtn").disabled = data.page <= 1;
    document.getElementById("nextBtn").disabled = data.page >= data.pages;
  } catch (e) {
    toast(e.message);
  }
}

async function init() {
  try {
    const f = await api("/audit/filters");
    fillSelect("fWard", f.wards);
    fillSelect("fUser", f.users);
  } catch (e) {
    toast(e.message);
  }
  load();
}

init();