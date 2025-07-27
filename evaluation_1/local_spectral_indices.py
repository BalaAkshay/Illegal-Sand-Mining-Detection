import rasterio
import numpy as np
import os

# --- Configuration ---
INPUT_DIR = "D:\\Workspaces\\COE-AIML\\Illegal-Sand-Mining-Detection\\evaluation_1\\SandMiningDetection_Exports" # Directory where you downloaded the GEE files
OUTPUT_DIR = "D:\\Workspaces\\COE-AIML\\Illegal-Sand-Mining-Detection\\evaluation_1\\processed_outputs"
S1_BEFORE_PATH = os.path.join(INPUT_DIR, "s1_before.tif")
S1_AFTER_PATH = os.path.join(INPUT_DIR, "s1_after.tif")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Function to calculate SAR indices ---
def calculate_sar_indices(s1_image_path):
    """Calculates SAR indices from Sentinel-1 GeoTIFF."""
    with rasterio.open(s1_image_path) as src:
        # Sentinel-1 has VV and VH polarization bands
        vv = src.read(1).astype(float)
        vh = src.read(2).astype(float)
        
        # Calculate SAR indices
        # 1. VV/VH ratio (useful for distinguishing different land covers)
        vv_vh_ratio = vv / vh
        
        # 2. SAR backscatter difference (useful for detecting changes)
        sar_backscatter = vv - vh
        
        # Get metadata for writing new files
        profile = src.profile
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        
        return vv_vh_ratio, sar_backscatter, profile

# --- Function to calculate difference ---
def calculate_difference(before_arr, after_arr, profile, output_path):
    """Calculates the difference between two numpy arrays and saves as GeoTIFF."""
    diff = after_arr - before_arr
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(diff.astype(rasterio.float32), 1)
    print(f"Saved difference map to: {output_path}")

# --- Main Processing ---
print("Calculating SAR indices for 'before' period...")
vv_vh_ratio_before, sar_backscatter_before, profile = calculate_sar_indices(S1_BEFORE_PATH)

print("Calculating SAR indices for 'after' period...")
vv_vh_ratio_after, sar_backscatter_after, _ = calculate_sar_indices(S1_AFTER_PATH)

print("Calculating difference maps...")
# Calculate and save SAR indices differences
calculate_difference(
    vv_vh_ratio_before, 
    vv_vh_ratio_after, 
    profile, 
    os.path.join(OUTPUT_DIR, "vv_vh_ratio_difference.tif")
)

# Calculate and save SAR backscatter difference
calculate_difference(
    sar_backscatter_before, 
    sar_backscatter_after, 
    profile, 
    os.path.join(OUTPUT_DIR, "sar_backscatter_difference.tif")
)

print("Processing complete. Check the 'processed_outputs' directory.")