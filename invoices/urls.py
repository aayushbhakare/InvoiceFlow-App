from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InvoiceViewSet, LineItemViewSet, ServiceViewSet, 
    download_invoice_pdf, ClientViewSet, RegisterView, ProfileManageView,RecurringInvoiceViewSet,
    create_payment_order, verify_razorpay_payment, razorpay_webhook, swiftpay_webhook, ai_chat_endpoint, DeleteAccountView,
    ForgotPasswordView, ResetPasswordView
)
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
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('chat/', ai_chat_endpoint, name='ai-chat'),
    path('', include(router.urls)),
    path('invoices/<int:pk>/download/', download_invoice_pdf, name='download-invoice-pdf'),
    path('', views.landing_page, name='landing-page'),
    path('invoices/<uuid:payment_token>/create-order/', create_payment_order, name='create-payment-order'),
    path('invoices/<uuid:payment_token>/verify-payment/', verify_razorpay_payment, name='verify-razorpay-payment'),
    path('webhooks/razorpay/', razorpay_webhook, name='razorpay-webhook'),
    path('webhooks/swiftpay/', swiftpay_webhook, name='swiftpay-webhook'),
]