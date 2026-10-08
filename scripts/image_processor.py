"""Batch watermark, compress, and convert local images."""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

DEFAULT_TEXT = "该图片有侵权风险"
DEFAULT_MAX_KB = 600
DEFAULT_MAX_BYTES = DEFAULT_MAX_KB * 1024
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
FORMAT_BY_SUFFIX = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".tif": "TIFF",
    ".tiff": "TIFF",
}


@dataclass(frozen=True)
class ProcessResult:
    """Describe the outputs or failure for one source image."""

    source: Path
    original: Path | None = None
    compressed: Path | None = None
    webp: Path | None = None
    error: str | None = None


def process_directory(
    input_dir: Path,
    output_dir: Path,
    text: str = DEFAULT_TEXT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    font_path: Path | None = None,
) -> list[ProcessResult]:
    """Process every supported image under a local directory.

    Args:
        input_dir: Directory containing source images.
        output_dir: Directory receiving the three output variants.
        text: Text drawn in the lower-right corner.
        max_bytes: Maximum size for each compressed output.
        font_path: Optional path to a font containing Chinese glyphs.

    Returns:
        A result for every discovered source image.

    Raises:
        FileNotFoundError: If the input directory does not exist.
        ValueError: If arguments are invalid.
    """
    input_dir = input_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")
    if input_dir == output_dir:
        raise ValueError("输出目录不能与输入目录相同")
    if not text.strip():
        raise ValueError("提示文字不能为空")
    if max_bytes <= 0:
        raise ValueError("压缩大小上限必须大于 0")

    resolved_font = find_cjk_font(font_path)
    source_files = _find_source_files(input_dir, output_dir)
    results: list[ProcessResult] = []
    for source in source_files:
        try:
            results.append(
                process_image(
                    source,
                    input_dir,
                    output_dir,
                    text,
                    max_bytes,
                    resolved_font,
                )
            )
        except (OSError, ValueError, UnidentifiedImageError) as exc:
            results.append(ProcessResult(source=source, error=str(exc)))
    return results


def process_image(
    source: Path,
    input_dir: Path,
    output_dir: Path,
    text: str,
    max_bytes: int,
    font_path: Path,
) -> ProcessResult:
    """Create all three output variants for one image."""
    relative_path = source.relative_to(input_dir)
    digest = _source_digest(source, relative_path)
    original_path = output_dir / "original" / relative_path
    compressed_path = output_dir / "compressed" / f"{digest}{source.suffix.lower()}"
    webp_path = output_dir / "webp" / f"{digest}.webp"

    with Image.open(source) as opened:
        source_format = opened.format or FORMAT_BY_SUFFIX[source.suffix.lower()]
        source_info = dict(opened.info)
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        watermarked = add_risk_notice(image, text, font_path)

        original_path.parent.mkdir(parents=True, exist_ok=True)
        compressed_path.parent.mkdir(parents=True, exist_ok=True)
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        _save_original(watermarked, original_path, source_format, opened, source_info)
        _save_under_limit(watermarked, compressed_path, source_format, max_bytes)
        _save_under_limit(watermarked, webp_path, "WEBP", max_bytes)

    return ProcessResult(
        source=source,
        original=original_path,
        compressed=compressed_path,
        webp=webp_path,
    )


def add_risk_notice(image: Image.Image, text: str, font_path: Path) -> Image.Image:
    """Draw a readable lower-right risk notice on an image."""
    result = image.convert("RGBA")
    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    short_side = max(min(result.size), 1)
    margin = max(round(short_side * 0.018), 4)
    padding_x = max(round(short_side * 0.014), 4)
    padding_y = max(round(short_side * 0.009), 3)
    max_text_width = max(result.width - 2 * (margin + padding_x), 1)
    font_size = max(min(round(short_side * 0.04), 72), 8)

    while True:
        font = ImageFont.truetype(str(font_path), font_size)
        bounds = draw.textbbox((0, 0), text, font=font, stroke_width=1)
        text_width = bounds[2] - bounds[0]
        text_height = bounds[3] - bounds[1]
        if text_width <= max_text_width or font_size <= 6:
            break
        font_size -= 1

    box_width = min(text_width + 2 * padding_x, result.width)
    box_height = min(text_height + 2 * padding_y, result.height)
    left = max(result.width - margin - box_width, 0)
    top = max(result.height - margin - box_height, 0)
    right = min(left + box_width, result.width)
    bottom = min(top + box_height, result.height)
    radius = min(max(round(box_height * 0.18), 2), box_height // 2)
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=radius,
        fill=(180, 20, 35, 210),
    )
    draw.text(
        (left + padding_x, top + padding_y - bounds[1]),
        text,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(110, 0, 10, 255),
    )
    return Image.alpha_composite(result, overlay)


def find_cjk_font(font_path: Path | None = None) -> Path:
    """Find a local font capable of rendering the Chinese notice.

    Raises:
        FileNotFoundError: If no suitable font can be found.
    """
    if font_path is not None:
        candidate = font_path.expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"字体文件不存在: {candidate}")
        return candidate

    windows_dir = Path(os.environ.get("WINDIR", "C:/Windows"))
    candidates = [
        windows_dir / "Fonts" / "msyh.ttc",
        windows_dir / "Fonts" / "simhei.ttf",
        windows_dir / "Fonts" / "simsun.ttc",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("未找到中文字体，请通过 --font 指定字体文件")


def _find_source_files(input_dir: Path, output_dir: Path) -> list[Path]:
    """Return sorted supported files while excluding generated output."""
    files = []
    for path in input_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.resolve().is_relative_to(output_dir):
            continue
        files.append(path)
    return sorted(files, key=lambda item: str(item).lower())


def _source_digest(source: Path, relative_path: Path) -> str:
    """Build a stable 32-character name from path and source bytes."""
    digest = hashlib.md5(usedforsecurity=False)
    digest.update(relative_path.as_posix().encode("utf-8"))
    digest.update(b"\0")
    with source.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _save_original(
    image: Image.Image,
    path: Path,
    image_format: str,
    source: Image.Image,
    source_info: dict,
) -> None:
    """Save the watermarked full-resolution image in its source format."""
    prepared = _prepare_for_format(image, image_format)
    options: dict = {}
    if image_format == "JPEG":
        options.update(quality=100, subsampling=0)
    elif image_format == "PNG":
        options.update(compress_level=6)
    elif image_format == "WEBP":
        options.update(lossless=True, quality=100, method=6)
    elif image_format == "TIFF":
        options.update(compression="tiff_lzw")

    icc_profile = source_info.get("icc_profile")
    if icc_profile and image_format in {"JPEG", "PNG", "WEBP", "TIFF"}:
        options["icc_profile"] = icc_profile
    exif = source.getexif()
    if exif and image_format in {"JPEG", "PNG", "WEBP", "TIFF"}:
        exif[274] = 1
        options["exif"] = exif.tobytes()
    prepared.save(path, format=image_format, **options)


def _save_under_limit(
    image: Image.Image,
    path: Path,
    image_format: str,
    max_bytes: int,
) -> None:
    """Encode and, when needed, resize an image below a byte limit."""
    current = image.copy()
    for _attempt in range(20):
        encoded = _encode_candidate(current, image_format, max_bytes)
        if encoded is not None:
            path.write_bytes(encoded)
            return
        next_width = max(round(current.width * 0.82), 1)
        next_height = max(round(current.height * 0.82), 1)
        if (next_width, next_height) == current.size:
            break
        current = current.resize((next_width, next_height), Image.Resampling.LANCZOS)
    raise ValueError(f"无法将图片压缩到 {max_bytes} 字节以内: {path.name}")


def _encode_candidate(
    image: Image.Image,
    image_format: str,
    max_bytes: int,
) -> bytes | None:
    """Return the highest-quality encoding under the target size."""
    prepared = _prepare_for_format(image, image_format)
    if image_format == "JPEG":
        for quality in range(95, 14, -5):
            data = _encode(
                prepared,
                image_format,
                quality=quality,
                optimize=True,
                progressive=True,
            )
            if len(data) <= max_bytes:
                return data
        return None
    if image_format == "WEBP":
        for quality in range(95, 14, -5):
            data = _encode(prepared, image_format, quality=quality, method=6)
            if len(data) <= max_bytes:
                return data
        return None
    if image_format == "PNG":
        data = _encode(prepared, image_format, optimize=True, compress_level=9)
        if len(data) <= max_bytes:
            return data
        quantized = prepared.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
        data = _encode(quantized, image_format, optimize=True, compress_level=9)
        return data if len(data) <= max_bytes else None
    if image_format == "TIFF":
        data = _encode(prepared, image_format, compression="tiff_lzw")
        return data if len(data) <= max_bytes else None
    data = _encode(prepared, image_format)
    return data if len(data) <= max_bytes else None


def _encode(image: Image.Image, image_format: str, **options) -> bytes:
    """Encode an image into memory."""
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **options)
    return buffer.getvalue()


def _prepare_for_format(image: Image.Image, image_format: str) -> Image.Image:
    """Convert an RGBA image into a mode accepted by the target format."""
    if image_format in {"JPEG", "BMP"}:
        background = Image.new("RGB", image.size, "white")
        if "A" in image.getbands():
            background.paste(image, mask=image.getchannel("A"))
        else:
            background.paste(image)
        return background
    return image


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="批量添加侵权风险提示，并生成原图、压缩图和 WebP 图。"
    )
    parser.add_argument("input", type=Path, help="待处理图片目录")
    parser.add_argument("output", type=Path, help="输出目录")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="右下角提示文字")
    parser.add_argument("--font", type=Path, help="中文字体文件路径")
    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument(
        "--max-kb",
        type=float,
        default=DEFAULT_MAX_KB,
        help=f"压缩图大小上限，默认 {DEFAULT_MAX_KB} KB",
    )
    size_group.add_argument(
        "--max-mb",
        type=float,
        help="压缩图大小上限（MB），与 --max-kb 不能同时使用",
    )
    return parser


def main() -> int:
    """Run the batch processor from the command line."""
    arguments = build_parser().parse_args()
    try:
        max_bytes = round(
            arguments.max_mb * 1024 * 1024
            if arguments.max_mb is not None
            else arguments.max_kb * 1024
        )
        results = process_directory(
            arguments.input,
            arguments.output,
            text=arguments.text,
            max_bytes=max_bytes,
            font_path=arguments.font,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"处理失败: {exc}", file=sys.stderr)
        return 2

    failures = [result for result in results if result.error]
    for result in results:
        if result.error:
            print(f"[失败] {result.source}: {result.error}", file=sys.stderr)
        else:
            print(f"[完成] {result.source}")
    print(f"共发现 {len(results)} 张，成功 {len(results) - len(failures)} 张，失败 {len(failures)} 张。")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())