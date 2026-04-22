const THEME_KEY = "cityvoice-theme";
const REACTION_EMOJIS = ["👍", "❤️", "😡", "😢"];

const OPTIONS = {
  categories: [
    { value: "Дороги", label: "Дороги" },
    { value: "Мусор", label: "Мусор" },
    { value: "Освещение", label: "Освещение" },
    { value: "Транспорт", label: "Транспорт" },
    { value: "Безопасность", label: "Безопасность" },
    { value: "Благоустройство", label: "Благоустройство" },
    { value: "Экология", label: "Экология" }
  ],
  districts: [
    { value: "Первомайский район", label: "Первомайский район" },
    { value: "Свердловский район", label: "Свердловский район" },
    { value: "Октябрьский район", label: "Октябрьский район" },
    { value: "Ленинский район", label: "Ленинский район" },
    { value: "Ош", label: "Ош" },
    { value: "Джалал-Абад", label: "Джалал-Абад" },
    { value: "Каракол", label: "Каракол" }
  ],
  filterCategories: [{ value: "", label: "Все категории" }],
  filterDistricts: [{ value: "", label: "Все районы" }],
  complaintSorts: [
    { value: "new", label: "Новые" },
    { value: "popular", label: "По популярности" }
  ],
  petitionSorts: [
    { value: "votes", label: "По голосам" },
    { value: "new", label: "Сначала новые" },
    { value: "popular", label: "По популярности" }
  ]
};

OPTIONS.filterCategories.push(...OPTIONS.categories);
OPTIONS.filterDistricts.push(...OPTIONS.districts);

const ADMIN_STATUS_OPTIONS = {
  complaint: ["Открыта", "В работе", "Решена"],
  petition: ["Активна", "На рассмотрении", "Реализована"]
};

const CATEGORY_COLORS = {
  "Дороги": "#f39b3d",
  "Мусор": "#32b46a",
  "Освещение": "#ffca42",
  "Транспорт": "#4b82ff",
  "Безопасность": "#ff7272",
  "Благоустройство": "#a56bff",
  "Экология": "#11b7a5"
};

const elements = {
  tabButtons: Array.from(document.querySelectorAll("[data-tab-link]")),
  panels: Array.from(document.querySelectorAll("[data-tab]")),
  moderationNav: document.getElementById("moderation-nav"),
  moderationPanel: document.getElementById("moderation-panel"),
  adminUsersCard: document.getElementById("admin-users-card"),
  adminComplaintsCard: document.getElementById("admin-complaints-card"),
  adminPetitionsCard: document.getElementById("admin-petitions-card"),
  toast: document.getElementById("toast"),
  heroCounters: document.getElementById("hero-counters"),
  tagCloud: document.getElementById("tag-cloud"),
  hotPetitions: document.getElementById("hot-petitions"),
  recentComplaints: document.getElementById("recent-complaints"),
  complaintCount: document.getElementById("complaint-count"),
  petitionCount: document.getElementById("petition-count"),
  complaintsFeed: document.getElementById("complaints-feed"),
  petitionsFeed: document.getElementById("petitions-feed"),
  complaintsLoadMore: document.getElementById("complaints-load-more"),
  petitionsLoadMore: document.getElementById("petitions-load-more"),
  complaintsSearch: document.getElementById("complaints-search"),
  petitionsSearch: document.getElementById("petitions-search"),
  complaintForm: document.getElementById("complaint-form"),
  petitionForm: document.getElementById("petition-form"),
  complaintLoginHint: document.getElementById("complaint-login-hint"),
  petitionLoginHint: document.getElementById("petition-login-hint"),
  guestAccount: document.getElementById("guest-account"),
  profileDashboard: document.getElementById("profile-dashboard"),
  accountHeading: document.getElementById("account-heading"),
  registerForm: document.getElementById("register-form"),
  loginForm: document.getElementById("login-form"),
  forgotPasswordForm: document.getElementById("forgot-password-form"),
  forgotPasswordLink: document.getElementById("forgot-password-link"),
  profileForm: document.getElementById("profile-form"),
  profileAvatar: document.getElementById("profile-avatar"),
  profileDisplayName: document.getElementById("profile-display-name"),
  profileDisplayEmail: document.getElementById("profile-display-email"),
  profileJoined: document.getElementById("profile-joined"),
  avatarInput: document.getElementById("avatar-input"),
  profileBadge: document.getElementById("profile-badge"),
  profileStats: document.getElementById("profile-stats"),
  myComplaints: document.getElementById("my-complaints"),
  myPetitions: document.getElementById("my-petitions"),
  changePasswordButton: document.getElementById("change-password-button"),
  logoutButton: document.getElementById("logout-button"),
  notificationsToggle: document.getElementById("notifications-toggle"),
  notificationCount: document.getElementById("notification-count"),
  notificationsDropdown: document.getElementById("notifications-dropdown"),
  notificationsList: document.getElementById("notifications-list"),
  markNotificationsRead: document.getElementById("mark-notifications-read"),
  moderationReports: document.getElementById("moderation-reports"),
  adminComplaints: document.getElementById("admin-complaints"),
  adminPetitions: document.getElementById("admin-petitions"),
  adminUsers: document.getElementById("admin-users"),
  themeToggle: document.getElementById("theme-toggle"),
  themeToggleLabel: document.getElementById("theme-toggle-label"),
  themeToggleIcon: document.getElementById("theme-toggle-icon")
};

const state = {
  theme: localStorage.getItem(THEME_KEY) || "dark",
  currentUser: null,
  complaints: [],
  petitions: [],
  notifications: [],
  unreadCount: 0,
  reports: [],
  users: [],
  comments: {},
  activeTab: new URLSearchParams(window.location.search).get("tab") || "home",
  focusPostId: new URLSearchParams(window.location.search).get("post") || "",
  map: null,
  markersLayer: null,
  avatarDraft: "",
  lastVotedPetitionId: "",
  voteFxTimer: null,
  revealObserver: null,
  editing: {},
  visibleCounts: {
    complaints: 6,
    petitions: 6
  },
  filters: {
    complaints: { search: "", category: "", district: "", sort: "new" },
    petitions: { search: "", category: "", district: "", sort: "votes" }
  }
};


function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}


function showToast(message, type = "success") {
  elements.toast.textContent = message;
  elements.toast.className = `toast ${type}`;
  clearTimeout(showToast.timeoutId);
  showToast.timeoutId = setTimeout(() => {
    elements.toast.className = "toast hidden";
  }, 2800);
}


async function apiFetch(url, options = {}) {
  const config = { ...options, headers: { ...(options.headers || {}) } };
  if (options.body && !(options.body instanceof FormData) && !config.headers["Content-Type"]) {
    config.headers["Content-Type"] = "application/json";
  }
  if (config.body && config.headers["Content-Type"] === "application/json" && typeof config.body !== "string") {
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(url, config);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Не удалось выполнить запрос.");
  }
  return data;
}


function setTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_KEY, theme);
  elements.themeToggleLabel.textContent = theme === "light" ? "Светлая тема" : "Тёмная тема";
  elements.themeToggleIcon.textContent = theme === "light" ? "☀️" : "🌙";
}


function getRelativeTime(isoDate) {
  const date = new Date(isoDate);
  const diffMs = Date.now() - date.getTime();
  const diffHours = Math.floor(diffMs / 3600000);
  if (diffHours < 1) {
    const minutes = Math.max(1, Math.floor(diffMs / 60000));
    return `${minutes} мин назад`;
  }
  if (diffHours < 24) {
    return `${diffHours} ч назад`;
  }
  if (diffHours < 48) {
    return "вчера";
  }
  const days = Math.floor(diffHours / 24);
  if (days < 7) {
    return `${days} дн назад`;
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long"
  }).format(date);
}


function getCategoryColor(category) {
  return CATEGORY_COLORS[category] || "#0d7c82";
}


function getStatusBadge(status) {
  const petitionStatusBadges = {
    "На рассмотрении": "status-progress",
    "Реализована": "status-done"
  };
  const normalized = String(status || "");
  if (petitionStatusBadges[normalized]) {
    return { className: petitionStatusBadges[normalized], label: normalized };
  }
  if (normalized === "Открыта") {
    return { className: "status-open", label: normalized };
  }
  if (normalized === "В работе") {
    return { className: "status-progress", label: normalized };
  }
  if (normalized === "Решена") {
    return { className: "status-done", label: normalized };
  }
  return { className: "status-active", label: normalized || "Активна" };
}


function renderAvatar(avatar, name, large = false) {
  if (!avatar) {
    return `<span class="avatar${large ? " large" : ""}" style="background: linear-gradient(135deg, #55cfff, #86f7ff);">${escapeHtml((name || "U").slice(0, 1).toUpperCase())}</span>`;
  }
  if (avatar.type === "image") {
    return `<span class="avatar${large ? " large" : ""}"><img src="${escapeHtml(avatar.src)}" alt="${escapeHtml(name)}" /></span>`;
  }
  const start = escapeHtml(avatar.start || "#55cfff");
  const end = escapeHtml(avatar.end || "#86f7ff");
  const initials = escapeHtml(avatar.initials || "CV");
  return `<span class="avatar${large ? " large" : ""}" style="background: linear-gradient(135deg, ${start}, ${end});">${initials}</span>`;
}


function renderActionIcon(name) {
  const icons = {
    comment: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 15.2c0 .88-.72 1.6-1.6 1.6H9.4L5 20v-3.2H4.6c-.88 0-1.6-.72-1.6-1.6V5.6C3 4.72 3.72 4 4.6 4h13.8c.88 0 1.6.72 1.6 1.6v9.6Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
    share: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M15 8l-6 3.5L15 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="18" cy="6" r="2.5" stroke="currentColor" stroke-width="1.8"/><circle cx="6" cy="12" r="2.5" stroke="currentColor" stroke-width="1.8"/><circle cx="18" cy="18" r="2.5" stroke="currentColor" stroke-width="1.8"/></svg>',
    flag: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 20V5m0 0h9.2l-1.1 2.2L15.2 9H6Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };
  return `<span class="action-icon">${icons[name] || ""}</span>`;
}


function formatProfileJoinedDate(isoDate) {
  if (!isoDate) {
    return "";
  }
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  const formatted = new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(parsed);
  return `Зарегистрирован: ${formatted}`;
}


function getProfileBadgeLabel(user) {
  if (!user) {
    return "";
  }
  if (user.role === "admin") {
    return "Администратор";
  }
  if (user.role === "moderator") {
    return "Модератор";
  }
  return user.stats?.badge || "Активный житель";
}


function closeAllSelects() {
  document.querySelectorAll("[data-select].open").forEach((select) => {
    select.classList.remove("open");
    select.querySelector("[data-select-menu]").classList.add("hidden");
  });
}


function setSelectValue(select, value, label) {
  const hiddenInput = select.querySelector('input[type="hidden"]');
  const labelNode = select.querySelector("[data-select-value]");
  hiddenInput.value = value;
  select.dataset.value = value;
  labelNode.textContent = label;
  select.querySelectorAll(".select-option").forEach((option) => {
    option.classList.toggle("active", option.dataset.value === value);
  });
  hiddenInput.dispatchEvent(new Event("change", { bubbles: true }));
}


function buildSelectOptions(select) {
  const menu = select.querySelector("[data-select-menu]");
  const triggerLabel = select.dataset.placeholder || "Выберите";
  const options = OPTIONS[select.dataset.optionsKey] || [];
  menu.innerHTML = options.map((option) => {
    const item = typeof option === "string" ? { value: option, label: option } : option;
    return `<button class="select-option" type="button" data-value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</button>`;
  }).join("");
  setSelectValue(select, "", triggerLabel);
}


function initSelects() {
  document.querySelectorAll("[data-select]").forEach((select) => {
    buildSelectOptions(select);

    const trigger = select.querySelector("[data-select-trigger]");
    const menu = select.querySelector("[data-select-menu]");

    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpen = select.classList.contains("open");
      closeAllSelects();
      if (!isOpen) {
        select.classList.add("open");
        menu.classList.remove("hidden");
      }
    });

    menu.addEventListener("click", (event) => {
      const option = event.target.closest(".select-option");
      if (!option) {
        return;
      }
      setSelectValue(select, option.dataset.value || "", option.textContent.trim());
      closeAllSelects();
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-select]")) {
      closeAllSelects();
    }
  });
}


function renderLoadingState() {
  const skeleton = Array.from({ length: 3 }, () => '<div class="skeleton-card"></div>').join("");
  elements.hotPetitions.innerHTML = skeleton;
  elements.recentComplaints.innerHTML = skeleton;
  elements.complaintsFeed.innerHTML = Array.from({ length: 4 }, () => '<div class="skeleton-card"></div>').join("");
  elements.petitionsFeed.innerHTML = Array.from({ length: 4 }, () => '<div class="skeleton-card"></div>').join("");
}


function isModerator() {
  return Boolean(state.currentUser && ["moderator", "admin"].includes(state.currentUser.role));
}


function isAdmin() {
  return Boolean(state.currentUser && state.currentUser.role === "admin");
}


function switchTab(tabName, options = {}) {
  if (tabName === "moderation" && !isModerator()) {
    tabName = "home";
  }

  state.activeTab = tabName;
  elements.panels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.tab === tabName);
  });
  elements.tabButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tabLink === tabName);
  });

  const params = new URLSearchParams(window.location.search);
  params.set("tab", tabName);
  if (Object.prototype.hasOwnProperty.call(options, "postId")) {
    state.focusPostId = options.postId || "";
  }
  if (state.focusPostId) {
    params.set("post", state.focusPostId);
  } else {
    params.delete("post");
  }
  history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);

  if (tabName === "home" && state.map) {
    setTimeout(() => state.map.invalidateSize(), 120);
  }

  if (state.focusPostId) {
    setTimeout(() => focusPostCard(state.focusPostId), 140);
  }
}


function getPopularityScore(item) {
  const reactions = REACTION_EMOJIS.reduce((sum, emoji) => sum + Number(item.reactionCounts?.[emoji] || 0), 0);
  return reactions + Number(item.commentCount || 0) + Number(item.votes || 0);
}


function summarize(text, maxLength = 120) {
  const value = String(text || "");
  return value.length > maxLength ? `${value.slice(0, maxLength).trim()}…` : value;
}


function animateNumber(node, target) {
  const duration = 1100;
  const start = performance.now();

  function step(now) {
    const progress = Math.min((now - start) / duration, 1);
    const value = Math.round(target * (1 - (1 - progress) * (1 - progress)));
    node.textContent = new Intl.NumberFormat("ru-RU").format(value);
    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }

  requestAnimationFrame(step);
}


function renderHeroCounters() {
  const complaints = state.complaints.length;
  const resolved = state.complaints.filter((item) => item.status === "Решена").length;
  const votes = state.petitions.reduce((sum, item) => sum + item.votes, 0);
  const active = state.petitions.filter((item) => item.status === "Активна").length;

  const metrics = [
    { label: "Жалоб подано", value: complaints },
    { label: "Петиций активно", value: active },
    { label: "Голосов собрано", value: votes },
    { label: "Проблем решено", value: resolved }
  ];

  elements.heroCounters.innerHTML = metrics.map((metric) => `
    <article class="counter-card">
      <span class="section-kicker">${escapeHtml(metric.label)}</span>
      <strong data-counter-target="${metric.value}">0</strong>
    </article>
  `).join("");

  elements.heroCounters.querySelectorAll("[data-counter-target]").forEach((node) => {
    animateNumber(node, Number(node.dataset.counterTarget || 0));
  });
}


function renderTagCloud() {
  const counts = new Map();
  [...state.complaints, ...state.petitions].forEach((item) => {
    counts.set(item.category, (counts.get(item.category) || 0) + 1);
  });

  const tags = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  elements.tagCloud.innerHTML = tags.length
    ? tags.map(([category, count]) => `<span class="tag-chip" style="border-color:${getCategoryColor(category)}33;color:${getCategoryColor(category)}">${escapeHtml(category)} · ${count}</span>`).join("")
    : '<div class="empty-card">Категории появятся после загрузки данных.</div>';
}


function renderCompactItem(item, kind) {
  const status = getStatusBadge(item.status);
  const extra = kind === "petition" ? `${item.votes} / ${item.goal} голосов` : item.district;

  return `
    <article class="compact-item">
      <div class="compact-item-top">
        <div>
          <strong>${escapeHtml(item.title)}</strong>
          <div class="meta-line">
            <span>${escapeHtml(item.category)}</span>
            <span>${escapeHtml(extra)}</span>
            <span>${escapeHtml(getRelativeTime(item.createdAt))}</span>
          </div>
        </div>
        <span class="status-badge ${status.className}">${escapeHtml(status.label)}</span>
      </div>
      <p>${escapeHtml(summarize(item.description, 110))}</p>
      <button class="ghost-button small" type="button" data-open-post="${item.id}" data-open-tab="${kind === "petition" ? "petitions" : "complaints"}">Открыть</button>
    </article>
  `;
}


function renderMap() {
  if (!window.L) {
    return;
  }

  if (!state.map) {
    state.map = L.map("city-map", { zoomControl: false }).setView([42.8746, 74.5698], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap"
    }).addTo(state.map);
    state.markersLayer = L.layerGroup().addTo(state.map);
  }

  state.markersLayer.clearLayers();
  state.complaints.forEach((item) => {
    if (item.latitude == null || item.longitude == null) {
      return;
    }
    const marker = L.circleMarker([item.latitude, item.longitude], {
      radius: 8,
      weight: 3,
      color: getCategoryColor(item.category),
      fillColor: getCategoryColor(item.category),
      fillOpacity: 0.92
    });
    marker.bindPopup(`
      <strong>${escapeHtml(item.title)}</strong><br />
      <span>${escapeHtml(item.district)}</span><br />
      <span>${escapeHtml(summarize(item.description, 90))}</span>
    `);
    marker.addTo(state.markersLayer);
  });
}


function renderHomePanels() {
  const topPetitions = [...state.petitions].sort((a, b) => b.votes - a.votes).slice(0, 3);
  const recentComplaints = [...state.complaints].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)).slice(0, 3);

  elements.hotPetitions.innerHTML = topPetitions.length
    ? topPetitions.map((item) => renderCompactItem(item, "petition")).join("")
    : '<div class="empty-card">Петиции появятся здесь после первой публикации.</div>';

  elements.recentComplaints.innerHTML = recentComplaints.length
    ? recentComplaints.map((item) => renderCompactItem(item, "complaint")).join("")
    : '<div class="empty-card">Жалобы появятся здесь после первой публикации.</div>';

  renderHeroCounters();
  renderTagCloud();
  renderMap();
}


function updateFormAccess(form, hintNode, enabled) {
  form.querySelectorAll("input, textarea, button").forEach((control) => {
    control.disabled = !enabled;
  });
  hintNode.classList.toggle("hidden", enabled);
}


function getFilteredItems(kind) {
  const source = kind === "complaints" ? state.complaints : state.petitions;
  const filters = state.filters[kind];

  const filtered = source.filter((item) => {
    const searchBase = `${item.title} ${item.description} ${item.authorName} ${item.district} ${item.category}`.toLowerCase();
    return (!filters.search || searchBase.includes(filters.search.toLowerCase()))
      && (!filters.category || item.category === filters.category)
      && (!filters.district || item.district === filters.district);
  });

  filtered.sort((a, b) => {
    if (filters.sort === "popular") {
      return getPopularityScore(b) - getPopularityScore(a);
    }
    if (filters.sort === "votes") {
      return Number(b.votes || 0) - Number(a.votes || 0);
    }
    return new Date(b.createdAt) - new Date(a.createdAt);
  });

  return filtered;
}


function renderReactionRow(item) {
  return REACTION_EMOJIS.map((emoji) => `
    <button class="reaction-button ${item.currentReaction === emoji ? "active" : ""}" type="button" data-action="react" data-kind="${item.type}" data-id="${item.id}" data-emoji="${emoji}">
      <span>${emoji}</span>
      <span>${Number(item.reactionCounts?.[emoji] || 0)}</span>
    </button>
  `).join("");
}


function renderCommentPanel(item) {
  const key = `${item.type}:${item.id}`;
  const commentState = state.comments[key];
  if (!commentState?.open) {
    return "";
  }

  const commentsMarkup = commentState.loading
    ? '<div class="skeleton-card"></div>'
    : commentState.items.length
      ? commentState.items.map((comment) => `
          <article class="comment-item">
            <div class="comment-head">
              <div class="post-author">
                ${renderAvatar(comment.authorAvatar, comment.authorName)}
                <div>
                  <strong>${escapeHtml(comment.authorName)}</strong>
                  <div class="post-meta">${escapeHtml(getRelativeTime(comment.createdAt))}</div>
                </div>
              </div>
              ${comment.canDelete ? `<button class="ghost-button small" type="button" data-action="delete-comment" data-comment-id="${comment.id}" data-kind="${item.type}" data-id="${item.id}">Удалить</button>` : ""}
            </div>
            <p class="post-content">${escapeHtml(comment.body)}</p>
          </article>
        `).join("")
      : '<div class="empty-card">Комментариев пока нет.</div>';

  const formMarkup = state.currentUser
    ? `
      <div class="comment-form">
        <textarea data-comment-body="${item.type}:${item.id}" placeholder="Оставьте комментарий"></textarea>
        <button class="button primary small" type="button" data-action="submit-comment" data-kind="${item.type}" data-id="${item.id}">Отправить</button>
      </div>
    `
    : '<div class="inline-note">Чтобы комментировать, войдите в аккаунт.</div>';

  return `
    <div class="comment-panel">
      ${commentsMarkup}
      ${formMarkup}
    </div>
  `;
}


function renderEditPanel(item) {
  const key = `${item.type}:${item.id}`;
  if (!state.editing[key]) {
    return "";
  }

  const goalField = item.type === "petition"
    ? `
      <label>
        Цель по голосам
        <input name="goal" type="number" min="10" step="10" value="${Number(item.goal || 100)}" />
      </label>
    `
    : "";

  return `
    <div class="edit-panel">
      <div class="edit-grid">
        <label>
          Заголовок
          <input name="title" type="text" value="${escapeHtml(item.title)}" />
        </label>
        <label>
          Категория
          <input name="category" type="text" value="${escapeHtml(item.category)}" />
        </label>
        <label>
          Район
          <input name="district" type="text" value="${escapeHtml(item.district)}" />
        </label>
        ${goalField}
        <label class="full">
          Описание
          <textarea name="description">${escapeHtml(item.description)}</textarea>
        </label>
      </div>
      <div class="post-actions">
        <button class="button primary small" type="button" data-action="save-edit" data-kind="${item.type}" data-id="${item.id}">Сохранить</button>
        <button class="ghost-button small" type="button" data-action="cancel-edit" data-kind="${item.type}" data-id="${item.id}">Отмена</button>
      </div>
    </div>
  `;
}


function renderPostCard(item) {
  const status = getStatusBadge(item.status);
  const isVoteHighlight = item.type === "petition" && state.lastVotedPetitionId === item.id;
  const progress = item.type === "petition"
    ? Math.min(100, Math.round((Number(item.votes || 0) / Math.max(Number(item.goal || 1), 1)) * 100))
    : 0;
  const canVote = item.type === "petition" && state.currentUser && !item.hasVoted && item.status === "Активна";
  const voteLabel = !state.currentUser
    ? "Поддержать"
    : item.hasVoted
      ? "Вы поддержали"
      : item.status === "Активна"
        ? "Поддержать"
        : "Недоступно";
  const progressBlock = item.type === "petition"
    ? `
      <div class="post-progress">
        <div class="post-progress-meta">
          <span>Прогресс</span>
          <strong>${item.votes} / ${item.goal}</strong>
        </div>
        <div class="progress-track"><div class="progress-fill ${isVoteHighlight ? "vote-progress-flash" : ""}" style="width:${progress}%"></div></div>
      </div>
    `
    : "";
  const supportButton = item.type === "petition"
    ? `
      <button class="${canVote ? "button primary small vote-button" : "ghost-button small vote-button"} ${isVoteHighlight ? "vote-button-pulse" : ""}" type="button" data-action="vote-petition" data-id="${item.id}" ${canVote ? "" : "disabled"}>
        ${voteLabel}
      </button>
    `
    : "";
  const ownerActions = [
    item.canEdit ? `<button class="ghost-button small" type="button" data-action="edit-post" data-kind="${item.type}" data-id="${item.id}">Редактировать</button>` : "",
    item.canDelete ? `<button class="ghost-button small" type="button" data-action="delete-post" data-kind="${item.type}" data-id="${item.id}">Удалить</button>` : ""
  ].filter(Boolean).join("");

  return `
    <article id="post-${item.id}" class="post-card ${isVoteHighlight ? "vote-highlight" : ""}" style="--accent-color:${getCategoryColor(item.category)}">
      <div class="post-card-body">
        <div class="post-head">
          <div class="post-author">
            ${renderAvatar(item.authorAvatar, item.authorName)}
            <div class="post-author-stack">
              <strong class="post-author-name">${escapeHtml(item.authorName)}</strong>
              <div class="post-meta">
                <span>${escapeHtml(getRelativeTime(item.createdAt))}</span>
              </div>
            </div>
          </div>
          <span class="status-badge ${status.className}">${escapeHtml(status.label)}</span>
        </div>

        <div class="post-tags">
          <span class="post-chip post-chip-category" style="--chip-color:${getCategoryColor(item.category)}">${escapeHtml(item.category)}</span>
          <span class="post-chip post-chip-location">${escapeHtml(item.district)}</span>
        </div>

        <h3 class="post-title">${escapeHtml(item.title)}</h3>
        <p class="post-content">${escapeHtml(item.description)}</p>
        ${progressBlock}

        <div class="post-footer">
          <div class="post-footer-left">
            ${supportButton}
            <div class="reaction-row">
              ${renderReactionRow(item)}
            </div>
          </div>

          <div class="post-utility-actions">
            <button class="post-utility-button" type="button" data-action="toggle-comments" data-kind="${item.type}" data-id="${item.id}">
              ${renderActionIcon("comment")}
              <span>Комментарии (${item.commentCount})</span>
            </button>
            <button class="post-utility-button icon-only" type="button" data-action="share-post" data-kind="${item.type}" data-id="${item.id}" aria-label="Поделиться">
              ${renderActionIcon("share")}
            </button>
            ${state.currentUser ? `
              <button class="post-utility-button icon-only" type="button" data-action="report-post" data-kind="${item.type}" data-id="${item.id}" aria-label="Пожаловаться">
                ${renderActionIcon("flag")}
              </button>
            ` : ""}
          </div>
        </div>

        ${ownerActions ? `<div class="post-owner-actions">${ownerActions}</div>` : ""}

        ${renderEditPanel(item)}
        ${renderCommentPanel(item)}
      </div>
    </article>
  `;
}


function renderFeed(kind) {
  const feed = kind === "complaints" ? elements.complaintsFeed : elements.petitionsFeed;
  const counter = kind === "complaints" ? elements.complaintCount : elements.petitionCount;
  const loadMoreButton = kind === "complaints" ? elements.complaintsLoadMore : elements.petitionsLoadMore;
  const filtered = getFilteredItems(kind);
  const visibleCount = state.visibleCounts[kind];
  const visibleItems = filtered.slice(0, visibleCount);

  counter.textContent = `${filtered.length} ${kind === "complaints" ? "жалоб" : "петиций"}`;

  if (!visibleItems.length) {
    feed.innerHTML = '<div class="empty-card">Ничего не найдено. Попробуйте изменить фильтры или добавить новую публикацию.</div>';
    loadMoreButton.classList.add("hidden");
    return;
  }

  feed.innerHTML = visibleItems.map(renderPostCard).join("");
  loadMoreButton.classList.toggle("hidden", filtered.length <= visibleCount);
}


function renderStats() {
  if (!state.currentUser) {
    elements.profileStats.innerHTML = "";
    return;
  }

  const stats = state.currentUser.stats || {};
  const items = [
    { label: "Жалоб подано", value: stats.complaintsCount || 0 },
    { label: "Петиций создано", value: stats.petitionsCount || 0 },
    { label: "Голосов отдано", value: stats.votesGiven || 0 },
    { label: "Всего публикаций", value: stats.publicationsCount || 0 }
  ];

  elements.profileStats.innerHTML = items.map((item) => `
    <article class="stat-card">
      <strong>${item.value}</strong>
      <span class="stat-label">${escapeHtml(item.label)}</span>
    </article>
  `).join("");
}


function renderProfileHistoryItem(item, kind) {
  const accent = getCategoryColor(item.category);
  const meta = kind === "petition"
    ? `${item.votes || 0} голосов`
    : getRelativeTime(item.createdAt);

  return `
    <article
      class="profile-history-item"
      data-open-post="${item.id}"
      data-open-tab="${kind === "petition" ? "petitions" : "complaints"}"
      tabindex="0"
      role="button"
      style="--accent-color:${accent}"
    >
      <strong>${escapeHtml(item.title)}</strong>
      <div class="profile-history-meta">
        <span>${escapeHtml(kind === "petition" ? item.category : item.district)}</span>
        <span>${escapeHtml(meta)}</span>
      </div>
    </article>
  `;
}


function renderProfile() {
  const user = state.currentUser;
  const isGuest = !user;
  elements.guestAccount.classList.toggle("hidden", !isGuest);
  elements.profileDashboard.classList.toggle("hidden", isGuest);
  elements.accountHeading.textContent = isGuest ? "Войдите или создайте профиль" : "Ваш личный кабинет";

  if (isGuest) {
    return;
  }

  elements.profileAvatar.innerHTML = renderAvatar(user.avatar, user.name, true);
  elements.profileDisplayName.textContent = user.name || "Пользователь";
  elements.profileDisplayEmail.textContent = user.email || "";
  elements.profileJoined.textContent = formatProfileJoinedDate(user.createdAt);
  elements.profileBadge.classList.remove("hidden");
  elements.profileBadge.textContent = getProfileBadgeLabel(user);

  elements.profileForm.elements.name.value = user.name || "";
  elements.profileForm.elements.email.value = user.email || "";
  elements.profileForm.elements.lastName.value = user.lastName || "";
  elements.profileForm.elements.firstName.value = user.firstName || "";
  elements.profileForm.elements.middleName.value = user.middleName || "";
  elements.profileForm.elements.birthYear.value = user.birthYear || "";

  const myComplaints = state.complaints.filter((item) => item.authorId === user.id).slice(0, 4);
  const myPetitions = state.petitions.filter((item) => item.authorId === user.id).slice(0, 4);

  elements.myComplaints.innerHTML = myComplaints.length
    ? `<div class="profile-history-list">${myComplaints.map((item) => renderProfileHistoryItem(item, "complaint")).join("")}</div>`
    : '<div class="profile-history-empty">У вас пока нет опубликованных жалоб.</div>';

  elements.myPetitions.innerHTML = myPetitions.length
    ? `<div class="profile-history-list">${myPetitions.map((item) => renderProfileHistoryItem(item, "petition")).join("")}</div>`
    : '<div class="profile-history-empty">Нет созданных петиций</div>';

  renderStats();
}


function renderNotifications() {
  const unread = Number(state.unreadCount || 0);
  elements.notificationCount.textContent = unread;
  elements.notificationCount.classList.toggle("hidden", unread === 0);

  elements.notificationsList.innerHTML = state.notifications.length
    ? state.notifications.map((item) => `
        <button class="compact-item notification-item" type="button" data-open-link="${escapeHtml(item.link)}">
          <strong>${escapeHtml(item.message)}</strong>
          <div class="meta-line">
            <span>${escapeHtml(getRelativeTime(item.createdAt))}</span>
            <span>${item.isRead ? "прочитано" : "новое"}</span>
          </div>
        </button>
      `).join("")
    : '<div class="empty-card">Уведомлений пока нет.</div>';
}


function renderModeration() {
  const visible = isModerator();
  elements.moderationNav.classList.toggle("hidden", !visible);
  elements.moderationPanel.classList.toggle("hidden", !visible);
  elements.adminUsersCard.classList.toggle("hidden", !isAdmin());
  elements.adminComplaintsCard.classList.toggle("hidden", !isAdmin());
  elements.adminPetitionsCard.classList.toggle("hidden", !isAdmin());

  if (!visible) {
    return;
  }

  elements.moderationReports.innerHTML = state.reports.length
    ? state.reports.map((report) => `
        <article class="moderation-item">
          <strong>${escapeHtml(report.postTitle)}</strong>
          <div class="meta-line">
            <span>${escapeHtml(report.reporterName)}</span>
            <span>${escapeHtml(getRelativeTime(report.createdAt))}</span>
            <span>${escapeHtml(report.contentType === "complaint" ? "Жалоба" : "Петиция")}</span>
          </div>
          <p>${escapeHtml(report.reason)}</p>
          <div class="moderation-actions">
            <button class="button primary small" type="button" data-action="approve-report" data-report-id="${report.id}">Одобрить</button>
            <button class="ghost-button small" type="button" data-action="delete-report-post" data-report-id="${report.id}">Удалить пост</button>
          </div>
        </article>
      `).join("")
    : '<div class="empty-card">Очередь модерации пуста.</div>';

  if (isAdmin()) {
    renderAdminStatusManagers();
    elements.adminUsers.innerHTML = state.users.length
      ? state.users.map((user) => `
          <article class="user-role-card">
            <div class="post-author">
              ${renderAvatar(user.avatar, user.name)}
              <div>
                <strong>${escapeHtml(user.name)}</strong>
                <div class="post-meta">
                  <span>${escapeHtml(user.email)}</span>
                  <span>${escapeHtml(user.role)}</span>
                </div>
              </div>
            </div>
            <div class="role-actions">
              ${["user", "moderator", "admin"].map((role) => `
                <button class="role-pill ${user.role === role ? "active" : ""}" type="button" data-action="set-role" data-user-id="${user.id}" data-role="${role}">
                  ${role}
                </button>
              `).join("")}
            </div>
          </article>
        `).join("")
      : '<div class="empty-card">Список пользователей пуст.</div>';
  }
}


function renderAdminStatusManagers() {
  const complaintItems = [...state.complaints]
    .sort((a, b) => new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt));
  const petitionItems = [...state.petitions]
    .sort((a, b) => new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt));

  const renderStatusManager = (item, kind) => `
    <article class="moderation-item">
      <strong>${escapeHtml(item.title)}</strong>
      <div class="meta-line">
        <span>${escapeHtml(item.authorName)}</span>
        <span>${escapeHtml(item.district)}</span>
        <span>${escapeHtml(item.status)}</span>
      </div>
      <div class="role-actions">
        ${ADMIN_STATUS_OPTIONS[kind].map((status) => `
          <button
            class="role-pill ${item.status === status ? "active" : ""}"
            type="button"
            data-action="set-publication-status"
            data-kind="${kind}"
            data-id="${item.id}"
            data-status="${escapeHtml(status)}"
          >
            ${escapeHtml(status)}
          </button>
        `).join("")}
      </div>
    </article>
  `;

  elements.adminComplaints.innerHTML = complaintItems.length
    ? complaintItems.map((item) => renderStatusManager(item, "complaint")).join("")
    : '<div class="empty-card">Жалоб пока нет.</div>';

  elements.adminPetitions.innerHTML = petitionItems.length
    ? petitionItems.map((item) => renderStatusManager(item, "petition")).join("")
    : '<div class="empty-card">Петиций пока нет.</div>';
}


function focusPostCard(postId) {
  const card = document.getElementById(`post-${postId}`);
  if (!card) {
    return;
  }
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  card.style.boxShadow = "0 0 0 3px rgba(255, 207, 77, 0.7)";
  setTimeout(() => {
    card.style.boxShadow = "";
  }, 1500);
}


function renderApp() {
  renderHomePanels();
  renderFeed("complaints");
  renderFeed("petitions");
  renderProfile();
  renderNotifications();
  renderModeration();
  updateFormAccess(elements.complaintForm, elements.complaintLoginHint, Boolean(state.currentUser));
  updateFormAccess(elements.petitionForm, elements.petitionLoginHint, Boolean(state.currentUser));
  switchTab(state.activeTab);
  requestAnimationFrame(() => {
    initScrollReveal();
  });
}


function initScrollReveal() {
  const targets = document.querySelectorAll(".hero-card, .surface-card, .compact-item, .post-card, .stat-card, .site-footer");
  if (!targets.length) {
    return;
  }

  const staggerGroups = [
    { selector: ".counter-card", step: 90, max: 360, offset: 56 },
    { selector: ".compact-item", step: 120, max: 420, offset: 76 },
    { selector: ".step-card", step: 120, max: 420, offset: 72 },
    { selector: ".stat-card", step: 90, max: 300, offset: 56 },
    { selector: ".post-card", step: 80, max: 320, offset: 52 }
  ];

  function resolveRevealTiming(node, fallbackIndex) {
    for (const group of staggerGroups) {
      if (!node.matches(group.selector) || !node.parentElement) {
        continue;
      }
      const siblings = Array.from(node.parentElement.children).filter((child) => child.matches(group.selector));
      const index = Math.max(0, siblings.indexOf(node));
      return {
        delay: Math.min(index * group.step, group.max),
        offset: group.offset
      };
    }

    return {
      delay: Math.min(fallbackIndex * 34, 180),
      offset: 40
    };
  }

  targets.forEach((node, index) => {
    const timing = resolveRevealTiming(node, index);
    node.classList.add("reveal-on-scroll");
    node.style.setProperty("--reveal-delay", `${timing.delay}ms`);
    node.style.setProperty("--reveal-offset", `${timing.offset}px`);
  });

  if (!("IntersectionObserver" in window)) {
    targets.forEach((node) => node.classList.add("is-visible"));
    return;
  }

  if (!state.revealObserver) {
    state.revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          state.revealObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.12,
      rootMargin: "0px 0px -48px 0px"
    });
  }

  targets.forEach((node) => {
    if (!node.classList.contains("is-visible")) {
      state.revealObserver.observe(node);
    }
  });
}


function updateItem(kind, updatedItem) {
  const collectionName = kind === "complaint" ? "complaints" : "petitions";
  state[collectionName] = state[collectionName].map((item) => item.id === updatedItem.id ? updatedItem : item);
}


function removeItem(kind, itemId) {
  const collectionName = kind === "complaint" ? "complaints" : "petitions";
  state[collectionName] = state[collectionName].filter((item) => item.id !== itemId);
}


async function loadComments(kind, itemId) {
  const key = `${kind}:${itemId}`;
  state.comments[key] = { ...(state.comments[key] || { items: [] }), open: true, loading: true };
  renderApp();
  const data = await apiFetch(`/api/${kind === "complaint" ? "complaints" : "petitions"}/${itemId}/comments`);
  state.comments[key] = { items: data.comments || [], open: true, loading: false };
  renderApp();
}


async function refreshNotifications() {
  if (!state.currentUser) {
    state.notifications = [];
    state.unreadCount = 0;
    renderNotifications();
    return;
  }
  const data = await apiFetch("/api/notifications");
  state.notifications = data.notifications || [];
  state.unreadCount = data.unreadCount || 0;
  renderNotifications();
}


async function refreshModerationData() {
  if (!isModerator()) {
    state.reports = [];
    state.users = [];
    renderModeration();
    return;
  }

  const [reportsData, usersData] = await Promise.all([
    apiFetch("/api/moderation/reports"),
    isAdmin() ? apiFetch("/api/admin/users") : Promise.resolve({ users: [] })
  ]);

  state.reports = reportsData.reports || [];
  state.users = usersData.users || [];
  renderModeration();
}


async function loadAppData() {
  const [meData, complaintsData, petitionsData] = await Promise.all([
    apiFetch("/api/me"),
    apiFetch("/api/complaints"),
    apiFetch("/api/petitions")
  ]);

  state.currentUser = meData.user;
  state.complaints = complaintsData.complaints || [];
  state.petitions = petitionsData.petitions || [];
  state.avatarDraft = "";

  await Promise.all([
    refreshNotifications(),
    refreshModerationData()
  ]);

  renderApp();
}


function syncFilterInputs() {
  const complaintCategory = document.querySelector("#complaints-category-filter input[type='hidden']");
  const complaintDistrict = document.querySelector("#complaints-district-filter input[type='hidden']");
  const complaintSort = document.querySelector("#complaints-sort-filter input[type='hidden']");
  const petitionCategory = document.querySelector("#petitions-category-filter input[type='hidden']");
  const petitionDistrict = document.querySelector("#petitions-district-filter input[type='hidden']");
  const petitionSort = document.querySelector("#petitions-sort-filter input[type='hidden']");

  complaintCategory.addEventListener("change", () => {
    state.filters.complaints.category = complaintCategory.value;
    state.visibleCounts.complaints = 6;
    renderFeed("complaints");
  });
  complaintDistrict.addEventListener("change", () => {
    state.filters.complaints.district = complaintDistrict.value;
    state.visibleCounts.complaints = 6;
    renderFeed("complaints");
  });
  complaintSort.addEventListener("change", () => {
    state.filters.complaints.sort = complaintSort.value || "new";
    renderFeed("complaints");
  });
  petitionCategory.addEventListener("change", () => {
    state.filters.petitions.category = petitionCategory.value;
    state.visibleCounts.petitions = 6;
    renderFeed("petitions");
  });
  petitionDistrict.addEventListener("change", () => {
    state.filters.petitions.district = petitionDistrict.value;
    state.visibleCounts.petitions = 6;
    renderFeed("petitions");
  });
  petitionSort.addEventListener("change", () => {
    state.filters.petitions.sort = petitionSort.value || "votes";
    renderFeed("petitions");
  });

  setSelectValue(document.getElementById("complaints-sort-filter"), "new", "Новые");
  setSelectValue(document.getElementById("petitions-sort-filter"), "votes", "По голосам");
}


async function handleAction(node) {
  const action = node.dataset.action;
  const kind = node.dataset.kind;
  const itemId = node.dataset.id;

  try {
    if (action === "vote-petition") {
      const data = await apiFetch(`/api/petitions/${itemId}/vote`, { method: "POST" });
      updateItem("petition", data.petition);
      state.lastVotedPetitionId = itemId;
      clearTimeout(state.voteFxTimer);
      state.voteFxTimer = setTimeout(() => {
        state.lastVotedPetitionId = "";
        renderApp();
      }, 1400);
      renderApp();
      showToast(data.message);
      return;
    }

    if (action === "react") {
      if (!state.currentUser) {
        showToast("Войдите, чтобы поставить реакцию.", "error");
        return;
      }
      const data = await apiFetch(`/api/${kind === "complaint" ? "complaints" : "petitions"}/${itemId}/reactions`, {
        method: "POST",
        body: { emoji: node.dataset.emoji }
      });
      const collection = kind === "complaint" ? state.complaints : state.petitions;
      const item = collection.find((entry) => entry.id === itemId);
      item.reactionCounts = data.reactionCounts;
      item.currentReaction = data.currentReaction;
      renderApp();
      return;
    }

    if (action === "toggle-comments") {
      const key = `${kind}:${itemId}`;
      if (state.comments[key]?.open) {
        state.comments[key].open = false;
        renderApp();
      } else if (state.comments[key]?.items) {
        state.comments[key].open = true;
        renderApp();
      } else {
        await loadComments(kind, itemId);
      }
      return;
    }

    if (action === "submit-comment") {
      if (!state.currentUser) {
        showToast("Войдите, чтобы комментировать.", "error");
        return;
      }
      const textarea = document.querySelector(`[data-comment-body="${kind}:${itemId}"]`);
      const body = textarea?.value.trim();
      if (!body) {
        showToast("Введите текст комментария.", "error");
        return;
      }
      const data = await apiFetch(`/api/${kind === "complaint" ? "complaints" : "petitions"}/${itemId}/comments`, {
        method: "POST",
        body: { body }
      });
      const key = `${kind}:${itemId}`;
      state.comments[key] = {
        open: true,
        loading: false,
        items: [...(state.comments[key]?.items || []), data.comment]
      };
      const collection = kind === "complaint" ? state.complaints : state.petitions;
      const item = collection.find((entry) => entry.id === itemId);
      item.commentCount += 1;
      renderApp();
      showToast(data.message);
      return;
    }

    if (action === "delete-comment") {
      const commentId = node.dataset.commentId;
      await apiFetch(`/api/comments/${commentId}`, { method: "DELETE" });
      const key = `${kind}:${itemId}`;
      state.comments[key].items = state.comments[key].items.filter((item) => item.id !== commentId);
      const collection = kind === "complaint" ? state.complaints : state.petitions;
      const item = collection.find((entry) => entry.id === itemId);
      item.commentCount = Math.max(0, item.commentCount - 1);
      renderApp();
      showToast("Комментарий удалён.");
      return;
    }

    if (action === "share-post") {
      const tab = kind === "complaint" ? "complaints" : "petitions";
      const url = `${window.location.origin}/?tab=${tab}&post=${itemId}`;
      await navigator.clipboard.writeText(url);
      showToast("Ссылка скопирована в буфер.");
      return;
    }

    if (action === "report-post") {
      await apiFetch(`/api/${kind === "complaint" ? "complaints" : "petitions"}/${itemId}/report`, {
        method: "POST",
        body: { reason: "Требует проверки модератором" }
      });
      showToast("Жалоба отправлена модератору.");
      return;
    }

    if (action === "edit-post") {
      state.editing[`${kind}:${itemId}`] = true;
      renderApp();
      return;
    }

    if (action === "cancel-edit") {
      delete state.editing[`${kind}:${itemId}`];
      renderApp();
      return;
    }

    if (action === "save-edit") {
      const card = node.closest(".post-card");
      const payload = {
        title: card.querySelector('[name="title"]').value,
        category: card.querySelector('[name="category"]').value,
        district: card.querySelector('[name="district"]').value,
        description: card.querySelector('[name="description"]').value
      };
      if (kind === "petition") {
        payload.goal = Number(card.querySelector('[name="goal"]').value || 0);
      }
      const data = await apiFetch(`/api/${kind === "complaint" ? "complaints" : "petitions"}/${itemId}`, {
        method: "PATCH",
        body: payload
      });
      updateItem(kind, data[kind]);
      delete state.editing[`${kind}:${itemId}`];
      renderApp();
      showToast(data.message);
      return;
    }

    if (action === "delete-post") {
      await apiFetch(`/api/${kind === "complaint" ? "complaints" : "petitions"}/${itemId}`, { method: "DELETE" });
      removeItem(kind, itemId);
      delete state.comments[`${kind}:${itemId}`];
      delete state.editing[`${kind}:${itemId}`];
      renderApp();
      showToast("Публикация удалена.");
      return;
    }

    if (action === "approve-report") {
      await apiFetch(`/api/moderation/reports/${node.dataset.reportId}/approve`, { method: "POST" });
      await refreshModerationData();
      showToast("Жалоба рассмотрена.");
      return;
    }

    if (action === "delete-report-post") {
      await apiFetch(`/api/moderation/reports/${node.dataset.reportId}/delete-post`, { method: "POST" });
      await loadAppData();
      showToast("Публикация удалена модератором.");
      return;
    }

    if (action === "set-publication-status") {
      const endpoint = kind === "complaint"
        ? `/api/admin/complaints/${itemId}/status`
        : `/api/admin/petitions/${itemId}/status`;
      const data = await apiFetch(endpoint, {
        method: "PATCH",
        body: { status: node.dataset.status || "" }
      });
      updateItem(kind, data[kind]);
      renderApp();
      showToast(data.message);
      return;
    }

    if (action === "set-role") {
      await apiFetch(`/api/admin/users/${node.dataset.userId}/role`, {
        method: "PATCH",
        body: { role: node.dataset.role }
      });
      await refreshModerationData();
      showToast("Роль пользователя обновлена.");
    }
  } catch (error) {
    showToast(error.message, "error");
  }
}


function attachStaticEvents() {
  elements.themeToggle.addEventListener("click", () => {
    setTheme(state.theme === "light" ? "dark" : "light");
  });

  elements.tabButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      if (button.dataset.tabLink) {
        event.preventDefault();
        switchTab(button.dataset.tabLink, { postId: "" });
      }
    });
  });

  elements.complaintsSearch.addEventListener("input", () => {
    state.filters.complaints.search = elements.complaintsSearch.value;
    state.visibleCounts.complaints = 6;
    renderFeed("complaints");
  });

  elements.petitionsSearch.addEventListener("input", () => {
    state.filters.petitions.search = elements.petitionsSearch.value;
    state.visibleCounts.petitions = 6;
    renderFeed("petitions");
  });

  elements.complaintsLoadMore.addEventListener("click", () => {
    state.visibleCounts.complaints += 4;
    renderFeed("complaints");
  });

  elements.petitionsLoadMore.addEventListener("click", () => {
    state.visibleCounts.petitions += 4;
    renderFeed("petitions");
  });

  elements.notificationsToggle.addEventListener("click", async () => {
    elements.notificationsDropdown.classList.toggle("hidden");
    if (!elements.notificationsDropdown.classList.contains("hidden")) {
      await refreshNotifications();
    }
  });

  elements.markNotificationsRead.addEventListener("click", async () => {
    try {
      await apiFetch("/api/notifications/mark-read", { method: "POST" });
      await refreshNotifications();
      showToast("Уведомления отмечены как прочитанные.");
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  document.addEventListener("click", async (event) => {
    if (!event.target.closest(".notification-wrap")) {
      elements.notificationsDropdown.classList.add("hidden");
    }

    const actionNode = event.target.closest("[data-action]");
    if (actionNode) {
      await handleAction(actionNode);
      return;
    }

    const linkNode = event.target.closest("[data-open-link]");
    if (linkNode) {
      const url = new URL(linkNode.dataset.openLink || "/", window.location.origin);
      switchTab(url.searchParams.get("tab") || "home", { postId: url.searchParams.get("post") || "" });
      elements.notificationsDropdown.classList.add("hidden");
      return;
    }

    const compactNode = event.target.closest("[data-open-post]");
    if (compactNode) {
      switchTab(compactNode.dataset.openTab, { postId: compactNode.dataset.openPost });
    }
  });

  elements.registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(elements.registerForm);
    try {
      const data = await apiFetch("/api/register", {
        method: "POST",
        body: {
          name: formData.get("name"),
          email: formData.get("email"),
          password: formData.get("password")
        }
      });
      elements.registerForm.reset();
      await loadAppData();
      switchTab("account");
      showToast(data.message);
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  elements.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(elements.loginForm);
    try {
      const data = await apiFetch("/api/login", {
        method: "POST",
        body: {
          email: formData.get("email"),
          password: formData.get("password")
        }
      });
      elements.loginForm.reset();
      await loadAppData();
      switchTab("account");
      showToast(data.message);
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  if (elements.forgotPasswordForm) {
    elements.forgotPasswordForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(elements.forgotPasswordForm);
      try {
        const data = await apiFetch("/api/password-reset/request", {
          method: "POST",
          body: { email: formData.get("email") }
        });
        elements.forgotPasswordForm.reset();
        showToast(data.message);
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  }

  if (elements.forgotPasswordLink) {
    elements.forgotPasswordLink.addEventListener("click", (event) => {
      event.preventDefault();
      window.open(
        elements.forgotPasswordLink.href,
        "cityvoice-forgot-password",
        "popup=yes,width=620,height=620,resizable=yes,scrollbars=yes"
      );
    });
  }

  elements.complaintForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.currentUser) {
      showToast("Сначала войдите в аккаунт.", "error");
      return;
    }
    const formData = new FormData(elements.complaintForm);
    try {
      const data = await apiFetch("/api/complaints", {
        method: "POST",
        body: {
          title: formData.get("title"),
          category: formData.get("category"),
          district: formData.get("district"),
          description: formData.get("description")
        }
      });
      elements.complaintForm.reset();
      const categorySelect = elements.complaintForm.querySelector("[data-select][data-options-key='categories']");
      const districtSelect = elements.complaintForm.querySelector("[data-select][data-options-key='districts']");
      setSelectValue(categorySelect, "", "Выберите категорию");
      setSelectValue(districtSelect, "", "Выберите район");
      state.complaints.unshift(data.complaint);
      renderApp();
      showToast(data.message);
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  elements.petitionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.currentUser) {
      showToast("Сначала войдите в аккаунт.", "error");
      return;
    }
    const formData = new FormData(elements.petitionForm);
    try {
      const data = await apiFetch("/api/petitions", {
        method: "POST",
        body: {
          title: formData.get("title"),
          category: formData.get("category"),
          district: formData.get("district"),
          description: formData.get("description"),
          goal: Number(formData.get("goal") || 0)
        }
      });
      elements.petitionForm.reset();
      elements.petitionForm.querySelectorAll("[data-select]").forEach((select) => {
        setSelectValue(select, "", select.dataset.placeholder);
      });
      state.petitions.unshift(data.petition);
      renderApp();
      showToast(data.message);
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  elements.profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.currentUser) {
      return;
    }
    const formData = new FormData(elements.profileForm);
    try {
      const data = await apiFetch("/api/profile", {
        method: "PATCH",
        body: {
          name: formData.get("name"),
          lastName: formData.get("lastName"),
          firstName: formData.get("firstName"),
          middleName: formData.get("middleName"),
          birthYear: formData.get("birthYear"),
          avatarData: state.avatarDraft || state.currentUser.avatarData || ""
        }
      });
      state.currentUser = data.user;
      await loadAppData();
      showToast(data.message);
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  elements.avatarInput.addEventListener("change", () => {
    const [file] = elements.avatarInput.files || [];
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      state.avatarDraft = String(reader.result || "");
      elements.profileAvatar.innerHTML = renderAvatar({ type: "image", src: state.avatarDraft }, state.currentUser?.name || "User", true);
      showToast("Аватар выбран. Сохраните профиль.");
    };
    reader.readAsDataURL(file);
  });

  if (elements.changePasswordButton) {
    elements.changePasswordButton.addEventListener("click", (event) => {
      if (!state.currentUser) {
        return;
      }
      event.preventDefault();
      const resetUrl = new URL(elements.changePasswordButton.href, window.location.origin);
      if (state.currentUser.email) {
        resetUrl.searchParams.set("email", state.currentUser.email);
      }
      window.location.assign(resetUrl.toString());
    });
  }

  elements.logoutButton.addEventListener("click", async () => {
    try {
      const data = await apiFetch("/api/logout", { method: "POST" });
      state.currentUser = null;
      state.comments = {};
      await loadAppData();
      switchTab("home");
      showToast(data.message);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
}


async function bootstrap() {
  setTheme(state.theme);
  renderLoadingState();
  initSelects();
  syncFilterInputs();
  attachStaticEvents();
  await loadAppData();
  switchTab(state.activeTab);
}


bootstrap().catch((error) => {
  showToast(error.message || "Не удалось загрузить приложение.", "error");
});
