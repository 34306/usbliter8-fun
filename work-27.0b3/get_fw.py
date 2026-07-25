#!/usr/bin/env python3.14

import requests
import os

def download_file(url):
    local_filename = url.split('/')[-1]

    if os.path.exists(local_filename):
        print(f"Skipping download_file: '{local_filename}' already exists.")
        return

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def unzip_file(zip_path, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")
    else:
        print(f"Skipping extract '{zip_path}' firmware")
        return

    print(f"Unzipping {zip_path} to {target_dir}...")
    exit_code = os.system(f"unzip -o '{zip_path}' -d '{target_dir}'")

    if exit_code == 0:
        print("Unzip successful.")
    else:
        print(f"Unzip failed with code: {exit_code}")

os.system(f"chmod +x tools/*")

# 1. Download
# iPhone 11 Pro / 17.0b3 (24A5380h)
print("Downloading iPhone 11 Pro / 17.0b3 (24A5380h)...")
target_url = "https://updates.cdn-apple.com/2026SpringSeed/fullrestores/140-35958/9EC7A77B-DC21-4DD3-B285-8CA45DEF7689/iPhone12,3,iPhone12,5_27.0_24A5380h_Restore.ipsw"
download_file(target_url)

# 2. extract things
unzip_file("iPhone12,3,iPhone12,5_27.0_24A5380h_Restore.ipsw", "iPhone12,3,iPhone12,5_27.0_24A5380h_Restore")