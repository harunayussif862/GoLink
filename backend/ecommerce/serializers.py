from rest_framework import serializers
from .models import Product, Category, ProductImage, Cart, CartItem, ProductReview, SellerReview, RefundRequest
from django.contrib.auth import get_user_model

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'is_default')

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'title', 'description', 'price', 'discount_price',
            'stock_quantity', 'sku', 'tags', 'is_featured', 'is_active',
            'category', 'images'
        )

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_id', 'quantity')

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'items', 'total_price')

    def get_total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())

class CheckoutSerializer(serializers.Serializer):
    pass

class ProductReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductReview
        fields = ('id', 'product', 'rating', 'review', 'created_at')
        read_only_fields = ('user', 'product')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class AnalyticsSerializer(serializers.Serializer):
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    top_products = ProductSerializer(many=True)

class RefundRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundRequest
        fields = ('id', 'order', 'reason', 'status', 'created_at')
        read_only_fields = ('status',)

class SellerReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = SellerReview
        fields = ('id', 'seller', 'rating', 'review', 'created_at')
        read_only_fields = ('user', 'seller')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
