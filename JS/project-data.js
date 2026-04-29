(function () {
  const MANIFEST_PATH = "Projects/manifest.json";
  const manifestCache = { value: null };
  const projectCache = new Map();
  const ASSET_VERSION = window.RadiantSiteConfig?.assetVersion || "";

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function getLinkAttributes(linkUrl) {
    const href = linkUrl && linkUrl.trim() ? linkUrl.trim() : "#";
    const isExternal = /^https?:\/\//i.test(href);

    return {
      href,
      extra: isExternal ? ' target="_blank" rel="noopener"' : "",
    };
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

    if (projectCache.has(versionedPath)) {
      return projectCache.get(versionedPath);
    }

    const promise = fetch(versionedPath).then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to load ${versionedPath}: ${response.status}`);
      }

      return response.json();
    });

    projectCache.set(versionedPath, promise);
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

  async function loadSectionProjects(sectionKey) {
    const manifest = await loadManifest();
    const files = manifest?.[sectionKey] || [];
    return Promise.all(files.map((file) => fetchJson(file)));
  }

  function renderFeaturedSlide(project) {
    const link = getLinkAttributes(project.linkUrl);
    const mobileSource = project.imageSrcMobile && project.imageSrcMobile.trim()
      ? `<source media="(max-width: 680px)" srcset="${escapeHtml(withAssetVersion(project.imageSrcMobile))}">`
      : "";

    return `
      <div class="slide slide-featured">
        <div class="slide-bg-container">
          <picture class="slide-bg-picture">
            ${mobileSource}
            <img
              src="${escapeHtml(withAssetVersion(project.imageSrc))}"
              class="slide-bg-img"
              alt="${escapeHtml(project.imageAlt || project.title)}"
              onerror="this.src='https://via.placeholder.com/1600x900?text=Story+Image'"
            >
          </picture>
          <div class="slide-overlay"></div>
        </div>
        <div class="slide-content">
          <div class="container">
            <div class="hero-copy">
              <h2 class="slide-title">${escapeHtml(project.title)}</h2>
              <p class="slide-desc">${escapeHtml(project.description)}</p>
              <a href="${escapeHtml(link.href)}" class="btn btn-primary"${link.extra}>${escapeHtml(project.buttonLabel || "Read Full Story")}</a>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function renderProjectCard(project) {
    const link = getLinkAttributes(project.linkUrl);

    return `
      <article class="project-card">
        <div class="project-media">
          <span class="project-badge">${escapeHtml(project.badge || "Featured Story")}</span>
          <img
            src="${escapeHtml(withAssetVersion(project.imageSrc))}"
            alt="${escapeHtml(project.imageAlt || project.title)}"
            onerror="this.src='https://via.placeholder.com/1200x800?text=Story+Image'"
          />
        </div>
        <div class="project-content">
          <div class="project-meta">
            <span class="source-pill">${escapeHtml(project.source || "Story")}</span>
            <span>${escapeHtml(project.meta || "")}</span>
          </div>
          <h2 class="project-title">${escapeHtml(project.title)}</h2>
          <p class="project-desc">${escapeHtml(project.description)}</p>
          <div class="project-impact">
            <strong>Radiant impact:</strong> ${escapeHtml(project.impact || "")}
          </div>
          <div class="project-actions">
            <a class="btn btn-primary" href="${escapeHtml(link.href)}"${link.extra}>${escapeHtml(project.buttonLabel || "Read the full story")}</a>
          </div>
        </div>
      </article>
    `;
  }

  function renderProjectLoadError() {
    const heroMount = document.getElementById("featuredSlidesMount");
    if (heroMount) {
      heroMount.remove();
    }

    const pageGrid = document.getElementById("projectPageGrid");
    if (pageGrid && !pageGrid.children.length) {
      pageGrid.innerHTML = '<p class="project-data-error">Project stories are temporarily unavailable. Please try again shortly.</p>';
    }
  }

  async function renderFeaturedSlides() {
    const mount = document.getElementById("featuredSlidesMount");
    if (!mount) return;

    const projects = await loadSectionProjects("featured");
    if (!projects.length) {
      mount.remove();
      return;
    }

    mount.insertAdjacentHTML("beforebegin", projects.map(renderFeaturedSlide).join(""));
    mount.remove();
  }

  async function renderProjectsPage() {
    const grid = document.getElementById("projectPageGrid");
    if (!grid) return;

    const projects = await loadSectionProjects("page");
    if (!projects.length) return;

    grid.innerHTML = projects.map(renderProjectCard).join("");
  }

  async function renderPageData() {
    try {
      await Promise.all([renderFeaturedSlides(), renderProjectsPage()]);
    } catch (error) {
      console.error("Project data rendering failed.", error);
      renderProjectLoadError();
    }
  }

  window.ProjectData = {
    renderPageData,
  };
})();
