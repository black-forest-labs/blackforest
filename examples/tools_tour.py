"""A guided tour of the FLUX Tools — outpaint, erase, deblur, virtual try-on.

The four tools live under ``client.tools`` and each has its own call shape,
because each endpoint takes different inputs. This script shows all four.

Two modes:

  # INSPECT (default) — prints the exact request body + endpoint each call
  # builds and sends, WITHOUT spending any credits. Great for seeing the wire
  # contract of each tool.
  python examples/tools_tour.py

  # LIVE — actually submits each tool to the API and saves the results.
  # Needs $BFL_API_KEY and will spend credits. Generates its own inputs first
  # so you don't have to supply any files.
  LIVE=1 python examples/tools_tour.py

Image inputs everywhere accept a path, an http(s) URL, raw bytes, a PIL image,
or a base64 string — the SDK encodes whatever you pass.
"""

from __future__ import annotations

import os

from bfl import BFL
from bfl._catalog import resolve
from bfl._requests import build_payload

LIVE = os.environ.get("LIVE") == "1"


def show(title: str, model_id: str, **kwargs: object) -> None:
    """Print the endpoint + the exact JSON body this call would POST.

    Uses the SDK's own ``build_payload`` so what you see is precisely what the
    client sends — validation, image coercion, and field naming included.
    URLs are used as inputs here so nothing is read from disk in inspect mode.
    """
    spec = resolve(model_id)
    payload = build_payload(spec, dict(kwargs))
    # Truncate any long base64 so the print stays readable.
    shown = {
        k: (v[:48] + "...") if isinstance(v, str) and len(v) > 60 else v
        for k, v in payload.items()
    }
    print(f"\n# {title}")
    print(f"  POST {spec.path}")
    print(f"  body = {shown}")


# --------------------------------------------------------------------------- #
# 1. OUTPAINT — extend an image onto a larger canvas.
#    Required: input_image, width, height.  Optional: reference_offset_x/y,
#    auto_crop, mode ('high'|'fast'), prompt.  (No webhook fields here.)
# --------------------------------------------------------------------------- #
show(
    "Outpaint — widen a 1024x1024 source to a 1920x1080 canvas",
    "flux-tools-outpaint",
    input_image="https://picsum.photos/seed/fox/1024/1024",
    width=1920,
    height=1080,
    mode="high",
)

# --------------------------------------------------------------------------- #
# 2. ERASE — remove a masked object and reconstruct behind it.
#    Required: image, mask (white = remove, black = keep).
#    Optional: dilate_pixels (0-25, default 10).
# --------------------------------------------------------------------------- #
show(
    "Erase — remove the masked region",
    "flux-tools-erase",
    image="https://picsum.photos/seed/room/1024/1024",
    mask="https://picsum.photos/seed/mask/1024/1024",
    dilate_pixels=12,
)

# --------------------------------------------------------------------------- #
# 3. DEBLUR — sharpen a whole image. No prompt, no mask: just the image.
# --------------------------------------------------------------------------- #
show(
    "Deblur — sharpen the whole image",
    "flux-tools-deblur",
    image="https://picsum.photos/seed/blurry/1024/1024",
)

# --------------------------------------------------------------------------- #
# 4. VIRTUAL TRY-ON — dress a person in a garment.
#    Required: prompt, person, garment. The server maps person -> input_image
#    and garment -> input_image_2 internally.
# --------------------------------------------------------------------------- #
show(
    "Virtual try-on — put the jacket on the person",
    "flux-tools-vto",
    prompt=(
        "The person of image 1, maintaining exactly their face and pose, "
        "wearing the olive green bomber jacket of image 2."
    ),
    person="https://picsum.photos/seed/person/768/1024",
    garment="https://picsum.photos/seed/jacket/1024/1024",
)

print("\n" + "-" * 70)

if not LIVE:
    print("Inspect mode only — no API calls made, no credits spent.")
    print("Re-run with `LIVE=1 python examples/tools_tour.py` to execute them.")
    raise SystemExit(0)


# --------------------------------------------------------------------------- #
# LIVE RUN — generate real inputs with FLUX.2, then feed them through each tool.
# --------------------------------------------------------------------------- #
print("LIVE run — generating source images, then exercising each tool.\n")

client = BFL()

# A sharp source image we can outpaint and (after blurring) deblur.
src = client.flux2.flex.generate(
    "a sharp studio photo of a red apple on a wooden table, centered",
    width=1024,
    height=1024,
)
src.save("tour_source.png")
print("source ->", "tour_source.png")

# 1. Outpaint it onto a wider canvas.
wide = client.tools.outpaint.generate(
    input_image="tour_source.png", width=1536, height=1024
)
wide.save("tour_outpaint.png")
print("outpaint ->", "tour_outpaint.png")

# 2. Deblur (re-uses the source; deblur just sharpens whatever you give it).
sharp = client.tools.deblur.generate(image="tour_source.png")
sharp.save("tour_deblur.png")
print("deblur ->", "tour_deblur.png")

# 3. Virtual try-on: make a person and a garment, then combine.
person = client.flux2.flex.generate(
    "full-body studio photo of a person standing, plain background, neutral clothing",
    width=768,
    height=1024,
)
person.save("tour_person.png")
garment = client.flux2.flex.generate(
    "flat-lay product photo of an olive green bomber jacket on white background",
    width=1024,
    height=1024,
)
garment.save("tour_garment.png")
look = client.tools.vto.generate(
    prompt=(
        "The person of image 1, maintaining exactly their face and pose, "
        "wearing the olive green bomber jacket of image 2."
    ),
    person="tour_person.png",
    garment="tour_garment.png",
)
look.save("tour_vto.png")
print("vto ->", "tour_vto.png")

# Note: ERASE needs a real binary mask matching the image, so it's left to the
# inspect section above rather than guessed at here.

print("\nDone. Saved: tour_source, tour_outpaint, tour_deblur, tour_vto (.png)")
