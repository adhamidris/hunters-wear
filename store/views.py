from django.shortcuts import render
from django.shortcuts import render, redirect
from .utils.cart import get_cart, save_cart
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction  
from .models import Products, Order, OrderItem


def home(request):
    products = Products.objects.all()
    session_cart = get_cart(request.session)

    return render(request, 'store/index.html', {'products': products, 'cart': session_cart})

def get_session_cart(request):
    session_cart = get_cart(request.session)
    if session_cart:
        return JsonResponse({"cart": session_cart})

def add_to_cart(request):

    product_id = int(request.POST['product_id'])
    qty = int(request.POST.get('qty', 1))

    product = Products.objects.get(pk=product_id)
    unit_price = product.price

    cart = get_cart(request.session)

    for item in cart['items']:
        if item['product_id'] == product_id:
            item['qty'] += qty
            save_cart(request.session, cart)
            return JsonResponse({"ok": True, "cart": cart})
        
    cart["items"].append({
        "product_id": product_id,
        "name": product.name,
        "qty": qty,
        "unit_price": str(unit_price),
        "image_url": product.image.url if product.image else "",
    })
    save_cart(request.session, cart)
    return JsonResponse({"ok": True, "cart": cart})

def remove_from_cart(request):
    product_id = int(request.POST['product_id'])
    cart = get_cart(request.session)

    for item in cart['items']:
        if item['product_id'] == product_id:
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
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item['qty'],
                        price=int(float(item['unit_price']))
                    )
                
                # Clear the cart after successful order
                request.session['cart'] = {'items': []}
                request.session.modified = True
                
                # Success message
                messages.success(request, f'Order #{order.order_number} placed successfully! We will contact you soon.')
                
                # Redirect to a success page or home
                return redirect('order_success', order_number=order.order_number)
                
        except Exception as e:
            messages.error(request, 'An error occurred while placing your order. Please try again.', e)
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
    

