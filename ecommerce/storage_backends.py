# storage_backends.py

from storages.backends.s3boto3 import S3Boto3Storage

class ImageStorage(S3Boto3Storage):
    bucket_name = 'euphoria-media'
    custom_domain = f'{bucket_name}.s3.amazonaws.com'
