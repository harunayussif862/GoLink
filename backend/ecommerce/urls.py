from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ProductListView, CategoryListView

app_name = 'ecommerce'

router = DefaultRouter()
router.register('products', ProductViewSet, basename='products')

urlpatterns = [
    path('api/ecommerce/', include(router.urls)),
    path('api/ecommerce/all-products/', ProductListView.as_view(), name='all_products'),
    path('api/ecommerce/categories/', CategoryListView.as_view(), name='categories'),
]
