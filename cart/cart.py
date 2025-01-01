from store.models import Product, Profile
import logging

logger = logging.getLogger(__name__)

class Cart():
    def __init__(self, request):
        self.session = request.session
        # Get request
        self.request = request
        # Get the current session key if it exists
        cart = self.session.get('session_key')

        # If the user is new, no session key!  Create one!
        if 'session_key' not in request.session:
            cart = self.session['session_key'] = {}

        # Make sure cart is available on all pages of site
        self.cart = cart

    def check_stock(self, product, quantity):
        """
        Verify if the requested quantity is available in stock
        Returns tuple (bool, str) - (is_valid, error_message)
        """
        try:
            if product.product_type == 'physical':
                if product.stock < quantity:
                    return False, f"Only {product.stock} units available"
                if quantity <= 0:
                    return False, "Quantity must be greater than 0"
            return True, ""
        except Exception as e:
            logger.error(f"Error checking stock for product {product.id}: {e}")
            return False, "Error checking stock availability"

    def db_add(self, product, quantity):
        product_id = str(product)
        product_qty = str(quantity)
        
        # Get product instance to check stock
        try:
            product_instance = Product.objects.get(id=int(product_id))
            is_valid, error_message = self.check_stock(product_instance, int(product_qty))
            
            if not is_valid:
                raise ValueError(error_message)
                
            # Logic
            if product_id in self.cart:
                pass
            else:
                self.cart[product_id] = int(product_qty)

            self.session.modified = True
            
            # Deal with logged in user
            logged_in_cart(self)
            
        except Product.DoesNotExist:
            logger.error(f"Product {product_id} not found")
            raise ValueError("Product not found")

    def add(self, product, quantity):
        product_id = str(product.id)
        product_qty = int(quantity)  # Convert to int immediately for validation
        
        # Check stock before adding
        is_valid, error_message = self.check_stock(product, product_qty)
        if not is_valid:
            raise ValueError(error_message)
            
        # Logic
        if product_id in self.cart:
            # If product exists, validate total quantity
            new_quantity = self.cart[product_id] + product_qty
            is_valid, error_message = self.check_stock(product, new_quantity)
            if not is_valid:
                raise ValueError(error_message)
            self.cart[product_id] = new_quantity
        else:
            self.cart[product_id] = product_qty

        self.session.modified = True

        # Deal with logged in user
        logged_in_cart(self)

    def update(self, product, quantity):
        product_id = str(product.id)
        product_qty = int(quantity)
        
        # Check stock before updating
        is_valid, error_message = self.check_stock(product, product_qty)
        if not is_valid:
            raise ValueError(error_message)

        if product_id in self.cart:
            self.cart[product_id] = product_qty
        else:
            raise ValueError("Product not found in cart.")

        self.session.modified = True
        logged_in_cart(self)

        return self.cart

    def cart_total(self):
        # Get product IDS
        product_ids = self.cart.keys()
        # lookup those keys in our products database model
        products = Product.objects.filter(id__in=product_ids)
        # Get quantities
        quantities = self.cart

        total = 0        
        for key, value in quantities.items():
            # Convert key string into int
            key = int(key)
            for product in products:
                if product.id == key:
                    if product.is_sale:
                        total += (product.sale_price * value)
                    else:
                        total += (product.price * value)
        return total

    def __len__(self):
        return len(self.cart)

    def get_prods(self):
        # Get ids from cart
        product_ids = self.cart.keys()
        # Use ids to lookup products in database model
        products = Product.objects.filter(id__in=product_ids)
        return products

    def get_quants(self):
        quantities = self.cart
        return quantities

    def delete(self, product):
        product_id = str(product)
        # Delete from dictionary/cart
        if product_id in self.cart:
            del self.cart[product_id]

        self.session.modified = True
        logged_in_cart(self)

def logged_in_cart(self):
    if self.request.user.is_authenticated:
        try:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            carty = str(self.cart).replace("\'", "\"")
            current_user.update(old_cart=str(carty))
        except Exception as e:
            logger.error(f"Error saving cart to user profile: {e}")