from django.shortcuts import render, redirect
from .models import Product, Category, Profile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django import forms
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
from payment.forms import ShippingAddressForm
from payment.models import ShippingAddress
from cart.cart import Cart
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
    product = Product.objects.get(pk=pk)
    return render(request,'store/product.html', {'product': product})

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
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            #login user
            user = authenticate(username=username, password=password)
            login(request, user)
            # redirect to home page
            messages.success(request, f"Account created for {username} successfully. Please fill out your info below.")
            return redirect('update_info')
        else:
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, "There was an error registering your account")
            return redirect('register')
    return render(request, 'store/register.html', {'form': form})

