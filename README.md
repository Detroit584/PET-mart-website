# PetMart — Final Package (SQLite)

## What's included
- Flask app (auth, product listing, cart, checkout via Stripe test mode)
- 10 seeded products + 4 banner images (carousel)
- Auto-seeding on first run (creates default admin & products)
- `seed.py` for manual reseeding
- `static/images/` (banners + product images) — real stock photos attempted; fallback SVGs used if download failed.

## Quick start (Windows)
1. Unzip `PetMart_final.zip` and open PowerShell in the project folder.
2. Create a virtual environment and activate it:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. Install dependencies (pinned versions):
   ```powershell
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and paste your **Stripe TEST** keys:
   - Go to https://dashboard.stripe.com/test/apikeys
   - Use the **Publishable key** (pk_test_...) and the **Secret key** (sk_test_...)
   Example `.env` (replace the ... with your keys):
   ```text
   STRIPE_SECRET_KEY=sk_test_XXXXXXXXXXXXXXXXXXXXXXXX
   STRIPE_PUBLISHABLE_KEY=pk_test_YYYYYYYYYYYYYYYYYYYYYYY
   DATABASE_URL=sqlite:///petmart.db
   FLASK_ENV=development
   SECRET_KEY=change_this_to_a_random_secret_string
   ```
5. Run the app (first run will auto-create DB & seed data):
   ```powershell
   python app.py
   ```
6. Open http://127.0.0.1:5000 in your browser.
   - Default admin login: **admin@petmart.com / admin123**

## Manual reseed (if you want to wipe & reseed):
```powershell
python seed.py
```

## Stripe test checkout (step-by-step)
1. Make sure you added your Stripe test keys to `.env` (see above).
2. Add items to cart as a logged-in user (or login with admin).
3. Go to Checkout and click **Pay with Stripe**.
4. In the Stripe-hosted test checkout page, use this test card:
   - Card number: `4242 4242 4242 4242`
   - Expiry: any future date (e.g., `12/34`)
   - CVC: any 3 digits (e.g., `123`)
   - ZIP: any 5 digits (e.g., `110001`)
5. After payment, you should be redirected to the app's **Payment success** page and the order will be stored in the DB.

## Replacing images
If any images are SVG placeholders (file names are clear), you can replace them with your own JPG/PNG files in `static/images/` (keep the same filenames).

## Troubleshooting
- If `python app.py` exits immediately, run it with:
  ```powershell
  python -m flask run
  ```
  or check the terminal for errors and paste them here for help.
- If Stripe checkout errors, verify your keys in `.env` and internet connectivity.

Enjoy — and tell me if you want any small UI or feature tweaks!

