from PIL import Image, ImageDraw
import sys

def modify_icon(input_path, output_png, output_ico):
    try:
        # Load image
        img = Image.open(input_path).convert("RGBA")
        width, height = img.size
        
        # 1. Zoom in on the center (Crop and Resize)
        # Assuming we want to zoom in by 30% to make the center larger
        zoom_factor = 1.3
        new_w = int(width / zoom_factor)
        new_h = int(height / zoom_factor)
        
        left = (width - new_w) // 2
        top = (height - new_h) // 2
        right = left + new_w
        bottom = top + new_h
        
        cropped = img.crop((left, top, right, bottom))
        zoomed = cropped.resize((width, height), Image.Resampling.LANCZOS)
        
        # 2. Create circular mask to make it round and remove any border
        # We will make the circle slightly smaller than the edges to ensure no borders remain
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        # Margin of 2 pixels
        draw.ellipse((2, 2, width - 2, height - 2), fill=255)
        
        # Apply mask
        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        result.paste(zoomed, (0, 0), mask)
        
        # Save PNG for preview
        result.save(output_png)
        
        # Save as ICO
        result.save(output_ico, format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
        print("Success")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    modify_icon(sys.argv[1], sys.argv[2], sys.argv[3])
