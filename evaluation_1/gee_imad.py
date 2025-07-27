import ee
import geemap
from datetime import datetime

# Initialize Earth Engine
try:
    ee.Initialize(project='coe-aiml-b8')
    print("Earth Engine initialized")
except Exception as e:
    ee.Authenticate()
    ee.Initialize()

# Define region of interest (e.g., a rectangle or polygon)
roi = ee.Geometry.Rectangle([78.0, 17.0, 78.2, 17.2])  # change this to your area

# Function to mask clouds and scale Sentinel-2 images
def mask_s2(image):
    cloud_mask = image.select('QA60').bitwiseAnd(1 << 10).eq(0)
    return image.updateMask(cloud_mask).divide(10000)

# Load and prepare Sentinel-2 image collections
def load_s2_images(start, end):
    return (
        ee.ImageCollection('COPERNICUS/S2_SR')
        .filterDate(start, end)
        .filterBounds(roi)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        .map(mask_s2)
        .select(['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B11'])
        .median()
    )

# Load image stacks for two time periods
image_1 = load_s2_images('2022-01-01', '2022-03-31')
image_2 = load_s2_images('2023-01-01', '2023-03-31')

print("Loaded images")

# Rename bands to avoid duplication
image_2 = image_2.rename([b + '_2' for b in image_2.bandNames().getInfo()])

# Stack images
stacked = image_1.addBands(image_2)

# Add constant bands for iMAD (required by reducer)
stacked = stacked.addBands(ee.Image(1)).addBands(ee.Image(1))

# Import iMAD script
# If you're using a custom iMAD function, replace this with its definition
# For example:
def compute_iMAD(image):
    n = int(len(image.bandNames().getInfo()) / 2)  # number of variables in each image
    meanReducer = ee.Reducer.mean().repeat(n)
    reducer = ee.Reducer.splitWeights(meanReducer)
    # this will fail if band count doesn't match reducer expectation
    stats = image.reduceRegion(
        reducer=reducer,
        geometry=roi,
        scale=30,
        maxPixels=1e13
    )
    return stats

# Attempt to run iMAD
try:
    result = compute_iMAD(stacked)
    print("iMAD results:", result.getInfo())
except Exception as e:
    print("iMAD failed:", e)

# Export images to Google Drive
task1 = ee.batch.Export.image.toDrive(
    image=image_1.clip(roi),
    description='Image_2022',
    folder='GEE',
    fileNamePrefix='image_2022',
    scale=10,
    region=roi
)
task1.start()

task2 = ee.batch.Export.image.toDrive(
    image=image_2.clip(roi),
    description='Image_2023',
    folder='GEE',
    fileNamePrefix='image_2023',
    scale=10,
    region=roi
)
task2.start()

print("Exports started. Check your Google Drive.")
