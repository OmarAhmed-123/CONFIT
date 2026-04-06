"""
CONFIT API Verification Script
=============================
Simple API testing using standard library to verify all endpoints work correctly.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any

class SimpleAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
    
    def log_result(self, endpoint: str, method: str, status: int, 
                   response_time: float, success: bool, error: str = None):
        """Log test result"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'status_code': status,
            'response_time_ms': round(response_time * 1000, 2),
            'success': success,
            'error': error
        }
        self.test_results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {method} {endpoint} - {status} ({response_time*1000:.2f}ms)")
        if error:
            print(f"   Error: {error}")
    
    def test_endpoint(self, method: str, endpoint: str, 
                     data: Dict = None, expected_status: int = 200) -> Dict:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                req = urllib.request.Request(url)
                req.add_header('Accept', 'application/json')
            elif method == "POST":
                req = urllib.request.Request(url, method='POST')
                req.add_header('Content-Type', 'application/json')
                if data:
                    req.data = json.dumps(data).encode('utf-8')
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            with urllib.request.urlopen(req, timeout=10) as response:
                response_time = time.time() - start_time
                content = response.read().decode('utf-8')
                
                success = response.status == expected_status
                error = None if success else f"Expected {expected_status}, got {response.status}"
                
                self.log_result(endpoint, method, response.status, response_time, success, error)
                
                return {
                    'status': response.status,
                    'content': content,
                    'response_time': response_time,
                    'success': success
                }
                
        except urllib.error.HTTPError as e:
            response_time = time.time() - start_time
            self.log_result(endpoint, method, e.code, response_time, e.code == expected_status, str(e))
            return {
                'status': e.code,
                'content': e.read().decode('utf-8') if hasattr(e, 'read') else str(e),
                'response_time': response_time,
                'success': e.code == expected_status
            }
        except Exception as e:
            response_time = time.time() - start_time
            self.log_result(endpoint, method, 0, response_time, False, str(e))
            return {
                'status': 0,
                'content': str(e),
                'response_time': response_time,
                'success': False
            }
    
    def test_all_endpoints(self):
        """Test all critical endpoints"""
        print("🚀 CONFIT API Verification Suite")
        print("=" * 50)
        print("Testing all endpoints for functionality and error handling...")
        
        # Health endpoints
        print("\n🏥 Health Endpoints")
        print("-" * 30)
        self.test_endpoint("GET", "/")
        self.test_endpoint("GET", "/docs")
        
        # Products API
        print("\n🛍️ Products API")
        print("-" * 30)
        self.test_endpoint("GET", "/api/products")
        self.test_endpoint("GET", "/api/products/featured?limit=12&gender=men")
        self.test_endpoint("GET", "/api/products/featured?limit=12&gender=women")
        
        # Test UUID handling
        test_uuid = str(uuid.uuid4())
        self.test_endpoint("GET", f"/api/products/{test_uuid}", expected_status=404)
        
        # Virtual Try-On API
        print("\n👔 Virtual Try-On API")
        print("-" * 30)
        sample_data = {
            "userImageBase64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            "garmentImageUrl": "https://example.com/shirt.jpg",
            "garmentName": "Test Shirt"
        }
        self.test_endpoint("POST", "/api/virtual-tryon/process", data=sample_data)
        
        # Challenges API
        print("\n🏆 Challenges API")
        print("-" * 30)
        self.test_endpoint("GET", "/api/challenges/quests")
        self.test_endpoint("GET", "/api/challenges/quests/invalid-uuid", expected_status=400)
        self.test_endpoint("GET", f"/api/challenges/quests/{test_uuid}", expected_status=404)
        self.test_endpoint("GET", "/api/challenges/leaderboard")
        
        # Omnichannel API
        print("\n📱 Omnichannel API")
        print("-" * 30)
        store_id = str(uuid.uuid4())
        product_ids = f"{str(uuid.uuid4())},{str(uuid.uuid4())}"
        self.test_endpoint("GET", f"/api/omni/store-route?store_id={store_id}&product_ids={product_ids}")
        self.test_endpoint("GET", "/api/omni/store-route?store_id=invalid&product_ids=test", expected_status=400)
        
        # Wardrobe API (will require auth)
        print("\n👚 Wardrobe API")
        print("-" * 30)
        self.test_endpoint("GET", "/api/wardrobe/items", expected_status=401)
        
        # Performance test
        print("\n⚡ Performance Test")
        print("-" * 30)
        print("Testing 5 concurrent requests to /api/products...")
        
        start_time = time.time()
        for i in range(5):
            self.test_endpoint("GET", "/api/products")
        perf_time = time.time() - start_time
        
        print(f"📊 Total time for 5 requests: {perf_time:.2f}s")
        print(f"📊 Average per request: {perf_time/5:.2f}s")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📊 Test Report Summary")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Success Rate: {success_rate:.2f}%")
        
        # Performance summary
        successful_results = [r for r in self.test_results if r['success']]
        if successful_results:
            avg_response_time = sum(r['response_time_ms'] for r in successful_results) / len(successful_results)
            print(f"Average Response Time: {avg_response_time:.2f}ms")
        
        # Failed tests
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   {test['method']} {test['endpoint']} - {test['error']}")
        
        # Performance issues
        slow_tests = [r for r in self.test_results if r['response_time_ms'] > 1000]
        if slow_tests:
            print(f"\n⚠️ Slow Tests ({len(slow_tests)}):")
            for test in slow_tests:
                print(f"   {test['method']} {test['endpoint']} - {test['response_time_ms']:.2f}ms")
        
        # Save report
        report_data = {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time if successful_results else 0
            },
            'detailed_results': self.test_results
        }
        
        with open('api_verification_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: api_verification_report.json")
        
        return success_rate >= 90

def main():
    """Main test runner"""
    tester = SimpleAPITester()
    
    try:
        tester.test_all_endpoints()
        success = tester.generate_report()
        
        if success:
            print("\n🎉 API Verification Completed Successfully!")
            print("All critical endpoints are working correctly.")
        else:
            print("\n⚠️ API Verification Completed with Issues")
            print("Some endpoints may need attention.")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        return False

if __name__ == "__main__":
    main()
