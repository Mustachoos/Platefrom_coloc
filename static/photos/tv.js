(function () {
  const slide = document.getElementById("slide");
  const empty = document.getElementById("empty");
  const topList = document.getElementById("top-list");
  const newPhotoOverlay = document.getElementById("new-photo-overlay");
  const newPhotoImg = document.getElementById("new-photo-img");
  const newPhotoUsername = document.getElementById("new-photo-username");
  const DEFAULT_INTERVAL_MS = 5000;
  const NEW_PHOTO_DISPLAY_MS = 3000;

  let photos = [];
  let index = 0;
  let timerId = null;
  let intervalMs = DEFAULT_INTERVAL_MS;
  let overlayTimeoutId = null;
  let overlayAnimateTimeoutId = null;
  const leaderboardEl = document.getElementById("leaderboard");

  function applyLikesEnabled(enabled) {
    if (!leaderboardEl) return;
    leaderboardEl.style.display = enabled ? "" : "none";
    if (enabled) renderLeaderboard();
  }
  // queue for sequential new-photo overlays
  const overlayQueue = [];
  let overlayShowing = false;

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
    // enqueue the photo overlay; it will be shown in order
    overlayQueue.push(photo);
    if (!overlayShowing) showNextOverlay();
  }

  function showNextOverlay() {
    const photo = overlayQueue.shift();
    if (!photo) {
      overlayShowing = false;
      return;
    }
    overlayShowing = true;
    // clear any previous timers
    if (overlayTimeoutId) {
      clearTimeout(overlayTimeoutId);
      overlayTimeoutId = null;
    }
    if (overlayAnimateTimeoutId) {
      clearTimeout(overlayAnimateTimeoutId);
      overlayAnimateTimeoutId = null;
    }
    newPhotoUsername.textContent = `New photo from ${photo.username}`;
    newPhotoImg.src = photo.url;
    // show centered overlay with entrance animation
    newPhotoOverlay.classList.add("visible", "new-photo-animate");
    // remove the animate class after the initial animation so it can replay later
    overlayAnimateTimeoutId = setTimeout(() => {
      newPhotoOverlay.classList.remove("new-photo-animate");
      overlayAnimateTimeoutId = null;
    }, 1200);
    // hide overlay after display time, then show next in queue
    overlayTimeoutId = setTimeout(() => {
      newPhotoOverlay.classList.remove("visible");
      overlayTimeoutId = null;
      overlayShowing = false;
      // small delay to let hide transition finish before showing next
      setTimeout(() => {
        if (overlayQueue.length > 0) showNextOverlay();
      }, 250);
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
      } else if (data.event === "likes_setting") {
        applyLikesEnabled(data.enabled);
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
    applyLikesEnabled(settingsData.likes_enabled);
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
