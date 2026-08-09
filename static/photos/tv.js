(function () {
  const slide = document.getElementById("slide");
  const empty = document.getElementById("empty");
  const INTERVAL_MS = 8000;

  let photos = [];
  let index = 0;
  let timerId = null;

  function displayPhoto(photo) {
    if (!photo) {
      slide.style.opacity = 0;
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
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

  function showCurrent() {
    displayPhoto(photos.length ? photos[index % photos.length] : null);
  }

  function advance() {
    if (photos.length === 0) return;
    index = (index + 1) % photos.length;
    showCurrent();
  }

  function restartTimer() {
    if (timerId) clearInterval(timerId);
    timerId = setInterval(advance, INTERVAL_MS);
  }

  // Shows a freshly uploaded photo right away, without touching `index`, then
  // gives it a full interval before the normal rotation resumes from exactly
  // where it left off.
  function interruptWithUpload(photo) {
    displayPhoto(photo);
    restartTimer();
  }

  function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(protocol + "://" + location.host + "/ws/tv/");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === "uploaded") {
        // Appended at the end to preserve chronological upload order; since
        // nothing before `index` shifts, the currently displayed photo stays put.
        const wasEmpty = photos.length === 0;
        photos.push(data.photo);
        if (wasEmpty) {
          index = 0;
          showCurrent();
          restartTimer();
        } else {
          interruptWithUpload(data.photo);
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
  restartTimer();
})();
