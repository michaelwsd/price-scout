"""
Base Scraper Abstract Class.

This module defines the abstract base class for all vendor-specific scrapers.
All scrapers must inherit from BaseScraper and implement the scrape() method.

Classes:
    BaseScraper: Abstract base class with common scraper interface and configuration.
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel
from .models import PriceResult


class BaseScraper(BaseModel, ABC):
    """
    Abstract base class for vendor-specific price scrapers.

    This class provides a common interface and configuration structure for all
    scrapers. Each vendor scraper must inherit from this class and implement
    the scrape() method.

    Attributes:
        vendor_id: Unique identifier for the vendor (e.g., "scorptec", "mwave").
        currency: Currency code for prices (default: "AUD" for Australian Dollar).
        not_found: Default PriceResult object returned when product is not found.

    Configuration:
        arbitrary_types_allowed: Allows usage of non-Pydantic types in model fields.

    Example:
        >>> class CustomScraper(BaseScraper):
        ...     vendor_id: str = "custom_vendor"
        ...     currency: str = "AUD"
        ...     not_found = PriceResult(vendor_id=vendor_id, found=False)
        ...
        ...     async def scrape(self, mpn: str) -> PriceResult:
        ...         # Implementation here
        ...         pass
    """

    vendor_id: str
    currency: str
    not_found: PriceResult

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True

    @abstractmethod
    async def scrape(self, mpn: str) -> PriceResult:
        """
        Extract price and metadata for a given MPN from the vendor's website.

        This is an abstract method that must be implemented by all subclasses.
        Each implementation should handle vendor-specific scraping logic.

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult object containing:
                - vendor_id: Identifier of the vendor
                - url: Product page URL
                - mpn: Confirmed MPN from the page
                - price: Product price (Decimal)
                - currency: Currency code
                - found: Boolean indicating if product was found

        Raises:
            NotImplementedError: If subclass doesn't implement this method.

        Example:
            >>> scraper = ScorptecScraper()
            >>> result = await scraper.scrape("BX8071512100F")
            >>> print(f"Price: ${result.price}")
        """
