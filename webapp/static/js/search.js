(function () {
  const input = document.getElementById("search-input");
  const box   = document.getElementById("suggestions");
  const form  = document.getElementById("search-form");
  if (!input || !box) return;

  let debounceTimer   = null;
  let activeIndex     = -1;
  let currentItems    = [];
  let currentController = null;

  function esc(str) {
    const d = document.createElement("div");
    d.textContent = str || "";
    return d.innerHTML;
  }

  function renderLoading() {
    box.innerHTML = '<div class="suggestion-loading">Qidirilmoqda…</div>';
    box.classList.add("open");
  }

  function renderEmpty(query) {
    box.innerHTML = `<div class="suggestion-empty">"${esc(query)}" bo'yicha hech narsa topilmadi</div>`;
    box.classList.add("open");
  }

  function renderResults(items, query) {
    currentItems = items;
    activeIndex  = -1;
    if (!items.length) { renderEmpty(query); return; }

    const rows = items.map((m, i) => {
      const thumb = m.image_url
        ? `<img class="suggestion-thumb" src="${esc(m.image_url)}" alt="" loading="lazy"
              onerror="this.outerHTML='<div class=&quot;suggestion-thumb-fallback&quot;>${esc(m.placeholder || "?")}</div>'">`
        : `<div class="suggestion-thumb-fallback">${esc(m.placeholder || "?")}</div>`;

      const meta = [m.category, m.manufacturer].filter(Boolean).join(" • ");
      const priceHtml = m.age_group
        ? `<span class="suggestion-price">${esc(m.age_group)}</span>`
        : "";
      const t136Html = m.t136_filial
        ? `<span class="badge badge-t136">T136</span>`
        : "";

      return `
        <div class="suggestion-item" data-idx="${i}" data-href="${esc(m.url || `/dori/${m.id}`)}">
          ${thumb}
          <div class="suggestion-text">
            <div class="suggestion-name">${esc(m.name)} ${t136Html}</div>
            <div class="suggestion-meta">${esc(meta || "—")}</div>
          </div>
          ${priceHtml}
        </div>`;
    }).join("");

    box.innerHTML = rows +
      `<a class="suggestion-more" href="/qidiruv?q=${encodeURIComponent(query)}">Barcha natijalarni ko'rish →</a>`;
    box.classList.add("open");

    box.querySelectorAll(".suggestion-item").forEach((el) => {
      el.addEventListener("click", () => { window.location.href = el.dataset.href; });
    });
  }

  function closeBox() {
    box.classList.remove("open");
    box.innerHTML = "";
    activeIndex = -1;
  }

  async function fetchResults(query) {
    if (currentController) currentController.abort();
    currentController = new AbortController();
    try {
      const res  = await fetch(`/api/qidiruv?q=${encodeURIComponent(query)}`, { signal: currentController.signal });
      const data = await res.json();
      renderResults(data.results || [], query);
    } catch (err) {
      if (err.name !== "AbortError") {
        box.innerHTML = '<div class="suggestion-empty">Xatolik yuz berdi, qayta urinib ko\'ring</div>';
      }
    }
  }

  input.addEventListener("input", () => {
    const query = input.value.trim();
    clearTimeout(debounceTimer);
    if (query.length < 2) { closeBox(); return; }
    renderLoading();
    debounceTimer = setTimeout(() => fetchResults(query), 220);
  });

  input.addEventListener("keydown", (e) => {
    const items = box.querySelectorAll(".suggestion-item");
    if (!items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      window.location.href = items[activeIndex].dataset.href;
      return;
    } else return;
    items.forEach((el, i) => el.classList.toggle("active", i === activeIndex));
    items[activeIndex].scrollIntoView({ block: "nearest" });
  });

  document.addEventListener("click", (e) => {
    if (!box.contains(e.target) && e.target !== input) closeBox();
  });
})();
