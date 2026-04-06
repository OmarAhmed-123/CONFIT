#!/usr/bin/env python3
"""
CONFIT API Testing Suite
========================
Comprehensive testing for all API endpoints with proper UUID handling.
Tests sending/receiving, performance, and error handling.
"""

import asyncio
import aiohttp
import json
import time
import uuid
from typing import Dict, List, Any
from datetime import datetime

class APITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results = []
        self.auth_token = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def log_result(self, endpoint: str, method: str, status: int, 
                        response_time: float, success: bool, error: str = None):
        """Log test result for performance tracking"""
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
    
    async def test_endpoint(self, method: str, endpoint: str, 
                           data: Dict = None, headers: Dict = None,
                           expected_status: int = 200) -> Dict:
        """Test a single endpoint with performance tracking"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.request(
                method=method, 
                url=url, 
                json=data, 
                headers=headers
            ) as response:
                response_time = time.time() - start_time
                content = await response.text()
                
                success = response.status == expected_status
                error = None if success else f"Expected {expected_status}, got {response.status}"
                
                await self.log_result(endpoint, method, response.status, response_time, success, error)
                
                return {
                    'status': response.status,
                    'content': content,
                    'response_time': response_time,
                    'success': success
                }
                
        except Exception as e:
            response_time = time.time() - start_time
            await self.log_result(endpoint, method, 0, response_time, False, str(e))
            return {
                'status': 0,
                'content': str(e),
                'response_time': response_time,
                'success': False
            }
    
    async def test_health_endpoints(self):
        """Test basic health and root endpoints"""
        print("\n🏥 Testing Health Endpoints")
        print("=" * 50)
        
        # Root endpoint
        await self.test_endpoint("GET", "/")
        
        # API docs
        await self.test_endpoint("GET", "/docs")
        
        # Products root
        await self.test_endpoint("GET", "/api/products")
    
    async def test_products_api(self):
        """Test all products-related endpoints"""
        print("\n🛍️ Testing Products API")
        print("=" * 50)
        
        # List all products
        result = await self.test_endpoint("GET", "/api/products")
        
        # Get featured products
        await self.test_endpoint("GET", "/api/products/featured?limit=12&gender=men")
        await self.test_endpoint("GET", "/api/products/featured?limit=12&gender=women")
        
        # Test with a valid UUID (using a known product ID if available)
        test_uuid = str(uuid.uuid4())  # This will likely return 404, which is expected
        await self.test_endpoint("GET", f"/api/products/{test_uuid}", expected_status=404)
    
    async def test_virtual_tryon_api(self):
        """Test virtual try-on endpoints"""
        print("\n👔 Testing Virtual Try-On API")
        print("=" * 50)
        
        # Test the process endpoint with sample data
        sample_data = {
            "userImageBase64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            "garmentImageUrl": "https://example.com/shirt.jpg",
            "garmentName": "Test Shirt"
        }
        
        await self.test_endpoint("POST", "/api/virtual-tryon/process", data=sample_data)
    
    async def test_challenges_api(self):
        """Test challenges/gamification endpoints"""
        print("\n🏆 Testing Challenges API")
        print("=" * 50)
        
        # List quests
        await self.test_endpoint("GET", "/api/challenges/quests")
        
        # Test with invalid UUID (should return 400)
        await self.test_endpoint("GET", "/api/challenges/quests/invalid-uuid", expected_status=400)
        
        # Test with valid UUID format (might return 404, which is expected)
        test_uuid = str(uuid.uuid4())
        await self.test_endpoint("GET", f"/api/challenges/quests/{test_uuid}", expected_status=404)
        
        # Leaderboard
        await self.test_endpoint("GET", "/api/challenges/leaderboard")
    
    async def test_omni_api(self):
        """Test omnichannel endpoints"""
        print("\n📱 Testing Omnichannel API")
        print("=" * 50)
        
        # Store route with valid UUID
        store_id = str(uuid.uuid4())
        product_ids = f"{str(uuid.uuid4())},{str(uuid.uuid4())}"
        await self.test_endpoint("GET", f"/api/omni/store-route?store_id={store_id}&product_ids={product_ids}")
        
        # Test with invalid store ID
        await self.test_endpoint("GET", "/api/omni/store-route?store_id=invalid&product_ids=test", expected_status=400)
    
    async def test_wardrobe_api(self):
        """Test wardrobe endpoints"""
        print("\n👚 Testing Wardrobe API")
        print("=" * 50)
        
        # List wardrobe items (will require auth, so expect 401)
        await self.test_endpoint("GET", "/api/wardrobe/items", expected_status=401)
    
    async def test_performance_benchmarks(self):
        """Run performance benchmarks on key endpoints"""
        print("\n⚡ Performance Benchmarks")
        print("=" * 50)
        
        # Test multiple concurrent requests
        endpoints = [
            "/api/products",
            "/api/products/featured?limit=12",
            "/api/challenges/quests",
            "/api/challenges/leaderboard"
        ]
        
        for endpoint in endpoints:
            print(f"\n🔄 Testing {endpoint} with 10 concurrent requests...")
            
            tasks = []
            for i in range(10):
                task = self.test_endpoint("GET", endpoint)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # Calculate performance metrics
            successful = [r for r in results if r['success']]
            if successful:
                avg_time = sum(r['response_time'] for r in successful) / len(successful)
                min_time = min(r['response_time'] for r in successful)
                max_time = max(r['response_time'] for r in successful)
                
                print(f"   📊 Average: {avg_time*1000:.2f}ms")
                print(f"   📊 Min: {min_time*1000:.2f}ms")
                print(f"   📊 Max: {max_time*1000:.2f}ms")
                print(f"   📊 Success Rate: {len(successful)}/10")
    
    async def generate_report(self):
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
            for test in failed_tests[:5]:  # Show first 5 failures
                print(f"   {test['method']} {test['endpoint']} - {test['error']}")
        
        # Performance issues (over 1 second)
        slow_tests = [r for r in self.test_results if r['response_time_ms'] > 1000]
        if slow_tests:
            print(f"\n⚠️ Slow Tests ({len(slow_tests)}):")
            for test in slow_tests:
                print(f"   {test['method']} {test['endpoint']} - {test['response_time_ms']:.2f}ms")
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time if successful_results else 0,
            'failed_tests': failed_tests,
            'slow_tests': slow_tests
        }

async def main():
    """Main test runner"""
    print("🚀 CONFIT API Testing Suite")
    print("=" * 50)
    print("Testing all endpoints for functionality, performance, and error handling...")
    
    async with APITester() as tester:
        # Run all test suites
        await tester.test_health_endpoints()
        await tester.test_products_api()
        await tester.test_virtual_tryon_api()
        await tester.test_challenges_api()
        await tester.test_omni_api()
        await tester.test_wardrobe_api()
        await tester.test_performance_benchmarks()
        
        # Generate final report
        report = await tester.generate_report()
        
        # Save report to file
        with open('api_test_report.json', 'w') as f:
            json.dump({
                'summary': report,
                'detailed_results': tester.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: api_test_report.json")
        
        # Return success/failure based on results
        if report['success_rate'] >= 90:
            print("\n🎉 API Testing Completed Successfully!")
            return True
        else:
            print(f"\n⚠️ API Testing Completed with {report['success_rate']:.2f}% success rate")
            return False

if __name__ == "__main__":
    asyncio.run(main())
