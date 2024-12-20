from django.http import JsonResponse
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
from django.views.decorators.csrf import csrf_exempt
import uuid
import datetime
import stripe
import logging
import json

stripe.api_key = settings.STRIPE_SECRET_KEY

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

logger = logging.getLogger(__name__)

def create_stripe_session(request):
    logger.info("Stripe checkout session started")
    if request.method == 'POST':
        try:
            # Initialize cart
            cart = Cart(request)
            cart_products = cart.get_prods
            totals = cart.cart_total()
            
            # Get shipping data from session
            shipping_data = request.session.get('shipping_data', {})
            
            # Create line items for Stripe
            line_items = []
            cart_items_data = []  # Store cart items for metadata
            
            for product in cart_products():
                price = product.sale_price if product.is_sale else product.price
                quantity = cart.get_quants().get(str(product.id), 0)
                
                # Add to line items for Stripe checkout
                line_items.append({
                    'price_data': {
                        'currency': 'huf',
                        'product_data': {
                            'name': product.name,
                            'description': getattr(product, 'description', None),  # Add description if available
                            'metadata': {
                                'product_id': product.id,
                                'product_type': getattr(product, 'product_type', 'physical')
                            }
                        },
                        'unit_amount': int(price * 100),  # Convert to cents
                    },
                    'quantity': quantity,
                })
                
                # Add to cart items data for metadata
                cart_items_data.append({
                    'product_id': str(product.id),
                    'quantity': quantity,
                    'price': float(price),
                    'product_type': getattr(product, 'product_type', 'physical')
                })

            # Create metadata with all necessary information
            metadata = {
                'order_id': str(uuid.uuid4()),
                'user_id': str(request.user.id) if request.user.is_authenticated else 'guest',
                'shipping_fullname': shipping_data.get('shipping_fullname', ''),
                'shipping_email': shipping_data.get('shipping_email', ''),
                'shipping_address1': shipping_data.get('shipping_address1', ''),
                'shipping_address2': shipping_data.get('shipping_address2', ''),
                'shipping_city': shipping_data.get('shipping_city', ''),
                'shipping_state': shipping_data.get('shipping_state', ''),
                'shipping_zipcode': shipping_data.get('shipping_zipcode', ''),
                'cart_items': json.dumps(cart_items_data),
                'total_amount': str(totals)
            }

            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri(reverse('payment_success')),
                cancel_url=request.build_absolute_uri(reverse('payment_failed')),
                metadata=metadata,
                customer_email=shipping_data.get('shipping_email'),  # Pre-fill customer email if available
                shipping_address_collection={
                    'allowed_countries': ['HU'],  # Adjust countries as needed
                },
                payment_intent_data={
                    'metadata': metadata,  # Include metadata in payment intent for webhook processing
                },
            )
            
            logger.info(f"Stripe session created successfully: {checkout_session.id}")
            return JsonResponse({
                'sessionId': checkout_session.id,
                'success': True
            })
            
        except stripe.error.StripeError as e:
            # Handle Stripe-specific errors
            logger.error(f"Stripe error: {str(e)}")
            return JsonResponse({
                'error': 'Payment service error. Please try again later.',
                'details': str(e)
            }, status=400)
            
        except Exception as e:
            # Handle any other unexpected errors
            logger.error(f"Unexpected error in create_stripe_session: {str(e)}")
            return JsonResponse({
                'error': 'An unexpected error occurred. Please try again later.',
                'details': str(e)
            }, status=500)
    
    # Handle non-POST requests
    return JsonResponse({
        'error': 'Invalid request method. Only POST requests are allowed.'
    }, status=405)

@csrf_exempt
def stripe_webhook(request):
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error("Invalid payload")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature")
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    logger.info(f"Stripe Event Received: {event}")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        logger.info(f"Stripe Checkout Session: {session}")
        handle_completed_checkout_session(session)

    return JsonResponse({'status': 'success'})


import logging
logger = logging.getLogger(__name__)

def handle_completed_checkout_session(session):
    """
    Handle the completed checkout session from Stripe webhook
    Creates order and order items in the database
    """
    logger.info("Starting to handle completed checkout session")
    
    try:
        # Get metadata from the session
        metadata = session.metadata
        if not metadata:
            raise ValueError("No metadata found in session")

        order_id = metadata.get('order_id')
        user_id = metadata.get('user_id')
        amount_total = session.amount_total  # Amount in cents
        
        # Get shipping details from metadata
        shipping_fullname = metadata.get('shipping_fullname')
        shipping_email = metadata.get('shipping_email')
        shipping_address = (
            f"{metadata.get('shipping_address1', '')}\n"
            f"{metadata.get('shipping_address2', '')}\n"
            f"{metadata.get('shipping_city', '')}\n"
            f"{metadata.get('shipping_state', '')}\n"
            f"{metadata.get('shipping_zipcode', '')}"
        ).strip()

        # Parse cart items from metadata
        try:
            cart_items = json.loads(metadata.get('cart_items', '[]'))
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding cart items: {e}")
            cart_items = []

        # Create order based on user type (authenticated or guest)
        if user_id and user_id != 'guest':
            try:
                user = User.objects.get(id=int(user_id))
                # Create order for authenticated user
                order = Order.objects.create(
                    user=user,
                    invoice=order_id,
                    full_name=shipping_fullname,
                    email=shipping_email,
                    shipping_address=shipping_address,
                    amount_paid=amount_total / 100,  # Convert cents to actual currency
                    paid=True,
                    shipped=False
                )
                
                # Create order items
                for item in cart_items:
                    try:
                        product = Product.objects.get(id=item['product_id'])
                        order_item = OrderItem.objects.create(
                            order=order,
                            product=product,
                            user=user,
                            quantity=item['quantity'],
                            price=item['price']
                        )
                        
                        # Handle digital products
                        if item.get('product_type') == 'digital' or getattr(product, 'product_type', '') == 'digital':
                            UserDigitalPurchase.objects.get_or_create(
                                user=user,
                                digital_product=product
                            )
                            
                        # Update product inventory if needed
                        if hasattr(product, 'quantity'):
                            new_quantity = product.quantity - item['quantity']
                            if new_quantity >= 0:
                                product.quantity = new_quantity
                                product.save()
                            else:
                                logger.warning(f"Insufficient inventory for product {product.id}")
                                
                    except Product.DoesNotExist:
                        logger.error(f"Product with ID {item['product_id']} not found")
                        continue
                    
                logger.info(f"Successfully created order {order.id} for user {user.id}")
                
            except User.DoesNotExist:
                logger.error(f"User with ID {user_id} does not exist")
                raise
                
        else:
            # Create order for guest user
            order = Order.objects.create(
                invoice=order_id,
                full_name=shipping_fullname,
                email=shipping_email,
                shipping_address=shipping_address,
                amount_paid=amount_total / 100,  # Convert cents to actual currency
                payment_method='stripe',
                payment_status='completed',
                shipped=False
            )
            
            # Create order items for guest
            for item in cart_items:
                try:
                    product = Product.objects.get(id=item['product_id'])
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item['quantity'],
                        price=item['price']
                    )
                    
                    # Update product inventory if needed
                    if hasattr(product, 'quantity'):
                        new_quantity = product.quantity - item['quantity']
                        if new_quantity >= 0:
                            product.quantity = new_quantity
                            product.save()
                        else:
                            logger.warning(f"Insufficient inventory for product {product.id}")
                            
                except Product.DoesNotExist:
                    logger.error(f"Product with ID {item['product_id']} not found")
                    continue
            
            logger.info(f"Successfully created guest order {order.id}")

        # # Send order confirmation email
        # try:
        #     send_order_confirmation_email(order)
        # except Exception as e:
        #     logger.error(f"Failed to send order confirmation email: {e}")

        return order

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in handle_completed_checkout_session: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in handle_completed_checkout_session: {e}")
        raise


def billing_info(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()

        # Create a session with shipping info
        shipping_data = request.POST
        request.session['shipping_data'] = shipping_data 

        host = request.get_host()
        my_invoice = str(uuid.uuid4())

        # PayPal configuration
        paypal_dict = {
            'business': settings.PAYPAL_RECEIVER_EMAIL,
            'amount': totals,
            'item_name': 'Shopping Cart',
            'invoice': my_invoice,
            'currency_code': 'HUF',
            'notify_url': f'https://{host}{reverse("paypal-ipn")}',
            'return_url': f'https://{host}{reverse("payment_success")}',
            'cancel_return': f'https://{host}{reverse("payment_failed")}',
        }

        paypal_form = PayPalPaymentsForm(initial=paypal_dict)

        # Prepare Stripe data
        stripe_data = {
            'publishable_key': settings.STRIPE_PUBLIC_KEY,
            'total_amount': int(totals * 100),  # Convert to cents
            'currency': 'huf',
        }

        context = {
            'paypal_form': paypal_form,
            'cart_products': cart_products,
            'quantities': quantities,
            'totals': totals,
            'shipping_info': request.POST,
            'stripe_data': stripe_data,
        }

        return render(request, "payment/billing_info.html", context)

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

    digital_products_with_urls = []

    if request.user.is_authenticated:
        order = Order.objects.filter(user=request.user).last()
        
        if order and hasattr(order, 'orderitem_set'):
            for item in order.orderitem_set.all():
                if item.product.product_type == 'digital':
                    UserDigitalPurchase.objects.get_or_create(user=request.user, digital_product=item.product)
                    
                    stream_url = item.product.get_presigned_url() if hasattr(item.product, 'get_presigned_url') else None
                    digital_products_with_urls.append({
                        'product': item.product,
                        'stream_url': stream_url
                    })

    context = {
        'order': order if request.user.is_authenticated else None,
        'digital_products_with_urls': digital_products_with_urls,
    }

    return render(request, 'payment/payment_success.html', context)


def payment_failed(request):
    return render(request, 'payment/payment_failed.html', {})