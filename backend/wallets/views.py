from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db import transaction
from .models import Wallet, Transaction
from .serializers import WalletSerializer, TransactionSerializer, DepositSerializer, WithdrawalSerializer, TransferSerializer

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
        amount = serializer.validated_data['amount']

        wallet = Wallet.objects.get(user=request.user)
        if wallet.balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        Transaction.objects.create(
            wallet=wallet,
            transaction_type='withdrawal',
            amount=amount,
            status='pending'
        )
        return Response({'message': 'Withdrawal request submitted'}, status=status.HTTP_200_OK)

class TransferView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']
        recipient_wallet_id = serializer.validated_data['recipient_wallet_id']

        sender_wallet = Wallet.objects.get(user=request.user)

        try:
            recipient_wallet = Wallet.objects.get(wallet_id=recipient_wallet_id)
        except Wallet.DoesNotExist:
            return Response({'error': 'Recipient wallet not found'}, status=status.HTTP_404_NOT_FOUND)

        if sender_wallet == recipient_wallet:
            return Response({'error': 'Cannot transfer to the same wallet'}, status=status.HTTP_400_BAD_REQUEST)

        if sender_wallet.balance < amount:
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

        return Response({'message': 'Transfer successful'}, status=status.HTTP_200_OK)
