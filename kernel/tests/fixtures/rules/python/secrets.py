# This is a safe retrieval
import os
my_secret = os.getenv("sk_live_1234567890abcdef")
config_key = os.environ["sk_live_1234567890abcdef"]

# This is a violation (direct assignment)
stripe_secret = "sk_live_1234567890abcdef"

# This is a violation in dictionary
config = {
    "key": "sk_live_1234567890abcdef"
}

# This is a violation in a call
api.setup(secret="sk_live_1234567890abcdef")
