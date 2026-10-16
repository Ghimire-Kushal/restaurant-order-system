from decimal import Decimal
import base64

from django.test import Client, TestCase
from rest_framework.test import APIClient

from accounts.models import User
from menu.models import Category, FoodItem, MenuSection
from tables.models import CustomerSession, Table, TableQRCode

from .models import Cart, CartItem, Order, OrderItem, Payment


class OrderingWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        section = MenuSection.objects.create(name="Mains")
        category = Category.objects.create(section=section, name="Food")
        self.food = FoodItem.objects.create(
            category=category,
            name="Noodles",
            price=Decimal("120.00"),
        )
        self.table = Table.objects.create(number=1)
        self.session = CustomerSession.objects.create(table=self.table)
        self.reception = User.objects.create_user(
            username="reception", password="pass", role=User.Role.RECEPTION
        )
        self.kitchen = User.objects.create_user(
            username="kitchen", password="pass", role=User.Role.KITCHEN_MANAGER
        )

    def test_customer_can_submit_server_priced_order(self):
        token = self.session.session_token
        response = self.client.post(
            f"/api/cart/{token}/add/",
            {"food_item_id": self.food.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.post(f"/api/cart/{token}/submit/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.total_amount, Decimal("240.00"))
        self.assertEqual(order.items.get().food_name, "Noodles")

        duplicate = self.client.post(
            f"/api/cart/{token}/submit/", {}, format="json"
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_invalid_and_inactive_table_qr_codes_are_rejected(self):
        self.assertEqual(self.client.get("/table/scan/not-a-uuid/").status_code, 404)

        qr = TableQRCode.objects.create(table=self.table, is_active=False)
        self.assertEqual(self.client.get(f"/table/scan/{qr.token}/").status_code, 404)

        qr.is_active = True
        qr.save(update_fields=["is_active"])
        self.table.is_active = False
        self.table.status = Table.Status.INACTIVE
        self.table.save(update_fields=["is_active", "status"])
        response = self.client.get(f"/table/scan/{qr.token}/")
        self.assertEqual(response.status_code, 403)

    def test_staff_workflow_and_duplicate_payment_guard(self):
        token = self.session.session_token
        self.client.post(f"/api/cart/{token}/add/", {"food_item_id": self.food.id}, format="json")
        self.client.post(f"/api/cart/{token}/submit/", {}, format="json")
        order = Order.objects.get()

        self.client.force_authenticate(self.reception)
        response = self.client.get("/api/cart/reception/")
        self.assertEqual(response.status_code, 200)
        response = self.client.post(f"/api/cart/reception/{order.order_number}/accept/", {}, format="json")
        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(self.kitchen)
        response = self.client.post(
            f"/api/cart/kitchen/{order.order_number}/start/",
            {"preparation_minutes": 15},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(f"/api/cart/kitchen/{order.order_number}/ready/", {}, format="json")
        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(self.reception)
        response = self.client.post(
            f"/api/cart/reception/{order.order_number}/payment/",
            {"amount": "120.00", "method": Payment.Method.CASH},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.post(
            f"/api/cart/reception/{order.order_number}/payment/",
            {"amount": "120.00", "method": Payment.Method.CASH},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_kitchen_cannot_access_reception(self):
        self.client.force_authenticate(self.kitchen)
        response = self.client.get("/api/cart/reception/")
        self.assertEqual(response.status_code, 403)

    def _create_order(self):
        token = self.session.session_token
        self.client.post(f"/api/cart/{token}/add/", {"food_item_id": self.food.id}, format="json")
        self.client.post(f"/api/cart/{token}/submit/", {}, format="json")
        return Order.objects.get()

    def test_discount_and_online_payment_are_safe(self):
        order = self._create_order()
        self.client.force_authenticate(self.reception)
        response = self.client.post(
            f"/api/cart/reception/{order.order_number}/discount/",
            {"percentage": "10"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.discount_amount, Decimal("12.00"))
        self.assertEqual(order.total_amount, Decimal("108.00"))
        response = self.client.post(
            f"/api/cart/reception/{order.order_number}/payment/",
            {"amount": "108.00", "method": Payment.Method.ONLINE}, format="json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Payment.objects.exists())

    def test_receipt_escapes_item_names(self):
        order = self._create_order()
        order.items.update(food_name="<script>alert('xss')</script>")

        self.client.force_authenticate(self.reception)
        response = self.client.get(
            f"/api/cart/reception/{order.order_number}/receipt/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>alert('xss')</script>", html=False)
        self.assertContains(response, "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;", html=False)

    def test_customer_session_isolation_and_release_guard(self):
        other_table = Table.objects.create(number=2)
        other_session = CustomerSession.objects.create(table=other_table)
        response = self.client.get(f"/api/cart/{other_session.session_token}/")
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/api/cart/{other_session.session_token}/order/not-yours/")
        self.assertEqual(response.status_code, 404)
        self._create_order()
        self.client.force_authenticate(self.reception)
        response = self.client.post(f"/api/cart/reception/table/{self.table.id}/release/", {}, format="json")
        self.assertEqual(response.status_code, 409)

        response = self.client.post(
            f"/api/cart/reception/table/{self.table.id}/release/",
            {"override": "false"}, format="json",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            f"/api/cart/reception/table/{self.table.id}/release/",
            {"override": True}, format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_dashboard_routes_and_reports_require_expected_access(self):
        self.assertContains(self.client.get(f"/table/{TableQRCode.objects.create(table=self.table).token}/"), "data-mode=\"customer\"")
        self.assertContains(self.client.get("/staff/reception/"), "data-mode=\"reception\"")
        self.client.force_authenticate(self.reception)
        response = self.client.get("/api/cart/reports/")
        self.assertEqual(response.status_code, 200)

    def test_browser_csrf_token_allows_staff_post(self):
        order = self._create_order()
        browser = Client(enforce_csrf_checks=True)
        page = browser.get("/staff/reception/")
        self.assertEqual(page.status_code, 200)
        csrf = browser.cookies["csrftoken"].value
        credentials = base64.b64encode(b"reception:pass").decode()
        response = browser.post(
            f"/api/cart/reception/{order.order_number}/accept/",
            data="{}",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Basic {credentials}",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_fifty_record_module_integration(self):
        """Exercise the main relationships and queues with a realistic small dataset."""
        users = [
            User(
                username=f"scale-user-{index}",
                role=(User.Role.RECEPTION if index % 2 else User.Role.KITCHEN_MANAGER),
            )
            for index in range(50)
        ]
        User.objects.bulk_create(users)
        self.assertEqual(User.objects.filter(username__startswith="scale-user-").count(), 50)

        foods = [
            FoodItem(
                category=self.food.category,
                name=f"Scale dish {index}",
                price=Decimal("10.00") + index,
                display_order=index,
            )
            for index in range(50)
        ]
        FoodItem.objects.bulk_create(foods)
        self.assertEqual(FoodItem.objects.filter(name__startswith="Scale dish ").count(), 50)

        tables = [
            Table(number=100 + index, capacity=index + 1)
            for index in range(50)
        ]
        Table.objects.bulk_create(tables)
        tables = list(Table.objects.filter(number__gte=100).order_by("number"))
        self.assertEqual(len(tables), 50)
        self.assertEqual(sum(table.capacity for table in tables), sum(range(1, 51)))

        TableQRCode.objects.bulk_create([TableQRCode(table=table) for table in tables])
        sessions = CustomerSession.objects.bulk_create(
            [CustomerSession(table=table) for table in tables]
        )
        self.assertEqual(len(sessions), 50)

        response = self.client.get(f"/table/scan/{tables[0].qr_code.token}/")
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/api/menu/{sessions[0].session_token}/")
        self.assertEqual(response.status_code, 200)
        visible_items = sum(
            len(category["food_items"])
            for section in response.data["menu"]
            for category in section["categories"]
        )
        self.assertEqual(visible_items, 51)

        carts = Cart.objects.bulk_create([Cart(session=session) for session in sessions])
        CartItem.objects.bulk_create([
            CartItem(cart=cart, food_item=foods[index], quantity=index % 3 + 1, unit_price=foods[index].price)
            for index, cart in enumerate(carts)
        ])
        orders = [
            Order(
                order_number=f"SCALE-{index:04d}",
                session=sessions[index],
                table=tables[index],
                status=Order.Status.PENDING,
                subtotal=Decimal("10.00") + index,
                total_amount=Decimal("10.00") + index,
            )
            for index in range(50)
        ]
        Order.objects.bulk_create(orders)
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                food_item=foods[index],
                food_name=foods[index].name,
                quantity=1,
                unit_price=foods[index].price,
                spice_name="",
                unit_total=foods[index].price,
                subtotal=foods[index].price,
            )
            for index, order in enumerate(orders)
        ])

        self.client.force_authenticate(self.reception)
        response = self.client.get("/api/cart/reception/?status=PENDING")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 50)
        response = self.client.get("/api/cart/reports/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["orders"]["count"], 50)

        self.client.force_authenticate(self.kitchen)
        response = self.client.get("/api/cart/reception/")
        self.assertEqual(response.status_code, 403)
        response = self.client.get("/api/cart/kitchen/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        self.client.force_authenticate(self.reception)
        response = self.client.post(
            f"/api/cart/reception/table/{tables[0].id}/release/",
            {}, format="json",
        )
        self.assertEqual(response.status_code, 409)
