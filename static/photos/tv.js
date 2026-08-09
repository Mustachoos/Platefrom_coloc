(function () {
  const slide = document.getElementById("slide");
  const empty = document.getElementById("empty");
  const INTERVAL_MS = 8000;

  let photos = [];
  let index = 0;

  function showCurrent() {
    if (photos.length === 0) {
      slide.style.opacity = 0;
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    const photo = photos[index % photos.length];
    const preload = new Image();
    preload.onload = () => {
      slide.style.opacity = 0;
      setTimeout(() => {
        slide.src = photo.url;
        requestAnimationFrame(() => {
          slide.style.opacity = 1;
        });
      }, 200);
    };
    preload.src = photo.url;
  }

  function advance() {
    if (photos.length === 0) return;
    index = (index + 1) % photos.length;
    showCurrent();
  }

  function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(protocol + "://" + location.host + "/ws/tv/");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === "uploaded") {
        // Appended at the end to preserve chronological upload order; since
        // nothing before `index` shifts, the currently displayed photo stays put.
        photos.push(data.photo);
        if (photos.length === 1) {
          index = 0;
          showCurrent();
        }
      } else if (data.event === "deleted") {
        const removedIndex = photos.findIndex((p) => p.url === data.url);
        if (removedIndex === -1) return;
        const wasCurrent = removedIndex === index;
        photos.splice(removedIndex, 1);
        if (photos.length === 0) {
          showCurrent();
          return;
        }
        if (removedIndex < index) {
          index -= 1;
        }
        index = index % photos.length;
        if (wasCurrent) showCurrent();
      }
    };
    ws.onclose = () => {
      setTimeout(connectWebSocket, 3000);
    };
  }

  fetch("/api/photos/")
    .then((response) => response.json())
    .then((data) => {
      photos = data;
      showCurrent();
    });

  connectWebSocket();
  setInterval(advance, INTERVAL_MS);
})();
