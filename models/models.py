"""
Data Models for Price Scout.

This module defines Pydantic models used throughout the Price Scout application
for type safety and data validation.

Classes:
    PriceResult: Model representing a price query result from a vendor.
"""

import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field
from decimal import Decimal


class PriceResult(BaseModel):
    """
    Data model representing the result of a price query from a vendor.

    This model encapsulates all information about a product's price at a specific
    vendor, including metadata like URL, MPN confirmation, and availability status.

    Attributes:
        vendor_id: Unique identifier for the vendor (e.g., "scorptec", "mwave").
        url: HTTP URL to the product page, if found.
        mpn: Manufacturer Part Number as confirmed on the product page.
        price: Product price as a Decimal for precise financial calculations.
        currency: ISO 4217 currency code (e.g., "AUD", "USD").
        found: Boolean indicating whether the product was found at this vendor.

    Example:
        >>> result = PriceResult(
        ...     vendor_id="scorptec",
        ...     url="https://www.scorptec.com.au/product/cpu",
        ...     mpn="BX8071512100F",
        ...     price=Decimal("245.00"),
        ...     currency="AUD",
        ...     found=True
        ... )
        >>> print(f"{result.vendor_id}: ${result.price} {result.currency}")
        scorptec: $245.00 AUD

    Note:
        - price is Optional and will be None if the product is not found or price unavailable
        - url and mpn are also Optional for cases where the product doesn't exist
        - found=False should be used when the product is not available at the vendor
    """

    vendor_id: str
    url: Optional[HttpUrl] = None
    mpn: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    found: bool 