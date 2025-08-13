from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from .serializers import UserSerializer, RegisterSerializer, RoleApplicationSerializer, RoleApplicationAdminSerializer
from django.contrib.auth import get_user_model, login
from knox.models import AuthToken
from knox.views import LoginView as KnoxLoginView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from .throttling import AuthRateThrottle
from .models import RoleApplication

User = get_user_model()

# Register API
class RegisterApi(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args,  **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        })

# Login API
class LoginApi(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [AuthRateThrottle]

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginApi, self).post(request, format=None)


# Get User API
class UserApi(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

# Role Application API
class RoleApplicationView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoleApplicationSerializer

    def get_queryset(self):
        return RoleApplication.objects.filter(user=self.request.user)

class RoleApplicationAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = RoleApplicationAdminSerializer
    queryset = RoleApplication.objects.all()

    def perform_update(self, serializer):
        application = serializer.instance
        if serializer.validated_data['status'] == 'approved':
            user = application.user
            user.user_type = application.role
            user.is_role_verified = True
            user.save()
        serializer.save()
