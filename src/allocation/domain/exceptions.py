class AllocationError(Exception):
    """Base exception for all allocation-related errors."""

    pass


class OutOfStock(AllocationError):
    """Raised when no batch with matching SKU has available quantity."""

    pass


class InvalidSku(AllocationError):
    """Raised when invalid SKU passed."""

    pass
