from rest_framework import serializers
from .models import Wallet, Transaction

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('wallet_id', 'balance')

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'transaction_type', 'amount', 'status', 'timestamp', 'description')

class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

class TransferSerializer(serializers.Serializer):
    recipient_wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

class VerifyWalletOTPSerializer(serializers.Serializer):
    otp_transaction_id = serializers.UUIDField()
    otp_code = serializers.CharField(min_length=6, max_length=6)
