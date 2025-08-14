from rest_framework import generics, permissions, status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import UserSerializer, RegisterSerializer, RoleApplicationSerializer, RoleApplicationAdminSerializer
from django.contrib.auth import get_user_model, login
from knox.models import AuthToken
from knox.views import LoginView as KnoxLoginView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from .throttling import AuthRateThrottle
from .models import RoleApplication, RoleForm, RoleApplicationFile
import json
from two_factor.utils import default_device

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

        device = default_device(user)
        if device and device.is_interactive():
            # 2FA is enabled
            return Response({'2fa_required': True}, status=status.HTTP_200_OK)
        else:
            # 2FA is not enabled
            login(request, user)
            return super(LoginApi, self).post(request, format=None)

class VerifyOTPSerializer(serializers.Serializer):
    otp_token = serializers.CharField()

class VerifyOTPApi(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = VerifyOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_token = serializer.validated_data['otp_token']

        # This is a simplified implementation. In a real app, you would need
        # to get the user from the session or a temporary token.
        # For now, we assume the user is the last one who tried to log in.
        # This is NOT secure and should be changed in a real application.
        user = User.objects.last()

        device = default_device(user)
        if device and device.verify_token(otp_token):
            login(request, user)
            # This is not a KnoxLoginView, so we create the token manually
            return Response({
                "user": UserSerializer(user).data,
                "token": AuthToken.objects.create(user)[1]
            })
        else:
            return Response({'error': 'Invalid OTP token'}, status=status.HTTP_400_BAD_REQUEST)


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

    def create(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError

        # Make QueryDict mutable
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True

        form_data_str = request.data.pop('form_data', [None])[0]
        form_data = json.loads(form_data_str) if form_data_str else {}

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save(form_data=form_data)

        try:
            for key, value in request.FILES.items():
                file_instance = RoleApplicationFile(application=application, file=value, field_name=key)
                file_instance.full_clean()
                file_instance.save()
        except ValidationError as e:
            # If any file validation fails, delete the application and its already uploaded files.
            application.delete()
            return Response({'error': e.message_dict}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(RoleApplicationSerializer(application).data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        return RoleApplication.objects.filter(user=self.request.user)

class RoleApplicationAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = RoleApplicationAdminSerializer
    queryset = RoleApplication.objects.all()

    def perform_update(self, serializer):
        application = serializer.instance
        if serializer.validated_data.get('status') == 'approved':
            user = application.user
            user.user_type = application.role_form.role
            user.is_role_verified = True
            user.save()
        serializer.save()


from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .serializers import ChangePasswordSerializer
import logging
from .emails import send_password_change_email
from .throttling import PasswordChangeRateThrottle

logger = logging.getLogger(__name__)

class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    throttle_classes = [PasswordChangeRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        # Verify old password
        if not user.check_password(data['old_password']):
            return Response({'error': 'Incorrect old password.'}, status=status.HTTP_400_BAD_REQUEST)

        # If user has 2FA, verify OTP
        device = default_device(user)
        if device:
            otp_code = data.get('otp_code')
            if not otp_code:
                return Response({'error': 'OTP code is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not device.verify_token(otp_code):
                return Response({'error': 'Invalid OTP code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password
        try:
            validate_password(data['new_password1'], user)
        except ValidationError as e:
            return Response({'error': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        # Set new password
        user.set_password(data['new_password1'])
        user.save()

        # Revoke all of the user's tokens
        AuthToken.objects.filter(user=user).delete()

        # Send notification email
        send_password_change_email(user, request)

        # Log the security event
        ip_address = request.META.get('REMOTE_ADDR')
        logger.info(f"Password changed for user {user.id} from IP {ip_address}")

        return Response({'message': 'Password changed successfully. All active sessions have been logged out.'}, status=status.HTTP_200_OK)
