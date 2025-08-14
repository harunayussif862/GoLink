from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db import transaction
from .models import Wallet, Transaction, WalletTransactionOTP
from .serializers import WalletSerializer, TransactionSerializer, DepositSerializer, WithdrawalSerializer, TransferSerializer, VerifyWalletOTPSerializer
from two_factor.utils import default_device
import uuid

class WalletView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WalletSerializer

    def get_object(self):
        return Wallet.objects.get(user=self.request.user)

class TransactionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        wallet = Wallet.objects.get(user=self.request.user)
        return Transaction.objects.filter(wallet=wallet).order_by('-timestamp')

class DepositView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DepositSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        wallet = Wallet.objects.get(user=request.user)
        wallet.balance += amount
        wallet.save()

        Transaction.objects.create(
            wallet=wallet,
            transaction_type='deposit',
            amount=amount,
            status='completed'
        )
        return Response({'message': 'Deposit successful'}, status=status.HTTP_200_OK)

class WithdrawalView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawalSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.get(user=request.user)
        device = default_device(request.user)

        if not device:
            return Response({'error': '2FA is not enabled for your account.'}, status=status.HTTP_400_BAD_REQUEST)

        otp_request = WalletTransactionOTP.objects.create(
            wallet=wallet,
            transaction_type='withdrawal',
            transaction_details=serializer.validated_data
        )
        return Response({
            'otp_required': True,
            'otp_transaction_id': otp_request.id
        }, status=status.HTTP_200_OK)

class TransferView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sender_wallet = Wallet.objects.get(user=request.user)
        device = default_device(request.user)

        if not device:
            return Response({'error': '2FA is not enabled for your account.'}, status=status.HTTP_400_BAD_REQUEST)

        # Pre-validate recipient and balance before creating OTP request
        recipient_wallet_id = serializer.validated_data['recipient_wallet_id']
        amount = serializer.validated_data['amount']
        try:
            recipient_wallet = Wallet.objects.get(wallet_id=recipient_wallet_id)
        except Wallet.DoesNotExist:
            return Response({'error': 'Recipient wallet not found'}, status=status.HTTP_404_NOT_FOUND)
        if sender_wallet == recipient_wallet:
            return Response({'error': 'Cannot transfer to the same wallet'}, status=status.HTTP_400_BAD_REQUEST)
        if sender_wallet.balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        otp_request = WalletTransactionOTP.objects.create(
            wallet=sender_wallet,
            transaction_type='transfer',
            transaction_details=serializer.validated_data
        )
        return Response({
            'otp_required': True,
            'otp_transaction_id': otp_request.id
        }, status=status.HTTP_200_OK)

class VerifyWalletOTPApi(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VerifyWalletOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp_transaction_id = serializer.validated_data['otp_transaction_id']
        otp_code = serializer.validated_data['otp_code']

        try:
            otp_request = WalletTransactionOTP.objects.get(id=otp_transaction_id, wallet__user=request.user)
        except WalletTransactionOTP.DoesNotExist:
            return Response({'error': 'Invalid OTP transaction ID.'}, status=status.HTTP_404_NOT_FOUND)

        device = default_device(request.user)
        if not device or not device.verify_token(otp_code):
            # Consider adding attempt tracking to prevent brute-force attacks
            return Response({'error': 'Invalid OTP code.'}, status=status.HTTP_400_BAD_REQUEST)

        # If OTP is valid, execute the transaction
        if otp_request.transaction_type == 'transfer':
            amount = otp_request.transaction_details['amount']
            recipient_wallet_id = otp_request.transaction_details['recipient_wallet_id']
            sender_wallet = otp_request.wallet

            # Re-verify recipient and balance in case something changed
            try:
                recipient_wallet = Wallet.objects.get(wallet_id=recipient_wallet_id)
            except Wallet.DoesNotExist:
                otp_request.delete()
                return Response({'error': 'Recipient wallet not found'}, status=status.HTTP_404_NOT_FOUND)
            if sender_wallet.balance < amount:
                otp_request.delete()
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                sender_wallet.balance -= amount
                sender_wallet.save()
                recipient_wallet.balance += amount
                recipient_wallet.save()
                Transaction.objects.create(
                    wallet=sender_wallet,
                    transaction_type='transfer',
                    amount=-amount,
                    status='completed',
                    description=f'Transfer to {recipient_wallet.user.username}'
                )
                Transaction.objects.create(
                    wallet=recipient_wallet,
                    transaction_type='transfer',
                    amount=amount,
                    status='completed',
                    description=f'Transfer from {sender_wallet.user.username}'
                )
            otp_request.delete()
            return Response({'message': 'Transfer successful'}, status=status.HTTP_200_OK)

        elif otp_request.transaction_type == 'withdrawal':
            amount = otp_request.transaction_details['amount']
            wallet = otp_request.wallet

            if wallet.balance < amount:
                otp_request.delete()
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

            Transaction.objects.create(
                wallet=wallet,
                transaction_type='withdrawal',
                amount=amount,
                status='pending' # Or 'completed' if withdrawal is instant
            )
            otp_request.delete()
            return Response({'message': 'Withdrawal successful'}, status=status.HTTP_200_OK)

        otp_request.delete()
        return Response({'error': 'Invalid transaction type.'}, status=status.HTTP_400_BAD_REQUEST)
