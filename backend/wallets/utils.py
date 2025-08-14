from django.db import transaction
from .models import Wallet, Transaction
from django.contrib.auth import get_user_model

User = get_user_model()

def handle_commission(provider_wallet, total_amount, commission_rate):
    """
    Calculates the commission and transfers it to the GoLink platform wallet.
    """
    golink_user = User.objects.get(username='golink_platform')
    golink_wallet = Wallet.objects.get(user=golink_user)

    commission_amount = total_amount * commission_rate

    with transaction.atomic():
        provider_wallet.balance -= commission_amount
        provider_wallet.save()

        golink_wallet.balance += commission_amount
        golink_wallet.save()

        Transaction.objects.create(
            wallet=provider_wallet,
            transaction_type='commission',
            amount=-commission_amount,
            status='completed',
            description='Commission for service'
        )
        Transaction.objects.create(
            wallet=golink_wallet,
            transaction_type='commission',
            amount=commission_amount,
            status='completed',
            description=f'Commission from {provider_wallet.user.username}'
        )

    return commission_amount
