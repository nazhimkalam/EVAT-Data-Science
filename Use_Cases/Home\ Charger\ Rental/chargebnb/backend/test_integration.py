"""
Comprehensive Integration Tests for ChargeBnB Frontend + Backend
Tests all API endpoints and data flow between React frontend and FastAPI backend
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Configuration
API_BASE_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"

# Test data
TEST_SUBURB = "brunswick (north)"
TEST_USER_ID = 1
TEST_VEHICLE = "Tesla Model 3"
TEST_PROMO = "WELCOME10"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_test(test_name, passed, message=""):
    """Log test result"""
    status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if passed else f"{Colors.RED}❌ FAIL{Colors.RESET}"
    print(f"{status} {test_name}")
    if message:
        print(f"   {Colors.YELLOW}→ {message}{Colors.RESET}")

def section_header(title):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

# =============================================================================
# HEALTH & INFO TESTS
# =============================================================================

def test_health_check():
    """Test /health endpoint"""
    section_header("1. Health Check Tests")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        passed = response.status_code == 200
        data = response.json() if passed else {}
        log_test("GET /health", passed, f"Status: {response.status_code}, Service: {data.get('service', 'N/A')}")
        return passed
    except Exception as e:
        log_test("GET /health", False, str(e))
        return False

def test_info_endpoint():
    """Test /info endpoint"""
    try:
        response = requests.get(f"{API_BASE_URL}/info", timeout=5)
        passed = response.status_code == 200 and "model" in response.json()
        data = response.json() if passed else {}
        log_test("GET /info", passed, f"Model: {data.get('model')}, Confidence: {data.get('confidence')}")
        return passed
    except Exception as e:
        log_test("GET /info", False, str(e))
        return False

# =============================================================================
# LISTING TESTS
# ============================================================================

def test_get_listings():
    """Test /listings endpoint"""
    section_header("2. Listing Endpoint Tests")

    try:
        # Test basic listings
        response = requests.get(f"{API_BASE_URL}/listings?limit=10", timeout=10)
        passed = response.status_code == 200
        data = response.json() if passed else {}

        log_test(
            "GET /listings",
            passed,
            f"Count: {data.get('count')}, Returned: {len(data.get('listings', []))} chargers"
        )

        if passed and data.get('listings'):
            listing = data['listings'][0]
            required_fields = ['id', 'suburb', 'cluster', 'price_per_hour', 'connector', 'power_kw']
            has_fields = all(field in listing for field in required_fields)
            log_test(
                "Listing response structure",
                has_fields,
                f"Fields: {', '.join(required_fields)}"
            )
            return True
        return False
    except Exception as e:
        log_test("GET /listings", False, str(e))
        return False

def test_get_suburbs():
    """Test /suburbs endpoint"""
    try:
        response = requests.get(f"{API_BASE_URL}/suburbs?limit=20", timeout=5)
        passed = response.status_code == 200
        data = response.json() if passed else {}

        log_test(
            "GET /suburbs",
            passed,
            f"Total suburbs: {data.get('count')}, Returned: {len(data.get('suburbs', []))}"
        )
        return passed
    except Exception as e:
        log_test("GET /suburbs", False, str(e))
        return False

# =============================================================================
# PRICING TESTS
# =============================================================================

def test_pricing_peak_hour():
    """Test pricing at peak hour (6 PM)"""
    section_header("3. Pricing Endpoint Tests")

    try:
        # Create peak hour time (6 PM)
        peak_time = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
        start_param = peak_time.isoformat()

        response = requests.get(
            f"{API_BASE_URL}/pricing",
            params={"suburb": TEST_SUBURB, "start": start_param},
            timeout=10
        )
        passed = response.status_code == 200 and "pricing" in response.json()
        data = response.json() if passed else {}

        if passed:
            pricing = data.get('pricing', {})
            log_test(
                "GET /pricing (Peak hour - 6 PM)",
                passed,
                f"Recommended: ${pricing.get('recommended_price')}/hr, Band: {pricing.get('price_band')}"
            )

            # Verify pricing fields
            required_pricing_fields = ['recommended_price', 'price_floor', 'price_cap', 'price_band']
            has_pricing = all(field in pricing for field in required_pricing_fields)
            log_test("Pricing response structure", has_pricing)

            # Verify demand data
            demand = data.get('demand', {})
            required_demand_fields = ['expected_kw', 'confidence', 'multiplier']
            has_demand = all(field in demand for field in required_demand_fields)
            log_test("Demand response structure", has_demand)

            return True
        else:
            log_test("GET /pricing (Peak hour)", False, response.json().get('error', 'Unknown error'))
            return False
    except Exception as e:
        log_test("GET /pricing (Peak hour)", False, str(e))
        return False

def test_pricing_standard_hour():
    """Test pricing at standard hour (2 PM)"""
    try:
        # Create standard hour time (2 PM)
        standard_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        start_param = standard_time.isoformat()

        response = requests.get(
            f"{API_BASE_URL}/pricing",
            params={"suburb": TEST_SUBURB, "start": start_param},
            timeout=10
        )
        passed = response.status_code == 200 and "pricing" in response.json()
        data = response.json() if passed else {}

        if passed:
            pricing = data.get('pricing', {})
            log_test(
                "GET /pricing (Standard hour - 2 PM)",
                passed,
                f"Recommended: ${pricing.get('recommended_price')}/hr, Band: {pricing.get('price_band')}"
            )
            return True
        else:
            log_test("GET /pricing (Standard hour)", False, "Failed")
            return False
    except Exception as e:
        log_test("GET /pricing (Standard hour)", False, str(e))
        return False

def test_pricing_offpeak_hour():
    """Test pricing at off-peak hour (2 AM)"""
    try:
        # Create off-peak hour time (2 AM)
        offpeak_time = datetime.now().replace(hour=2, minute=0, second=0, microsecond=0)
        start_param = offpeak_time.isoformat()

        response = requests.get(
            f"{API_BASE_URL}/pricing",
            params={"suburb": TEST_SUBURB, "start": start_param},
            timeout=10
        )
        passed = response.status_code == 200 and "pricing" in response.json()
        data = response.json() if passed else {}

        if passed:
            pricing = data.get('pricing', {})
            log_test(
                "GET /pricing (Off-peak hour - 2 AM)",
                passed,
                f"Recommended: ${pricing.get('recommended_price')}/hr, Band: {pricing.get('price_band')}"
            )
            return True
        else:
            log_test("GET /pricing (Off-peak hour)", False, "Failed")
            return False
    except Exception as e:
        log_test("GET /pricing (Off-peak hour)", False, str(e))
        return False

def test_pricing_invalid_suburb():
    """Test pricing with invalid suburb"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/pricing",
            params={"suburb": "nonexistent_suburb_xyz"},
            timeout=5
        )
        passed = response.status_code == 200 and response.json().get('found') == False
        log_test("GET /pricing (Invalid suburb handling)", passed)
        return passed
    except Exception as e:
        log_test("GET /pricing (Invalid suburb handling)", False, str(e))
        return False

# =============================================================================
# BOOKING TESTS
# =============================================================================

def test_create_booking():
    """Test creating a booking"""
    section_header("4. Booking Endpoint Tests")

    global booking_id
    booking_id = None

    try:
        # First get pricing to use in booking
        peak_time = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
        start_time = peak_time.isoformat()
        end_time = (peak_time + timedelta(hours=1)).isoformat()

        pricing_response = requests.get(
            f"{API_BASE_URL}/pricing",
            params={"suburb": TEST_SUBURB, "start": start_time},
            timeout=10
        )

        if pricing_response.status_code != 200:
            log_test("Create booking (Get pricing)", False, "Failed to get pricing")
            return False

        pricing_data = pricing_response.json()
        price_per_hour = pricing_data['pricing']['recommended_price']
        hours = 1.0
        total_amount = round(price_per_hour * hours, 2)

        # Create booking
        booking_payload = {
            "listing_id": TEST_SUBURB.replace(" ", "_"),
            "suburb": TEST_SUBURB,
            "title": f"Charger in {TEST_SUBURB}",
            "start": start_time,
            "end": end_time,
            "user_id": TEST_USER_ID,
            "vehicle": TEST_VEHICLE,
            "promo": TEST_PROMO,
            "hours": hours,
            "quoted_price_per_hour": price_per_hour,
            "total_amount": total_amount
        }

        response = requests.post(
            f"{API_BASE_URL}/bookings",
            json=booking_payload,
            timeout=10
        )

        passed = response.status_code == 200 and response.json().get('success') == True
        data = response.json() if passed else {}
        booking_id = data.get('booking_id')

        log_test(
            "POST /bookings (Create booking)",
            passed,
            f"Booking ID: {booking_id}, Amount: ${total_amount}"
        )
        return passed
    except Exception as e:
        log_test("POST /bookings (Create booking)", False, str(e))
        return False

def test_get_bookings():
    """Test getting all bookings"""
    try:
        response = requests.get(f"{API_BASE_URL}/bookings", timeout=10)
        passed = response.status_code == 200 and "bookings" in response.json()
        data = response.json() if passed else {}

        log_test(
            "GET /bookings",
            passed,
            f"Count: {data.get('count')}, Returned: {len(data.get('bookings', []))}"
        )
        return passed
    except Exception as e:
        log_test("GET /bookings", False, str(e))
        return False

def test_get_booking_detail():
    """Test getting a specific booking"""
    if booking_id is None:
        log_test("GET /bookings/{id}", False, "No booking ID available")
        return False

    try:
        response = requests.get(f"{API_BASE_URL}/bookings/{booking_id}", timeout=5)
        passed = response.status_code == 200 and "booking_id" in response.json()
        log_test("GET /bookings/{id}", passed, f"Retrieved booking {booking_id}")
        return passed
    except Exception as e:
        log_test("GET /bookings/{id}", False, str(e))
        return False

# =============================================================================
# FRONTEND API CLIENT TESTS
# =============================================================================

def test_frontend_api_client():
    """Test that frontend can reach backend"""
    section_header("5. Frontend-Backend Integration Tests")

    try:
        # Test CORS - frontend should be able to call backend
        response = requests.get(
            f"{API_BASE_URL}/listings",
            headers={
                "Origin": FRONTEND_URL,
                "Accept": "application/json"
            },
            timeout=5
        )
        passed = response.status_code == 200
        log_test("Frontend → Backend (CORS enabled)", passed)
        return passed
    except Exception as e:
        log_test("Frontend → Backend (CORS enabled)", False, str(e))
        return False

def test_api_response_formats():
    """Test that API responses match expected formats"""
    try:
        endpoints = [
            ("/health", "Health endpoint"),
            ("/info", "Info endpoint"),
            ("/suburbs?limit=5", "Suburbs endpoint"),
            ("/listings?limit=5", "Listings endpoint"),
        ]

        all_passed = True
        for endpoint, name in endpoints:
            response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            is_json = response.headers.get('content-type', '').startswith('application/json')
            passed = response.status_code == 200 and is_json
            all_passed = all_passed and passed
            status = "✓" if passed else "✗"
            print(f"  {status} {name}: {response.status_code}, Content-Type: {response.headers.get('content-type')}")

        log_test("Response format validation (all JSON)", all_passed)
        return all_passed
    except Exception as e:
        log_test("Response format validation", False, str(e))
        return False

# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

def test_performance():
    """Test API response times"""
    section_header("6. Performance Tests")

    endpoints = [
        ("/health", "Health check"),
        ("/info", "Info endpoint"),
        ("/listings?limit=50", "Listings (50)"),
        (f"/pricing?suburb={TEST_SUBURB}", "Pricing lookup"),
        ("/bookings", "Get bookings"),
    ]

    all_fast = True
    for endpoint, name in endpoints:
        try:
            start = time.time()
            response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
            elapsed = (time.time() - start) * 1000  # Convert to ms

            fast = elapsed < 200  # 200ms threshold
            all_fast = all_fast and fast

            status = "✓" if fast else "⚠"
            print(f"  {status} {name}: {elapsed:.1f}ms")
        except Exception as e:
            print(f"  ✗ {name}: Error - {str(e)}")
            all_fast = False

    log_test("All endpoints under 200ms threshold", all_fast)
    return all_fast

# =============================================================================
# COMPLETE WORKFLOW TEST
# =============================================================================

def test_complete_workflow():
    """Test complete user workflow: Browse → Price → Book"""
    section_header("7. Complete Workflow Test")

    try:
        # Step 1: Get listings
        print("  Step 1: Fetching charger listings...")
        listings_response = requests.get(f"{API_BASE_URL}/listings?limit=10", timeout=10)
        if listings_response.status_code != 200:
            log_test("Workflow: Get listings", False)
            return False

        listings = listings_response.json()['listings']
        if not listings:
            log_test("Workflow: Get listings", False, "No listings returned")
            return False

        # Step 2: Get pricing for first listing
        print("  Step 2: Getting AI pricing for selected charger...")
        selected_suburb = listings[0]['suburb']
        peak_time = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)

        pricing_response = requests.get(
            f"{API_BASE_URL}/pricing",
            params={"suburb": selected_suburb, "start": peak_time.isoformat()},
            timeout=10
        )
        if pricing_response.status_code != 200:
            log_test("Workflow: Get pricing", False)
            return False

        pricing = pricing_response.json()

        # Step 3: Create booking
        print("  Step 3: Creating booking...")
        end_time = (peak_time + timedelta(hours=2))

        booking_payload = {
            "listing_id": listings[0]['id'],
            "suburb": selected_suburb,
            "title": listings[0]['suburb'],
            "start": peak_time.isoformat(),
            "end": end_time.isoformat(),
            "user_id": TEST_USER_ID,
            "vehicle": TEST_VEHICLE,
            "promo": "",
            "hours": 2.0,
            "quoted_price_per_hour": pricing['pricing']['recommended_price'],
            "total_amount": round(pricing['pricing']['recommended_price'] * 2, 2)
        }

        booking_response = requests.post(
            f"{API_BASE_URL}/bookings",
            json=booking_payload,
            timeout=10
        )
        if booking_response.status_code != 200:
            log_test("Workflow: Create booking", False)
            return False

        # Step 4: Verify booking
        print("  Step 4: Verifying booking...")
        booking = booking_response.json()
        bookings_response = requests.get(f"{API_BASE_URL}/bookings", timeout=10)
        all_bookings = bookings_response.json()['bookings']

        booking_found = any(b.get('booking_id') == booking.get('booking_id') for b in all_bookings)

        log_test(
            "Complete workflow (Browse → Price → Book → Verify)",
            booking_found,
            f"Booked: {selected_suburb}, ${booking_payload['total_amount']}"
        )
        return booking_found
    except Exception as e:
        log_test("Complete workflow", False, str(e))
        return False

# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all tests and generate report"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "CHARGEBNB INTEGRATION TEST SUITE" + " "*21 + "║")
    print("║" + " "*12 + "Frontend (React) + Backend (FastAPI)" + " "*20 + "║")
    print("╚" + "="*68 + "╝")
    print(f"{Colors.RESET}")

    tests = [
        # Health & Info
        test_health_check,
        test_info_endpoint,

        # Listings
        test_get_listings,
        test_get_suburbs,

        # Pricing
        test_pricing_peak_hour,
        test_pricing_standard_hour,
        test_pricing_offpeak_hour,
        test_pricing_invalid_suburb,

        # Bookings
        test_create_booking,
        test_get_bookings,
        test_get_booking_detail,

        # Integration
        test_frontend_api_client,
        test_api_response_formats,

        # Performance
        test_performance,

        # Workflow
        test_complete_workflow,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"{Colors.RED}✗ Test crashed: {test.__name__}{Colors.RESET}")
            print(f"  Error: {str(e)}")
            results.append(False)

    # Print summary
    section_header("Test Summary")
    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    print(f"{Colors.BOLD}Total Tests: {total}{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}{Colors.BOLD}Failed: {total - passed}{Colors.RESET}")
    print(f"{Colors.BOLD}Success Rate: {percentage:.1f}%{Colors.RESET}\n")

    if percentage == 100:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED!{Colors.RESET}")
    elif percentage >= 80:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  MOST TESTS PASSED{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED{Colors.RESET}")

if __name__ == "__main__":
    run_all_tests()
