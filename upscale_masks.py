import replicate
from io import BytesIO
from pathlib import Path
from PIL import Image

MASKS_DIR = Path(__file__).parent / "masks"

for mask_file in sorted(MASKS_DIR.glob("mask_[0-9].png")):
    with Image.open(mask_file) as img:
        orig_size = img.size
        print(f"Upscaling {mask_file.name} ({orig_size[0]}x{orig_size[1]})...")

        # Extract alpha channel and convert to RGB grayscale image for upscaling
        alpha = img.split()[-1]  # Get alpha channel
        # Convert alpha to RGB (grayscale) so Replicate can process it
        alpha_rgb = Image.merge("RGB", (alpha, alpha, alpha))

        # Save temporarily for upload
        temp_path = mask_file.with_suffix(".temp.png")
        alpha_rgb.save(temp_path, "PNG")

    # Upscale the alpha channel with Replicate
    with open(temp_path, "rb") as f:
        output = replicate.run(
            "recraft-ai/recraft-crisp-upscale",
            input={"image": f}
        )

    # Load upscaled result
    upscaled_alpha_rgb = Image.open(BytesIO(output.read()))

    # Extract one channel as the new alpha (convert from RGB back to single channel)
    upscaled_alpha = upscaled_alpha_rgb.convert("L")

    # Create white RGB at the new size
    new_size = upscaled_alpha.size
    white_rgb = Image.new("RGB", new_size, (255, 255, 255))

    # Combine white RGB + upscaled alpha
    result = Image.new("RGBA", new_size)
    result.paste(white_rgb, (0, 0))
    result.putalpha(upscaled_alpha)

    # Save final result
    result.save(mask_file, "PNG")

    # Clean up temp file
    temp_path.unlink()

    print(f"  Done: {mask_file.name} -> {new_size[0]}x{new_size[1]}")

print("\nAll masks upscaled!")
