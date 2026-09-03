"""Single-threaded, in-memory inventory and reservation subsystem."""

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class ReservationStatus(Enum):
    ACTIVE = "active"
    RELEASED = "released"
    FINALIZED = "finalized"


@dataclass
class Product:
    product_id: str
    display_name: str
    description: str
    on_hand: int = 0
    reserved: int = 0

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


@dataclass
class Reservation:
    reservation_id: str
    items: dict[str, int]
    status: ReservationStatus = ReservationStatus.ACTIVE


@dataclass
class Shortage:
    product_id: str
    requested: int
    available: int

    @property
    def missing(self) -> int:
        return self.requested - self.available


@dataclass
class ReservationResult:
    reservation_id: str | None = None
    shortages: list[Shortage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.reservation_id is not None


class InventorySystem:
    def __init__(self) -> None:
        self.products_by_id: dict[str, Product] = {}
        self.reservations_by_id: dict[str, Reservation] = {}

    def add_product(
        self, product_id: str, display_name: str, description: str = ""
    ) -> None:
        """Register a product with zero stock. Receive stock separately."""
        if not isinstance(product_id, str) or not product_id.strip():
            raise ValueError("Product ID must be a nonempty string")
        if product_id in self.products_by_id:
            raise ValueError(f"Product already exists: {product_id}")
        self.products_by_id[product_id] = Product(product_id, display_name, description)

    def receive_stock(self, product_id: str, quantity: int) -> None:
        """Add a shipment to physical inventory."""
        if not self._is_positive_integer(quantity):
            raise ValueError("Quantity must be a positive integer")
        product = self._get_product(product_id)
        product.on_hand += quantity

    def get_available(self, product_id: str) -> int:
        return self._get_product(product_id).available

    def create_reservation(self, items: dict[str, int]) -> ReservationResult:
        """Reserve every requested item or none; return all validation failures."""
        if not items:
            return ReservationResult(errors=["Reservation must contain at least one item"])

        # Copy the basket so later caller edits cannot change the reservation.
        requested_items = dict(items)
        result = ReservationResult()

        # First pass: validate everything without changing any inventory.
        for product_id, quantity in requested_items.items():
            valid_id = isinstance(product_id, str) and bool(product_id.strip())
            product = self.products_by_id.get(product_id) if valid_id else None
            if product is None:
                result.errors.append(f"Unknown product: {product_id}")
            if not self._is_positive_integer(quantity):
                result.errors.append(f"Quantity for {product_id} must be a positive integer")
                continue
            if product is not None and quantity > product.available:
                result.shortages.append(Shortage(product_id, quantity, product.available))

        if result.errors or result.shortages:
            return result

        reservation_id = str(uuid4())
        reservation = Reservation(reservation_id, requested_items)

        # Second pass: all checks passed, so reserve every item.
        for product_id, quantity in requested_items.items():
            self.products_by_id[product_id].reserved += quantity
        self.reservations_by_id[reservation_id] = reservation
        return ReservationResult(reservation_id=reservation_id)

    def release_reservation(self, reservation_id: str) -> bool:
        """Cancel an active reservation; preserve its record for later lookup."""
        reservation = self._get_reservation(reservation_id)
        if reservation.status != ReservationStatus.ACTIVE:
            return False
        self._validate_reserved_stock(reservation)

        for product_id, quantity in reservation.items.items():
            self.products_by_id[product_id].reserved -= quantity
        reservation.status = ReservationStatus.RELEASED
        return True

    def finalize_reservation(self, reservation_id: str) -> bool:
        """Ship an active reservation. Deduct its quantities exactly once."""
        reservation = self._get_reservation(reservation_id)
        if reservation.status != ReservationStatus.ACTIVE:
            return False
        self._validate_reserved_stock(reservation)

        for product_id, quantity in reservation.items.items():
            product = self.products_by_id[product_id]
            product.on_hand -= quantity
            product.reserved -= quantity
        reservation.status = ReservationStatus.FINALIZED
        return True

    def _validate_reserved_stock(self, reservation: Reservation) -> None:
        """Check all items before modifying any, including internal consistency."""
        for product_id, quantity in reservation.items.items():
            product = self.products_by_id.get(product_id)
            if (
                product is None
                or not self._is_positive_integer(quantity)
                or not 0 <= quantity <= product.reserved <= product.on_hand
            ):
                raise RuntimeError(f"Inconsistent reserved stock for product: {product_id}")

    def _get_product(self, product_id: str) -> Product:
        if product_id not in self.products_by_id:
            raise KeyError(f"Unknown product: {product_id}")
        return self.products_by_id[product_id]

    def _get_reservation(self, reservation_id: str) -> Reservation:
        if reservation_id not in self.reservations_by_id:
            raise KeyError(f"Unknown reservation: {reservation_id}")
        return self.reservations_by_id[reservation_id]

    @staticmethod
    def _is_positive_integer(quantity: int) -> bool:
        # bool is a subclass of int in Python, but isn't a stock quantity.
        return type(quantity) is int and quantity > 0
