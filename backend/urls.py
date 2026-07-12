from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from invoices.throttles import LoginRateThrottle

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('invoices.urls')),
    path('api/token/', TokenObtainPairView.as_view(throttle_classes=[LoginRateThrottle]), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(throttle_classes=[LoginRateThrottle]), name='token_refresh'),
]