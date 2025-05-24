#!/bin/bash

# Input image
INPUT_IMAGE="ottotone.png"
# Output directory (same as input, as per .iconset structure)
OUTPUT_DIR="."

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Check if the input image exists
if [ ! -f "$INPUT_IMAGE" ]; then
  echo "Error: Input image '$INPUT_IMAGE' not found."
  exit 1
fi

echo "Generating icons from $INPUT_IMAGE..."

# Define sizes and output names
# Format: "widthxheight output_filename_base"
# For @2x, the actual pixel dimensions are doubled.

# 16x16
ffmpeg -i "$INPUT_IMAGE" -vf scale=16:16 "$OUTPUT_DIR/icon_16x16.png" -y
# 16x16@2x (32x32 pixels)
ffmpeg -i "$INPUT_IMAGE" -vf scale=32:32 "$OUTPUT_DIR/icon_16x16@2x.png" -y

# 32x32
ffmpeg -i "$INPUT_IMAGE" -vf scale=32:32 "$OUTPUT_DIR/icon_32x32.png" -y
# 32x32@2x (64x64 pixels)
ffmpeg -i "$INPUT_IMAGE" -vf scale=64:64 "$OUTPUT_DIR/icon_32x32@2x.png" -y

# 128x128
ffmpeg -i "$INPUT_IMAGE" -vf scale=128:128 "$OUTPUT_DIR/icon_128x128.png" -y
# 128x128@2x (256x256 pixels)
ffmpeg -i "$INPUT_IMAGE" -vf scale=256:256 "$OUTPUT_DIR/icon_128x128@2x.png" -y

# 256x256
ffmpeg -i "$INPUT_IMAGE" -vf scale=256:256 "$OUTPUT_DIR/icon_256x256.png" -y
# 256x256@2x (512x512 pixels)
ffmpeg -i "$INPUT_IMAGE" -vf scale=512:512 "$OUTPUT_DIR/icon_256x256@2x.png" -y

# 512x512
ffmpeg -i "$INPUT_IMAGE" -vf scale=512:512 "$OUTPUT_DIR/icon_512x512.png" -y
# 512x512@2x (1024x1024 pixels)
ffmpeg -i "$INPUT_IMAGE" -vf scale=1024:1024 "$OUTPUT_DIR/icon_512x512@2x.png" -y

echo "Icon generation complete."
echo "All icons saved in $OUTPUT_DIR"
echo ""
echo "Next step: Create the .icns file using iconutil:"
echo "  iconutil -c icns $OUTPUT_DIR"
