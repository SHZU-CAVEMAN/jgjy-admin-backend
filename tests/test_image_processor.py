"""Tests for the standalone batch image processor."""

import re

from PIL import Image, ImageChops

from scripts.image_processor import (
    DEFAULT_MAX_BYTES,
    add_risk_notice,
    build_parser,
    find_cjk_font,
    process_directory,
)


def test_default_compression_limit_is_600_kb():
    """Both compressed variants should default to a 600 KB ceiling."""
    arguments = build_parser().parse_args(["input", "output"])

    assert DEFAULT_MAX_BYTES == 600 * 1024
    assert arguments.max_kb == 600
    assert arguments.max_mb is None


def test_risk_notice_is_prominent_on_regular_images():
    """The notice should occupy a clearly visible lower-right area."""
    source = Image.new("RGBA", (800, 600), "white")

    result = add_risk_notice(source, "该图片有侵权风险", find_cjk_font())
    difference = ImageChops.difference(source.convert("RGB"), result.convert("RGB"))
    changed_bounds = difference.getbbox()

    assert changed_bounds is not None
    assert changed_bounds[2] >= 780
    assert changed_bounds[3] >= 580
    assert changed_bounds[2] - changed_bounds[0] >= 300
    assert changed_bounds[3] - changed_bounds[1] >= 50


def test_process_directory_creates_three_watermarked_variants(tmp_path):
    """One source should produce named, compressed, and WebP variants."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    nested_dir = input_dir / "nested"
    nested_dir.mkdir(parents=True)
    source_path = nested_dir / "sample.png"
    Image.new("RGB", (800, 600), "#e5edf4").save(source_path, format="PNG")

    results = process_directory(
        input_dir,
        output_dir,
        max_bytes=24 * 1024,
        font_path=find_cjk_font(),
    )

    assert len(results) == 1
    result = results[0]
    assert result.error is None
    assert result.original == output_dir / "original" / "nested" / "sample.png"
    assert result.compressed is not None
    assert result.webp is not None
    assert re.fullmatch(r"[0-9a-f]{32}", result.compressed.stem)
    assert result.compressed.stem == result.webp.stem
    assert result.compressed.suffix == ".png"
    assert result.webp.suffix == ".webp"
    assert result.compressed.stat().st_size <= 24 * 1024
    assert result.webp.stat().st_size <= 24 * 1024

    with Image.open(source_path) as source, Image.open(result.original) as original:
        assert original.format == "PNG"
        assert original.size == source.size
        difference = ImageChops.difference(
            source.convert("RGB"),
            original.convert("RGB"),
        )
        assert difference.getbbox() is not None
        bottom_right = difference.crop((400, 300, 800, 600))
        assert bottom_right.getbbox() is not None

    with Image.open(result.compressed) as compressed:
        assert compressed.format == "PNG"
    with Image.open(result.webp) as webp:
        assert webp.format == "WEBP"


def test_output_inside_input_is_not_reprocessed(tmp_path):
    """Generated files should be excluded when output is below input."""
    input_dir = tmp_path / "images"
    output_dir = input_dir / "generated"
    input_dir.mkdir()
    Image.new("RGB", (320, 240), "white").save(input_dir / "photo.jpg")

    first = process_directory(input_dir, output_dir, font_path=find_cjk_font())
    second = process_directory(input_dir, output_dir, font_path=find_cjk_font())

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].compressed == second[0].compressed