from django.contrib import admin
from django.urls import path, include
from . import settings
from django.conf.urls.static import static
from storages.backends.s3boto3 import S3Boto3Storage

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('accounts/', include('allauth.urls')),
    path('cart/', include('cart.urls')),
    path('payment/', include('payment.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    bucket = settings.AWS_MEDIA_BUCKET_NAME
    urlpatterns += static(settings.MEDIA_URL, document_root=S3Boto3Storage())