(function () {
  const MANIFEST_PATH = "Jobs/manifest.json";
  const manifestCache = { value: null };
  const jobCache = new Map();
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
    if (jobCache.has(versionedPath)) {
      return jobCache.get(versionedPath);
    }
    const promise = fetch(versionedPath).then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to load ${versionedPath}: ${response.status}`);
      }
      return response.json();
    });
    jobCache.set(versionedPath, promise);
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

  async function loadAllJobs() {
    const manifest = await loadManifest();
    const files = manifest?.jobs || [];
    const jobs = await Promise.all(files.map((file) => fetchJson(file)));
    jobs.sort((a, b) => {
      const da = a.posted || "";
      const db = b.posted || "";
      return db.localeCompare(da);
    });
    return jobs;
  }

  function renderJobCard(job) {
    const highlights = Array.isArray(job.highlights) ? job.highlights : [];
    const highlightsHtml = highlights
      .map((line) => `<li>${escapeHtml(line)}</li>`)
      .join("");
    const applyUrl = (job.applyUrl && String(job.applyUrl).trim()) || "#";
    const applyLabel = escapeHtml(job.applyLabel || "Apply");
    const isExternal = /^https?:\/\//i.test(applyUrl);
    const applyExtra = isExternal ? ' target="_blank" rel="noopener"' : "";

    return `
      <article class="job-card" data-slug="${escapeHtml(job.slug || "")}">
        <div class="job-card-main">
          <div class="job-card-head">
            <h2 class="job-title">${escapeHtml(job.title)}</h2>
            <div class="job-meta">
              ${job.location ? `<span class="job-meta-item">${escapeHtml(job.location)}</span>` : ""}
              ${job.unit ? `<span class="job-meta-item">${escapeHtml(job.unit)}</span>` : ""}
              ${job.employmentType ? `<span class="job-meta-item">${escapeHtml(job.employmentType)}</span>` : ""}
            </div>
          </div>
          <p class="job-summary">${escapeHtml(job.summary)}</p>
          ${
            highlightsHtml
              ? `<ul class="job-highlights">${highlightsHtml}</ul>`
              : ""
          }
          ${
            job.closingDisplay
              ? `<p class="job-closing"><strong>Closing:</strong> ${escapeHtml(job.closingDisplay)}</p>`
              : ""
          }
        </div>
        <div class="job-card-cta">
          <a href="${escapeHtml(applyUrl)}" class="btn btn-gold job-apply-btn"${applyExtra}>${applyLabel}</a>
        </div>
      </article>
    `;
  }

  async function mountJobsBoard() {
    const mount = document.getElementById("jobsBoard");
    if (!mount) return;

    try {
      const jobs = await loadAllJobs();
      if (!jobs.length) {
        mount.innerHTML =
          '<p class="jobs-empty">No open positions are listed at this time. Please check back soon.</p>';
        return;
      }
      mount.innerHTML = jobs.map(renderJobCard).join("");
    } catch (err) {
      console.error(err);
      mount.innerHTML =
        '<p class="jobs-error" role="alert">We could not load job listings. Please refresh the page or try again later.</p>';
    }
  }

  document.addEventListener("DOMContentLoaded", mountJobsBoard);
})();
