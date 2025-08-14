from django.shortcuts import render
from django.shortcuts import render, redirect
from .utils.cart import get_cart, save_cart
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction  
from .models import Products, Order, OrderItem, ProductSize


def home(request):
    return render(request, 'store/index.html')

def products(request):
    products = Products.objects.all()
    session_cart = get_cart(request.session)

    best_sellers, tshirts, shorts, suits, trousers = [], [], [], [], []

    for p in products:
        if getattr(p, "best_seller", False) or p.classification == 'best_sellers':
            best_sellers.append(p)

        if p.classification == 'tshirts':
            tshirts.append(p)

        if p.classification == 'shorts':
            shorts.append(p)

        if p.classification == 'suit':
            suits.append(p)

        if p.classification == 'trouser':
            trousers.append(p)

    return render(request, 'store/products.html', {
        'best_sellers': best_sellers,
        'tshirts': tshirts,
        'shorts': shorts,
        'trousers': trousers,
        'suits': suits,
        'cart': session_cart
    })

def get_session_cart(request):
    session_cart = get_cart(request.session)
    if session_cart:
        return JsonResponse({"cart": session_cart})

def add_to_cart(request):
    product_id = int(request.POST['product_id'])
    size = request.POST.get('size', '')  # Get size if provided
    qty = int(request.POST.get('qty', 1))

    product = Products.objects.get(pk=product_id)
    unit_price = product.price

    # If size is provided, check stock in ProductSize
    if size:
        try:
            product_size = ProductSize.objects.get(product_id=product_id, size=size)
            if product_size.stock_count < qty:
                return JsonResponse({"ok": False, "error": f"Only {product_size.stock_count} items available in size {size}"})
        except ProductSize.DoesNotExist:
            return JsonResponse({"ok": False, "error": "This size is not available"})

    cart = get_cart(request.session)

    # Create unique cart item identifier (include size if present)
    cart_item_key = f"{product_id}_{size}" if size else str(product_id)

    for item in cart['items']:
        # Check both product_id and size for existing items
        existing_key = f"{item['product_id']}_{item.get('size', '')}" if item.get('size') else str(item['product_id'])
        if existing_key == cart_item_key:
            item['qty'] += qty
            save_cart(request.session, cart)
            return JsonResponse({"ok": True, "cart": cart})
    
    # Create new cart item
    cart_item = {
        "product_id": product_id,
        "name": product.name,
        "qty": qty,
        "unit_price": str(unit_price),
        "image_url": product.image.url if product.image else "",
    }
    
    # Add size info if provided
    if size:
        cart_item["size"] = size
        try:
            product_size = ProductSize.objects.get(product_id=product_id, size=size)
            cart_item["size_display"] = product_size.get_size_display()
        except ProductSize.DoesNotExist:
            cart_item["size_display"] = size
        
    cart["items"].append(cart_item)
    save_cart(request.session, cart)
    return JsonResponse({"ok": True, "cart": cart})

def remove_from_cart(request):
    product_id = int(request.POST['product_id'])
    size = request.POST.get('size', '')  # Get size if provided
    cart = get_cart(request.session)

    # Create the same cart item key used in add_to_cart
    cart_item_key = f"{product_id}_{size}" if size else str(product_id)

    for item in cart['items']:
        # Check both product_id and size for the item to remove
        existing_key = f"{item['product_id']}_{item.get('size', '')}" if item.get('size') else str(item['product_id'])
        if existing_key == cart_item_key:
            item['qty'] -= 1
            if item['qty'] <= 0:
                cart['items'].remove(item)
            break

    save_cart(request.session, cart)
    return JsonResponse({"ok": True, "cart": cart})


def checkout(request):
    cart = get_cart(request.session)
    return render(request, 'store/checkout.html', {"cart": cart})


def place_order(request):
    if request.method == 'POST':
        try:
            # Get cart from session
            cart = get_cart(request.session)
            
            # Validate cart is not empty
            if not cart or not cart.get('items'):
                messages.error(request, 'Your cart is empty. Please add items before checkout.')
                return redirect('checkout')
            
            # Extract form data
            first_name = request.POST.get('first_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            area = request.POST.get('area', '').strip()
            nearest_landmark = request.POST.get('nearest_landmark', '').strip()
            notes = request.POST.get('notes', '').strip()
            total_amount = int(request.POST.get('total_amount', 0))
            
            # Basic validation
            if not all([first_name, phone, address, area]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('checkout')
            
            # Create order with transaction to ensure data integrity
            with transaction.atomic():
                # Create the main order
                order = Order.objects.create(
                    first_name=first_name,
                    phone=phone,
                    address=address,
                    area=area,
                    nearest_landmark=nearest_landmark,
                    total_amount=total_amount,
                    notes=notes,
                    status='pending'
                )
                
                # Create order items
                for item in cart['items']:
                    product = Products.objects.get(pk=item['product_id'])
                    
                    # Handle sized products
                    if item.get('size'):
                        # Check and update stock for sized products
                        product_size = ProductSize.objects.select_for_update().get(
                            product=product, size=item['size']
                        )
                        if product_size.stock_count < item['qty']:
                            raise Exception(f"Not enough stock for {product.name} in size {item['size']}")
                        
                        # Create order item with size
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            size=item['size'],  # Add size to OrderItem
                            quantity=item['qty'],
                            price=int(float(item['unit_price']))
                        )
                        
                        # Reduce stock count
                        product_size.stock_count -= item['qty']
                        product_size.save()
                        
                    else:
                        # Handle non-sized products (your existing logic)
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=item['qty'],
                            price=int(float(item['unit_price']))
                        )
                        # Keep your existing stock logic for non-sized products
                        if hasattr(product, 'stock_count'):
                            product.stock_count -= item['qty']
                            if product.stock_count == 0:
                                product.in_stock = False
                            product.save()
                
                # Clear the cart after successful order
                request.session['cart'] = {'items': []}
                request.session.modified = True
                
                # Success message
                messages.success(request, f'Order #{order.order_number} placed successfully! We will contact you soon.')
                
                # Redirect to a success page or home
                return redirect('order_success', order_number=order.order_number)
                
        except Exception as e:
            messages.error(request, 'An error occurred while placing your order. Please try again.')
            return redirect('checkout')
    
    # If not POST, redirect to checkout
    return redirect('checkout')


# ADDED: Order success page
def order_success(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number)
        return render(request, 'store/order_success.html', {'order': order})
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('home')