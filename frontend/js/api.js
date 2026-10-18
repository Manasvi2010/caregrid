function getToken() {
  return sessionStorage.getItem("token");
}

function logout() {
  sessionStorage.clear();
  location.href = "/index.html";
}

// Read the role and ward out of the JWT payload
function parseToken() {
  try {
    const part = getToken().split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(part));
  } catch (e) {
    return null;
  }
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;

  const res = await fetch(path, { ...options, headers });

  let data = null;
  try { data = await res.json(); } catch (e) {}

  if (res.status === 401 && !path.startsWith("/auth/")) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }
  if (!res.ok) {
    const err = new Error((data && data.detail) || "Request failed");
    err.status = res.status;
    throw err;
  }
  return data;
}