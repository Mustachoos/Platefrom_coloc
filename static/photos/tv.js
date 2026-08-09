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
      const photo = JSON.parse(event.data);
      const wasEmpty = photos.length === 0;
      photos.unshift(photo);
      if (wasEmpty) {
        index = 0;
        showCurrent();
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
