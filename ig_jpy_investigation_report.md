# IG Demo API JPY Pairs Rejection Investigation Report

## Executive Summary

The issue with JPY pairs (GBPJPY, USDJPY, EURJPY) being rejected with `dealStatus: REJECTED` and `reason: UNKNOWN` is most likely due to an **incorrect `currency_code` parameter** in the API request.

## Root Cause

The `currency_code` parameter in `create_open_position()` is **NOT** your account currency (EUR) - it is the **counter currency of the market** being traded.

### The Problem

| Pair | Base Currency | Counter Currency | Correct `currency_code` |
|------|---------------|------------------|------------------------|
| EURUSD | EUR | USD | `"USD"` |
| GBPUSD | GBP | USD | `"USD"` |
| XAUUSD | XAU | USD | `"USD"` |
| **GBPJPY** | GBP | **JPY** | **`"JPY"`** |
| **USDJPY** | USD | **JPY** | **`"JPY"`** |
| **EURJPY** | EUR | **JPY** | **`"JPY"`** |

### Why Other Pairs Work

If you've been using `currency_code="EUR"` for all pairs:
- EURUSD, GBPUSD, XAUUSD work because they accept USD as the counter currency
- EUR accounts can trade USD-denominated pairs
- But JPY pairs explicitly require JPY as the counter currency

## Evidence from IG API Library Issue #186

From the official trading-ig GitHub repository, issue #186 documents the exact same problem:

> **User reported:** "'reason': 'UNKNOWN', 'dealStatus': 'REJECTED'"

> **Resolution:** "I thought that currency_code was the currency of my account, but it is the currency of the market."

Source: https://github.com/ig-python/trading-ig/issues/186

## Solution

### Correct API Call for JPY Pairs

```javascript
// INCORRECT - Using account currency
{
  "currencyCode": "EUR",  // ❌ Wrong - this is your account currency
  "epic": "CS.D.GBPJPY.CFD.IP",
  ...
}

// CORRECT - Using market counter currency
{
  "currencyCode": "JPY",  // ✅ Correct - this is the pair's counter currency
  "epic": "CS.D.GBPJPY.CFD.IP",
  ...
}
```

### Implementation Example

```python
# Helper function to determine currency code from epic/pair
def get_currency_code_from_pair(pair_name, epic):
    """
    Extract counter currency from forex pair or epic.
    
    Args:
        pair_name: e.g., "GBPJPY", "EURUSD"
        epic: e.g., "CS.D.GBPJPY.CFD.IP"
    
    Returns:
        str: Counter currency code (JPY, USD, etc.)
    """
    # Method 1: Extract from pair name (last 3 characters for forex)
    if pair_name and len(pair_name) >= 6:
        return pair_name[3:].upper()
    
    # Method 2: Extract from epic
    if epic:
        parts = epic.split('.')
        if len(parts) >= 3:
            # Epic format: CS.D.XXXYYY.CFD.IP
            currency_pair = parts[2]
            return currency_pair[3:].upper()
    
    # Fallback for JPY pairs
    if 'JPY' in (pair_name or epic):
        return 'JPY'
    
    return 'USD'  # Default fallback


# Usage in your trading code
pairs_config = {
    'GBPJPY': {'epic': 'CS.D.GBPJPY.CFD.IP', 'currency': 'JPY'},
    'USDJPY': {'epic': 'CS.D.USDJPY.CFD.IP', 'currency': 'JPY'},
    'EURJPY': {'epic': 'CS.D.EURJPY.CFD.IP', 'currency': 'JPY'},
    'EURUSD': {'epic': 'CS.D.EURUSD.CFD.IP', 'currency': 'USD'},
    'GBPUSD': {'epic': 'CS.D.GBPUSD.CFD.IP', 'currency': 'USD'},
    'XAUUSD': {'epic': 'CS.D.XAUUSD.CFD.IP', 'currency': 'USD'},
}

# Create position with correct currency
def create_position(pair, direction, size):
    config = pairs_config.get(pair, {})
    
    params = {
        'currencyCode': config.get('currency', 'USD'),  # Use pair's currency, not account currency
        'epic': config.get('epic'),
        'direction': direction,
        'size': size,
        'orderType': 'MARKET',
        'expiry': '-',
        'forceOpen': 'true',
        'guaranteedStop': 'false',
        # ... other params
    }
    
    return ig_service.create_open_position(**params)
```

## Additional Considerations

### 1. Demo Account Limitations
IG Demo accounts can have different restrictions than Live accounts. However, since JPY pairs worked before March 19, 2026, this suggests a recent change in:
- API validation stricter enforcement
- Account settings
- Market availability

### 2. IG API Version
Ensure you're using API version 2 for position creation:
```python
# The library uses version 2 by default for create_open_position
version = "2"  # Recommended for new applications
```

### 3. Alternative: Check Market Details First
Always verify market availability before placing orders:

```python
# Fetch market details to confirm trading is enabled
market_details = ig_service.fetch_market_by_epic(epic)
print(f"Market Status: {market_details.marketStatus}")
print(f"Currency: {market_details.snapshot.currency}")
```

## Testing Checklist

1. **Test with correct currency_code:**
   ```python
   # Test JPY pair with JPY currency
   result = ig_service.create_open_position(
       currency_code='JPY',  # NOT 'EUR' or 'USD'
       epic='CS.D.GBPJPY.CFD.IP',
       direction='BUY',
       size=0.5,
       ...
   )
   ```

2. **Verify with API Companion:**
   - Use IG's REST API Companion: https://labs.ig.com/sample-apps/api-companion/index.html
   - Test the same parameters to isolate API vs library issues

3. **Check Account Preferences:**
   - Login to IG web platform
   - Verify demo account is active and funded
   - Check for any account-specific restrictions

## Related IG API Error Codes

Common rejection reasons to watch for:
- `REJECT_CFD_ORDER_ON_SPREADBET_ACCOUNT` - Wrong expiry format (use `'-'` for CFDs)
- `error.public-api.failure.kyc.required` - Need to complete KYC verification
- `error.public-api.exceeded-account-trading-allowance` - Rate limit hit
- `UNKNOWN` - Often indicates parameter validation failure (like wrong currency)

## References

1. IG Labs API Documentation: https://labs.ig.com/rest-trading-api-reference
2. trading-ig GitHub Issue #186: https://github.com/ig-python/trading-ig/issues/186
3. IG Status Page: https://status.ig.com/ (no incidents reported March 19-24, 2026)

## Conclusion

The most likely cause of JPY pair rejections is using the account currency (EUR) instead of the pair's counter currency (JPY) in the `currency_code` parameter. Update your code to dynamically set `currency_code` based on the pair being traded, and JPY pairs should work correctly.

If the issue persists after correcting the currency_code, contact IG API support at webapisupport@ig.com with:
- Account ID
- Exact API request/response (redact sensitive data)
- Timestamp of failed trades
- Epic codes being used
