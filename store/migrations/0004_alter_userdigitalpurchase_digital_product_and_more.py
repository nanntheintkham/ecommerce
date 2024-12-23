# Generated by Django 5.1.3 on 2024-12-15 23:51

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_remove_digitalproduct_stream_url_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userdigitalpurchase',
            name='digital_product',
            field=models.ForeignKey(limit_choices_to={'product_type': 'digital'}, on_delete=django.db.models.deletion.CASCADE, to='store.product'),
        ),
        migrations.RemoveField(
            model_name='product',
            name='image',
        ),
        migrations.RemoveField(
            model_name='product',
            name='is_sale',
        ),
        migrations.RemoveField(
            model_name='product',
            name='sale_price',
        ),
        migrations.AddField(
            model_name='product',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='dimensions',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='product_type',
            field=models.CharField(choices=[('physical', 'Physical Product'), ('digital', 'Digital Product')], default='physical', max_length=10),
        ),
        migrations.AddField(
            model_name='product',
            name='s3_object_key',
            field=models.CharField(blank=True, help_text='S3 object key for digital products', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='stock',
            field=models.PositiveIntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='thumbnail',
            field=models.ImageField(blank=True, null=True, upload_to='digital_product_thumbnails/'),
        ),
        migrations.AddField(
            model_name='product',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='weight',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.DeleteModel(
            name='DigitalProduct',
        ),
    ]
