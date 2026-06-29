"""Tests for request building, validation, and the model catalog."""

from __future__ import annotations

import pytest

from bfl import _catalog
from bfl._exceptions import BFLValidationError
from bfl._requests import build_payload, spread_images


def test_catalog_resolves_aliases():
    assert _catalog.resolve("flux2-pro").id == "flux-2-pro"
    assert _catalog.resolve("klein-9b").id == "flux-2-klein-9b"
    assert _catalog.resolve("flux-2-pro").path == "/v1/flux-2-pro"


def test_catalog_unknown_raises():
    with pytest.raises(KeyError):
        _catalog.resolve("flux-9000")


def test_canny_depth_not_registered():
    """canny/depth have no public route; they must not be addressable."""
    for missing in (
        "flux-pro-1.0-canny",
        "flux-canny",
        "flux-pro-1.0-depth",
        "flux-depth",
    ):
        with pytest.raises(KeyError):
            _catalog.resolve(missing)
    assert not any("canny" in i or "depth" in i for i in _catalog.model_ids())


def test_spread_images_slots():
    slots = spread_images(["a", "b", "c"])
    assert slots == {"input_image": "a", "input_image_2": "b", "input_image_3": "c"}


def test_spread_images_empty():
    assert spread_images(None) == {}
    assert spread_images([]) == {}


def test_flux2_pro_basic_payload():
    spec = _catalog.resolve("flux-2-pro")
    payload = build_payload(spec, {"prompt": "a fox", "width": 1024, "height": 1024})
    assert payload["prompt"] == "a fox"
    assert payload["width"] == 1024
    # Only caller-supplied fields are sent; unset defaults (output_format,
    # safety_tolerance, ...) are omitted so the server applies its own.
    assert payload == {"prompt": "a fox", "width": 1024, "height": 1024}


def test_flux2_caller_set_fields_are_sent():
    spec = _catalog.resolve("flux-2-pro")
    payload = build_payload(spec, {"prompt": "x", "output_format": "png", "seed": 5})
    assert payload["output_format"] == "png"
    assert payload["seed"] == 5


def test_flux2_4mp_limit_enforced():
    spec = _catalog.resolve("flux-2-pro")
    with pytest.raises(BFLValidationError):
        build_payload(spec, {"prompt": "x", "width": 3000, "height": 3000})


def test_flux2_4mp_boundary_ok():
    spec = _catalog.resolve("flux-2-pro")
    payload = build_payload(spec, {"prompt": "x", "width": 2048, "height": 2048})
    assert payload["width"] == 2048


def test_transparent_requires_alpha_format():
    spec = _catalog.resolve("flux-2-pro")
    with pytest.raises(BFLValidationError):
        build_payload(
            spec, {"prompt": "x", "transparent_bg": True, "output_format": "jpeg"}
        )
    # png is fine
    payload = build_payload(
        spec, {"prompt": "x", "transparent_bg": True, "output_format": "png"}
    )
    assert payload["transparent_bg"] is True


def test_flux2_min_dimension_enforced():
    spec = _catalog.resolve("flux-2-pro")
    with pytest.raises(BFLValidationError):
        build_payload(spec, {"prompt": "x", "width": 32, "height": 64})


def test_klein_4b_reference_limit():
    spec = _catalog.resolve("flux-2-klein-4b")
    imgs = spread_images([f"https://e/{i}.png" for i in range(5)])
    with pytest.raises(BFLValidationError):
        build_payload(spec, {"prompt": "x", **imgs})


def test_klein_4b_four_refs_ok():
    spec = _catalog.resolve("flux-2-klein-4b")
    imgs = spread_images([f"https://e/{i}.png" for i in range(4)])
    payload = build_payload(spec, {"prompt": "x", **imgs})
    assert payload["input_image"] == "https://e/0.png"
    assert payload["input_image_4"] == "https://e/3.png"


def test_url_image_passthrough():
    spec = _catalog.resolve("flux-2-pro")
    payload = build_payload(spec, {"prompt": "x", "input_image": "https://e/a.jpg"})
    assert payload["input_image"] == "https://e/a.jpg"


def test_prompt_upsampling_translates_to_disable_pup_for_pro():
    """pro/max accept disable_pup, not prompt_upsampling. False must disable."""
    spec = _catalog.resolve("flux-2-pro")
    payload = build_payload(spec, {"prompt": "x", "prompt_upsampling": False})
    assert payload.get("disable_pup") is True
    assert "prompt_upsampling" not in payload

    payload_on = build_payload(spec, {"prompt": "x", "prompt_upsampling": True})
    assert payload_on.get("disable_pup") is False


def test_prompt_upsampling_dropped_for_klein():
    """klein has no upsampling control; the field must not be sent."""
    spec = _catalog.resolve("flux-2-klein-9b")
    payload = build_payload(spec, {"prompt": "x", "prompt_upsampling": True})
    assert "prompt_upsampling" not in payload
    assert "disable_pup" not in payload


def test_prompt_upsampling_native_for_flex():
    """flex has a real prompt_upsampling field; pass it through unchanged."""
    spec = _catalog.resolve("flux-2-flex")
    payload = build_payload(spec, {"prompt": "x", "prompt_upsampling": False})
    assert payload["prompt_upsampling"] is False
    assert "disable_pup" not in payload


def test_prompt_upsampling_unset_is_not_sent():
    """When the caller doesn't touch it, no upsampling field is emitted."""
    spec = _catalog.resolve("flux-2-pro")
    payload = build_payload(spec, {"prompt": "x"})
    assert "disable_pup" not in payload
    assert "prompt_upsampling" not in payload


def test_flex_specific_params():
    spec = _catalog.resolve("flux-2-flex")
    payload = build_payload(spec, {"prompt": "x", "guidance": 7.0, "steps": 40})
    assert payload["guidance"] == 7.0
    assert payload["steps"] == 40


def test_flex_guidance_out_of_range():
    spec = _catalog.resolve("flux-2-flex")
    with pytest.raises(BFLValidationError):
        build_payload(spec, {"prompt": "x", "guidance": 99.0})


def test_legacy_model_still_builds():
    spec = _catalog.resolve("flux-pro-1.1")
    payload = build_payload(spec, {"prompt": "a fox", "width": 1024, "height": 768})
    assert payload["prompt"] == "a fox"


def test_webhook_fields_pass_through_on_legacy_model():
    """webhook_url/secret must reach the body for FLUX.1 too, not be dropped."""
    spec = _catalog.resolve("flux-pro-1.1")
    payload = build_payload(
        spec,
        {
            "prompt": "a fox",
            "webhook_url": "https://example.com/hook",
            "webhook_secret": "s3cret",
        },
    )
    assert payload["webhook_url"] == "https://example.com/hook"
    assert payload["webhook_secret"] == "s3cret"


def test_webhook_fields_pass_through_on_flux2():
    spec = _catalog.resolve("flux-2-pro")
    payload = build_payload(
        spec, {"prompt": "x", "webhook_url": "https://e/h", "webhook_secret": "k"}
    )
    assert payload["webhook_url"] == "https://e/h"
    assert payload["webhook_secret"] == "k"


def test_unknown_kwarg_rejected_for_flux2():
    spec = _catalog.resolve("flux-2-pro")
    with pytest.raises(BFLValidationError):
        build_payload(spec, {"prompt": "x", "bogus_field": 1})


# --- FLUX Tools -------------------------------------------------------------


def test_tools_resolve_via_aliases():
    assert _catalog.resolve("outpaint").path == "/v1/flux-tools/outpainting-v1"
    assert _catalog.resolve("erase").path == "/v1/flux-tools/erase-v1"
    assert _catalog.resolve("deblur").path == "/v1/flux-tools/deblur-v1"
    assert _catalog.resolve("vto").path == "/v1/flux-tools/vto-v1"


def test_outpaint_payload_minimal():
    spec = _catalog.resolve("flux-tools-outpaint")
    payload = build_payload(
        spec, {"input_image": "https://e/a.png", "width": 1024, "height": 1024}
    )
    assert payload == {
        "input_image": "https://e/a.png",
        "width": 1024,
        "height": 1024,
    }


def test_outpaint_canvas_limit_enforced():
    spec = _catalog.resolve("flux-tools-outpaint")
    with pytest.raises(BFLValidationError):
        build_payload(
            spec, {"input_image": "https://e/a.png", "width": 3000, "height": 3000}
        )


def test_outpaint_rejects_webhook_fields():
    """Outpainting forbids extras; webhook fields would 422 server-side."""
    spec = _catalog.resolve("flux-tools-outpaint")
    with pytest.raises(BFLValidationError):
        build_payload(
            spec,
            {
                "input_image": "https://e/a.png",
                "width": 512,
                "height": 512,
                "webhook_url": "https://e/hook",
            },
        )


def test_erase_payload_and_image_fields():
    spec = _catalog.resolve("flux-tools-erase")
    payload = build_payload(
        spec,
        {"image": "https://e/a.png", "mask": "https://e/m.png", "dilate_pixels": 15},
    )
    assert payload["image"] == "https://e/a.png"
    assert payload["mask"] == "https://e/m.png"
    assert payload["dilate_pixels"] == 15


def test_deblur_minimal_payload():
    spec = _catalog.resolve("flux-tools-deblur")
    payload = build_payload(spec, {"image": "https://e/a.png"})
    assert payload == {"image": "https://e/a.png"}


def test_vto_person_garment_fields():
    spec = _catalog.resolve("flux-tools-vto")
    payload = build_payload(
        spec,
        {
            "prompt": "The person of image 1 wearing the jacket of image 2.",
            "person": "https://e/p.png",
            "garment": "https://e/g.png",
        },
    )
    assert payload["person"] == "https://e/p.png"
    assert payload["garment"] == "https://e/g.png"
    assert payload["prompt"].startswith("The person")


def test_vto_requires_prompt():
    spec = _catalog.resolve("flux-tools-vto")
    with pytest.raises(BFLValidationError):
        build_payload(spec, {"person": "https://e/p.png", "garment": "https://e/g.png"})
