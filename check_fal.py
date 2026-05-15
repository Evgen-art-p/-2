import requests
from studio.config import FAL_KEY, OPENROUTER_API_KEY

print("=" * 50)
print("FAL.AI — перебираем endpoints")
print("=" * 50)

urls = [
    "https://fal.ai/api/billing",
    "https://fal.ai/api/v1/billing",
    "https://fal.ai/api/me",
    "https://rest.alpha.fal.ai/billing",
    "https://rest.alpha.fal.ai/billing/v1/balance",
    "https://rest.alpha.fal.ai/v1/billing",
    "https://queue.fal.run/fal-ai/billing",
]

for url in urls:
    try:
        r = requests.get(url, headers={"Authorization": f"Key {FAL_KEY}"}, timeout=6)
        print(f"{r.status_code}  {url}")
        if r.status_code == 200:
            print(f"      → {r.text[:200]}")
    except Exception as e:
        print(f"ERR   {url}  ({e})")

print()
print("=" * 50)
print("OPENROUTER — usage (pay-as-you-go)")
print("=" * 50)

r = requests.get(
    "https://openrouter.ai/api/v1/auth/key",
    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
    timeout=6,
)
print(r.status_code, r.text[:300])
