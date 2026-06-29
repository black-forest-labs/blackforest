"""The one-liner happy path: text -> image -> file.

export BFL_API_KEY=...    # get one at https://dashboard.bfl.ai
python examples/quickstart.py
"""

from bfl import BFL

client = BFL()  # reads $BFL_API_KEY

image = client.generate(
    "a red fox curled up in fresh snow, soft morning light, photographic",
)
path = image.save("fox.png")

print(f"Saved {path}")
print(f"Signed URL: {image.url}")
print(f"Seed: {image.seed}")
