# Inventory system interview practice

Python 3.10+, standard library only. From this folder run:

```powershell
python demo.py
python -m unittest -v
```

Start reviewing `inventory.py`: the data classes come first, followed by the
inventory service. `demo.py` demonstrates shortage reporting, checkout,
cancellation, shipping, and retained reservation records.

## Agreed design

- Products have an ID, display name, description, on-hand quantity, and reserved
  quantity. Available stock is calculated as `on_hand - reserved`.
- `products_by_id` maps product IDs to products. `reservations_by_id` maps
  reservation IDs to reservations.
- Each reservation has a UUID string ID, a copied dictionary of product IDs and
  quantities, and an ACTIVE, RELEASED, or FINALIZED status.
- Baskets are outside this subsystem. Checkout submits a complete item request.
- Creation checks all items before changing stock. Empty requests, unknown
  products, and non-positive or non-integer quantities fail. All shortages are
  returned with requested and available quantities. No partial reservations.
- Release cancels: decrease reserved quantities, preserve physical stock, and
  retain the reservation as RELEASED.
- Finalize ships: decrease both on-hand and reserved quantities by this
  reservation's quantities, and retain the record as FINALIZED.
- Repeating either transition, or attempting the other transition afterward,
  returns False without changing stock. Unknown reservation IDs raise KeyError.
- Inconsistent internal stock raises RuntimeError before any transition changes.

## API

| Method | Result |
| --- | --- |
| `add_product(product_id, display_name, description="")` | Registers zero-stock product; duplicates raise ValueError |
| `receive_stock(product_id, quantity)` | Increases on-hand stock; invalid quantity raises ValueError |
| `get_available(product_id)` | Current availability; unknown product raises KeyError |
| `create_reservation(items)` | ReservationResult with an ID on success, or errors/shortages on failure |
| `release_reservation(reservation_id)` | True when released, False when already inactive |
| `finalize_reservation(reservation_id)` | True when shipped, False when already inactive |

Single thread, in memory, approximately 10,000 products. No backorders, automatic
expiry, persistence, partial shipments, basket editing, users, or timestamps.
The calling application displays errors and requests release or finalization.
Availability is only a snapshot until a reservation succeeds.

Lookup is average O(1); creating, releasing, and finalizing a reservation are O(k)
for k distinct products in that reservation. Completed records remain in memory.
The dictionaries and data classes are exposed for learning and inspection;
callers should modify inventory through the service methods, not edit records
directly. Concurrent callers would require synchronization around the complete
validation-and-update operation.
