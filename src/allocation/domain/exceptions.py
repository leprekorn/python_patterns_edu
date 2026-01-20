class AllocationError(Exception):
    """Base exception for all allocation-related errors."""

    pass


class DeallocationError(Exception):
    """Base exception for all deallocation-related errors."""

    pass


class OutOfStock(AllocationError):
    """Raised when no batch with matching SKU has available quantity."""

    pass


class InvalidSku(AllocationError):
    """Raised when invalid SKU passed."""

    pass


class InvalidBatchReference(AllocationError):
    """Raised when invalid batch reference passed."""

    pass


class UnallocatedLine(DeallocationError):
    """Raised when trying to deallocate a line that was not allocated."""

    pass
