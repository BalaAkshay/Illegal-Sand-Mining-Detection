import ee
import time

# --- Initialize the Earth Engine API ---
try:
    ee.Initialize(project='coe-aiml-b8')
    print("Google Earth Engine API initialized successfully.")
except ee.EEException:
    print("Authentication failed. Please run 'earthengine authenticate' in your terminal.")
    exit()

# --- Configuration ---
# Define your Area of Interest (AOI).
# For this example, we'll use a sample rectangle over a river area.
# Replace this with your own ee.Geometry or feature collection.
AOI = ee.Geometry.Rectangle([88.20, 22.00, 88.30, 22.05]) # Example: Part of Hooghly River, India

# Define time periods for 'before' and 'after' analysis
BEFORE_START_DATE = '2022-01-01'
BEFORE_END_DATE = '2022-03-31'
AFTER_START_DATE = '2023-01-01'
AFTER_END_DATE = '2023-03-31'

# --- Sentinel-2 (Optical) Data Processing ---
print("Processing Sentinel-2 Optical Data...")

def mask_s2_clouds(image):
    """Masks clouds in a Sentinel-2 image using the S2 cloud probability asset."""
    qa = image.select('QA60')
    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    return image.updateMask(mask).divide(10000) # Scale to surface reflectance values

# Get 'before' and 'after' Sentinel-2 collections
s2_before_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
   .filterDate(BEFORE_START_DATE, BEFORE_END_DATE) \
   .filter(ee.Filter.bounds(AOI)) \
   .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
   .map(mask_s2_clouds)

s2_after_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
   .filterDate(AFTER_START_DATE, AFTER_END_DATE) \
   .filter(ee.Filter.bounds(AOI)) \
   .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
   .map(mask_s2_clouds)

# Create median composites to get a single, clear image for each period [4]
s2_before_image = s2_before_collection.median().clip(AOI)
s2_after_image = s2_after_collection.median().clip(AOI)

# --- Sentinel-1 (SAR) Data Processing ---
print("Processing Sentinel-1 SAR Data...")

# Get 'before' and 'after' Sentinel-1 collections [1]
s1_before_collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
   .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
   .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
   .filter(ee.Filter.eq('instrumentMode', 'IW')) \
   .filter(ee.Filter.bounds(AOI)) \
   .filterDate(BEFORE_START_DATE, BEFORE_END_DATE)

s1_after_collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
   .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
   .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
   .filter(ee.Filter.eq('instrumentMode', 'IW')) \
   .filter(ee.Filter.bounds(AOI)) \
   .filterDate(AFTER_START_DATE, AFTER_END_DATE)

# Create median composites
s1_before_image = s1_before_collection.median().clip(AOI)
s1_after_image = s1_after_collection.median().clip(AOI)

# --- Exporting to Google Drive ---
print("Starting export tasks to Google Drive...")

# Export Sentinel-2 images
task_s2_before = ee.batch.Export.image.toDrive(
    image=s2_before_image.select(), # Red, Green, Blue, NIR
    description='S2_Before_Composite',
    folder='SandMiningDetection_Exports',
    fileNamePrefix='s2_before',
    region=AOI,
    scale=10,
    crs='EPSG:4326'
)
task_s2_before.start()

task_s2_after = ee.batch.Export.image.toDrive(
    image=s2_after_image.select(),
    description='S2_After_Composite',
    folder='SandMiningDetection_Exports',
    fileNamePrefix='s2_after',
    region=AOI,
    scale=10,
    crs='EPSG:4326'
)
task_s2_after.start()

# Export Sentinel-1 images
task_s1_before = ee.batch.Export.image.toDrive(
    image=s1_before_image.select(['VV', 'VH']),
    description='S1_Before_Composite',
    folder='SandMiningDetection_Exports',
    fileNamePrefix='s1_before',
    region=AOI,
    scale=10,
    crs='EPSG:4326'
)
task_s1_before.start()

task_s1_after = ee.batch.Export.image.toDrive(
    image=s1_after_image.select(['VV', 'VH']),
    description='S1_After_Composite',
    folder='SandMiningDetection_Exports',
    fileNamePrefix='s1_after',
    region=AOI,
    scale=10,
    crs='EPSG:4326'
)
task_s1_after.start()

# --- Monitor Task Status ---
while task_s2_after.active() or task_s1_after.active():
    print(f"Monitoring export tasks... S2_After: {task_s2_after.status()['state']}, S1_After: {task_s1_after.status()['state']}")
    time.sleep(60)

print("All export tasks have been submitted. Check your Google Drive 'SandMiningDetection_Exports' folder.")

