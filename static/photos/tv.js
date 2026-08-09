(function () {
  const slide = document.getElementById("slide");
  const empty = document.getElementById("empty");
  const topList = document.getElementById("top-list");
  const newPhotoOverlay = document.getElementById("new-photo-overlay");
  const newPhotoImg = document.getElementById("new-photo-img");
  const newPhotoUsername = document.getElementById("new-photo-username");
  const DEFAULT_INTERVAL_MS = 5000;
  const NEW_PHOTO_DISPLAY_MS = 10000;

  let photos = [];
  let index = 0;
  let timerId = null;
  let intervalMs = DEFAULT_INTERVAL_MS;
  let overlayTimeoutId = null;

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
    timerId = setInterval(advance, intervalMs);
  }

  // Announces a freshly uploaded photo in a floating overlay for a fixed
  // 10s, independent of the slideshow interval. The background rotation
  // (`slide`) keeps running on its own schedule underneath, untouched.
  function announceNewPhoto(photo) {
    if (overlayTimeoutId) clearTimeout(overlayTimeoutId);
    newPhotoUsername.textContent = photo.username;
    newPhotoImg.src = photo.url;
    // show overlay
    newPhotoOverlay.classList.add("visible");
    // subtle zoom of the main slide to draw attention
    slide.classList.add("slide-zoom");
    setTimeout(() => slide.classList.remove("slide-zoom"), 700);
    overlayTimeoutId = setTimeout(() => {
      newPhotoOverlay.classList.remove("visible");
    }, NEW_PHOTO_DISPLAY_MS);
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
        }
        announceNewPhoto(data.photo);
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
      } else if (data.event === "settings") {
        intervalMs = data.interval_seconds * 1000;
        restartTimer();
      } else if (data.event === "liked") {
        // update local photo likes and re-render leaderboard
        const idx = photos.findIndex((p) => p.id === data.photo_id);
        if (idx !== -1) {
          photos[idx].likes_count = data.likes_count;
        }
        renderLeaderboard();
      }
    };
    ws.onclose = () => {
      setTimeout(connectWebSocket, 3000);
    };
  }

  Promise.all([
    fetch("/api/photos/").then((response) => response.json()),
    fetch("/api/settings/").then((response) => response.json()),
  ]).then(([photoData, settingsData]) => {
    photos = photoData;
    intervalMs = settingsData.interval_seconds * 1000;
    showCurrent();
    restartTimer();
    renderLeaderboard();
  });

  function renderLeaderboard() {
    if (!topList) return;
    const top = photos
      .slice()
      .sort((a, b) => b.likes_count - a.likes_count)
      .slice(0, 3);
    topList.innerHTML = top
      .map(
        (p) =>
          `<div class="leaderboard-item"><img class="leaderboard-thumb" src="${p.url}" alt="thumb"><div class="leaderboard-meta"><div class="leaderboard-username">${p.username}</div><div class="leaderboard-count">${p.likes_count} ♥</div></div></div>`
      )
      .join("");
  }

  // (rendering kicked from initial fetch)

  connectWebSocket();
})();
