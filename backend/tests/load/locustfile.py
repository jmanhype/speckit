"""
Load testing with Locust

Tests API performance under load.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

Access UI at http://localhost:8089
"""

from locust import HttpUser, task, between
import random
import json


class MarketPrepUser(HttpUser):
    """
    Simulates vendor user behavior

    Scenarios:
    - Login
    - View products
    - Generate recommendations
    - View dashboard
    - Submit feedback
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Login and get access token"""
        # In production, use real test accounts
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test_vendor@example.com",
            "password": "test_password",
        })

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(5)  # Weight: 5 (most common action)
    def view_dashboard(self):
        """View dashboard (most common)"""
        if not self.token:
            return

        self.client.get("/api/v1/dashboard", headers=self.headers, name="/api/v1/dashboard")

    @task(3)
    def list_products(self):
        """List products"""
        if not self.token:
            return

        self.client.get("/api/v1/products", headers=self.headers, name="/api/v1/products")

    @task(2)
    def generate_recommendation(self):
        """Generate recommendation"""
        if not self.token:
            return

        self.client.post(
            "/api/v1/recommendations/generate",
            json={
                "market_date": "2025-02-15T09:00:00Z",
                "venue_id": "test-venue-id",
                "products": ["product-1", "product-2"],
            },
            headers=self.headers,
            name="/api/v1/recommendations/generate",
        )

    @task(2)
    def view_sales_analytics(self):
        """View sales analytics"""
        if not self.token:
            return

        self.client.get(
            "/api/v1/sales/analytics?days=30",
            headers=self.headers,
            name="/api/v1/sales/analytics",
        )

    @task(1)
    def submit_feedback(self):
        """Submit feedback (less common)"""
        if not self.token:
            return

        self.client.post(
            "/api/v1/feedback",
            json={
                "recommendation_id": "test-rec-id",
                "actual_quantity_sold": random.randint(1, 50),
                "rating": random.randint(3, 5),
            },
            headers=self.headers,
            name="/api/v1/feedback",
        )

    @task(1)
    def view_health(self):
        """Health check (monitoring)"""
        self.client.get("/health", name="/health")


class AdminUser(HttpUser):
    """
    Simulates admin user behavior

    Scenarios:
    - View metrics
    - View detailed health
    - Export data
    """

    wait_time = between(5, 10)  # Admins check less frequently

    @task(3)
    def view_metrics(self):
        """View Prometheus metrics"""
        self.client.get("/metrics", name="/metrics")

    @task(2)
    def detailed_health_check(self):
        """Detailed health check"""
        self.client.get("/health/detailed", name="/health/detailed")

    @task(1)
    def view_system_logs(self):
        """View system logs (admin endpoint)"""
        # This would require admin auth
        pass
