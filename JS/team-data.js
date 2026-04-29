(function () {
  const MANIFEST_PATH = "People/manifest.json";
  const manifestCache = { value: null };
  const personCache = new Map();
  const RANDOMIZED_SECTIONS = new Set(["faculty", "affiliation", "postdocs", "graduate"]);
  const ASSET_VERSION = window.RadiantSiteConfig?.assetVersion || "";

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function slugify(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/['"]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function getMeaningfulNameParts(fullName) {
    const TITLE_PREFIXES = new Set(["dr", "prof", "professor", "mr", "mrs", "ms", "miss"]);
    const cleaned = String(fullName || "").replace(/\s+/g, " ").trim();
    if (!cleaned) return [];

    const parts = cleaned
      .split(" ")
      .map((part) =>
        part
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .replace(/[^a-zA-Z0-9-]/g, "")
      )
      .filter(Boolean);

    let startIndex = 0;
    while (startIndex < parts.length && TITLE_PREFIXES.has(parts[startIndex].toLowerCase())) {
      startIndex += 1;
    }

    return parts.slice(startIndex);
  }

  function personKeyFromName(fullName) {
    const parts = getMeaningfulNameParts(fullName);
    if (parts.length < 2) return null;

    const firstName = parts[0];
    const lastName = parts[parts.length - 1];
    return `${slugify(firstName)}-${slugify(lastName)}`;
  }

  function legacyPersonKeysFromName(fullName) {
    const cleaned = String(fullName || "").replace(/\s+/g, " ").trim();
    if (!cleaned) return [];

    const parts = cleaned
      .split(" ")
      .map((part) =>
        part
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .replace(/[^a-zA-Z0-9-]/g, "")
      )
      .filter(Boolean);

    if (parts.length < 2) return [];

    const firstPart = parts[0];
    const lastPart = parts[parts.length - 1];
    const legacyKey = `${slugify(firstPart)}-${slugify(lastPart?.[0] || "")}`;
    const modernKey = personKeyFromName(fullName);

    return [legacyKey, modernKey].filter((key, index, allKeys) => key && allKeys.indexOf(key) === index);
  }

  function formatRoleAndType(person) {
    return [person.role, person.type].filter(Boolean).join(" • ");
  }

  function renderFocusMarkup(focusValue) {
    const items = String(focusValue || "")
      .split("•")
      .map((item) => item.trim())
      .filter(Boolean);

    if (items.length <= 1) {
      return `<div class="value">${escapeHtml(focusValue)}</div>`;
    }

    return `
      <ul class="value fact-list">
        ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    `;
  }

  function getProfileAttributes(profileUrl) {
    const href = profileUrl && profileUrl.trim() ? profileUrl.trim() : "#";
    const isExternal = /^https?:\/\//i.test(href);
    return {
      href,
      extra: isExternal ? ' target="_blank" rel="noopener"' : "",
    };
  }

  function hasUsableProfileUrl(profileUrl) {
    return Boolean(profileUrl && profileUrl.trim() && profileUrl.trim() !== "#");
  }

  function renderHomepageInlineMarkup(value) {
    return escapeHtml(value).replace(/\r?\n/g, "<br>");
  }

  function renderHomepageSchoolMarkup(person) {
    const schools = [person.school, person.secondarySchool].filter(Boolean);
    return schools
      .map((school) => `<div class="card-school">${escapeHtml(school)}</div>`)
      .join("");
  }

  function withAssetVersion(path) {
    const trimmed = String(path || "").trim();
    if (!trimmed || /^https?:\/\//i.test(trimmed) || trimmed.startsWith("data:") || !ASSET_VERSION) {
      return trimmed;
    }

    const separator = trimmed.includes("?") ? "&" : "?";
    return `${trimmed}${separator}v=${encodeURIComponent(ASSET_VERSION)}`;
  }

  function getHeadshotVariantPath(imageSrc, variantName) {
    const trimmed = String(imageSrc || "").trim();
    if (!trimmed || /^https?:\/\//i.test(trimmed) || trimmed.startsWith("data:")) {
      return null;
    }

    const pathOnly = trimmed.split("?")[0];
    const lastSlashIndex = pathOnly.lastIndexOf("/");
    const directory = lastSlashIndex >= 0 ? pathOnly.slice(0, lastSlashIndex + 1) : "";
    const filename = lastSlashIndex >= 0 ? pathOnly.slice(lastSlashIndex + 1) : pathOnly;
    const baseName = filename.replace(/\.[^.]+$/, "");

    if (!baseName) {
      return null;
    }

    return `${directory}variants/${variantName}/${baseName}.webp`;
  }

  function getImageStyle(person) {
    const parts = [];

    if (person?.imageFit) {
      parts.push(`object-fit: ${escapeHtml(person.imageFit)}`);
    }

    if (person?.imagePosition) {
      parts.push(`object-position: ${escapeHtml(person.imagePosition)}`);
    }

    return parts.length ? ` style="${parts.join("; ")}"` : "";
  }

  function renderHeadshotPicture({ person, variantName, imageClass, width, height, fallbackSrc }) {
    const imageStyle = getImageStyle(person);
    const variantPath = getHeadshotVariantPath(person.imageSrc, variantName);
    const sourceMarkup = variantPath
      ? `<source type="image/webp" srcset="${escapeHtml(withAssetVersion(variantPath))}">`
      : "";
    const imageClassAttribute = imageClass ? ` class="${escapeHtml(imageClass)}"` : "";

    return `
      <picture class="headshot-picture headshot-picture-${escapeHtml(variantName)}">
        ${sourceMarkup}
        <img
          src="${escapeHtml(withAssetVersion(person.imageSrc))}"
          ${imageClassAttribute}
          alt="${escapeHtml(person.name)} headshot"
          width="${escapeHtml(width)}"
          height="${escapeHtml(height)}"
          loading="lazy"
          decoding="async"
          ${imageStyle}
          onerror="this.src='${escapeHtml(fallbackSrc)}'"
        >
      </picture>
    `;
  }

  async function fetchJson(path) {
    const versionedPath = withAssetVersion(path);

    if (personCache.has(versionedPath)) {
      return personCache.get(versionedPath);
    }

    const promise = fetch(versionedPath).then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to load ${versionedPath}: ${response.status}`);
      }
      return response.json();
    });

    personCache.set(versionedPath, promise);
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

  async function loadSectionPeople(sectionKey) {
    const manifest = await loadManifest();
    const files = manifest?.[sectionKey] || [];
    return Promise.all(files.map((file) => fetchJson(file)));
  }

  function getLastName(value) {
    const cleaned = String(value || "").replace(/\s+/g, " ").trim();
    if (!cleaned) return "";

    const parts = cleaned.split(" ");
    return parts[parts.length - 1].replace(/['"]/g, "").toLowerCase();
  }

  function sortPeopleByLastName(people) {
    return [...people].sort((a, b) => {
      const lastNameCompare = getLastName(a.name).localeCompare(getLastName(b.name));
      if (lastNameCompare !== 0) return lastNameCompare;
      return String(a.name || "").localeCompare(String(b.name || ""));
    });
  }

  function shufflePeople(people) {
    const shuffled = [...people];
    for (let i = shuffled.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }

  const LOW_RES_ENTER_SCALE = 1.08;
  const LOW_RES_EXIT_SCALE = 1.18;
  const TEAM_BIO_MIN_HEIGHT = 120;
  const TEAM_BIO_MOBILE_PREVIEW_LINES = 7;
  let lowResolutionHeadshotResizeTimer = null;
  let teamBioLayoutResizeTimer = null;

  function markLowResolutionHeadshots(options = {}) {
    const { selector = ".profile-image, .person-photo-frame img" } = options;
    const images = document.querySelectorAll(selector);

    images.forEach((img) => {
      const evaluate = () => {
        const renderedWidth = Math.round(img.clientWidth);
        const renderedHeight = Math.round(img.clientHeight);
        const naturalWidth = img.naturalWidth || 0;
        const naturalHeight = img.naturalHeight || 0;

        if (!renderedWidth || !renderedHeight || !naturalWidth || !naturalHeight) {
          return;
        }

        const widthScale = naturalWidth / renderedWidth;
        const heightScale = naturalHeight / renderedHeight;
        const effectiveScale = Math.min(widthScale, heightScale);
        const wasLowRes = img.dataset.lowResState === "true";
        const enterThreshold = img.closest(".person-photo-frame")
          ? LOW_RES_ENTER_SCALE - 0.05
          : LOW_RES_ENTER_SCALE;
        const exitThreshold = img.closest(".person-photo-frame")
          ? LOW_RES_EXIT_SCALE + 0.08
          : LOW_RES_EXIT_SCALE;

        const isLowRes = wasLowRes
          ? effectiveScale < exitThreshold
          : effectiveScale < enterThreshold;

        img.classList.toggle("is-low-res", isLowRes);
        img.dataset.lowResState = String(isLowRes);
      };

      if (img.complete) {
        evaluate();
      } else {
        img.addEventListener("load", evaluate, { once: true });
      }
    });
  }

  function scheduleLowResolutionHeadshotResizeCheck() {
    window.clearTimeout(lowResolutionHeadshotResizeTimer);
    lowResolutionHeadshotResizeTimer = window.setTimeout(() => {
      markLowResolutionHeadshots({ selector: ".profile-image" });
    }, 140);
  }

  function setTeamBioExpanded(card, expanded) {
    const toggle = card.querySelector(".person-bio-toggle");
    const toggleText = toggle?.querySelector(".person-bio-toggle-text");

    card.classList.toggle("bio-expanded", expanded);

    if (toggle) {
      toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
    }

    if (toggleText) {
      toggleText.textContent = expanded ? "Show less" : "Show more";
    }
  }

  function refreshTeamBioLayouts() {
    const cards = document.querySelectorAll(".team-page .person-feature");
    if (!cards.length) {
      return;
    }

    const isDesktop = window.matchMedia("(min-width: 901px)").matches;

    cards.forEach((card) => {
      const photoFrame = card.querySelector(".person-photo-frame");
      const content = card.querySelector(".person-content");
      const bioWrap = card.querySelector(".person-bio-wrap");
      const bio = card.querySelector(".person-bio");
      const toggle = card.querySelector(".person-bio-toggle");

      if (!photoFrame || !content || !bioWrap || !bio || !toggle) {
        return;
      }

      const wasExpanded = card.classList.contains("bio-expanded");

      card.classList.add("bio-measuring");
      bioWrap.style.removeProperty("--collapsed-bio-height");
      toggle.hidden = false;

      const lineHeight = Number.parseFloat(window.getComputedStyle(bio).lineHeight) || 26;
      const mobilePreviewHeight = Math.round(lineHeight * TEAM_BIO_MOBILE_PREVIEW_LINES);
      const wrapExtraHeight = Math.max(0, Math.round(bioWrap.scrollHeight - bio.scrollHeight));
      const contentWithoutBioHeight = Math.max(0, Math.round(content.scrollHeight - bioWrap.scrollHeight));
      const photoHeight = Math.round(photoFrame.getBoundingClientRect().height);
      const desktopCollapsedHeight = Math.max(
        TEAM_BIO_MIN_HEIGHT,
        photoHeight - contentWithoutBioHeight - wrapExtraHeight - 4
      );
      const collapsedHeight = isDesktop ? desktopCollapsedHeight : Math.max(TEAM_BIO_MIN_HEIGHT, mobilePreviewHeight);
      const bioOverflows = bio.scrollHeight > collapsedHeight + 4;

      bioWrap.style.setProperty("--collapsed-bio-height", `${collapsedHeight}px`);
      card.dataset.bioExpandable = bioOverflows ? "true" : "false";
      toggle.hidden = !bioOverflows;
      card.classList.remove("bio-measuring");

      if (bioOverflows) {
        setTeamBioExpanded(card, wasExpanded);
      } else {
        setTeamBioExpanded(card, false);
      }
    });
  }

  function scheduleTeamBioLayoutRefresh() {
    window.clearTimeout(teamBioLayoutResizeTimer);
    teamBioLayoutResizeTimer = window.setTimeout(() => {
      refreshTeamBioLayouts();
    }, 140);
  }

  function initTeamBioToggles() {
    const cards = document.querySelectorAll(".team-page .person-feature");
    if (!cards.length) {
      return;
    }

    cards.forEach((card) => {
      const toggle = card.querySelector(".person-bio-toggle");
      if (!toggle || toggle.dataset.bound === "true") {
        return;
      }

      toggle.dataset.bound = "true";
      toggle.addEventListener("click", () => {
        const expand = !card.classList.contains("bio-expanded");
        setTeamBioExpanded(card, expand);
      });
    });

    document.querySelectorAll(".team-page .person-photo-frame img").forEach((img) => {
      if (img.complete || img.dataset.bioLayoutBound === "true") {
        return;
      }

      img.dataset.bioLayoutBound = "true";
      const refresh = () => scheduleTeamBioLayoutRefresh();
      img.addEventListener("load", refresh, { once: true });
      img.addEventListener("error", refresh, { once: true });
    });

    refreshTeamBioLayouts();
  }

  function normalizeSearchText(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  const TEAM_SECTION_PREVIEW_COUNT = 3;
  const SECTIONS_WITHOUT_COLLAPSE = new Set(["leadership"]);

  function ensureSectionCollapseButtons(sections) {
    sections.forEach((section) => {
      if (SECTIONS_WITHOUT_COLLAPSE.has(section.id)) return;
      if (section.querySelector(".team-section-collapse-footer")) return;
      const stack = section.querySelector(".person-stack");
      if (!stack) return;

      const footer = document.createElement("div");
      footer.className = "team-section-collapse-footer";
      footer.hidden = true;

      const button = document.createElement("button");
      button.type = "button";
      button.className = "team-section-collapse-toggle";
      button.setAttribute("aria-expanded", "false");
      button.innerHTML = `
        <span class="team-section-collapse-text">Show all</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 9l6 6 6-6"></path>
        </svg>
      `;

      button.addEventListener("click", () => {
        const expanded = !section.classList.contains("is-expanded");
        section.classList.toggle("is-expanded", expanded);
        button.setAttribute("aria-expanded", String(expanded));
        applyCollapseState(section);
        scheduleTeamBioLayoutRefresh();
      });

      footer.appendChild(button);
      stack.insertAdjacentElement("afterend", footer);
    });
  }

  function applyCollapseState(section) {
    const button = section.querySelector(".team-section-collapse-toggle");
    const textEl = button?.querySelector(".team-section-collapse-text");
    const visibleCards = Array.from(section.querySelectorAll(".person-feature"))
      .filter((card) => !card.hidden);
    const isCollapsible = section.classList.contains("is-collapsible");
    const isExpanded = section.classList.contains("is-expanded");
    const lastPreviewIndex = TEAM_SECTION_PREVIEW_COUNT - 1;

    visibleCards.forEach((card, index) => {
      const shouldHide = isCollapsible && !isExpanded && index >= TEAM_SECTION_PREVIEW_COUNT;
      const shouldFade = isCollapsible && !isExpanded && index === lastPreviewIndex;
      card.classList.toggle("is-collapse-hidden", shouldHide);
      card.classList.toggle("is-collapse-fade", shouldFade);
    });

    if (button && textEl) {
      const hidden = Math.max(0, visibleCards.length - TEAM_SECTION_PREVIEW_COUNT);
      textEl.textContent = isExpanded
        ? "Show fewer"
        : `Show ${hidden} more`;
    }
  }

  function findPersonCardById(targetId) {
    if (!targetId) return null;

    let target = document.getElementById(targetId);
    if (target && target.classList.contains("person-feature")) {
      return target;
    }

    target = Array.from(document.querySelectorAll(".person-feature[data-person-legacy-keys]"))
      .find((card) => {
        const keys = (card.dataset.personLegacyKeys || "").split("|").filter(Boolean);
        return keys.includes(targetId);
      });

    return target || null;
  }

  function expandSectionForHash(options = {}) {
    const { scroll = true } = options;
    const rawHash = window.location.hash || "";
    if (!rawHash || rawHash.length < 2) return;

    let targetId;
    try {
      targetId = decodeURIComponent(rawHash.slice(1));
    } catch (_err) {
      targetId = rawHash.slice(1);
    }

    const target = findPersonCardById(targetId);
    if (!target) return;

    const section = target.closest(".team-section");
    if (section && section.classList.contains("is-collapsible") && !section.classList.contains("is-expanded")) {
      section.classList.add("is-expanded");
      applyCollapseState(section);
      const button = section.querySelector(".team-section-collapse-toggle");
      if (button) {
        button.setAttribute("aria-expanded", "true");
      }
      scheduleTeamBioLayoutRefresh();
    }

    if (scroll) {
      window.requestAnimationFrame(() => {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  function applySectionCollapse({ activeFilters, sections }) {
    sections.forEach((section) => {
      const visibleCards = Array.from(section.querySelectorAll(".person-feature"))
        .filter((card) => !card.hidden);
      const footer = section.querySelector(".team-section-collapse-footer");
      const collapseAllowed = !SECTIONS_WITHOUT_COLLAPSE.has(section.id);
      const shouldCollapse =
        collapseAllowed && !activeFilters && visibleCards.length > TEAM_SECTION_PREVIEW_COUNT;

      section.classList.toggle("is-collapsible", shouldCollapse);

      if (!shouldCollapse) {
        section.classList.remove("is-expanded");
      }

      if (footer) {
        footer.hidden = !shouldCollapse;
      }

      applyCollapseState(section);
    });
  }

  function initTeamFilters() {
    const searchInput = document.getElementById("teamSearch");
    const sectionFilter = document.getElementById("teamSectionFilter");
    const emptyState = document.getElementById("teamFilterEmpty");
    const sections = Array.from(document.querySelectorAll(".team-section"));

    if (!searchInput || !sectionFilter || !sections.length) {
      return;
    }

    const cards = Array.from(document.querySelectorAll(".person-feature"));
    if (!cards.length) {
      return;
    }

    cards.forEach((card) => {
      const section = card.closest(".team-section");
      const sectionId = section?.id || "";
      card.dataset.section = sectionId;
      card.dataset.searchText = normalizeSearchText(card.textContent);
    });

    ensureSectionCollapseButtons(sections);

    const applyFilters = () => {
      const term = normalizeSearchText(searchInput.value);
      const selectedSection = sectionFilter.value;
      const activeFilters = Boolean(term) || selectedSection !== "all";
      let visibleCards = 0;

      sections.forEach((section) => {
        const sectionCards = Array.from(section.querySelectorAll(".person-feature"));
        let sectionVisible = 0;

        sectionCards.forEach((card) => {
          const matchesSection = selectedSection === "all" || card.dataset.section === selectedSection;
          const matchesTerm = !term || card.dataset.searchText.includes(term);
          const isVisible = matchesSection && matchesTerm;

          card.hidden = !isVisible;
          if (isVisible) {
            sectionVisible += 1;
            visibleCards += 1;
          }
        });

        section.hidden = sectionVisible === 0;
      });

      if (emptyState) {
        emptyState.hidden = visibleCards !== 0;
      }

      applySectionCollapse({ activeFilters, sections });
      scheduleTeamBioLayoutRefresh();
    };

    searchInput.addEventListener("input", applyFilters);
    sectionFilter.addEventListener("change", applyFilters);
    applyFilters();
  }

  function renderHomepageCard(person) {
    const anchorKey = personKeyFromName(person.name);
    const aboutHref = anchorKey ? `Our_Team.html#${anchorKey}` : "Our_Team.html";
    const homepageType = person.homepageType || person.type;

    return `
      <div class="profile-card">
        <div>
          <h3 class="card-title">${escapeHtml(person.name)}</h3>
        </div>
        <div class="image-container">
          ${renderHeadshotPicture({
            person,
            variantName: "card",
            imageClass: "profile-image",
            width: 160,
            height: 200,
            fallbackSrc: "https://via.placeholder.com/150"
          })}
        </div>
        <div class="card-details">
          <div class="card-role">${escapeHtml(person.role)}</div>
          <div class="card-type">${renderHomepageInlineMarkup(homepageType)}</div>
          ${renderHomepageSchoolMarkup(person)}
        </div>
        <div class="action-row">
          <a href="${escapeHtml(aboutHref)}" class="action-btn about-btn">About</a>
        </div>
      </div>
    `;
  }

  function renderTeamProfile(person) {
    const profile = getProfileAttributes(person.profileUrl);
    const anchorKey = personKeyFromName(person.name);
    const legacyKeys = legacyPersonKeysFromName(person.name);
    const bioId = anchorKey ? `${anchorKey}-bio` : `${slugify(person.name)}-bio`;
    const roleAndType = formatRoleAndType(person);
    const quickFactsActionMarkup = hasUsableProfileUrl(person.profileUrl)
      ? `
            <div class="person-actions" aria-label="Profile actions">
              <a class="btn-team primary" href="${escapeHtml(profile.href)}"${profile.extra} aria-label="View full profile for ${escapeHtml(person.name)}">
                View Profile
              </a>
            </div>
        `
      : "";

    return `
      <article
        class="person-feature"
        ${anchorKey ? `id="${escapeHtml(anchorKey)}"` : ""}
        ${anchorKey ? `data-person-key="${escapeHtml(anchorKey)}"` : ""}
        ${legacyKeys.length ? `data-person-legacy-keys="${escapeHtml(legacyKeys.join("|"))}"` : ""}
      >
        <div class="person-feature-inner">
          <div class="person-media">
            <div class="person-photo-frame">
              ${renderHeadshotPicture({
                person,
                variantName: "team",
                imageClass: "",
                width: 280,
                height: 350,
                fallbackSrc: "https://via.placeholder.com/600x750?text=Headshot"
              })}
            </div>

            <div class="person-quickfacts" aria-label="Quick facts">
              <div class="fact">
                <div class="label">Affiliation</div>
                <div class="value">${escapeHtml(person.affiliation)}</div>
              </div>
              <div class="fact">
                <div class="label">Focus</div>
                ${renderFocusMarkup(person.focus)}
              </div>
${quickFactsActionMarkup}
            </div>
          </div>

          <div class="person-content">
            <h3 class="person-name">${escapeHtml(person.name)}</h3>
            <p class="person-title">${escapeHtml(roleAndType)}</p>
            <p class="person-school">${escapeHtml(person.school)}</p>
            <div class="person-bio-wrap">
              <p class="person-bio" id="${escapeHtml(bioId)}">${escapeHtml(person.bio)}</p>
              <button type="button" class="person-bio-toggle" aria-controls="${escapeHtml(bioId)}" aria-expanded="false" hidden>
                <span class="person-bio-toggle-text">Show more</span>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 9l6 6 6-6"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </article>
    `;
  }

  function renderDataLoadError() {
    document.querySelectorAll(".person-stack, .card-wrapper, .card-wrapper-leadership").forEach((container) => {
      if (container.children.length) return;
      container.innerHTML = '<p class="team-data-error">Team information is temporarily unavailable. Please try again shortly.</p>';
    });
  }

  async function renderHomepageTeam() {
    const sections = [
      ["leadership", "leadershipContainer"],
      ["faculty", "facultyContainer"],
      ["affiliation", "affiliationContainer"],
      ["staff", "staffContainer"],
      ["postdocs", "postDocContainer"],
      ["graduate", "gradContainer"],
    ];

    for (const [sectionKey, containerId] of sections) {
      const container = document.getElementById(containerId);
      if (!container) continue;

      let people = await loadSectionPeople(sectionKey);
      if (!people.length) continue;

      if (RANDOMIZED_SECTIONS.has(sectionKey)) {
        people = shufflePeople(people);
      }

      container.innerHTML = people.map(renderHomepageCard).join("");
    }
  }

  async function renderTeamPage() {
    const sections = [
      ["leadership", "leadership"],
      ["faculty", "faculty"],
      ["affiliation", "affiliation"],
      ["staff", "staff"],
      ["postdocs", "postdocs"],
      ["graduate", "graduate"],
    ];

    for (const [sectionKey, sectionId] of sections) {
      const stack = document.querySelector(`#${sectionId} .person-stack`);
      if (!stack) continue;

      let people = await loadSectionPeople(sectionKey);
      if (!people.length) continue;

      if (RANDOMIZED_SECTIONS.has(sectionKey)) {
        people = sortPeopleByLastName(people);
      }

      stack.innerHTML = people.map(renderTeamProfile).join("");
    }
  }

  async function renderPageData() {
    try {
      const tasks = [];

      if (document.getElementById("leadershipContainer")) {
        tasks.push(renderHomepageTeam());
      }

      if (document.querySelector(".team-page")) {
        tasks.push(renderTeamPage());
      }

      await Promise.all(tasks);
      initTeamFilters();
      expandSectionForHash();
      markLowResolutionHeadshots();
      initTeamBioToggles();
      window.addEventListener("resize", scheduleLowResolutionHeadshotResizeCheck);
      window.addEventListener("resize", scheduleTeamBioLayoutRefresh);
      window.addEventListener("hashchange", () => expandSectionForHash());
    } catch (error) {
      console.error("Team data rendering failed.", error);
      renderDataLoadError();
    }
  }

  window.TeamData = {
    legacyPersonKeysFromName,
    personKeyFromName,
    renderPageData,
  };
})();
