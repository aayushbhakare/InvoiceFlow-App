from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InvoiceViewSet, LineItemViewSet, ServiceViewSet, 
    download_invoice_pdf, ClientViewSet, RegisterView, ProfileManageView,RecurringInvoiceViewSet,
    create_razorpay_order, verify_razorpay_payment, razorpay_webhook, ai_chat_endpoint
)
from .views import RegisterView, ProfileManageView
from invoices import views
 
router = DefaultRouter()


router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'line-items', LineItemViewSet, basename='lineitem')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'clients', ClientViewSet, basename='clients')
router.register(r'recurring-invoices', RecurringInvoiceViewSet, basename='recurring-invoice')


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileManageView.as_view(), name='profile'),
    path('chat/', ai_chat_endpoint, name='ai-chat'),
    path('', include(router.urls)),
    path('invoices/<int:pk>/download/', download_invoice_pdf, name='download-invoice-pdf'),
    path('', views.landing_page, name='landing-page'),
    path('invoices/<int:pk>/create-order/', create_razorpay_order, name='create-razorpay-order'),
    path('invoices/<int:pk>/verify-payment/', verify_razorpay_payment, name='verify-razorpay-payment'),
    path('webhooks/razorpay/', razorpay_webhook, name='razorpay-webhook'),
    

]