from django.shortcuts import render, get_object_or_404
from .cart import Cart
from store.models import Product
from django.http import JsonResponse
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


def cart_summary(request):
	# Get the cart
	cart = Cart(request)
	cart_products = cart.get_prods
	quantities = cart.get_quants
	totals = cart.cart_total()
	return render(request, "cart/cart_summary.html", {"cart_products": cart_products, "quantities": quantities, "totals": totals})

def cart_add(request):
	# Get the cart
	cart = Cart(request)
	# test for POST
	if request.POST.get('action') == 'post':
		# Get stuff
		product_id = int(request.POST.get('product_id'))
		product_qty = int(request.POST.get('product_qty'))

		# lookup product in DB
		product = get_object_or_404(Product, id=product_id)
		
		# Save to session
		cart.add(product=product, quantity=product_qty)

		# Get Cart Quantity
		cart_quantity = cart.__len__()

		# Return response
		response = JsonResponse({'qty': cart_quantity})
		messages.success(request, ("Product Added To Cart"))
		return response

def cart_delete(request):
	
	cart = Cart(request)
	if request.POST.get('action') == 'post':
		# Get stuff
		product_id = int(request.POST.get('product_id'))
		# Call delete Function in Cart
		cart.delete(product=product_id)

		response = JsonResponse({'product':product_id})
		#return redirect('cart_summary')
		messages.success(request, ("Item Deleted From Shopping Cart"))
		return response


def cart_update(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        try:
            product_id = int(request.POST.get('product_id'))
            product_qty = int(request.POST.get('product_qty'))
            logger.info(f"Updating cart: Product ID={product_id}, Quantity={product_qty}")

            product = get_object_or_404(Product, id=product_id)
            cart.update(product=product, quantity=product_qty)

            cart_quantity = cart.__len__()

            logger.info(f"Cart updated: Total Quantity={cart_quantity}")
            messages.success(request, "Your Cart Has Been Updated")
            return JsonResponse({'qty': cart_quantity, 'message': 'Cart updated successfully'})
        
        except Product.DoesNotExist:
            logger.error(f"Product with ID {product_id} does not exist.")
            return JsonResponse({'error': 'Product does not exist'}, status=400)
        except ValueError as e:
            logger.error(f"ValueError: {e}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            return JsonResponse({'error': str(e)}, status=400)
    else:
        logger.warning("Invalid request method for cart_update")
        return JsonResponse({'error': 'Invalid request'}, status=400)
