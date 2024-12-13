from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from cart.cart import Cart
from .forms import ShippingAddressForm, PaymentForm
from .models import ShippingAddress, Order, OrderItem
from store.models import Product, Profile, UserDigitalPurchase
from django.urls import reverse
from paypal.standard.forms import PayPalPaymentsForm
from django.conf import settings
from django.contrib.auth.decorators import login_required
import uuid
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
                 # Handle digital products
                if product.product_type == 'digital':
                    UserDigitalPurchase.objects.get_or_create(user=user, digital_product=product)

                else:
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

         # Get Order info
        full_name = shipping_data['shipping_fullname']
        email = shipping_data['shipping_email']

        # Get shipping address from session info
        shipping_address = f"{shipping_data['shipping_address1']}\n{shipping_data['shipping_address2']}\n{shipping_data['shipping_city']}\n{shipping_data['shipping_state']}\n{shipping_data['shipping_zipcode']}\n{shipping_data['shipping_country']}"
        amount_paid = totals

        host = request.get_host()
        # Create Invoice number 
        my_invoice = str(uuid.uuid4())

        # Create Order

        # Create Paypal form
        paypal_dict = {
            'business': settings.PAYPAL_RECEIVER_EMAIL,
            'amount': totals,
            'item_name': 'Shopping Cart',
            'no_shipping': '2',
            'invoice': my_invoice,
            'currency_code': 'HUF',
            'notify_url': 'https://{}{}'.format(host, reverse("paypal-ipn")),
            'return_url': 'https://{}{}'.format(host, reverse("payment_success")),
            'cancel_return': 'https://{}{}'.format(host, reverse("payment_failed")),
            
        }

        

        paypal_form = PayPalPaymentsForm(initial=paypal_dict)
        # Check to see if user is logged in
        if request.user.is_authenticated:
			# Get The Billing Form
            billing_form = PaymentForm()
            # logged in
            user = request.user
            create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid, invoice=my_invoice)
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

            
            # Delete Cart from db
            current_user = Profile.objects.filter(user__id=request.user.id)
            current_user.update(old_cart="")
            return render(request, "payment/billing_info.html", {"paypal_form":paypal_form, "cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_info":request.POST, "billing_info":billing_form})
                    
        else:
            billing_form = PayPalPaymentsForm(initial=paypal_dict)
            # guest user
            create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid, invoice=my_invoice)
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

            return render(request, "payment/billing_info.html", {"paypal_form":paypal_form, "cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_info":request.POST, "billing_info":billing_form})


		
        # shipping_form = request.POST
        # return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form})	
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

@login_required
def purchase_digital_product(request, pk):
    """
    Handle digital product purchases directly.
    """
    product = get_object_or_404(Product, pk=pk, product_type='digital')
    host = request.get_host()

    paypal_dict = {
        'business': 'your-paypal-email@example.com',
        'amount': product.price,
        'item_name': product.name,
        'currency_code': 'HUF',
        'notify_url': f'https://{host}{reverse("paypal-ipn")}',
        'return_url': f'https://{host}{reverse("payment_success")}?product_id={product.id}',
        'cancel_return': f'https://{host}{reverse("payment_failed")}',
    }

    form = PayPalPaymentsForm(initial=paypal_dict)
    return render(request, 'purchase_digital_product.html', {'product': product, 'form': form})

def payment_success(request):
    clear_cart(request)

    # Fetch the most recent order of the logged-in user
    if request.user.is_authenticated:
        order = Order.objects.filter(user=request.user).last()
        
        if order and hasattr(order, 'orderitem_set'):  # Check for associated items
            # Get the first product related to the order
            first_item = order.orderitem_set.first()

            if first_item and first_item.product.product_type == 'digital':
                product = first_item.product
                UserDigitalPurchase.objects.get_or_create(user=request.user, digital_product=product)
                stream_url = product.get_presigned_url()

                return render(request, 'payment/payment_success.html', {
                    'product': product,
                    'stream_url': stream_url
                })
        return render(request, 'payment/payment_success.html', {'order': order})
    else:
        # For guest users or fallback
        order = None
    return render(request, 'payment/payment_success.html', {'order': order})

def payment_failed(request):
    return render(request, 'payment/payment_failed.html', {})