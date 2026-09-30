const frameStates = new Map();
let lastStateSentToEva = null;

function removeExpiredStates() {
  const oldestAllowed = Date.now() - 5000;

  for (const [key, state] of frameStates) {
    if (state.updatedAt < oldestAllowed) {
      frameStates.delete(key);
    }
  }
}

function isAnyVideoPlaying() {
  removeExpiredStates();

  return Array.from(frameStates.values()).some(
    (state) => state.videoPlaying,
  );
}

async function sendStateToEva(force = false) {
  const videoPlaying = isAnyVideoPlaying();

  if (!force && videoPlaying === lastStateSentToEva) {
    return;
  }

  try {
    await fetch("http://127.0.0.1:8765/media-state", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ video_playing: videoPlaying }),
    });

    lastStateSentToEva = videoPlaying;
  } catch {
    // EVA läuft gerade nicht. Der nächste Statusbericht versucht es erneut.
    lastStateSentToEva = null;
  }
}

chrome.runtime.onMessage.addListener((message, sender) => {
  if (
    message?.type !== "eva-video-state"
    || typeof message.videoPlaying !== "boolean"
    || sender.tab?.id === undefined
  ) {
    return;
  }

  const frameId = sender.frameId ?? 0;
  const key = `${sender.tab.id}:${frameId}`;

  frameStates.set(key, {
    videoPlaying: message.videoPlaying,
    updatedAt: Date.now(),
  });

  sendStateToEva();
});

chrome.tabs.onRemoved.addListener((tabId) => {
  const prefix = `${tabId}:`;

  for (const key of frameStates.keys()) {
    if (key.startsWith(prefix)) {
      frameStates.delete(key);
    }
  }

  sendStateToEva(true);
});

setInterval(() => sendStateToEva(), 2000);
