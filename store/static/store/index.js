document.addEventListener("DOMContentLoaded", () => {

    console.log('DOM LOADED')

    // Initialize cart system
    const cartAPI = new CartAPI();
    const cartModal = new CartModal(cartAPI);

    // Update cart counter on page load
    cartAPI.updateCartCounter();

    document.addEventListener('click', async function(e) {
        if (e.target.classList.contains('add-to-cart-btn')) {
            e.preventDefault();
            
            const btn = e.target;
            const productBox = btn.closest('.product-box');
            const productId = productBox.dataset.productId;
            
            const sizeSelector = productBox.querySelector('.size-selector');
            let size = '';
            if (sizeSelector) {
                size = sizeSelector.value;
                if (!size) {
                    alert('Please select a size first');
                    return;
                }
            }
            
            if (productId) {
                
                btn.innerHTML = 'Adding...';
                
                const result = await cartAPI.addToCart(parseInt(productId), 1, size); // ADD size parameter
                
                if (result && result.ok) {
                    btn.classList.add('added');
                    btn.innerHTML = 'Added to Cart ✓';
                    
                    setTimeout(() => {
                        btn.classList.remove('added');
                        btn.innerHTML = '+ Add to Cart';
                    }, 2000);
                } else {
                    btn.classList.remove('added');
                    btn.innerHTML = '+ Add to Cart';
                    // ADD: Show error message if provided
                    if (result && result.error) {
                        alert(result.error);
                    }
                }
            }
        }
    });

    // Export for global access
    window.cartAPI = cartAPI;
    window.cartModal = cartModal;


    // CHECKOUT JS
    // Populate CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                     document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    if (csrfToken) {
        document.querySelector('#checkoutForm [name=csrfmiddlewaretoken]').value = csrfToken;
    }

    // Populate checkout cart items
    function populateCheckoutCart() {
        const cartItemsContainer = document.getElementById('checkoutCartItems');
        const subtotalEl = document.getElementById('checkoutSubtotal');
        const totalEl = document.getElementById('checkoutTotal');
        const totalAmountInput = document.getElementById('total_amount');
        const addMore = document.getElementById('add-more');
        
        // Check if cartAPI exists and has items
        if (!window.cartAPI || !window.cartAPI.cart || window.cartAPI.cart.items.length === 0) {
            cartItemsContainer.innerHTML = `
                <div class="empty-checkout-cart">
                    <i class="fas fa-shopping-cart"></i>
                    <p>Your cart is empty</p>
                    <a href="/#products" style="color: #007bff; text-decoration: none;">Continue Shopping</a>
                </div>
            `;
            subtotalEl.textContent = '0 EGP';
            totalEl.textContent = '0 EGP';
            totalAmountInput.value = '0';
            document.getElementById('placeOrderBtn').disabled = true;
            return;
        }

        const cart = window.cartAPI.cart;
        let itemsHTML = '';
        let subtotal = 0;

        cart.items.forEach(item => {
            const itemTotal = parseFloat(item.unit_price) * item.qty;
            subtotal += itemTotal;
            
            itemsHTML += `
                <div class="checkout-cart-item">
                    <img src="${item.image_url || '/static/placeholder.jpg'}" 
                        alt="${item.name}" class="checkout-item-image">
                    <div class="checkout-item-details">
                        <div class="checkout-item-name">${item.name}</div>
                        ${item.size ? `<div class="checkout-item-size">Size: ${item.size_display || item.size}</div>` : ''} 
                        <div class="checkout-item-meta">
                            <div class="checkout-item-qty">
                                <button class="qty-btn" onclick="updateCheckoutQuantity(${item.product_id}, -1, '${item.size || ''}')" type="button">-</button>
                                <span class="qty-display">${item.qty}</span>
                                <button class="qty-btn" onclick="updateCheckoutQuantity(${item.product_id}, 1, '${item.size || ''}')" type="button">+</button>
                            </div>
                            <span class="checkout-item-price">${itemTotal} EGP</span>
                        </div>
                    </div>
                </div>
            `;
        });

        addMore.innerHTML = `<a href="/#products" style="color: #007bff; text-decoration: none;">Add more items?</a>`
        cartItemsContainer.innerHTML = itemsHTML;
        subtotalEl.textContent = `${subtotal} EGP`;
        totalEl.textContent = `${subtotal} EGP`;
        totalAmountInput.value = Math.round(subtotal); // Convert to integer for backend
        
        // Enable order button if cart has items
        document.getElementById('placeOrderBtn').disabled = false;
    }

    // UPDATED: Form submission with better error handling and feedback
    document.getElementById('checkoutForm').addEventListener('submit', async function(e) {
        e.preventDefault(); // CHANGED: Always prevent default, handle submission manually
        
        const form = e.target;
        const btn = document.getElementById('placeOrderBtn');
        const cart = window.cartAPI?.cart;
        
        // Check if cart is empty
        if (!cart || cart.items.length === 0) {
            alert('Your cart is empty. Please add items before checkout.');
            return;
        }
        
        // Validate form
        if (!form.checkValidity()) {
            form.reportValidity(); // Show browser validation messages
            return;
        }
        
        // ADDED: Visual feedback during submission
        const originalBtnText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Processing Order...';
        btn.style.opacity = '0.7';
        
        try {
            // ADDED: Submit form data via fetch for better error handling
            const formData = new FormData(form);
            console.log("DATA:", formData);
            
            const response = await fetch('/place-order/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });
            
            // ADDED: Handle response based on status
            if (response.ok) {
                // Check if it's a redirect (Django will redirect on success)
                console.log("Response ok")
                if (response.redirected) {
                    window.location.href = response.url;
                } else {
                    // If not redirected, show success and redirect manually
                    cartAPI.showCartNotification('Order placed successfully!', 'success');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1000);
                }
            } else {
                // ADDED: Handle server errors
                throw new Error('Server error occurred');
            }
            
        } catch (error) {
            console.error('Order submission error:', error);
            
            // ADDED: Show error message to user
            cartAPI.showCartNotification('Error placing order. Please try again.', 'error');
            
            // ADDED: Re-enable button on error
            btn.disabled = false;
            btn.textContent = originalBtnText;
            btn.style.opacity = '1';
        }
    });

    // Phone number formatting (Egyptian format)
    document.getElementById('phone').addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove non-digits
        if (value.startsWith('2')) value = value.substring(1); // Remove country code if present
        if (value.length > 11) value = value.substring(0, 11); // Limit to 11 digits
        e.target.value = value;
    });

    // Initialize checkout cart
    populateCheckoutCart();
    
    // Update checkout when cart changes
    if (window.cartAPI) {
        // Override the updateCartCounter to also update checkout
        const originalUpdateCartCounter = window.cartAPI.updateCartCounter;
        window.cartAPI.updateCartCounter = function() {
            originalUpdateCartCounter.call(this);
            if (document.getElementById('checkoutCartItems')) {
                populateCheckoutCart();
            }
        };
    }

    // Global function for updating quantities in checkout
    window.updateCheckoutQuantity = async function(productId, change, size = '') {
        if (!window.cartAPI) return;
        
        const btn = event.target;
        const originalText = btn.textContent;
        
        // Visual feedback
        btn.disabled = true;
        btn.style.opacity = '0.5';
        
        try {
            if (change > 0) {
                await window.cartAPI.addToCart(productId, 1, size);
            } else {
                await window.cartAPI.removeFromCart(productId, size);
            }
            
            // Update will happen automatically via the overridden updateCartCounter
            
        } catch (error) {
            console.error('Error updating quantity:', error);
            window.cartAPI?.showCartNotification('Error updating quantity', 'error');
        } finally {
            // Re-enable button
            btn.disabled = false;
            btn.style.opacity = '1';
        }
    };

})

    // Cart API Class
class CartAPI {
    constructor() {
        this.cart = window.CART_DATA || { items: [] };
    }

        getCSRFToken() {
            const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            
            return csrfInput?.value || csrfMeta?.getAttribute('content');
        }

    // Add item to cart
    async addToCart(productId, qty = 1, size = '') { // ADD size parameter
        try {
            const formData = new FormData();
            formData.append('product_id', productId);
            formData.append('qty', qty);
            if (size) { // ADD: Include size if provided
                formData.append('size', size);
            }
            formData.append('csrfmiddlewaretoken', this.getCSRFToken());

            const response = await fetch(`/add/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });

            const data = await response.json();
            
            if (data.ok) {
                if (data.cart) {
                    this.cart = data.cart;
                }
                this.updateCartCounter();
                this.showCartNotification(`Item added to cart!`);
                return data;
            } else {
                // ADD: Return error data for handling
                return data;
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            this.showCartNotification('Error adding item to cart', 'error');
            return { ok: false, error: 'Network error' };
        }
}

    // Remove from Cart

    async removeFromCart(productId, size = '') { // ADD size parameter
        const formData = new FormData();
        formData.append('product_id', productId);
        if (size) { // ADD: Include size if provided
            formData.append('size', size);
        }
        formData.append('csrfmiddlewaretoken', this.getCSRFToken());

        const response = await fetch(`/remove/`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json()
        if (data.ok) {
            this.cart = data.cart;
            this.updateCartCounter();
        }
        return data;
    }

    // Update cart counter in UI
    updateCartCounter() {
        const counter = document.querySelector('.cart-counter');
        const totalItems = this.cart.items.reduce((sum, item) => sum + item.qty, 0);
        if (counter) {
            counter.textContent = totalItems;
            counter.style.display = totalItems > 0 ? 'flex' : 'none';
        }
    }

    // UPDATED: Enhanced notification system with better styling
    showCartNotification(message, type = 'success') {
        // Remove any existing notifications
        const existingNotification = document.querySelector('.cart-notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        const notification = document.createElement('div');
        notification.className = `cart-notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: ${type === 'error' ? '#ff4757' : '#2ed573'};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-weight: 500;
            animation: slideInRight 0.3s ease;
            max-width: 300px;
        `;
        
        // ADDED: Add animation keyframes if not already present
        if (!document.querySelector('#notification-animations')) {
            const style = document.createElement('style');
            style.id = 'notification-animations';
            style.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(notification);
        
        // ADDED: Smooth fade out animation
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }, 2700);
    }

    // Get cart total
    getCartTotal() {
        return this.cart.items.reduce((total, item) => {
            return total + (parseFloat(item.unit_price) * item.qty);
        }, 0);
    }
}

// Cart Modal Component
class CartModal {
    constructor(cartAPI) {
        this.cartAPI = cartAPI;
        this.modal = null;
        this.createModal();
        this.bindEvents();
    }

    createModal() {
        const modalHTML = `
            <div class="cart-modal" id="cartModal" style="display: none;">
                <div class="cart-overlay"></div>
                <div class="cart-content">
                    <div class="cart-header">
                        <h2>Your Cart</h2>
                        <button class="cart-close">&times;</button>
                    </div>
                    <div class="cart-body">
                        <div class="cart-items" id="cartItems"></div>
                    </div>
                    <div class="cart-footer">
                        <div class="cart-total">
                            <strong>Total: <span id="cartTotal">0</span> EGP</strong>
                        </div>
                        <button class="checkout-btn" id="modalCheckoutBtn" disabled>Checkout</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('cartModal');
    }

    bindEvents() {
        // Open cart modal
        document.querySelector('.cart')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.openModal();
        });

        // Close modal events
        this.modal?.querySelector('.cart-close')?.addEventListener('click', () => this.closeModal());
        this.modal?.querySelector('.cart-overlay')?.addEventListener('click', () => this.closeModal());

        // Checkout button click handler
        this.modal?.querySelector('#modalCheckoutBtn')?.addEventListener('click', (e) => {
            if (this.cartAPI.cart.items.length === 0) {
                e.preventDefault();
                return;
            }
            // Redirect to checkout page
            window.location.href = 'checkout/'; 
        });

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal?.classList.contains('active')) {
                this.closeModal();
            }
        });
    }

    openModal() {
        this.renderCartItems();
        this.modal.style.display = 'block';
        setTimeout(() => this.modal.classList.add('active'), 10);
    }

    closeModal() {
        this.modal.classList.remove('active');
        setTimeout(() => this.modal.style.display = 'none', 300);
    }

    renderCartItems() {
        const cartItemsContainer = document.getElementById('cartItems');
        const cartTotal = document.getElementById('cartTotal');
        const checkoutBtn = document.getElementById('modalCheckoutBtn');
        
        if (this.cartAPI.cart.items.length === 0) {
            cartItemsContainer.innerHTML = '<div class="empty-cart">Your cart is empty</div>';
            cartTotal.textContent = '0';
            
            // Disable checkout button when cart is empty
            checkoutBtn.disabled = true;
            checkoutBtn.textContent = 'Cart is Empty';
            checkoutBtn.style.opacity = '0.5';
            checkoutBtn.style.cursor = 'not-allowed';
            
            return;
        }

        const itemsHTML = this.cartAPI.cart.items.map(item => `
            <div class="cart-item">
                <img src="${item.image_url || '/static/placeholder.jpg'}" alt="${item.name}" class="cart-item-image">
                <div class="cart-item-details">
                    <div class="cart-item-name">${item.name}</div>
                    ${item.size ? `<div class="cart-item-size">Size: ${item.size_display || item.size}</div>` : ''}
                    <div class="cart-item-price">${item.unit_price} EGP</div>
                    <div class="cart-item-qty">
                        <button class="qty-btn" onclick="cartModal.updateQuantity(${item.product_id}, -1, '${item.size || ''}')">-</button>
                        <span>${item.qty}</span>
                        <button class="qty-btn" onclick="cartModal.updateQuantity(${item.product_id}, 1, '${item.size || ''}')">+</button>
                    </div>
                </div>
            </div>
        `).join('');

        cartItemsContainer.innerHTML = itemsHTML;
        cartTotal.textContent = this.cartAPI.getCartTotal().toFixed(2);
        
        // Enable checkout button when cart has items
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = 'Checkout';
        checkoutBtn.style.opacity = '1';
        checkoutBtn.style.cursor = 'pointer';
    }

    async updateQuantity(productId, change, size = '') {
        if (change > 0) {
            await this.cartAPI.addToCart(productId, 1, size);
        } else {
            await this.cartAPI.removeFromCart(productId, size);
        }
        this.cartAPI.updateCartCounter();
        this.renderCartItems();
    }
}