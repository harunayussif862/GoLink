from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import ProductViewSet, ProductListView, CategoryListView, CartViewSet, CheckoutView, ProductReviewViewSet, SellerReviewViewSet, RefundRequestViewSet, AnalyticsView

app_name = 'ecommerce'

router = DefaultRouter()
router.register('products', ProductViewSet, basename='products')
router.register('cart', CartViewSet, basename='cart')
router.register('refunds', RefundRequestViewSet, basename='refunds')

products_router = routers.NestedSimpleRouter(router, r'products', lookup='product')
products_router.register(r'reviews', ProductReviewViewSet, basename='product-reviews')

# This is not ideal, as sellers are users. A better approach would be to have a separate endpoint for seller reviews.
# For now, I will create a separate router for seller reviews.
sellers_router = routers.DefaultRouter()
sellers_router.register(r'sellers/(?P<seller_pk>\d+)/reviews', SellerReviewViewSet, basename='seller-reviews')


urlpatterns = [
    path('api/ecommerce/', include(router.urls)),
    path('api/ecommerce/', include(products_router.urls)),
    path('api/ecommerce/', include(sellers_router.urls)),
    path('api/ecommerce/all-products/', ProductListView.as_view(), name='all_products'),
    path('api/ecommerce/categories/', CategoryListView.as_view(), name='categories'),
    path('api/ecommerce/checkout/', CheckoutView.as_view(), name='checkout'),
    path('api/ecommerce/analytics/', AnalyticsView.as_view(), name='analytics'),
]
