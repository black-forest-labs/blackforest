# Static type-check fixture (NOT run by pytest — it's a pyright smoke target).
#
# Verifies the typed keyword surface: every call below uses valid, model-
# appropriate keywords and must type-check cleanly under:
#     npx pyright tests/typing/check_generate_kwargs.py
#
# Manual negative check (proves typos are caught): add an unknown keyword such
# as `client.generate("x", guidancee=6.0)` and pyright reports
# `No parameter named "guidancee" (reportCallIssue)`.
from bfl import BFL

client = BFL(api_key="bfl_" + "x" * 32)

# Top-level flat path with a model string + typed kwargs.
client.generate("a fox", model="flux-2-flex", guidance=6.0, steps=40)

# Namespaced accessors expose the same typed keyword surface.
client.flux2.flex.submit("a fox", guidance=6.0, steps=40, seed=7)
client.flux2.pro.generate("a fox", width=1024, height=1024, output_format="png")
client.flux2.pro.generate("a fox", transparent_bg=True, output_format="png")
client.tools.outpaint.submit(input_image="a.png", width=1920, height=1080)
client.tools.vto.submit(prompt="try on", person="p.png", garment="g.png")
