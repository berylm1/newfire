#!/usr/bin/env python3

import http.client
import json
import uuid

def test_health():
    """Test GET /health returns 200"""
    conn = http.client.HTTPConnection("localhost", 8080)
    conn.request("GET", "/health")
    response = conn.getresponse()
    data = response.read().decode()
    
    print(f"Health check: {response.status}")
    if response.status == 200:
        result = json.loads(data)
        if result.get("status") == "ok":
            print("PASS: Health check returned OK")
            return True
        else:
            print(f"FAIL: Health check returned wrong data: {result}")
            return False
    else:
        print(f"FAIL: Health check returned status {response.status}")
        return False

def test_create_payment():
    """Test POST /v1/payments with valid payload"""
    conn = http.client.HTTPConnection("localhost", 8080)
    
    payment_data = {
        "sender_id": "acc-001",
        "receiver_id": "acc-002",
        "amount": 100.00,
        "currency": "USD"
    }
    
    headers = {"Content-type": "application/json"}
    conn.request("POST", "/v1/payments", json.dumps(payment_data), headers)
    response = conn.getresponse()
    data = response.read().decode()
    
    print(f"Create payment: {response.status}")
    
    if response.status == 200:
        result = json.loads(data)
        payment_id = result.get("id")
        if payment_id and uuid.UUID(payment_id):
            print(f"PASS: Created payment with ID {payment_id}")
            return True, payment_id
        else:
            print(f"FAIL: Invalid payment ID returned: {result}")
            return False, None
    else:
        print(f"FAIL: Create payment returned status {response.status}: {data}")
        return False, None

def test_get_payment_status(payment_id):
    """Test GET /v1/payments/{id} with the returned ID"""
    conn = http.client.HTTPConnection("localhost", 8080)
    
    conn.request("GET", f"/v1/payments/{payment_id}")
    response = conn.getresponse()
    data = response.read().decode()
    
    print(f"Get payment status: {response.status}")
    
    if response.status == 200:
        result = json.loads(data)
        if (result.get("id") == payment_id and 
            result.get("sender_id") == "acc-001" and
            result.get("receiver_id") == "acc-002" and
            result.get("amount") == 100.00 and
            result.get("currency") == "USD"):
            print(f"PASS: Retrieved correct payment status for {payment_id}")
            return True
        else:
            print(f"FAIL: Retrieved incorrect payment data: {result}")
            return False
    else:
        print(f"FAIL: Get payment status returned status {response.status}: {data}")
        return False

def main():
    print("Running Payment Switch API tests...")
    
    # Test health endpoint
    health_result = test_health()
    
    # Test create payment
    create_result, payment_id = test_create_payment()
    
    # Test get payment
    get_result = False
    if create_result and payment_id:
        get_result = test_get_payment_status(payment_id)
    
    print("\n--- Test Results ---")
    print(f"Health check: {'PASS' if health_result else 'FAIL'}")
    print(f"Create payment: {'PASS' if create_result else 'FAIL'}")
    print(f"Get payment status: {'PASS' if get_result else 'FAIL'}")
    
    if health_result and create_result and get_result:
        print("\nAll tests PASSED!")
        return 0
    else:
        print("\nSome tests FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())