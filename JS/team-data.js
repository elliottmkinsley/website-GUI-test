(function () {
  const MANIFEST_PATH = "People/manifest.json";
  const manifestCache = { value: null };
  const personCache = new Map();
  const RANDOMIZED_SECTIONS = new Set(["faculty", "postdocs", "graduate"]);

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

  async function fetchJson(path) {
    if (personCache.has(path)) {
      return personCache.get(path);
    }

    const promise = fetch(path).then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to load ${path}: ${response.status}`);
      }
      return response.json();
    });

    personCache.set(path, promise);
    return promise;
  }

  async function loadManifest() {
    if (manifestCache.value) {
      return manifestCache.value;
    }

    const response = await fetch(MANIFEST_PATH);
    if (!response.ok) {
      throw new Error(`Failed to load ${MANIFEST_PATH}: ${response.status}`);
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
  let lowResolutionHeadshotResizeTimer = null;

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

  function normalizeSearchText(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
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

    const applyFilters = () => {
      const term = normalizeSearchText(searchInput.value);
      const selectedSection = sectionFilter.value;
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
    };

    searchInput.addEventListener("input", applyFilters);
    sectionFilter.addEventListener("change", applyFilters);
    applyFilters();
  }

  function renderHomepageCard(person) {
    const anchorKey = personKeyFromName(person.name);
    const aboutHref = anchorKey ? `Our_Team.html#${anchorKey}` : "Our_Team.html";
    const imageStyle = getImageStyle(person);
    const homepageType = person.homepageType || person.type;

    return `
      <div class="profile-card">
        <div>
          <h3 class="card-title">${escapeHtml(person.name)}</h3>
        </div>
        <div class="image-container">
          <img
            src="${escapeHtml(person.imageSrc)}"
            class="profile-image"
            alt="${escapeHtml(person.name)} headshot"
            ${imageStyle}
            onerror="this.src='https://via.placeholder.com/150'"
          >
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
    const roleAndType = formatRoleAndType(person);
    const imageStyle = getImageStyle(person);
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
              <img
                src="${escapeHtml(person.imageSrc)}"
                alt="${escapeHtml(person.name)} headshot"
                ${imageStyle}
                onerror="this.src='https://via.placeholder.com/600x750?text=Headshot'"
              />
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
            <p class="person-bio">${escapeHtml(person.bio)}</p>
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
      markLowResolutionHeadshots();
      window.addEventListener("resize", scheduleLowResolutionHeadshotResizeCheck);
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
