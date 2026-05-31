from rest_framework import viewsets
from .models import Invoice, LineItem, Services
from .serializers import InvoiceSerializer, LineItemSerializer, ServicesSerializer
from rest_framework.permissions import IsAuthenticated

class ServicesViewSet(viewsets.ModelViewSet):
    queryset = Services.objects.all()
    serializer_class = ServicesSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

class LineItemViewSet(viewsets.ModelViewSet):
    queryset = LineItem.objects.all()
    serializer_class = LineItemSerializer


