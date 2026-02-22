// Heathify Main JS — Coffee & Beige Theme
document.addEventListener('DOMContentLoaded', () => {
    // ===== Fade-in on scroll =====
    const fadeElems = document.querySelectorAll('.product-card, .section-title, .glass-card, .trust-stat, .testimonial-card');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    fadeElems.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        observer.observe(el);
    });

    // ===== Shop Filters =====
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => {
                b.style.color = 'var(--text-muted)';
                b.style.background = 'transparent';
                b.style.border = '1.5px solid var(--glass-border)';
            });
            btn.style.color = 'white';
            btn.style.background = 'var(--accent)';
            btn.style.border = '1.5px solid var(--accent)';

            const cat = btn.dataset.category;
            document.querySelectorAll('.product-card[data-category]').forEach(card => {
                card.style.display = (cat === 'All' || card.dataset.category === cat) ? '' : 'none';
            });
        });
    });

    // ===== Add to Cart Buttons =====
    document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const name = this.dataset.name;
            const price = parseFloat(this.dataset.price);
            const category = this.dataset.category || '';
            const origText = this.textContent;
            this.textContent = 'Adding...';
            this.disabled = true;

            fetch('/cart/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, price, category })
            })
                .then(r => {
                    if (r.status === 401) {
                        window.location.href = '/auth/login';
                        return;
                    }
                    return r.json();
                })
                .then(data => {
                    if (!data) return;
                    if (data.success) {
                        // Update cart badge
                        const badges = document.querySelectorAll('.cart-badge');
                        if (badges.length > 0) {
                            badges.forEach(b => b.textContent = data.cart_count);
                        } else {
                            const cartLinks = document.querySelectorAll('.nav-cart');
                            cartLinks.forEach(l => {
                                let badge = l.querySelector('.cart-badge');
                                if (!badge) {
                                    badge = document.createElement('span');
                                    badge.className = 'cart-badge';
                                    l.appendChild(badge);
                                }
                                badge.textContent = data.cart_count;
                            });
                        }

                        this.textContent = '✓ Added!';
                        this.style.background = 'linear-gradient(135deg, #27ae60, #2ecc71)';
                        // Show toast
                        showAddToCartToast(data.message || `${name} added to cart!`);
                        setTimeout(() => {
                            this.textContent = origText;
                            this.style.background = '';
                            this.disabled = false;
                        }, 2000);
                    }
                })
                .catch(() => {
                    this.textContent = origText;
                    this.disabled = false;
                });
        });
    });

    // ===== Cart quantity controls =====
    document.querySelectorAll('.qty-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const itemId = this.dataset.itemId;
            const delta = parseInt(this.dataset.delta);
            const qtyEl = document.getElementById(`qty-${itemId}`);
            if (!qtyEl) return;
            const newQty = Math.max(0, parseInt(qtyEl.textContent) + delta);

            fetch('/cart/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: itemId, quantity: newQty })
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        if (newQty === 0) {
                            const row = document.getElementById(`cart-row-${itemId}`);
                            if (row) row.remove();
                        } else {
                            qtyEl.textContent = newQty;
                        }
                        // Update totals
                        const subEl = document.getElementById('cart-subtotal');
                        const gstEl = document.getElementById('cart-gst');
                        const grandEl = document.getElementById('cart-grand');
                        if (subEl) subEl.textContent = '₹' + data.subtotal.toLocaleString('en-IN');
                        if (gstEl) gstEl.textContent = '₹' + data.gst.toLocaleString('en-IN');
                        if (grandEl) grandEl.textContent = '₹' + data.grand.toLocaleString('en-IN');

                        // Cart badge
                        document.querySelectorAll('.cart-badge').forEach(b => b.textContent = data.count);
                    }
                });
        });
    });

    // ===== Cart remove buttons =====
    document.querySelectorAll('.remove-item-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const itemId = this.dataset.itemId;
            fetch('/cart/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: itemId })
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const row = document.getElementById(`cart-row-${itemId}`);
                        if (row) row.remove();
                        location.reload();
                    }
                });
        });
    });

    // ===== Points redemption slider =====
    const redeemSlider = document.getElementById('redeem-slider');
    const redeemInput = document.getElementById('points_redeem');
    const redeemDisplay = document.getElementById('redeem-display');
    if (redeemSlider) {
        redeemSlider.addEventListener('input', function () {
            const val = parseInt(this.value);
            if (redeemInput) redeemInput.value = val;
            if (redeemDisplay) redeemDisplay.textContent = val + ' pts (saves ₹' + val + ')';
            // Update grand total display
            const baseGrand = parseFloat(document.getElementById('base-grand')?.dataset.value || 0);
            const grandEl = document.getElementById('checkout-grand');
            if (grandEl) {
                const newGrand = Math.max(0, baseGrand - val);
                grandEl.textContent = '₹' + newGrand.toLocaleString('en-IN', { minimumFractionDigits: 2 });
            }
        });
    }
});

function showAddToCartToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'flash success';
    toast.style.cssText = 'position:fixed;top:80px;right:20px;z-index:5000;animation:slideInRight 0.4s ease-out,fadeOut 0.4s ease-in 3s forwards;';
    toast.textContent = '🛒 ' + msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
