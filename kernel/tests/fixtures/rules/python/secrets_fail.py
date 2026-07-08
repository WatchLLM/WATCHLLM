# SHOULD FAIL: hardcoded Stripe live secret
STRIPE_KEY = "sk_live_abcdefghij1234567890XYZ"

def charge(amount):
    import requests
    requests.post("https://api.stripe.com/v1/charges", headers={
        "Authorization": f"Bearer {STRIPE_KEY}"
    })
