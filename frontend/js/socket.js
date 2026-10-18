function setLive(on) {
  const el = document.getElementById("live");
  el.textContent = on ? "Live" : "Reconnecting...";
  el.className = "live" + (on ? "" : " off");
}

function connectSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = proto + "://" + location.host + "/ws?token=" + encodeURIComponent(getToken());
  const ws = new WebSocket(url);

  ws.onopen = () => {
    setLive(true);
    loadBeds(); // catch up on anything missed while disconnected
  };

  ws.onmessage = (e) => {
    const bed = JSON.parse(e.data);
    if (String(bed.ward_id) !== wardSelect.value) return; // different ward on screen
    const i = beds.findIndex(b => b.id === bed.id);
    if (i !== -1) beds[i] = bed;
    render();
  };

  ws.onclose = () => {
    setLive(false);
    setTimeout(connectSocket, 2000); // auto-reconnect
  };
}

connectSocket();