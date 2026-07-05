// ── Inline kategoriya o'zgartirish ──────────────────────────────────────────
(function () {
  document.querySelectorAll(".js-category-select").forEach((select) => {
    select.addEventListener("change", async () => {
      const medId = select.dataset.medId;
      const hint  = select.parentElement.querySelector(".save-hint");
      const fd    = new FormData();
      fd.append("kategoriya", select.value);
      select.disabled = true;
      try {
        const res  = await fetch(`/admin/dorilar/${medId}/kategoriya`, { method: "POST", body: fd });
        const data = await res.json();
        if (data.ok) {
          hint.classList.add("show");
          setTimeout(() => hint.classList.remove("show"), 2000);
        } else {
          alert("Saqlashda xatolik yuz berdi.");
        }
      } catch {
        alert("Tarmoq xatoligi. Qayta urinib ko'ring.");
      } finally {
        select.disabled = false;
      }
    });
  });
})();

// ── GoPharm qidiruv paneli ──────────────────────────────────────────────────
(function () {
  const toggleBtn  = document.getElementById("toggle-gp-search");
  const searchBody = document.getElementById("gp-search-body");
  if (!toggleBtn || !searchBody) return;

  toggleBtn.addEventListener("click", () => {
    const open = searchBody.style.display !== "none";
    searchBody.style.display = open ? "none" : "block";
    toggleBtn.textContent = open ? "Ko'rish ↓" : "Yashirish ↑";
  });

  const gpQ       = document.getElementById("gp-q");
  const gpBtn     = document.getElementById("gp-search-btn");
  const gpResults = document.getElementById("gp-results");
  const gpCatSel  = document.getElementById("gp-save-cat");
  if (!gpQ || !gpBtn || !gpResults) return;

  function esc(str) {
    const d = document.createElement("div");
    d.textContent = str || "";
    return d.innerHTML;
  }

  async function doSearch() {
    const q = gpQ.value.trim();
    if (q.length < 2) { gpResults.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">Kamida 2 harf kiriting.</p>'; return; }
    gpBtn.disabled = true;
    gpBtn.textContent = "Qidirmoqda…";
    gpResults.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">Yuklanmoqda…</p>';
    try {
      const res  = await fetch(`/admin/api/gopharm-izlash?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      renderGpResults(data.results || []);
    } catch {
      gpResults.innerHTML = '<p style="color:#B4432A;font-size:13px;">Xatolik yuz berdi.</p>';
    } finally {
      gpBtn.disabled = false;
      gpBtn.textContent = "Qidirish";
    }
  }

  function renderGpResults(items) {
    if (!items.length) {
      gpResults.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">Hech narsa topilmadi.</p>';
      return;
    }
    const rows = items.map((d, i) => {
      const img = d.image_url
        ? `<img class="gp-result-img" src="${esc(d.image_url)}" loading="lazy"
              onerror="this.style.display='none'">`
        : `<div class="gp-result-img" style="display:flex;align-items:center;justify-content:center;background:var(--primary);color:#fff;font-weight:700;">${esc((d.name||"?")[0].toUpperCase())}</div>`;
      const meta = [d.category, d.manufacturer].filter(Boolean).join(" • ");
      return `
        <div class="gp-result-row" id="gp-row-${i}">
          ${img}
          <div class="gp-result-info">
            <div class="gp-result-name">${esc(d.name)}</div>
            <div class="gp-result-meta">${esc(meta)}</div>
          </div>
          <span class="gp-result-price">${esc(d.price)}</span>
          <button class="btn btn-primary btn-sm gp-save-btn"
                  data-idx="${i}"
                  data-id="${d.id}" data-name="${esc(d.name)}"
                  data-cat="${esc(d.category)}" data-mfr="${esc(d.manufacturer)}"
                  data-image="${esc(d.image_url)}" data-price="${esc(d.price)}"
                  data-barcode="${esc(d.barcode)}" data-dosage="${esc(d.dosage_form)}"
                  data-comp="${esc(d.composition)}"
                  data-recept="${d.prescription ? 'true' : 'false'}"
                  data-slug="${esc(d.slug)}">
            Saqlash
          </button>
        </div>`;
    }).join("");
    gpResults.innerHTML = rows;

    gpResults.querySelectorAll(".gp-save-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const localCat = gpCatSel ? gpCatSel.value : "";
        btn.disabled = true;
        btn.textContent = "…";
        const fd = new FormData();
        fd.append("gp_id",      btn.dataset.id);
        fd.append("gp_name",    btn.dataset.name);
        fd.append("gp_category",btn.dataset.cat);
        fd.append("gp_mfr",     btn.dataset.mfr);
        fd.append("gp_image",   btn.dataset.image);
        fd.append("gp_price",   btn.dataset.price);
        fd.append("gp_barcode", btn.dataset.barcode);
        fd.append("gp_dosage",  btn.dataset.dosage);
        fd.append("gp_comp",    btn.dataset.comp);
        fd.append("gp_recept",  btn.dataset.recept);
        fd.append("gp_slug",    btn.dataset.slug);
        fd.append("local_category", localCat);
        try {
          const res  = await fetch("/admin/gopharm/saqlash", { method: "POST", body: fd });
          const data = await res.json();
          if (data.ok) {
            btn.textContent = data.duplicate ? "✓ Mavjud" : "✓ Saqlandi";
            btn.style.background = "#0a6146";
          } else {
            btn.textContent = "Xato";
            btn.disabled = false;
          }
        } catch {
          btn.textContent = "Xato";
          btn.disabled = false;
        }
      });
    });
  }

  gpBtn.addEventListener("click", doSearch);
  gpQ.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); doSearch(); } });
})();
