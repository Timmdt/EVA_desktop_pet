let lastReportedState = null;

function isVideoPlaying(video) {
  return (
    !video.paused
    && !video.ended
    && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA
    && video.currentTime > 0
  );
}

function getVideoState() {
  return Array.from(document.querySelectorAll("video")).some(isVideoPlaying);
}

function reportVideoState(force = false) {
  const videoPlaying = getVideoState();

  if (!force && videoPlaying === lastReportedState) {
    return;
  }

  lastReportedState = videoPlaying;

  chrome.runtime.sendMessage({
    type: "eva-video-state",
    videoPlaying,
  }).catch(() => {
    // Die Erweiterung wurde möglicherweise gerade neu geladen.
  });
}

for (const eventName of ["play", "playing", "pause", "ended", "emptied"]) {
  document.addEventListener(
    eventName,
    () => reportVideoState(true),
    true,
  );
}

new MutationObserver(() => reportVideoState()).observe(
  document.documentElement,
  {
    childList: true,
    subtree: true,
  },
);

window.addEventListener("pagehide", () => {
  chrome.runtime.sendMessage({
    type: "eva-video-state",
    videoPlaying: false,
  }).catch(() => {});
});

reportVideoState(true);
setInterval(() => reportVideoState(true), 2000);
