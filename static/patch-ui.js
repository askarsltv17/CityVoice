function renderCompactItem(item, kind) {
  const status = getStatusBadge(item.status);
  const accent = getCategoryColor(item.category);
  const metaPrimary = kind === "petition" ? "Прогресс" : item.district;
  const isVoteHighlight = kind === "petition" && state.lastVotedPetitionId === item.id;
  const progress = kind === "petition"
    ? Math.min(100, Math.round((Number(item.votes || 0) / Math.max(Number(item.goal || 1), 1)) * 100))
    : 0;

  const progressMarkup = kind === "petition"
    ? `
      <div class="compact-progress">
        <div class="compact-progress-meta">
          <span>${item.votes} / ${item.goal}</span>
          <span>Прогресс</span>
        </div>
        <div class="compact-progress-track">
          <div class="compact-progress-fill ${isVoteHighlight ? "vote-progress-flash" : ""}" style="width:${progress}%"></div>
        </div>
      </div>
    `
    : "";

  return `
    <article
      class="compact-item compact-item-link compact-item-${kind} ${isVoteHighlight ? "vote-highlight" : ""}"
      data-open-post="${item.id}"
      data-open-tab="${kind === "petition" ? "petitions" : "complaints"}"
      tabindex="0"
      role="button"
      style="--accent-color:${accent}"
    >
      <div class="compact-item-top">
        <div class="compact-item-tags">
          <span class="compact-pill" style="color:${accent};background:${accent}18;border-color:${accent}33">${escapeHtml(item.category)}</span>
          <span>${escapeHtml(kind === "petition" ? item.authorName : item.district)}</span>
        </div>
        <span class="status-badge ${status.className}">${escapeHtml(status.label)}</span>
      </div>

      <strong>${escapeHtml(item.title)}</strong>
      <p>${escapeHtml(summarize(item.description, kind === "petition" ? 138 : 120))}</p>

      <div class="compact-item-footer">
        <div class="meta-line">
          <span>${escapeHtml(metaPrimary)}</span>
          <span>${escapeHtml(getRelativeTime(item.createdAt))}</span>
        </div>
        <span class="compact-arrow" aria-hidden="true">→</span>
      </div>

      ${progressMarkup}
    </article>
  `;
}

function renderProfile() {
  const user = state.currentUser;
  const isGuest = !user;
  elements.guestAccount.classList.toggle("hidden", !isGuest);
  elements.profileDashboard.classList.toggle("hidden", isGuest);
  elements.accountHeading.textContent = isGuest ? "Войдите или создайте профиль" : "Личный кабинет";

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

document.addEventListener("click", (event) => {
  const navTargetNode = event.target.closest("[data-nav-target]");
  if (navTargetNode) {
    event.preventDefault();
    switchTab(navTargetNode.dataset.navTarget, { postId: "" });
  }
});

document.addEventListener("keydown", (event) => {
  const card = event.target.closest(".compact-item-link");
  if (card && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    switchTab(card.dataset.openTab, { postId: card.dataset.openPost });
  }
});

setTimeout(() => {
  if (typeof renderApp === "function") {
    renderApp();
  }
}, 0);
