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
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
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
        print(items)

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

@login_required
def order_dashboard(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.all()
    elif request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user)
    else:
        messages.error(request, 'Unauthorized access. Please login to view the order history and details.')
        return redirect('home')

    # Apply filters
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if status:
        if status == 'processing':
            orders = orders.filter(shipped=False)
        elif status == 'shipped':
            orders = orders.filter(shipped=True)

    if start_date:
        orders = orders.filter(date_ordered__gte=start_date)

    if end_date:
        orders = orders.filter(date_ordered__lte=end_date)
    
    orders = orders.order_by('-date_ordered')

    return render(request, 'payment/order_dashboard.html', {
        'orders': orders,
        'is_admin': request.user.is_superuser
    })


@staff_member_required
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status == 'shipped':
            order.shipped = True
        elif new_status == 'processing':
            order.shipped = False
        order.save()
        messages.success(request, f'Order #{order.id} status updated to {new_status}.')
    return redirect('order_dashboard')

def validate_stock(cart):
    """
    Validates if all items in cart have sufficient stock.
    Returns (bool, list of tuples with insufficient stock items)
    """
    insufficient_stock = []
    has_sufficient_stock = True
    
    for product in cart.get_prods():
        quantity = cart.get_quants().get(str(product.id), 0)
        if product.stock < quantity:
            insufficient_stock.append((product.name, product.stock))
            has_sufficient_stock = False
            
    return has_sufficient_stock, insufficient_stock

def create_stripe_session(request):
    logger.info("Stripe checkout session started")
    if request.method == 'POST':
        try:
            # Initialize cart
            cart = Cart(request)
            # Validate stock before proceeding
            has_stock, insufficient_items = validate_stock(cart)
            if not has_stock:
                return JsonResponse({
                    'error': 'Some items are out of stock',
                    'insufficient_items': insufficient_items
                }, status=400)
            
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

logger = logging.getLogger(__name__)

def handle_completed_checkout_session(session):
    """
    Handle the completed checkout session from Stripe webhook
    Creates order and order items in the database
    """
    logger.info("Starting to handle completed checkout session")
    
    try:
        with transaction.atomic():
            # Get metadata from the session
            metadata = session.metadata
            if not metadata:
                raise ValueError("No metadata found in session")

            order_id = metadata.get('order_id')
            user_id = metadata.get('user_id')
            amount_total = session.amount_total  # Amount in cents

            # Parse cart items from metadata
            try:
                cart_items = json.loads(metadata.get('cart_items', '[]'))
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding cart items: {e}")
                cart_items = []

            order = Order.objects.filter(invoice=order_id).first()
            if order:
                order.paid = True
                order.amount_paid = session.amount_total / 100  # Convert from cents
                order.save()
                logger.info(f"Order {order_id} marked as paid.")

                # Update stock for each product
                for item in cart_items:
                    product_id = item.get('product_id')
                    quantity = item.get('quantity')

                    # Fetch product and update stock
                    product = Product.objects.get(id=product_id)
                    logger.info(f"Product {product.name} (ID: {product.id}) stock before update: {product.stock}")
                    if product.product_type == 'physical':
                        product.stock -= quantity
                        product.save()
                        logger.info(f"Updated stock for product {product.name} (ID: {product_id}). New stock: {product.stock}")
            else:
                logger.error(f"Order {order_id} not found.")

            return order

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in handle_completed_checkout_session: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in handle_completed_checkout_session: {e}")
        raise

def send_order_confirmation_email(order):
    """
    Send order confirmation email to customer
    """
    try:
        subject = f'Order Confirmation - Order #{order.invoice}'
        message = f"""
        Thank you for your order!
        
        Order Details:
        Order Number: {order.invoice}
        Total Amount: {order.amount_paid} HUF
        
        Shipping Address:
        {order.shipping_address}
        
        We will process your order soon.
        """
        
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [order.email]
        
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        
        logger.info(f"Order confirmation email sent for order {order.invoice}")
        
    except Exception as e:
        logger.error(f"Failed to send order confirmation email: {e}")
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

        # Create the order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            invoice=my_invoice,
            full_name=shipping_data.get('shipping_fullname'),
            email=shipping_data.get('shipping_email'),
            shipping_address=f"{shipping_data.get('shipping_address1')}, {shipping_data.get('shipping_city')}",
            amount_paid=totals,
            paid=False,  # Mark as unpaid initially
        )

        # Create order items
        for product in cart.get_prods():
            OrderItem.objects.create(
                order=order,
                product=product,
                user=request.user if request.user.is_authenticated else None,
                quantity=cart.get_quants().get(str(product.id), 0),
                price=product.sale_price if product.is_sale else product.price,
            )

        # PayPal configuration
        paypal_dict = {
            'business': settings.PAYPAL_RECEIVER_EMAIL,
            'amount': totals,
            'item_name': 'Shopping Cart',
            'invoice': my_invoice,
            'currency_code': 'HUF',
            'notify_url': f'https://{host}{reverse("paypal-ipn")}',
            'return_url': f'https://{host}{reverse("payment_success")}?inovoice={my_invoice}',
            'cancel_return': f'https://{host}{reverse("payment_failed")}',
        }

        paypal_form = PayPalPaymentsForm(initial=paypal_dict)

        # Prepare Stripe data
        stripe_data = {
            'publishable_key': settings.STRIPE_PUBLIC_KEY,
            'total_amount': int(totals * 100),  # Convert to cents
            'currency': 'huf',
            'invoice': my_invoice,
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

@csrf_exempt
def paypal_ipn(request):
    from paypal.standard.ipn.models import PayPalIPN

    ipn = PayPalIPN(request.POST)

    if ipn.verify():
        invoice_id = ipn.invoice
        order = Order.objects.filter(invoice=invoice_id).first()
        if order:
            order.paid = True
            order.save()
            logger.info(f"Order {invoice_id} marked as paid.")

            # Update stock for order items
            for item in order.orderitem_set.all():
                product = item.product
                if product.product_type == 'physical' and product.stock >= item.quantity:
                    product.stock -= item.quantity
                    product.save()
                    logger.info(f"Updated stock for product {product.name} (ID: {product.id}). New stock: {product.stock}")
                else:
                    logger.error(f"Insufficient stock for product {product.name} (ID: {product.id}).")
        else:
            logger.error(f"No order found for invoice: {invoice_id}")
    return JsonResponse({'status': 'OK'})

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
    # Clear cart after successful payment
    clear_cart(request)

    # Fetch the last authenticated user's order or handle guest logic
    order = None
    if request.user.is_authenticated:
        order = Order.objects.filter(user=request.user).last()
    else:
        invoice_id = request.GET.get('invoice')
        if invoice_id:
            order = Order.objects.filter(invoice=invoice_id).first()

    # Handle digital products
    digital_products_with_urls = []
    if order and order.orderitem_set.exists():
        for item in order.orderitem_set.all():
            if item.product.product_type == 'digital':
                UserDigitalPurchase.objects.get_or_create(user=request.user, digital_product=item.product)
                stream_url = item.product.get_presigned_url() if hasattr(item.product, 'get_presigned_url') else None
                digital_products_with_urls.append({
                    'product': item.product,
                    'stream_url': stream_url
                })
            else:
                product = Product.objects.get(id=item.product.id)
                logger.info(f"Updating stock for product: {product.name} (Current Stock: {product.stock})")
                product.stock -= item.quantity
                product.save()
                logger.info(f"New stock for product: {product.name} is {product.stock}")

    # Pass order details to the template
    context = {
        'order': order,
        'digital_products_with_urls': digital_products_with_urls,
    }

    return render(request, 'payment/payment_success.html', context)



def payment_failed(request):
    return render(request, 'payment/payment_failed.html', {})
