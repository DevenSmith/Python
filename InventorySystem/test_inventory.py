import unittest

from inventory import InventorySystem, ReservationStatus


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = InventorySystem()
        for product_id, quantity in [("keyboard", 10), ("mouse", 2), ("monitor", 1)]:
            self.inventory.add_product(product_id, product_id.title())
            self.inventory.receive_stock(product_id, quantity)

    def reserve(self, items: dict[str, int]) -> str:
        result = self.inventory.create_reservation(items)
        self.assertTrue(result.succeeded)
        assert result.reservation_id is not None
        return result.reservation_id

    def test_all_shortages_reported_without_partial_reservation(self) -> None:
        result = self.inventory.create_reservation({"keyboard": 2, "mouse": 3, "monitor": 4})
        self.assertFalse(result.succeeded)
        self.assertEqual(
            [(s.product_id, s.requested, s.available, s.missing) for s in result.shortages],
            [("mouse", 3, 2, 1), ("monitor", 4, 1, 3)],
        )
        self.assertTrue(all(p.reserved == 0 for p in self.inventory.products_by_id.values()))
        self.assertEqual(self.inventory.reservations_by_id, {})

    def test_invalid_requests_leave_inventory_unchanged(self) -> None:
        for items in [{}, {"unknown": 1}, {"keyboard": 0}, {"keyboard": -1},
                      {"keyboard": 1.5}, {"keyboard": True}]:
            with self.subTest(items=items):
                result = self.inventory.create_reservation(items)
                self.assertFalse(result.succeeded)
                self.assertTrue(result.errors)
        self.assertEqual(self.inventory.get_available("keyboard"), 10)
        self.assertEqual(self.inventory.reservations_by_id, {})

    def test_release_preserves_record_and_cannot_be_repeated_or_shipped(self) -> None:
        reservation_id = self.reserve({"keyboard": 3, "mouse": 1})
        self.assertEqual(self.inventory.get_available("keyboard"), 7)
        self.assertTrue(self.inventory.release_reservation(reservation_id))
        self.assertEqual(self.inventory.get_available("keyboard"), 10)
        self.assertEqual(self.inventory.get_available("mouse"), 2)
        self.assertFalse(self.inventory.release_reservation(reservation_id))
        self.assertFalse(self.inventory.finalize_reservation(reservation_id))
        reservation = self.inventory.reservations_by_id[reservation_id]
        self.assertEqual(reservation.status, ReservationStatus.RELEASED)
        self.assertEqual(reservation.items, {"keyboard": 3, "mouse": 1})

    def test_shipping_deducts_only_this_reservation_and_only_once(self) -> None:
        first = self.reserve({"keyboard": 3})
        second = self.reserve({"keyboard": 2})
        self.assertTrue(self.inventory.finalize_reservation(first))
        product = self.inventory.products_by_id["keyboard"]
        self.assertEqual((product.on_hand, product.reserved, product.available), (7, 2, 5))
        self.assertFalse(self.inventory.finalize_reservation(first))
        self.assertFalse(self.inventory.release_reservation(first))
        self.assertEqual(self.inventory.reservations_by_id[first].status, ReservationStatus.FINALIZED)
        self.inventory.release_reservation(second)
        self.assertEqual((product.on_hand, product.reserved, product.available), (7, 0, 7))

    def test_exact_stock_and_caller_basket_changes(self) -> None:
        basket = {"mouse": 2}
        reservation_id = self.reserve(basket)
        basket["mouse"] = 100
        self.assertFalse(self.inventory.create_reservation({"mouse": 1}).succeeded)
        self.inventory.finalize_reservation(reservation_id)
        self.assertEqual(self.inventory.get_available("mouse"), 0)

    def test_unknown_reservation_and_invalid_shipments(self) -> None:
        for operation in [self.inventory.release_reservation, self.inventory.finalize_reservation]:
            with self.assertRaises(KeyError):
                operation("unknown")
        with self.assertRaises(ValueError):
            self.inventory.receive_stock("keyboard", -1)
        with self.assertRaises(ValueError):
            self.inventory.add_product("keyboard", "Duplicate")
        with self.assertRaises(KeyError):
            self.inventory.receive_stock("unknown", 1)

    def test_consistency_checks_prevent_partial_changes(self) -> None:
        for operation_name in ["release_reservation", "finalize_reservation"]:
            with self.subTest(operation=operation_name):
                self.setUp()
                reservation_id = self.reserve({"keyboard": 2, "mouse": 1})
                del self.inventory.products_by_id["mouse"]  # Simulate internal corruption.
                with self.assertRaises(RuntimeError):
                    getattr(self.inventory, operation_name)(reservation_id)
                product = self.inventory.products_by_id["keyboard"]
                self.assertEqual((product.on_hand, product.reserved), (10, 2))
                self.assertEqual(self.inventory.reservations_by_id[reservation_id].status,
                                 ReservationStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()
