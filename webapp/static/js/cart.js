/**
 * PharmBaseUZ — Cart, Favorites & Compare System
 * All data stored in localStorage (no payment/checkout)
 */
(function() {
  'use strict';

  // ═══ UTILITY ═══════════════════════════════════════
  function getStore(key) {
    try { return JSON.parse(localStorage.getItem(key)) || []; }
    catch { return []; }
  }
  function setStore(key, data) {
    localStorage.setItem(key, JSON.stringify(data));
  }

  // ═══ TOAST NOTIFICATIONS ═══════════════════════════
  window.showToast = function(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-icon">${icons[type] || ''}</span><span>${message}</span><button class="toast-close" onclick="this.parentElement.remove()">&times;</button>`;
    container.appendChild(toast);
    setTimeout(() => { if (toast.parentElement) toast.remove(); }, 3500);
  };


  // ═══ CART ═══════════════════════════════════════════
  window.Cart = {
    KEY: 'pharmbase_cart',
    getItems() { return getStore(this.KEY); },
    setItems(items) { setStore(this.KEY, items); this.updateBadge(); },
    add(medicine) {
      const items = this.getItems();
      const existing = items.find(i => i.id === medicine.id);
      if (existing) { existing.qty += 1; }
      else { items.push({ ...medicine, qty: 1 }); }
      this.setItems(items);
      showToast(`${medicine.name} savatchaga qo'shildi`);
    },
    remove(id) {
      const items = this.getItems().filter(i => i.id !== id);
      this.setItems(items);
    },
    updateQty(id, delta) {
      const items = this.getItems();
      const item = items.find(i => i.id === id);
      if (!item) return;
      item.qty = Math.max(1, item.qty + delta);
      this.setItems(items);
    },
    setQty(id, qty) {
      const items = this.getItems();
      const item = items.find(i => i.id === id);
      if (!item) return;
      item.qty = Math.max(1, qty);
      this.setItems(items);
    },
    clear() { this.setItems([]); },
    getTotal() {
      return this.getItems().reduce((sum, i) => sum + (i.price || 0) * i.qty, 0);
    },
    getTotalQty() {
      return this.getItems().reduce((sum, i) => sum + i.qty, 0);
    },
    updateBadge() {
      const el = document.getElementById('cart-count');
      if (!el) return;
      const count = this.getTotalQty();
      el.textContent = count;
      el.classList.toggle('has-items', count > 0);
    }
  };

  // ═══ FAVORITES ═════════════════════════════════════
  window.Favorites = {
    KEY: 'pharmbase_favorites',
    getItems() { return getStore(this.KEY); },
    setItems(items) { setStore(this.KEY, items); this.updateBadge(); },
    toggle(medicine) {
      const items = this.getItems();
      const idx = items.findIndex(i => i.id === medicine.id);
      if (idx >= 0) {
        items.splice(idx, 1);
        this.setItems(items);
        showToast(`${medicine.name} sevimlilardan olib tashlandi`, 'info');
        return false;
      } else {
        items.push(medicine);
        this.setItems(items);
        showToast(`${medicine.name} sevimlilarga qo'shildi`);
        return true;
      }
    },
    has(id) { return this.getItems().some(i => i.id === id); },
    remove(id) {
      const items = this.getItems().filter(i => i.id !== id);
      this.setItems(items);
    },
    updateBadge() {
      const el = document.getElementById('fav-count');
      if (!el) return;
      const count = this.getItems().length;
      el.textContent = count;
      el.classList.toggle('has-items', count > 0);
    }
  };


  // ═══ COMPARE ══════════════════════════════════════
  window.Compare = {
    KEY: 'pharmbase_compare',
    MAX: 4,
    getItems() { return getStore(this.KEY); },
    setItems(items) { setStore(this.KEY, items); this.updateBadge(); },
    toggle(medicine) {
      const items = this.getItems();
      const idx = items.findIndex(i => i.id === medicine.id);
      if (idx >= 0) {
        items.splice(idx, 1);
        this.setItems(items);
        showToast(`${medicine.name} taqqoslashdan olib tashlandi`, 'info');
        return false;
      } else {
        if (items.length >= this.MAX) {
          showToast(`Maksimum ${this.MAX} ta dori taqqoslanishi mumkin`, 'error');
          return false;
        }
        items.push(medicine);
        this.setItems(items);
        showToast(`${medicine.name} taqqoslashga qo'shildi`);
        return true;
      }
    },
    has(id) { return this.getItems().some(i => i.id === id); },
    remove(id) {
      const items = this.getItems().filter(i => i.id !== id);
      this.setItems(items);
    },
    clear() { this.setItems([]); },
    updateBadge() {
      const el = document.getElementById('compare-count');
      if (!el) return;
      const count = this.getItems().length;
      el.textContent = count;
      el.classList.toggle('has-items', count > 0);
    }
  };

  // ═══ INIT BADGES ══════════════════════════════════
  document.addEventListener('DOMContentLoaded', function() {
    Cart.updateBadge();
    Favorites.updateBadge();
    Compare.updateBadge();
  });

})();
