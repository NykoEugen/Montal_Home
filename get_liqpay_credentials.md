# 🔑 How to Get Real Liqpay Test Credentials

## Step 1: Register on Liqpay
1. Go to [https://www.liqpay.ua/](https://www.liqpay.ua/)
2. Click "Реєстрація" (Registration)
3. Fill in your details and create an account

## Step 2: Get API Keys
1. After registration, go to your dashboard
2. Navigate to "Налаштування" (Settings) → "API"
3. You'll find your:
   - **Public Key** (starts with `i` or `sandbox_i`)
   - **Private Key** (long string)

## Step 3: Update Your Settings
Replace the placeholder credentials in `store/settings.py`:

```python
# Replace these lines:
LIQPAY_PUBLIC_KEY = os.getenv("LIQPAY_PUBLIC_KEY", "sandbox_i1234567890")
LIQPAY_PRIVATE_KEY = os.getenv("LIQPAY_PRIVATE_KEY", "sandbox_private_key")

# With your real credentials:
LIQPAY_PUBLIC_KEY = os.getenv("LIQPAY_PUBLIC_KEY", "your_real_public_key")
LIQPAY_PRIVATE_KEY = os.getenv("LIQPAY_PRIVATE_KEY", "your_real_private_key")
```

## Step 4: Test the Payment
1. Restart your Django server
2. Go to `http://localhost:8000/payments/test/`
3. Try the payment with test card: 4444555566667777

## Alternative: Use Environment Variables
```bash
export LIQPAY_PUBLIC_KEY="your_public_key"
export LIQPAY_PRIVATE_KEY="your_private_key"
export LIQPAY_SANDBOX="True"
```

Then restart your server. 