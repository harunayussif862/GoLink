from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction, models
from rest_framework.exceptions import PermissionDenied
from .models import Product, Category, Cart, CartItem, Order, OrderItem, ProductReview, SellerReview, RefundRequest
from .serializers import ProductSerializer, CategorySerializer, CartSerializer, CartItemSerializer, CheckoutSerializer, ProductReviewSerializer, SellerReviewSerializer, RefundRequestSerializer
from .permissions import IsSeller
from wallets.models import Wallet
from wallets.utils import handle_commission
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.validated_data['product']
            quantity = serializer.validated_data['quantity']
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            if not created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()
            return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def update_item(self, request, pk=None):
        try:
            cart_item = CartItem.objects.get(pk=pk, cart__user=request.user)
        except CartItem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = CartItemSerializer(cart_item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            cart = Cart.objects.get(user=request.user)
            return Response(CartSerializer(cart).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_item(self, request, pk=None):
        try:
            cart_item = CartItem.objects.get(pk=pk, cart__user=request.user)
        except CartItem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CheckoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CheckoutSerializer

    def post(self, request, *args, **kwargs):
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        total_price = sum(item.product.price * item.quantity for item in cart.items.all())

        buyer_wallet = Wallet.objects.get(user=request.user)
        if buyer_wallet.balance < total_price:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Deduct from buyer's wallet
            buyer_wallet.balance -= total_price
            buyer_wallet.save()

            # Create Order
            order = Order.objects.create(user=request.user, total_price=total_price)

            # Group items by seller
            items_by_seller = {}
            for item in cart.items.all():
                if item.product.seller not in items_by_seller:
                    items_by_seller[item.product.seller] = []
                items_by_seller[item.product.seller].append(item)

            # Process payment and commission for each seller
            for seller, items in items_by_seller.items():
                seller_total = sum(item.product.price * item.quantity for item in items)

                # Transfer to seller's wallet
                seller_wallet = Wallet.objects.get(user=seller)
                seller_wallet.balance += seller_total
                seller_wallet.save()

                # Handle commission
                commission_rate = Decimal('0.10') # 10% commission, should be configurable later
                handle_commission(seller_wallet, seller_total, commission_rate)

                # Create OrderItems
                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )

            # Clear the cart
            cart.items.all().delete()

        return Response({'message': 'Checkout successful'}, status=status.HTTP_200_OK)

class ProductReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProductReview.objects.filter(product_id=self.kwargs['product_pk'])

    def perform_create(self, serializer):
        product = Product.objects.get(pk=self.kwargs['product_pk'])
        serializer.save(user=self.request.user, product=product)

class SellerReviewViewSet(viewsets.ModelViewSet):
    serializer_class = SellerReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SellerReview.objects.filter(seller_id=self.kwargs['seller_pk'])

    def perform_create(self, serializer):
        seller = User.objects.get(pk=self.kwargs['seller_pk'])
        serializer.save(user=self.request.user, seller=seller)

class RefundRequestViewSet(viewsets.ModelViewSet):
    serializer_class = RefundRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.user_type == 'seller':
            return RefundRequest.objects.all()
        return RefundRequest.objects.filter(order__user=self.request.user)

    def perform_create(self, serializer):
        order = serializer.validated_data['order']
        if order.user != self.request.user:
            raise PermissionDenied("You cannot request a refund for an order that is not yours.")
        serializer.save()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if not (request.user.is_staff or request.user.user_type == 'seller'):
            raise PermissionDenied("You do not have permission to approve refunds.")

        refund_request = self.get_object()
        if refund_request.status != 'pending':
            return Response({'error': 'Refund request has already been processed'}, status=status.HTTP_400_BAD_REQUEST)

        order = refund_request.order
        buyer_wallet = Wallet.objects.get(user=order.user)

        with transaction.atomic():
            # For simplicity, we assume the full order amount is refunded to the buyer.
            # A more complex implementation would handle partial refunds and commission reversals.
            buyer_wallet.balance += order.total_price
            buyer_wallet.save()

            # Mark refund request as approved
            refund_request.status = 'approved'
            refund_request.save()

            # Update order status
            order.status = 'cancelled' # Or 'refunded'
            order.save()

        return Response({'message': 'Refund approved'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if not (request.user.is_staff or request.user.user_type == 'seller'):
            raise PermissionDenied("You do not have permission to reject refunds.")

        refund_request = self.get_object()
        if refund_request.status != 'pending':
            return Response({'error': 'Refund request has already been processed'}, status=status.HTTP_400_BAD_REQUEST)

        refund_request.status = 'rejected'
        refund_request.save()

        return Response({'message': 'Refund rejected'}, status=status.HTTP_200_OK)

class AnalyticsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_staff:
            # Admin analytics
            total_sales = Order.objects.aggregate(total=models.Sum('total_price'))['total'] or 0
            total_orders = Order.objects.count()
            top_products = Product.objects.annotate(total_quantity=models.Sum('orderitem__quantity')).order_by('-total_quantity')[:5]
        elif user.user_type == 'seller':
            # Seller analytics
            total_sales = Order.objects.filter(items__product__seller=user).aggregate(total=models.Sum('total_price'))['total'] or 0
            total_orders = Order.objects.filter(items__product__seller=user).distinct().count()
            top_products = Product.objects.filter(seller=user).annotate(total_quantity=models.Sum('orderitem__quantity')).order_by('-total_quantity')[:5]
        else:
            return Response({'error': 'You do not have permission to view analytics.'}, status=status.HTTP_403_FORBIDDEN)

        data = {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'top_products': ProductSerializer(top_products, many=True).data
        }
        return Response(data)
