from django.urls import path
from .views import WalletView, TransactionListView, DepositView, WithdrawalView, TransferView, VerifyWalletOTPApi

app_name = 'wallets'

urlpatterns = [
    path('api/wallet/', WalletView.as_view(), name='wallet'),
    path('api/wallet/transactions/', TransactionListView.as_view(), name='transactions'),
    path('api/wallet/deposit/', DepositView.as_view(), name='deposit'),
    path('api/wallet/withdraw/', WithdrawalView.as_view(), name='withdraw'),
    path('api/wallet/transfer/', TransferView.as_view(), name='transfer'),
    path('api/wallet/verify-otp/', VerifyWalletOTPApi.as_view(), name='verify_otp'),
]
