# SHOULD PASS: secrets loaded from environment, never hardcoded
import os

STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

def charge(amount):
    import requests
    requests.post("https://api.stripe.com/v1/charges", headers={
        "Authorization": f"Bearer {STRIPE_KEY}"
    })
