from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.conf import settings
import datetime
from django.utils import timezone
import boto3

PRODUCT_TYPE_CHOICES = [
    ('physical', 'Physical Product'),
    ('digital', 'Digital Product'),
]

# Create Customer Profile
class Profile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	date_modified = models.DateTimeField(User, auto_now=True)
	phone = models.CharField(max_length=20, blank=True)
	address1 = models.CharField(max_length=200, blank=True)
	address2 = models.CharField(max_length=200, blank=True)
	city = models.CharField(max_length=200, blank=True)
	state = models.CharField(max_length=200, blank=True)
	zipcode = models.CharField(max_length=200, blank=True)
	country = models.CharField(max_length=200, blank=True)
	old_cart = models.CharField(max_length=200, blank=True, null=True)

	def __str__(self):
		return self.user.username
     
# Create a user Profile by default when user signs up
def create_profile(sender, instance, created, **kwargs):
	if created:
		user_profile = Profile(user=instance)
		user_profile.save()

# Automate the profile thing
post_save.connect(create_profile, sender=User)

class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Categories'

#All of the products
# class Product(models.Model):
#     name = models.CharField(max_length=100)
#     price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
#     category = models.ForeignKey(Category, on_delete=models.CASCADE)
#     description = models.TextField()
#     image = models.ImageField(upload_to='upload/products', null=True, blank=True)
#     #Sale stuff
#     is_sale = models.BooleanField(default=False)
#     sale_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)

#     def __str__(self):
#         return self.name
    
# class DigitalProduct(models.Model):
#     """
#     Model for digital products that can be streamed
#     """
#     name = models.CharField(max_length=255)
#     description = models.TextField()
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='digital_products')
    
#     # Streaming-specific fields
#     # Add the S3 object key field
#     s3_object_key = models.CharField(max_length=255, help_text="S3 object key for the digital content")
#     thumbnail = models.ImageField(upload_to='digital_product_thumbnails/', null=True, blank=True)
    
#     # Metadata
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.name
    
#     def get_presigned_url(self, expiration=3600):
#         """
#         Generate a pre-signed URL for secure streaming.
#         """

#         s3_client = boto3.client(
#             's3',
#             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#             region_name=settings.AWS_S3_REGION_NAME,
#         )
#         return s3_client.generate_presigned_url(
#             'get_object',
#             Params={
#                 'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
#                 'Key': self.s3_object_key,
#             },
#             ExpiresIn=expiration
#         )

class Product(models.Model):
    """
    Unified model for physical and digital products.
    """
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='upload/products', null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES, default='physical')
    
    #Sale stuff
    is_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)

    # Digital-specific fields
    s3_object_key = models.CharField(max_length=255, blank=True, null=True, help_text="S3 object key for digital products")

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True,blank=True, null=True)

    def get_presigned_url(self, expiration=3600):
        """
        Generate pre-signed URL for secure streaming of digital products.
        """
        if self.product_type != 'digital':
            return None
        import boto3
        from django.conf import settings

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': self.s3_object_key},
            ExpiresIn=expiration
        )

    def __str__(self):
        return self.name

class UserDigitalPurchase(models.Model):
    """
    Tracks purchased digital products for users
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    digital_product = models.ForeignKey(Product, on_delete=models.CASCADE, limit_choices_to={'product_type': 'digital'})
    purchased_at = models.DateTimeField(auto_now_add=True)
    last_viewed = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'digital_product')
        verbose_name_plural = 'User Digital Purchases'

    def __str__(self):
        return f"{self.user.username} - {self.digital_product.name}"


#Customers
class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=10)
    email = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

#Customer Orders
class Order(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    quantty = models.IntegerField(default=1)
    address = models.CharField(max_length=200, default='', blank=True)
    phone = models.CharField(max_length=12, default='', blank=True)
    date = models.DateField(default=datetime.datetime.today)
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.product