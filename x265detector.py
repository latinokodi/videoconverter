#!/usr/bin/env python3
import os
import subprocess
import shutil

def is_video_file(filename):
    """Return True if the file has a common video extension."""
    video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv']
    ext = os.path.splitext(filename)[1].lower()
    return ext in video_exts

def get_video_codec(filepath):
    """Use ffprobe to get the codec of the first video stream."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1", filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        codec = result.stdout.strip().lower()
        return codec
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return None

def main():
    input_folder = input("Enter the folder path to scan for video files: ").strip()
    if not os.path.isdir(input_folder):
        print("Invalid folder path.")
        return

    # Create a subfolder inside the input folder named "<foldername>_notX265"
    folder_basename = os.path.basename(os.path.normpath(input_folder))
    new_folder_name = folder_basename + "_notX265"
    new_folder_path = os.path.join(input_folder, new_folder_name)
    if not os.path.exists(new_folder_path):
        os.makedirs(new_folder_path)
        print(f"Created folder: {new_folder_path}")

    files_moved = []
    count = 0

    # Loop through items in the input folder (non-recursive)
    for item in os.listdir(input_folder):
        item_path = os.path.join(input_folder, item)
        # Skip directories and also skip the new subfolder itself
        if os.path.isdir(item_path) and item == new_folder_name:
            continue

        if os.path.isfile(item_path) and is_video_file(item):
            codec = get_video_codec(item_path)
            if codec != "hevc":
                # Move the file if it is not encoded in H.265 (HEVC)
                dest_path = os.path.join(new_folder_path, item)
                shutil.move(item_path, dest_path)
                files_moved.append(item)
                count += 1
                print(f"Moved: {item} (codec: {codec})")
            else:
                print(f"Skipped (already H265): {item}")
    
    print("\nSummary:")
    print(f"Total files moved: {count}")
    if count > 0:
        print("Files moved:")
        for f in files_moved:
            print(f" - {f}")

if __name__ == "__main__":
    main()

