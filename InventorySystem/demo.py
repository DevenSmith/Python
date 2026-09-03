from inventory import InventorySystem


def show_stock(inventory: InventorySystem) -> None:
    for product in inventory.products_by_id.values():
        print(
            f"  {product.display_name}: on hand={product.on_hand}, "
            f"reserved={product.reserved}, available={product.available}"
        )


def main() -> None:
    inventory = InventorySystem()
    inventory.add_product("keyboard", "Keyboard", "USB keyboard")
    inventory.add_product("mouse", "Mouse", "Wireless mouse")
    inventory.receive_stock("keyboard", 10)
    inventory.receive_stock("mouse", 2)

    print("Checkout with insufficient stock:")
    failed = inventory.create_reservation({"keyboard": 2, "mouse": 3})
    for shortage in failed.shortages:
        print(
            f"  {shortage.product_id}: requested {shortage.requested}, "
            f"available {shortage.available}, reduce by {shortage.missing}"
        )
    show_stock(inventory)

    print("\nSuccessful checkout:")
    result = inventory.create_reservation({"keyboard": 3, "mouse": 1})
    assert result.reservation_id is not None
    show_stock(inventory)

    print("\nCancel that reservation:")
    inventory.release_reservation(result.reservation_id)
    show_stock(inventory)

    print("\nReserve and ship a new order:")
    shipped = inventory.create_reservation({"keyboard": 3})
    assert shipped.reservation_id is not None
    inventory.finalize_reservation(shipped.reservation_id)
    show_stock(inventory)
    print("Repeated shipment accepted:", inventory.finalize_reservation(shipped.reservation_id))

    print("\nRetained reservation records:")
    for reservation in inventory.reservations_by_id.values():
        print(f"  {reservation.reservation_id}: {reservation.status.value}, {reservation.items}")


if __name__ == "__main__":
    main()
