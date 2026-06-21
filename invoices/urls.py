from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, LineItemViewSet, ServiceViewSet, download_invoice_pdf, ClientViewSet
from .views import RegisterView, ProfileManageView
from invoices import views
 
router = DefaultRouter()


router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'line-items', LineItemViewSet, basename='lineitem')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'clients', ClientViewSet, basename='clients')


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileManageView.as_view(), name='profile'),
    path('', include(router.urls)),
    path('invoices/<int:pk>/download/', download_invoice_pdf, name='download-invoice-pdf'),
    path('', views.landing_page, name='landing-page'),
]