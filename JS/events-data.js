(function () {
  const MANIFEST_PATH = "Events/manifest.json";
  const manifestCache = { value: null };
  const eventCache = new Map();
  const ASSET_VERSION = window.RadiantSiteConfig?.assetVersion || "";

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function withAssetVersion(path) {
    const trimmed = String(path || "").trim();
    if (!trimmed || /^https?:\/\//i.test(trimmed) || trimmed.startsWith("data:") || !ASSET_VERSION) {
      return trimmed;
    }
    const separator = trimmed.includes("?") ? "&" : "?";
    return `${trimmed}${separator}v=${encodeURIComponent(ASSET_VERSION)}`;
  }

  async function fetchJson(path) {
    const versionedPath = withAssetVersion(path);
    if (eventCache.has(versionedPath)) {
      return eventCache.get(versionedPath);
    }
    const promise = fetch(versionedPath).then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to load ${versionedPath}: ${response.status}`);
      }
      return response.json();
    });
    eventCache.set(versionedPath, promise);
    return promise;
  }

  async function loadManifest() {
    if (manifestCache.value) {
      return manifestCache.value;
    }
    const versionedManifestPath = withAssetVersion(MANIFEST_PATH);
    const response = await fetch(versionedManifestPath);
    if (!response.ok) {
      throw new Error(`Failed to load ${versionedManifestPath}: ${response.status}`);
    }
    manifestCache.value = await response.json();
    return manifestCache.value;
  }

  async function loadHomeEvents() {
    const manifest = await loadManifest();
    const files = manifest?.homepage || [];
    return Promise.all(files.map((file) => fetchJson(file)));
  }

  function eventHeadline(event) {
    const h = event.headline || event.title;
    return h && String(h).trim() ? String(h).trim() : "Event";
  }

  function renderEventCard(event, index, compact) {
    const headline = eventHeadline(event);
    const summary = event.summary && String(event.summary).trim();
    const summaryHtml = summary
      ? `<p class="home-event-desc">${escapeHtml(summary)}</p>`
      : "";

    const imgSrc = escapeHtml(withAssetVersion(event.imageSrc));
    const alt = escapeHtml(event.imageAlt || headline);
    const sizesMulti =
      "(max-width: 540px) 100vw, (max-width: 900px) 45vw, 280px";
    const sizesSingle =
      "(max-width: 640px) 100vw, (max-width: 1100px) min(94vw, 720px), min(1100px, 92vw)";
    const sizes = compact ? sizesMulti : sizesSingle;
    const fetchPriority = index === 0 ? "fetchpriority=\"high\"" : "";

    return `
      <article class="home-event-card" data-event-slug="${escapeHtml(event.slug || "")}">
        <div class="home-event-media">
          <img
            src="${imgSrc}"
            sizes="${sizes}"
            alt="${alt}"
            width="4080"
            height="3060"
            loading="${index === 0 ? "eager" : "lazy"}"
            decoding="async"
            ${fetchPriority}
          />
        </div>
        <div class="home-event-strip">
          <h3 class="home-event-title">${escapeHtml(headline)}</h3>
          ${summaryHtml}
        </div>
      </article>
    `;
  }

  async function renderHomeEvents() {
    const section = document.getElementById("homeEventsSection");
    const mount = document.getElementById("homeEventsMount");
    if (!section || !mount) return;

    try {
      const events = await loadHomeEvents();
      if (!events.length) {
        section.remove();
        return;
      }
      const compact = events.length > 1;
      mount.classList.toggle("home-events-grid--compact", compact);
      mount.classList.toggle("home-events-grid--single", !compact);
      mount.dataset.eventCount = String(events.length);
      mount.innerHTML = events.map((ev, i) => renderEventCard(ev, i, compact)).join("");
    } catch (error) {
      console.error("Events data rendering failed.", error);
      section.remove();
    }
  }

  window.EventsData = {
    renderPageData: renderHomeEvents,
  };
})();
