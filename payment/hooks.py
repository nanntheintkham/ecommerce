import logging
from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received
from django.dispatch import receiver
from .models import Order

logger = logging.getLogger(__name__)

@receiver(valid_ipn_received)
def payment_notification(sender, **kwargs):
    try:
        # Get the PayPal IPN object
        paypal_obj = sender

        # Verify the transaction is completed
        if paypal_obj.payment_status == ST_PP_COMPLETED:
            # Get the invoice from the PayPal object
            my_invoice = str(paypal_obj.invoice)
            logger.info(f"Processing PayPal payment for invoice: {my_invoice}")

            # Match the invoice with the order
            my_order = Order.objects.get(invoice=my_invoice)

            # Update the order as paid
            my_order.paid = True
            my_order.save()
            logger.info(f"Order {my_order.id} marked as paid.")
        else:
            logger.warning(f"PayPal payment not completed. Status: {paypal_obj.payment_status}")

    except Order.DoesNotExist:
        logger.error(f"No order found with invoice: {paypal_obj.invoice}")
    except Exception as e:
        logger.error(f"Error processing PayPal payment: {e}")
