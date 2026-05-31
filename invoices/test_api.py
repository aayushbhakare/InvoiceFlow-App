import pytest
from rest_framework.test import APIClient
from invoices.models import Services

# This decorator tells Pytest it is allowed to use the PostgreSQL database
@pytest.mark.django_db
def test_invoice_financial_calculations():
    # 1. Setup: Initialize the API test client
    client = APIClient()

    # 2. Setup: Create our Master Catalog Data
    service = Services.objects.create(name="Video Editing", rate="50.00")

    # 3. Execution: Define the nested JSON payload
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

    # 4. Execution: Post the payload to the endpoint
    response = client.post('/api/invoices/', payload, format='json')

    # 5. Assertion: Did the server accept it? (201 Created)
    assert response.status_code == 201
    
    # 6. Assertion: Did the serializer calculate the math perfectly?
    data = response.data
    assert data['subtotal'] == 750.00        
    assert data['discount_amount'] == 75.00  
    assert data['total_amount'] == 675.00    