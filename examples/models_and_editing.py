"""Model selection, jobs, progress, and reference-image editing.

python examples/models_and_editing.py
"""

from bfl import BFL

client = BFL()

# 1. Highest quality, with explicit dimensions.
hero = client.flux2.max.generate(
    "a neon-lit alley in the rain at night, cinematic, shallow depth of field",
    width=1536,
    height=1024,
    seed=7,
)
hero.save("alley.png")

# 2. Non-blocking submit -> do other work -> wait with a progress callback.
job = client.flux2.pro.submit("a serene mountain lake at dawn")
print(f"Submitted {job.id} (est. cost {job.cost} credits)")
result = job.wait(on_progress=lambda p: print("  ...", p.get("status")))
result.save("lake.png")

# 3. Flex exposes guidance + steps for fine control.
poster = client.flux2.flex.generate(
    "an intricate art-nouveau travel poster of the Black Forest",
    guidance=6.0,
    steps=40,
)
poster.save("poster.png")

# 4. Edit using reference images (paths, URLs, bytes, or PIL — all accepted).
edited = client.flux2.pro.generate(
    "place the subject on a marble countertop with studio lighting",
    images=["alley.png", "lake.png"],
)
edited.save("composite.png")

print("Done.")
