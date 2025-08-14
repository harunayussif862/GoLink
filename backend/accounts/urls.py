from django.urls import path, include
from .views import RegisterApi, UserApi, LoginApi, RoleApplicationView, RoleApplicationAdminViewSet, VerifyOTPApi, ChangePasswordView
from knox import views as knox_views
from rest_framework.routers import DefaultRouter

app_name = 'accounts'

router = DefaultRouter()
router.register('api/admin/roles', RoleApplicationAdminViewSet, basename='admin_roles')

urlpatterns = [
    path('api/auth/register', RegisterApi.as_view(), name='register'),
    path('api/auth/login', LoginApi.as_view(), name='knox_login'),
    path('api/auth/verify-otp', VerifyOTPApi.as_view(), name='verify_otp'),
    path('api/auth/user', UserApi.as_view(), name='user'),
    path('api/auth/logout', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('api/auth/logoutall', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('api/auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('api/role/apply', RoleApplicationView.as_view(), name='role_apply'),
    path('', include(router.urls)),
]
