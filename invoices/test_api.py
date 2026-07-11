import pytest
from rest_framework.test import APIClient
from invoices.models import Services
@pytest.mark.django_db
def test_invoice_financial_calculations():
    client = APIClient()
    service = Services.objects.create(name="Video Editing", rate="50.00")
    payload = {
        "invoice_number": "2026-05-31-004",
        "client_name": "Wayne Enterprises",
        "issue_date": "2026-05-31",
        "due_date": "2026-06-30",
        "status": "DRAFT",
        "discount_percentage": "10.00",
        "items": [
            {
                "services": service.id,
                "total_hours": "15.00"
            }
        ]
    }
    response = client.post('/api/invoices/', payload, format='json')
    assert response.status_code == 201
    data = response.data
    assert data['subtotal'] == 750.00        
    assert data['discount_amount'] == 75.00  
    assert data['total_amount'] == 675.00    