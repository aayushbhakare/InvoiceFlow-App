
        const urlParams = new URLSearchParams(window.location.search);
        const invoiceToken = urlParams.get('token');
        let orderData = null;

        async function init() {
            if (!invoiceToken) {
                document.getElementById('status').textContent = 'Invalid payment link.';
                return;
            }

            try {
                const res = await fetch(`${BASE_API_URL}/invoices/${invoiceToken}/create-order/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!res.ok) {
                    const err = await res.json();
                    document.getElementById('status').textContent = err.error || 'Failed to load invoice.';
                    return;
                }

                orderData = await res.json();
                document.getElementById('inv-num').textContent = orderData.invoice_number;
                document.getElementById('amount').textContent = '₹' + (orderData.amount / 100).toLocaleString('en-IN');
                document.getElementById('client').textContent = 'Billed to: ' + orderData.client_name;
                document.getElementById('pay-btn').disabled = false;
            } catch (e) {
                document.getElementById('status').textContent = 'Network error.';
            }
        }

        function startPayment() {
            const options = {
                key: orderData.razorpay_key_id,
                amount: orderData.amount,
                currency: orderData.currency,
                name: 'InvoiceFlow',
                description: orderData.invoice_number,
                order_id: orderData.order_id,
                prefill: {
                    email: orderData.client_email || '',
                },
                handler: async function (response) {
                    document.getElementById('pay-btn').disabled = true;
                    document.getElementById('status').textContent = 'Verifying payment...';

                    try {
                        const verifyRes = await fetch(`${BASE_API_URL}/invoices/${invoiceToken}/verify-payment/`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                razorpay_order_id: response.razorpay_order_id,
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_signature: response.razorpay_signature,
                            })
                        });

                        if (verifyRes.ok) {
                            document.getElementById('status').innerHTML = '<span class="success">✓ Payment successful!</span>';
                            document.getElementById('pay-btn').style.display = 'none';
                        } else {
                            document.getElementById('status').textContent = 'Verification failed. Contact the business.';
                        }
                    } catch (e) {
                        document.getElementById('status').textContent = 'Network error during verification.';
                    }
                },
                theme: { color: '#1D9E75' }
            };

            const rzp = new Razorpay(options);
            rzp.open();
        }

        init();