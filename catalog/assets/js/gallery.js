(function () {
  "use strict";

  const data = window.CATALOG_DATA;
  if (!data || !Array.isArray(data.photos) || data.photos.length === 0) return;

  const photos = data.photos;
  const root = window.CATALOG_ROOT || "";
  const photoIndex = new Map(photos.map((photo, index) => [String(photo.id), index]));
  const lightbox = document.getElementById("lightbox");
  const image = document.getElementById("lightboxImage");
  const panel = document.getElementById("lightboxPanel");
  const counter = document.getElementById("lightboxCounter");
  const closeButton = lightbox ? lightbox.querySelector(".lightbox__close") : null;

  let currentIndex = -1;
  let lastFocused = null;

  const escapeHtml = (value) =>
    String(value == null ? "" : value).replace(/[&<>"']/g, (character) => {
      switch (character) {
        case "&": return "&amp;";
        case "<": return "&lt;";
        case ">": return "&gt;";
        case '"': return "&quot;";
        case "'": return "&#039;";
        default: return character;
      }
    });

  const num = (value) => {
    const number = Number(value) || 0;
    return number.toLocaleString("ru-RU").replace(/\u00a0/g, " ");
  };

  const plural = (value, one, few, many) => {
    const number = Math.abs(Number(value) || 0) % 100;
    if (number >= 11 && number <= 19) return many;
    const last = number % 10;
    if (last === 1) return one;
    if (last >= 2 && last <= 4) return few;
    return many;
  };

  const url = (path) => (path ? root + path : "");

  const fullImage = (photo) =>
    url(photo.image.full_url) || photo.image.full || photo.image.source || "";

  const thumbImage = (photo) =>
    url(photo.image.thumb_url) || photo.image.thumb || "";

  const flag = (author) => {
    if (!author.flag) return "";
    return `<img class="flag" src="${url(author.flag)}" alt="" loading="lazy">`;
  };

  const avatar = (author) => {
    const source = url(author.avatar_url) || author.avatar || "";
    if (source) {
      return `<img class="avatar" src="${escapeHtml(source)}" alt="${escapeHtml(author.name)}" loading="lazy">`;
    }
    const initial = escapeHtml((author.name || "?").slice(0, 1).toUpperCase());
    return `<span class="avatar avatar-fallback" aria-hidden="true">${initial}</span>`;
  };

  const awardChips = (photo) => {
    const honours = (photo.honours || []).filter((item) => item && item.label);
    if (honours.length === 0) return "";
    return honours
      .map((item) => {
        const className =
          item.tier === "win"
            ? "lb-chip lb-chip--win"
            : item.tier === "best"
              ? "lb-chip lb-chip--best"
              : "lb-chip";
        const label = escapeHtml(item.label);
        const contest = item.contest
          ? ` <span class="lb-chip__contest">${escapeHtml(item.contest)}${
              item.year ? ` · ${escapeHtml(String(item.year))}` : ""
            }</span>`
          : "";
        if (item.contest_key) {
          const target = `${root}index.html?contest=${encodeURIComponent(
            item.contest_key
          )}&award=${encodeURIComponent(item.tier || "")}#catalog`;
          return `<a class="${className}" href="${target}" title="Показать работы с этой наградой в этом конкурсе">${label}${contest}</a>`;
        }
        return `<span class="${className}">${label}${contest}</span>`;
      })
      .join("");
  };

  const badgeImages = (photo) => {
    const badges = photo.badge_urls || photo.badge_images || [];
    if (!Array.isArray(badges) || badges.length === 0) return "";
    return badges
      .map(
        (source) =>
          `<img class="lb-badge" src="${escapeHtml(url(source))}" alt="100 best photos of the year" loading="lazy">`
      )
      .join("");
  };

  const metrics = (photo) => `
    <div class="lb-metrics">
      <div class="lb-metric"><b>${num(photo.metrics.views)}</b><span>просмотры</span></div>
      <div class="lb-metric"><b>${num(photo.metrics.likes)}</b><span>лайки</span></div>
      <div class="lb-metric"><b>${num(photo.metrics.favorites)}</b><span>в избранном</span></div>
    </div>
  `;

  const authorFacts = (author) => {
    const facts = [];
    if (author.rank_in_nomination) {
      facts.push(`<div class="lb-fact"><b>#${num(author.rank_in_nomination)}</b>Great photographers</div>`);
    }
    if (author.followers != null) {
      facts.push(`<div class="lb-fact"><b>${num(author.followers)}</b>подписчиков</div>`);
    }
    if (author.photos_count) {
      facts.push(`<div class="lb-fact"><b>${num(author.photos_count)}</b>работ на 35AWARDS</div>`);
    }
    if (author.following) {
      facts.push(`<div class="lb-fact"><b>${num(author.following)}</b>подписок</div>`);
    }
    return facts.length ? `<div class="lb-facts">${facts.join("")}</div>` : "";
  };

  const analysisBlock = (photo) => {
    const analysis = photo.analysis;
    if (!analysis) return "";

    const rows = [];
    if (analysis.light) {
      rows.push({
        label: "Свет",
        main: analysis.light.scheme,
        details: [analysis.light.direction, analysis.light.ratio, analysis.light.notes]
          .filter(Boolean)
          .join(" · "),
      });
    }
    if (analysis.color) {
      rows.push({
        label: "Цвет",
        main: analysis.color.palette,
        details: [analysis.color.temperature, analysis.color.contrast, analysis.color.notes]
          .filter(Boolean)
          .join(" · "),
      });
    }
    if (analysis.lens) {
      rows.push({
        label: "Объектив / фокусное",
        main: [analysis.lens.estimate, analysis.lens.aperture].filter(Boolean).join(" · "),
        details: [analysis.lens.perspective, analysis.lens.notes].filter(Boolean).join(" · "),
      });
    }
    if (analysis.background) {
      rows.push({ label: "Фон", main: analysis.background, details: "" });
    }
    const recipe = analysis.recipe || {};
    const camera = recipe.camera || {};
    if (camera && Object.keys(camera).length) {
      rows.push({
        label: "Камера и настройки",
        main: [camera.mode && `режим ${camera.mode}`, camera.lens, camera.aperture, camera.shutter, camera.iso && `ISO ${camera.iso}`, camera.wb]
          .filter(Boolean)
          .join(" · "),
        details: camera.notes || "",
      });
    }

    const lighting = Array.isArray(recipe.lighting) && recipe.lighting.length
      ? `<div class="lb-analysis__notes">
           <h4>Схема света</h4>
           <ul>${recipe.lighting
             .map(
               (item) =>
                 `<li><b>${escapeHtml(item.role || "свет")}</b>: ${escapeHtml(
                   [item.modifier, item.position, item.power, item.distance, item.notes]
                     .filter(Boolean)
                     .join(" · ")
                 )}</li>`
             )
             .join("")}</ul>
         </div>`
      : "";

    const confidence = recipe.confidence && Object.keys(recipe.confidence).length
      ? `<p class="lb-analysis__confidence">Уверенность: ${Object.entries(recipe.confidence)
          .map(([key, value]) => `${escapeHtml(key)} ${Math.round(Number(value) * 100)}%`)
          .join(" · ")}</p>`
      : "";

    const alternatives = Array.isArray(recipe.alternatives) && recipe.alternatives.length
      ? `<div class="lb-analysis__notes">
           <h4>Равноценные варианты</h4>
           <ul>${recipe.alternatives.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
         </div>`
      : "";

    const protocol = Array.isArray(recipe.test_protocol) && recipe.test_protocol.length
      ? `<div class="lb-analysis__notes">
           <h4>Как повторить</h4>
           <ol>${recipe.test_protocol.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
         </div>`
      : "";

    const notes = Array.isArray(analysis.nuances) && analysis.nuances.length
      ? `<div class="lb-analysis__notes">
           <h4>Нюансы</h4>
           <ul>${analysis.nuances.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
         </div>`
      : "";

    return `
      <div class="lb-section lb-analysis">
        <h4>Разбор фотографа</h4>
        <p class="lb-analysis__summary">${escapeHtml(analysis.summary)}</p>
        <div class="lb-analysis__grid">
          ${rows
            .map(
              (row) => `<div class="lb-analysis__item">
                <span class="lb-analysis__label">${escapeHtml(row.label)}</span>
                <p>${escapeHtml(row.main)}</p>
                ${row.details ? `<small>${escapeHtml(row.details)}</small>` : ""}
              </div>`
            )
            .join("")}
        </div>
        ${confidence}
        ${lighting}
        ${notes}
        ${alternatives}
        ${protocol}
      </div>
    `;
  };

  const tags = (author) => {
    if (!Array.isArray(author.genres) || author.genres.length === 0) return "";
    return `
      <div class="lb-section">
        <h4>Жанры</h4>
        <div class="lb-tags">${author.genres
          .map((genre) => `<span class="lb-tag">${escapeHtml(genre)}</span>`)
          .join("")}</div>
      </div>
    `;
  };

  const gear = (author) => {
    if (!Array.isArray(author.gear) || author.gear.length === 0) return "";
    const items = author.gear.slice(0, 4);
    return `
      <div class="lb-section">
        <h4>Техника автора</h4>
        <div class="lb-gear">${items
          .map(
            (item) => `<div class="lb-gear__item"><span>${escapeHtml(item.name)}</span><span>${num(
              item.count
            )}</span></div>`
          )
          .join("")}</div>
      </div>
    `;
  };

  const membershipBlock = (photo) => {
    const memberships = (photo.memberships || []).filter(
      (item) => item && (item.type === "nomination" || item.type === "theme")
    );
    if (memberships.length === 0) return "";
    const items = memberships.map((item) => {
      const key =
        item.contest_key ||
        `${item.type}:${item.type === "nomination" ? item.under_id : item.contest_id}`;
      const target = `${root}index.html?contest=${encodeURIComponent(
        key
      )}${item.tier ? `&award=${encodeURIComponent(item.tier)}` : ""}#catalog`;
      const title = item.title || item.under_title || item.name || key;
      const year = item.year ? ` · ${item.year}` : "";
      return `<a class="lb-member" href="${target}"><span class="lb-member__name">${escapeHtml(
        title
      )}${escapeHtml(year)}</span><span class="lb-member__badge">${escapeHtml(item.badge || "")}</span></a>`;
    });
    return `
      <div class="lb-section">
        <h4>Участие в конкурсах</h4>
        <div class="lb-memberships">${items.join("")}</div>
        <p class="lb-source">Нажмите на конкурс, чтобы отфильтровать каталог по этому контексту.</p>
      </div>
    `;
  };

  const links = (photo) => {
    const items = [];
    if (photo.author.profile_url) {
      items.push(
        `<a class="lb-link" href="${escapeHtml(photo.author.profile_url)}" target="_blank" rel="noopener"><span>Профиль на 35AWARDS</span><span>↗</span></a>`
      );
    }
    if (photo.author.external_profile) {
      items.push(
        `<a class="lb-link" href="${escapeHtml(photo.author.external_profile)}" target="_blank" rel="noopener"><span>Профиль на 35photo.pro</span><span>↗</span></a>`
      );
    }
    if (photo.page_url) {
      items.push(
        `<a class="lb-link" href="${escapeHtml(photo.page_url)}" target="_blank" rel="noopener"><span>Работа в результатах конкурса</span><span>↗</span></a>`
      );
    }
    return items.length ? `<div class="lb-section"><h4>Ссылки</h4><div class="lb-links">${items.join("")}</div></div>` : "";
  };

  const contextKicker = (photo) => {
    const nomination = photo.nomination || data.nomination || {};
    const edition = photo.edition || data.edition || {};
    return [nomination.name, edition.title].filter(Boolean).join(" · ");
  };

  const renderPanel = (photo) => {
    const author = photo.author;
    const title = photo.title || "Без названия";
    const description = photo.description
      ? `<p class="lb-desc">${escapeHtml(photo.description)}</p>`
      : "";
    const location = [author.city, author.country].filter(Boolean).join(", ");
    const rank = `#${String(photo.rank).padStart(2, "0")}`;

    panel.innerHTML = `
      <div class="lb-kicker">${escapeHtml(contextKicker(photo))}</div>
      <span class="lb-rank">${rank} / ${photos.length}</span>
      <h2 class="lb-title">${escapeHtml(title)}</h2>
      ${description}
      <div class="lb-chips">${awardChips(photo)}</div>
      ${badgeImages(photo)}
      <div class="lb-author">
        ${avatar(author)}
        <div>
          <div class="lb-author__name">${escapeHtml(author.name)}</div>
          <div class="lb-author__meta">${flag(author)}${escapeHtml(location)}</div>
        </div>
      </div>
      <div class="lb-section">
        <h4>Метрики работы</h4>
        ${metrics(photo)}
      </div>
      ${authorFacts(author) ? `<div class="lb-section"><h4>Автор</h4>${authorFacts(author)}</div>` : ""}
      ${membershipBlock(photo)}
      ${analysisBlock(photo)}
      ${tags(author)}
      ${gear(author)}
      ${links(photo)}
      <div class="lb-source">
        Источник: <a href="${escapeHtml(photo.source_url)}" target="_blank" rel="noopener">35awards.com</a>.
        Фотография принадлежит автору. Технические параметры съёмки указаны приблизительно.
      </div>
    `;
  };

  const setHash = (photo) => {
    try {
      history.replaceState(null, "", "#photo_" + photo.id);
    } catch (error) {
      /* file:// pages can reject history updates in some browsers */
    }
  };

  const clearHash = () => {
    try {
      history.replaceState(null, "", location.pathname + location.search);
    } catch (error) {
      /* ignore */
    }
  };

  const open = (index, options) => {
    if (index < 0 || index >= photos.length || !lightbox) return;
    currentIndex = index;
    const photo = photos[index];
    lastFocused = document.activeElement;

    image.src = fullImage(photo);
    image.alt = [photo.title, photo.author.name].filter(Boolean).join(" — ");
    counter.textContent = `${index + 1} / ${photos.length}`;
    renderPanel(photo);

    lightbox.hidden = false;
    document.body.classList.add("is-locked");
    if (!options || options.hash !== false) setHash(photo);
    if (closeButton) closeButton.focus({ preventScroll: true });
  };

  const close = () => {
    if (!lightbox || lightbox.hidden) return;
    lightbox.hidden = true;
    document.body.classList.remove("is-locked");
    currentIndex = -1;
    image.removeAttribute("src");
    clearHash();
    if (lastFocused && typeof lastFocused.focus === "function") {
      lastFocused.focus({ preventScroll: true });
    }
  };

  const step = (delta) => {
    if (currentIndex < 0) return;
    const sourceCards = matchingCards.length
      ? matchingCards
      : Array.from(document.querySelectorAll(".photo-card"));
    const ids = sourceCards.map((card) => Number(card.getAttribute("data-photo-id")));
    const currentId = Number(photos[currentIndex].id);
    const position = ids.indexOf(currentId);
    if (position < 0) {
      open((currentIndex + delta + photos.length) % photos.length);
      return;
    }
    const nextId = ids[(position + delta + ids.length) % ids.length];
    const nextIndex = photos.findIndex((photo) => Number(photo.id) === nextId);
    if (nextIndex >= 0) open(nextIndex);
  };

  document.querySelectorAll("[data-open-photo]").forEach((link) => {
    link.addEventListener("click", (event) => {
      const id = String(link.getAttribute("data-open-photo"));
      const index = photoIndex.get(id);
      if (index === undefined) return;
      event.preventDefault();
      open(index);
    });
  });

  if (lightbox) {
    lightbox.querySelectorAll("[data-close-lightbox]").forEach((element) => {
      element.addEventListener("click", close);
    });
    lightbox.querySelector("[data-prev-photo]").addEventListener("click", () => step(-1));
    lightbox.querySelector("[data-next-photo]").addEventListener("click", () => step(1));
  }

  document.addEventListener("keydown", (event) => {
    if (!lightbox || lightbox.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      step(-1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      step(1);
    }
  });

  /* --------------------------------------------------------------- filtering */
  const filterButtons = Array.from(document.querySelectorAll("button[data-filter-group]"));
  const cards = Array.from(document.querySelectorAll(".photo-card[data-photo-id]"));
  const emptyState = document.getElementById("emptyState");
  const filterCount = document.getElementById("filterCount");
  const resetButton = document.getElementById("resetFilters");
  const contestContext = document.getElementById("contestContext");
  const contextSelect = document.getElementById("contextSelect");
  const loadMoreButton = document.getElementById("loadMore");
  const PAGE_SIZE = 48;
  let visibleLimit = PAGE_SIZE;
  let matchingCards = [];
  const contestLabels = data.contest_labels || {};
  const state = {};
  const buttonGroups = new Set(
    filterButtons.map((button) => button.getAttribute("data-filter-group")).filter(Boolean)
  );
  const groups = new Set([...buttonGroups, "contest"]);

  const contextKeysForOption = (option) => {
    if (!option) return [];
    const raw = option.getAttribute("data-keys");
    if (raw) {
      return raw
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
    }
    return option.value && option.value !== "all" ? [option.value] : [];
  };

  const sameKeySet = (left, right) => {
    if (left.length !== right.length) return false;
    const values = new Set(right);
    return left.every((value) => values.has(value));
  };

  const buttonsInGroup = (group) =>
    filterButtons.filter((button) => button.getAttribute("data-filter-group") === group);

  const matchesValue = (photo, group, value) => {
    if (value === "all") return true;
    const facets = photo.facets || {};
    const values = facets[group];
    return Array.isArray(values) && values.includes(value);
  };

  const photoMatches = (photo) =>
    Object.entries(state).every(([group, values]) => {
      if (!values || values.length === 0) return true;
      return values.some((value) => matchesValue(photo, group, value));
    });

  const updateButtonStates = () => {
    buttonGroups.forEach((group) => {
      const selected = state[group] || [];
      buttonsInGroup(group).forEach((button) => {
        const value = button.getAttribute("data-filter-value");
        button.classList.toggle(
          "is-active",
          value === "all" ? selected.length === 0 : selected.includes(value)
        );
      });
    });
  };

  const updateUrl = () => {
    try {
      const params = new URLSearchParams(location.search);
      groups.forEach((group) => {
        const values = state[group] || [];
        if (values.length) params.set(group, values.join(","));
        else params.delete(group);
      });
      const query = params.toString();
      const next = location.pathname + (query ? "?" + query : "") + location.hash;
      history.replaceState(null, "", next);
    } catch (error) {
      /* ignore file:// restrictions */
    }
  };

  const renderContestContext = () => {
    if (!contestContext) return;
    const selected = state.contest || [];
    let matchedGroup = null;
    if (contextSelect) {
      const options = Array.from(contextSelect.options);
      let option = null;
      if (selected.length === 1) {
        option = options.find((item) => item.value === selected[0]) || null;
      }
      if (!option && selected.length > 0) {
        option =
          options.find(
            (item) =>
              item.value.startsWith("group:") &&
              sameKeySet(contextKeysForOption(item), selected)
          ) || null;
        if (option) matchedGroup = option;
      }
      contextSelect.value = option ? option.value : "all";
    }
    if (selected.length === 0) {
      contestContext.hidden = true;
      contestContext.innerHTML = "";
      return;
    }
    contestContext.hidden = false;
    const groupLabel = matchedGroup ? matchedGroup.getAttribute("data-label") : "";
    if (groupLabel) {
      contestContext.innerHTML =
        '<span class="filter-context__label">Контекст:</span>' +
        `<span class="filter-context__item">${escapeHtml(
          groupLabel
        )}<button type="button" data-clear-contest-group="1" aria-label="Убрать контекст">×</button></span>`;
    } else {
      contestContext.innerHTML =
        '<span class="filter-context__label">Контекст:</span>' +
        selected
          .map(
            (key) =>
              `<span class="filter-context__item">${escapeHtml(
                contestLabels[key] || key
              )}<button type="button" data-clear-contest="${escapeHtml(
                key
              )}" aria-label="Убрать контекст">×</button></span>`
          )
          .join("");
    }
    contestContext.querySelectorAll("[data-clear-contest]").forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.getAttribute("data-clear-contest");
        state.contest = (state.contest || []).filter((value) => value !== key);
        applyFilters();
      });
    });
    const groupClear = contestContext.querySelector("[data-clear-contest-group]");
    if (groupClear) {
      groupClear.addEventListener("click", () => {
        state.contest = [];
        applyFilters();
      });
    }
  };

  const renderVisibility = () => {
    cards.forEach((card) => {
      const position = matchingCards.indexOf(card);
      card.hidden = position < 0 || position >= visibleLimit;
    });
    if (loadMoreButton) {
      const remaining = Math.max(0, matchingCards.length - visibleLimit);
      loadMoreButton.hidden = remaining === 0;
      loadMoreButton.textContent = `Показать ещё ${Math.min(PAGE_SIZE, remaining)}`;
    }
  };

  if (loadMoreButton) {
    loadMoreButton.addEventListener("click", () => {
      visibleLimit += PAGE_SIZE;
      renderVisibility();
    });
  }

  if (contextSelect) {
    contextSelect.addEventListener("change", () => {
      const option = contextSelect.selectedOptions[0];
      state.contest = contextKeysForOption(option);
      applyFilters();
    });
  }

  const applyFilters = (resetPage = true) => {
    if (resetPage) visibleLimit = PAGE_SIZE;
    matchingCards = [];
    cards.forEach((card) => {
      const index = photoIndex.get(String(card.getAttribute("data-photo-id")));
      if (index === undefined) return;
      if (photoMatches(photos[index])) matchingCards.push(card);
    });
    renderVisibility();
    if (emptyState) emptyState.hidden = matchingCards.length !== 0;
    if (filterCount) {
      filterCount.textContent = `${matchingCards.length} ${plural(
        matchingCards.length,
        "работа",
        "работы",
        "работ"
      )}`;
    }
    updateButtonStates();
    renderContestContext();
    updateUrl();
  };

  const setGroup = (group, values) => {
    state[group] = Array.from(new Set(values));
  };

  const toggleValue = (group, value) => {
    const current = state[group] || [];
    if (value === "all") {
      state[group] = [];
      return;
    }
    if (current.includes(value)) {
      state[group] = current.filter((item) => item !== value);
    } else {
      state[group] = current.concat(value);
    }
  };

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const group = button.getAttribute("data-filter-group");
      const value = button.getAttribute("data-filter-value");
      if (!group) return;
      toggleValue(group, value);
      applyFilters();
    });
  });

  if (resetButton) {
    resetButton.addEventListener("click", () => {
      groups.forEach((group) => setGroup(group, []));
      applyFilters();
    });
  }

  const params = new URLSearchParams(location.search);
  const parseParam = (value) =>
    (value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  groups.forEach((group) => {
    if (group === "contest") {
      state.contest = parseParam(params.get("contest"));
      return;
    }
    const allowed = new Set(
      buttonsInGroup(group)
        .map((button) => button.getAttribute("data-filter-value"))
        .filter((value) => value && value !== "all")
    );
    state[group] = parseParam(params.get(group)).filter((value) => allowed.has(value));
  });
  applyFilters();

  const hashMatch = location.hash.match(/^#photo_(\d+)$/);
  if (hashMatch) {
    const index = photoIndex.get(hashMatch[1]);
    if (index !== undefined) open(index, { hash: false });
  }
})();
