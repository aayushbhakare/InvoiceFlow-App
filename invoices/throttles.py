from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'


class AIRateThrottle(UserRateThrottle):
    scope = 'ai'
