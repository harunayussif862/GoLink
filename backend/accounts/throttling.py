from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class AuthRateThrottle(AnonRateThrottle):
    scope = 'auth'

class PasswordChangeRateThrottle(UserRateThrottle):
    scope = 'password_change'
