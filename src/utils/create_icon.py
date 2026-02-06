from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    size = (256, 256)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    driver = ImageDraw.Draw(img)
    
    # Background - Rounded Square with Gradient-ish look (Solid for simplicity)
    # Dark Blue/Purple background
    driver.rounded_rectangle([10, 10, 246, 246], radius=40, fill="#3F51B5", outline="#1A237E", width=5)
    
    # Text "VC"
    try:
        # Try to use a default font
        font = ImageFont.truetype("arial.ttf", 120)
    except:
        font = ImageFont.load_default()
        
    # Draw Text centered
    text = "VC"
    # wrapper for textbbox/textsize depending on pillow version
    try:
        left, top, right, bottom = driver.textbbox((0, 0), text, font=font)
        w = right - left
        h = bottom - top
    except:
        w, h = driver.textsize(text, font=font)
        
    driver.text(((size[0]-w)/2, (size[1]-h)/2 - 10), text, font=font, fill="white")
    
    # Save
    output_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico")
    img.save(output_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icon created at {output_path}")

if __name__ == "__main__":
    create_icon()
