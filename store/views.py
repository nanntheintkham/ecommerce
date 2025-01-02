import re
from django.shortcuts import get_object_or_404, render, redirect
from .models import Product, Category, Profile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django import forms
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
from .models import UserDigitalPurchase
from payment.forms import ShippingAddressForm
from payment.models import ShippingAddress, Order, OrderItem
from cart.cart import Cart
from django.http import JsonResponse, StreamingHttpResponse
from django.core.signing import Signer, BadSignature
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponseForbidden
import boto3
from botocore.exceptions import ClientError
import time
import hashlib
import requests
import logging
import json

logger = logging.getLogger(__name__)

def search(request):
    #Determine if the form is filled
    if request.method == "POST":
        searched = request.POST['searched']

        # Query thr product DB model
        searched = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
        # Test for null
        if not searched:
            messages.error(request, 'No product found matching your search.')
            return redirect('search')
        else:
            return render(request, 'store/search.html', {'searched':searched})
    else:
        return render(request, 'store/search.html', {})

def update_info(request):
	if request.user.is_authenticated:
		# Get Current User
		current_user = Profile.objects.get(user__id=request.user.id)
		## Get Current User's Shipping Info
		shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
		
		# Get original User Form
		form = UserInfoForm(request.POST or None, instance=current_user)
		# Get User's Shipping Form
		shipping_form = ShippingAddressForm(request.POST or None, instance=shipping_user)		
		if form.is_valid() or shipping_form.is_valid():
			# Save original form
			form.save()
			# Save shipping form
			shipping_form.save()

			messages.success(request, "Your Info Has Been Updated!!")
			return redirect('home')
		return render(request, "store/update_info.html", {'form':form, 'shipping_form':shipping_form})
	else:
		messages.success(request, "You Must Be Logged In To Access That Page!!")
		return redirect('home')

def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user
        if request.method == 'POST':
            form = ChangePasswordForm(current_user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Password updated successfully! Please log in again")
                return redirect('login')
            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)
                    return redirect('update_password')
        else:
            form = ChangePasswordForm(current_user)
            return render(request, 'store/update_password.html', {'form': form})
    else:
        messages.error(request, "You must be logged in to update password")
        return redirect('home')
def update_user(request):
    if request.user.is_authenticated:
        current_users = User.objects.get(id=request.user.id)
        user_form = UpdateUserForm(request.POST or None,instance=current_users)

        if user_form.is_valid():
            user_form.save()
            login(request, current_users)
            messages.success(request, "User details updated successfully")
            return redirect('home')
        return render(request, 'store/update_user.html', {'user_form': user_form})
    else:
        messages.error(request, "You must be logged in to update profile details")
        return redirect('home')

    return render(request, 'store/update_user.html', {})

def category_summary(request):
	categories = Category.objects.all()
	return render(request, 'store/category_summary.html', {"categories":categories})	

def category(request, slug):
    try:
        category = Category.objects.get(slug=slug)
        products = Product.objects.filter(category=category)
        return render(request, 'store/category.html', {'products': products, 'category': category})
    except Category.DoesNotExist:
        messages.error(request, "That Category Doesn't Exist!")
        return redirect('home')

def product(request, pk):
    """
    Show product details based on type.
    """
    product = get_object_or_404(Product, pk=pk)

    if product.product_type == 'digital':
        # Check if user has purchased this digital product
        purchased = False
        if request.user.is_authenticated:
            purchased = UserDigitalPurchase.objects.filter(
            user=request.user, 
            digital_product=product
        ).exists()
    
        return render(request, 'store/digital_product_detail.html', {
            'product': product,
            'purchased': purchased
        })
    stock_range = range(1, product.stock + 1) if product.stock > 0 else []
        
    return render(request,'store/product.html', {'product': product, 'stock_range': stock_range})    
    
def generate_stream_id(user_id, product_id):
    """Generate a unique stream ID for rate limiting"""
    return hashlib.sha256(f"{user_id}:{product_id}:{int(time.time() // 300)}".encode()).hexdigest()

def get_secure_token(user_id, product_id, session_id, expires=30):
    """
    Generate a short-lived signed token for video access
    
    Args:
        user_id (int): The ID of the user requesting access
        product_id (int): The ID of the product being accessed
        session_id (str): Browser session ID for additional validation
        expires (int): Token expiration time in seconds (shortened to 30s)
    """
    signer = Signer()
    timestamp = int(time.time()) + expires
    # Include session ID and user agent hash in token
    token_data = f"{user_id}:{product_id}:{timestamp}:{session_id}"
    return signer.sign(token_data)

def verify_token(token, session_id):
    """
    Verify the streaming token with additional checks
    """
    signer = Signer()
    try:
        token_data = signer.unsign(token)
        user_id, product_id, timestamp, token_session_id = token_data.split(':')
        
        # Verify timestamp
        if int(time.time()) > int(timestamp):
            return None
            
        # Verify session ID matches
        if token_session_id != session_id:
            return None
            
        return {
            'user_id': int(user_id),
            'product_id': int(product_id)
        }
    except (BadSignature, ValueError):
        return None

logger = logging.getLogger(__name__)

@login_required
def view_digital_product(request, pk):
    """View a purchased digital product with enhanced security"""
    digital_product = get_object_or_404(Product, pk=pk, product_type='digital')
    
    # Check purchase
    purchase = get_object_or_404(
        UserDigitalPurchase,
        user=request.user, 
        digital_product=digital_product
    )

    # Handle AJAX requests for URL refresh
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Generate new token
            token = get_secure_token(
                request.user.id,
                digital_product.id,
                request.session.session_key if request.session.session_key else '',
                expires=30
            )
            stream_url = f'/stream/{digital_product.pk}?token={token}'
            return JsonResponse({'stream_url': stream_url})
        except Exception as e:
            logger.error(f"Error generating streaming token: {str(e)}")
            return JsonResponse({'error': 'Failed to generate streaming URL'}, status=500)

    # Regular page load
    # Ensure user has a session
    if not request.session.session_key:
        request.session.create()
    
    # Generate initial token
    token = get_secure_token(
        request.user.id,
        digital_product.id,
        request.session.session_key,
        expires=30
    )
    
    stream_url = f'/stream/{digital_product.pk}?token={token}'
    
    return render(request, 'store/view_digital_product.html', {
        'product': digital_product,
        'stream_url': stream_url
    })

@login_required
def stream_video(request, pk):
    """Secure video streaming endpoint with enhanced protection"""
    try:
        # Check referrer
        referer = request.META.get('HTTP_REFERER', '')
        if not referer or request.get_host() not in referer:
            return HttpResponseForbidden("Invalid request origin")
        
        # Verify token with session
        token = request.GET.get('token')
        if not token:
            return HttpResponseForbidden("Missing token")
        
        session_id = request.session.session_key or ''
        token_data = verify_token(token, session_id)
        if not token_data or token_data['user_id'] != request.user.id:
            return HttpResponseForbidden("Invalid token")
        
        # Verify purchase
        product = get_object_or_404(Product, pk=token_data['product_id'])
        purchase = get_object_or_404(
            UserDigitalPurchase, 
            user=request.user,
            digital_product=product
        )

        # Get S3 object
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        s3_object = s3_client.get_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=product.s3_object_key
        )
        
        # Support range requests for better video playback
        range_header = request.META.get('HTTP_RANGE', '').strip()
        content_length = s3_object['ContentLength']
        
        if range_header:
            range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else content_length - 1
                
                if start >= content_length:
                    return HttpResponse(status=416)  # Requested range not satisfiable
                
                # Get partial content
                s3_object = s3_client.get_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=product.s3_object_key,
                    Range=f'bytes={start}-{end}'
                )
                
                response = StreamingHttpResponse(
                    streaming_content=s3_object['Body'].iter_chunks(chunk_size=8192),
                    status=206,
                    content_type='video/mp4'
                )
                
                response['Content-Range'] = f'bytes {start}-{end}/{content_length}'
                response['Content-Length'] = end - start + 1
            else:
                return HttpResponse(status=400)  # Bad request
        else:
            response = StreamingHttpResponse(
                streaming_content=s3_object['Body'].iter_chunks(chunk_size=8192),
                content_type='video/mp4'
            )
            response['Content-Length'] = content_length
        
        # Security headers
        response['Content-Disposition'] = 'inline'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Accept-Ranges'] = 'bytes'  # Support range requests
        
        return response
        
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        return HttpResponse(status=500)

def home(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'store/home.html', {'products': products, 'categories': categories})

def about(request):
    return render(request, 'store/about.html')

def login_user(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Cart persistence on login
            current_user = Profile.objects.get(user__id=request.user.id)
            # Get the saved cart from db
            saved_cart = current_user.old_cart
            # Convert string to python dict
            if saved_cart:
                 # Convert to dict using JSON
                converted_cart = json.loads(saved_cart)
                 # Update the cart in the session
                cart = Cart(request)
                for key, value in converted_cart.items():
                    cart.db_add(product=key, quantity=value)
            messages.success(request, "You have been logged in successfully")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('login')
    return render(request, 'store/login.html', {})

def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out")
    return redirect('home')

def register_user(request):
    form = SignUpForm()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Check if user registered via social account
            try:
                social_account = SocialAccount.objects.get(user=user)
                # Additional processing for social login if needed
            except SocialAccount.DoesNotExist:
                pass
            
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, f"Account created for {username} successfully. Please fill out your info below.")
            return redirect('update_info')
        else:
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, "There was an error registering your account")
            return redirect('register')
    return render(request, 'store/register.html', {'form': form})

