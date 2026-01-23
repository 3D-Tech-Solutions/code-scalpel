"""
Demo Application for Code Scalpel MCP Server

This is a sample application with intentionally verbose code to demonstrate
the token efficiency of Code Scalpel's extract_code tool.

In a real scenario, this file would be 500+ lines. For demo purposes,
we've included enough functions to show the extraction capability.
"""

import json
import logging
from datetime import datetime
from typing import Any

# Configuration and Constants
TAX_RATES = {
    "CA": 0.0725,
    "NY": 0.04,
    "TX": 0.0625,
    "FL": 0.06,
    "WA": 0.065,
    "IL": 0.0625,
    "PA": 0.06,
    "OH": 0.0575,
}

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "crypto", "bank_transfer"]

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
}


# Core Business Logic Functions


def calculate_tax(amount: float, state: str) -> float:
    """
    Calculate sales tax based on state.

    This function demonstrates Code Scalpel's ability to extract
    just the function you need from a large file.

    Args:
        amount: The pre-tax amount
        state: Two-letter state code (e.g., 'CA', 'NY')

    Returns:
        The tax amount to be added

    Example:
        >>> calculate_tax(100.0, 'CA')
        7.25
    """
    rate = TAX_RATES.get(state.upper(), 0.0)
    return round(amount * rate, 2)


def calculate_total(subtotal: float, state: str, discount_code: str | None = None) -> dict[str, float]:
    """
    Calculate order total including tax and discounts.

    Args:
        subtotal: Pre-tax subtotal
        state: Two-letter state code
        discount_code: Optional discount code

    Returns:
        Dictionary with subtotal, tax, discount, and total
    """
    discount = apply_discount(subtotal, discount_code) if discount_code else 0.0
    discounted_subtotal = subtotal - discount
    tax = calculate_tax(discounted_subtotal, state)
    total = discounted_subtotal + tax

    return {
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
    }


def apply_discount(amount: float, discount_code: str) -> float:
    """
    Apply discount code to amount.

    Args:
        amount: Original amount
        discount_code: Discount code to apply

    Returns:
        Discount amount to subtract
    """
    # Simulated discount database
    discounts = {
        "SAVE10": 0.10,
        "SAVE20": 0.20,
        "WELCOME": 0.15,
        "VIP": 0.25,
    }

    rate = discounts.get(discount_code.upper(), 0.0)
    return round(amount * rate, 2)


def process_payment(amount: float, method: str, payment_details: dict[str, Any]) -> dict[str, Any]:
    """
    Process payment with given method.

    Args:
        amount: Amount to charge
        method: Payment method (credit_card, paypal, etc.)
        payment_details: Payment-specific details

    Returns:
        Payment result with transaction ID and status
    """
    if method not in PAYMENT_METHODS:
        return {
            "success": False,
            "error": f"Invalid payment method: {method}",
            "transaction_id": None,
        }

    # Simulate payment processing
    transaction_id = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Validate payment details based on method
    if method == "credit_card":
        if not validate_credit_card(payment_details):
            return {
                "success": False,
                "error": "Invalid credit card details",
                "transaction_id": None,
            }

    return {
        "success": True,
        "transaction_id": transaction_id,
        "amount": amount,
        "method": method,
        "processed_at": datetime.now().isoformat(),
    }


def validate_credit_card(details: dict[str, str]) -> bool:
    """
    Validate credit card details.

    Args:
        details: Dictionary with card_number, cvv, expiry

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["card_number", "cvv", "expiry"]

    # Check all required fields present
    if not all(field in details for field in required_fields):
        return False

    # Basic card number validation (Luhn algorithm would go here)
    card_number = details["card_number"].replace(" ", "").replace("-", "")
    if not card_number.isdigit() or len(card_number) not in [15, 16]:
        return False

    # CVV validation
    cvv = details["cvv"]
    if not cvv.isdigit() or len(cvv) not in [3, 4]:
        return False

    # Expiry validation (format: MM/YY)
    try:
        month, year = details["expiry"].split("/")
        if not (1 <= int(month) <= 12):
            return False
    except (ValueError, AttributeError):
        return False

    return True


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format amount as currency string.

    Args:
        amount: Amount to format
        currency: Currency code (USD, EUR, etc.)

    Returns:
        Formatted currency string
    """
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return f"{symbol}{amount:,.2f}"


def calculate_shipping(weight_kg: float, destination: str, express: bool = False) -> float:
    """
    Calculate shipping cost based on weight and destination.

    Args:
        weight_kg: Package weight in kilograms
        destination: Destination country code
        express: Whether to use express shipping

    Returns:
        Shipping cost
    """
    # Base rates per kg
    base_rates = {
        "US": 5.00,
        "CA": 7.00,
        "UK": 10.00,
        "EU": 12.00,
        "AU": 15.00,
    }

    base_rate = base_rates.get(destination, 20.00)
    cost = base_rate * weight_kg

    # Express shipping multiplier
    if express:
        cost *= 1.5

    return round(cost, 2)


def generate_invoice(order_id: str, items: list[dict], customer: dict) -> dict:
    """
    Generate invoice for order.

    Args:
        order_id: Unique order identifier
        items: List of order items
        customer: Customer information

    Returns:
        Complete invoice data
    """
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    total_data = calculate_total(subtotal, customer["state"])

    invoice = {
        "invoice_number": f"INV-{order_id}",
        "date": datetime.now().isoformat(),
        "customer": {
            "name": customer["name"],
            "email": customer["email"],
            "address": customer["address"],
        },
        "items": items,
        "subtotal": total_data["subtotal"],
        "tax": total_data["tax"],
        "discount": total_data["discount"],
        "total": total_data["total"],
    }

    return invoice


def send_confirmation_email(email: str, order_data: dict) -> bool:
    """
    Send order confirmation email to customer.

    Args:
        email: Customer email address
        order_data: Order information

    Returns:
        True if email sent successfully
    """
    # This would integrate with an email service in production
    logging.info(f"Sending confirmation email to {email}")
    logging.info(f"Order ID: {order_data.get('order_id')}")

    # Simulate email sending
    return True


def log_transaction(transaction_data: dict) -> None:
    """
    Log transaction for audit purposes.

    Args:
        transaction_data: Transaction details to log
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "transaction": transaction_data,
    }

    # In production, this would write to a database or log file
    logging.info(f"Transaction logged: {json.dumps(log_entry)}")


def get_customer_order_history(customer_id: str) -> list[dict]:
    """
    Retrieve customer's order history.

    Args:
        customer_id: Customer identifier

    Returns:
        List of previous orders
    """
    # This would query a database in production
    # For demo purposes, return empty list
    return []


def calculate_loyalty_points(order_total: float) -> int:
    """
    Calculate loyalty points earned from purchase.

    Args:
        order_total: Total order amount

    Returns:
        Number of loyalty points earned
    """
    # 1 point per dollar spent, with bonuses
    base_points = int(order_total)

    # Bonus points for large orders
    if order_total > 100:
        base_points = int(base_points * 1.5)
    elif order_total > 50:
        base_points = int(base_points * 1.2)

    return base_points


# ... In a real application, this file would continue for hundreds more lines
# with additional utility functions, database queries, API integrations, etc.
# The point of Code Scalpel is that you can extract just the function you need
# without loading this entire file into the AI's context window.


if __name__ == "__main__":
    # Example usage
    amount = 100.0
    state = "CA"
    tax = calculate_tax(amount, state)
    print(f"Tax on ${amount} in {state}: ${tax}")

    total = calculate_total(100.0, "CA", "SAVE10")
    print(f"Order total: {json.dumps(total, indent=2)}")
