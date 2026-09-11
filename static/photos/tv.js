(function () {
  const slide = document.getElementById("slide");
  const empty = document.getElementById("empty");
  const topList = document.getElementById("top-list");
  const newPhotoOverlay = document.getElementById("new-photo-overlay");
  const newPhotoImg = document.getElementById("new-photo-img");
  const newPhotoUsername = document.getElementById("new-photo-username");
  const slideshowWrap = document.getElementById("slideshow-wrap");
  const whiteboardWrap = document.getElementById("whiteboard-wrap");
  const boardSlide = document.getElementById("board-slide");
  const boardEmpty = document.getElementById("board-empty");
  // Tabler "heart-filled" icon, inlined (no cross-file <use> — see photos/templatetags/icons.py for why)
  const HEART_ICON = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:-2px"><path d="M6.979 3.074a6 6 0 0 1 4.988 1.425l.037 .033l.034 -.03a6 6 0 0 1 4.733 -1.44l.246 .036a6 6 0 0 1 3.364 10.008l-.18 .185l-.048 .041l-7.45 7.379a1 1 0 0 1 -1.313 .082l-.094 -.082l-7.493 -7.422a6 6 0 0 1 3.176 -10.215z" /></svg>';
  const DEFAULT_INTERVAL_MS = 5000;
  const NEW_PHOTO_DISPLAY_MS = 3000;

  function applyWhiteboardImage(url) {
    if (!boardSlide || !boardEmpty) return;
    if (url) {
      boardSlide.src = url;
      boardSlide.style.display = "block";
      boardEmpty.style.display = "none";
    } else {
      boardSlide.style.display = "none";
      boardEmpty.style.display = "block";
    }
  }

  function applyTvLayout(layout, whiteboardImageUrl) {
    if (!slideshowWrap || !whiteboardWrap) return;
    if (layout === "whiteboard") {
      slideshowWrap.style.display = "none";
      whiteboardWrap.style.display = "flex";
      applyWhiteboardImage(whiteboardImageUrl);
    } else {
      whiteboardWrap.style.display = "none";
      slideshowWrap.style.display = "flex";
    }
  }

  const wifiQrCard = document.getElementById("wifi-qr-card");

  function applyWifiQr(shown) {
    if (!wifiQrCard) return;
    if (shown) {
      const img = wifiQrCard.querySelector("img");
      if (img && !img.getAttribute("src")) img.src = img.dataset.src;
      wifiQrCard.style.display = "";
    } else {
      wifiQrCard.style.display = "none";
    }
  }

  function applyTvSettings(settings) {
    applyTvLayout(settings.tv_layout, settings.whiteboard_image_url);
    applyBottomRightWidget(settings.tv_bottom_right === "leaderboard");
    applyWifiQr(settings.wifi_qr_shown);
  }

  let photos = [];
  let index = 0;
  let timerId = null;
  let intervalMs = DEFAULT_INTERVAL_MS;
  let overlayTimeoutId = null;
  let overlayAnimateTimeoutId = null;
  const leaderboardEl = document.getElementById("leaderboard");

  function applyBottomRightWidget(showLeaderboard) {
    if (!leaderboardEl) return;
    leaderboardEl.style.display = showLeaderboard ? "" : "none";
    if (showLeaderboard) renderLeaderboard();
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
    newPhotoUsername.textContent = `Nouvelle photo de ${photo.username}`;
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
      } else if (data.event === "hidden") {
        // Same as "deleted": pull the photo out of the live rotation. Its
        // DB row and file are untouched — unhiding re-adds it via a normal
        // "uploaded" event.
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
      } else if (data.event === "whiteboard_updated") {
        applyWhiteboardImage(data.url);
      } else if (data.event === "tv_settings_changed") {
        // Simplest correct thing: refetch settings and reapply every zone,
        // rather than trying to track each field's state incrementally.
        fetch("/api/settings/")
          .then((response) => response.json())
          .then((settingsData) => applyTvSettings(settingsData));
      } else if (data.event === "event_switched") {
        // The active event changed entirely (different photos, settings) —
        // simplest correct thing is a full reload rather than trying to
        // reconcile local state incrementally.
        location.reload();
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
    applyTvSettings(settingsData);
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
          `<div class="media-item"><img class="thumb thumb--sm" src="${p.url}" alt="thumb"><div><div class="media-item__name">${p.username}</div><div class="like like--active">${HEART_ICON} ${p.likes_count}</div></div></div>`
      )
      .join("");
  }

  // (rendering kicked from initial fetch)

  connectWebSocket();
})();
