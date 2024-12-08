from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from cart.cart import Cart
from .forms import ShippingAddressForm, PaymentForm
from .models import ShippingAddress, Order, OrderItem
from store.models import Product, Profile
import datetime

def clear_cart(request):
    # Clear the cart
    for key in list(request.session.keys()):
        if key == 'session_key':
            del request.session[key]

def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        # Get the order
        order = Order.objects.get(id=pk)
        # Get the order items
        items = OrderItem.objects.filter(order=pk)

        if request.POST:
            status = request.POST['shipping_status']
            if status == "true":
                order = Order.objects.filter(id=pk)
                now = datetime.datetime.now()
                order.update(shipped=True, date_shipped=now)
                messages.success(request, 'Order status updated successfully')
                return redirect('processing_dash')
            else:
                order = Order.objects.filter(id=pk)
                order.update(shipped=False)
                messages.success(request, 'Order status updated successfully')
                return redirect('shipped_dash')
            
        

        return render(request, 'payment/orders.html', {"order": order, "items": items})
        
    else:
        messages.error(request, 'Unauthorized access. Please login as a superuser.')
        return redirect('home')

def processing_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=False)

        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
			# Get the order
            order = Order.objects.filter(id=num)
			# grab Date and time
            now = datetime.datetime.now()
			# update order
            order.update(shipped=True, date_shipped=now)

            messages.success(request, 'Order status updated successfully')
            return redirect('processing_dash')

        return render(request, 'payment/processing_dash.html', {"orders": orders})
    else:
        messages.error(request, 'Unauthorized access. Please login as a superuser.')
        return redirect('home')

def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True)

        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
			# Get the order
            order = Order.objects.filter(id=num)
			# update order
            order.update(shipped=False)

            messages.success(request, 'Order status updated successfully')
            return redirect('shipped_dash')
        return render(request, 'payment/shipped_dash.html', {"orders": orders})
    else:
        messages.error(request, 'Unauthorized access. Please login as a superuser.')
        return redirect('home')

def process_order(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()
        # Get billing info from the last page
        payment_form = PaymentForm(request.POST or None)
        # Get shipping data
        shipping_data = request.session.get('shipping_data')
        
        # Get Order info
        full_name = shipping_data['shipping_fullname']
        email = shipping_data['shipping_email']

        # Get shipping address from session info
        shipping_address = f"{shipping_data['shipping_address1']}\n{shipping_data['shipping_address2']}\n{shipping_data['shipping_city']}\n{shipping_data['shipping_state']}\n{shipping_data['shipping_zipcode']}\n{shipping_data['shipping_country']}"
        amount_paid = totals

        # Create order
        if request.user.is_authenticated:
            # logged in
            user = request.user
            create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
            create_order.save()

            # Add order items
            order_id = create_order.pk
            # Get product information
            for product in cart_products():
                product_id = product.id
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price
                
                for key, value in quantities().items():
                    if int(key) == product_id:
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value, price=price)
                        create_order_item.save()

            clear_cart(request)
            # Delete Cart from db
            current_user = Profile.objects.filter(user__id=request.user.id)
            current_user.update(old_cart="")
            
                    
        else:
            # guest user
            create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
            create_order.save()

            # Add order items
            order_id = create_order.pk
            # Get product information
            for product in cart_products():
                product_id = product.id
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price
                
                for key, value in quantities().items():
                    if int(key) == product_id:
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value, price=price)
                        create_order_item.save()

            clear_cart(request)

            

        messages.success(request, "Your order has been placed!")
        return redirect('home')

    else:
        messages.error(request, "Access denied!")
        return redirect('home')


def billing_info(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()

        # Create a session with shipping info
        shipping_data = request.POST
        request.session['shipping_data'] = shipping_data 

        # Check to see if user is logged in
        if request.user.is_authenticated:
			# Get The Billing Form
            billing_form = PaymentForm()
            return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_info":shipping_data, "billing_info":billing_form})

        else:
			# Not logged in
			# Get The Billing Form
            billing_form = PaymentForm()
            return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_info":request.POST, "billing_info":billing_form})


		
        shipping_form = request.POST
        return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form})	
    else:
        messages.error(request, "Access denied!")
        return redirect('home')

def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()

    if request.user.is_authenticated:
        # Chech out as logged in user
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
        shipping_form = ShippingAddressForm(request.POST or None,instance=shipping_user)
        return render(request, 'payment/checkout.html', {"cart_products": cart_products, "quantities": quantities, "totals": totals, "shipping_form": shipping_form})
    else:
        # Chek out as guest user
        shipping_form = ShippingAddressForm(request.POST or None)
        return render(request, 'payment/checkout.html', {"cart_products": cart_products, "quantities": quantities, "totals": totals, "shipping_form": shipping_form})

def payment_success(request):
    return render(request, 'payment/payment_success.html', {})

