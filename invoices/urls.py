from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, LineItemViewSet, ServicesViewSet
 
#DefaultRouter automatically generates URL patterns for our viewsets and we need to 
#register each viewset with the router. The first argument is the URL prefix, 
#and the second is the viewset class.
router = DefaultRouter()

router.register(r'invoices', InvoiceViewSet)
router.register(r'line-items', LineItemViewSet)
router.register(r'services', ServicesViewSet)


urlpatterns = [
    path('', include(router.urls)),
]