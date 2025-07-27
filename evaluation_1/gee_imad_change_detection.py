import ee
import time

# --- Initialize the Earth Engine API ---
try:
    ee.Initialize(project='coe-aiml-b8')
    print("Google Earth Engine API initialized successfully.")
except ee.EEException:
    print("Authentication failed. Please run 'earthengine authenticate' in your terminal.")
    exit()

# --- Configuration (same as Script 1.1) ---
AOI = ee.Geometry.Rectangle([88.20, 22.00, 88.30, 22.05])
BEFORE_START_DATE = '2022-01-01'
BEFORE_END_DATE = '2022-03-31'
AFTER_START_DATE = '2023-01-01'
AFTER_END_DATE = '2023-03-31'
# Use fewer bands for faster processing in this example
BANDS = ['B2', 'B3', 'B4', 'B8'] # Blue, Green, Red, NIR

# --- Get Image Composites (Simplified from Script 1.1) ---
def get_composite(start_date, end_date):
    """Creates a cloud-masked median composite for a given period."""
    def mask_s2_clouds(image):
        qa = image.select('QA60')
        cloud_bit_mask = 1 << 10
        cirrus_bit_mask = 1 << 11
        mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
        return image.updateMask(mask).select(BANDS).divide(10000)

    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
       .filterDate(start_date, end_date) \
       .filter(ee.Filter.bounds(AOI)) \
       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
       .map(mask_s2_clouds)
    return collection.median().clip(AOI)

im1 = get_composite(BEFORE_START_DATE, BEFORE_END_DATE)
im2 = get_composite(AFTER_START_DATE, AFTER_END_DATE)

# --- iMAD Algorithm Implementation (adapted from GEE Community Tutorials) ---
# [6, 7]
def geneiv(C, B):
    """
    Solves the generalized eigenproblem C*X = l*B*X using matrix inversion.
    This is an alternative to the Cholesky decomposition method, as the
    cholesky() method is not available in the GEE Python API for ee.Array.
    """
    # We solve by converting to a standard eigenvalue problem: inv(B)*C*x = l*x
    C = ee.Array(C)
    B = ee.Array(B)

    # Compute inv(B) * C
    B_inv_C = B.matrixInverse().matrixMultiply(C)

    # Solve the standard eigenvalue problem
    eigen = B_inv_C.eigen()

    # Eigenvalues are the first element (λ), eigenvectors are the second (X)
    eigenvalues = eigen.slice(1, 0, 1)
    eigenvectors = eigen.slice(1, 1)

    return (eigenvalues, eigenvectors)

def imad(im1, im2, max_iter=30):
    """The iMAD algorithm."""
    n_bands = im1.bandNames().length()
    
    # Initial weights are all 1
    weights = ee.Image.constant(1).clip(im1.geometry())
    
    for i in range(max_iter):
        # Weighted covariance matrix
        combined = im1.addBands(im2)
        means = combined.addBands(weights).reduceRegion(
            reducer=ee.Reducer.mean().repeat(n_bands.multiply(2)).splitWeights(),
            geometry=im1.geometry(),
            scale=30,
            maxPixels=1e9
        )
        means = ee.Array(means.values())
        centered = combined.toArray().subtract(means.project([1]))
        
        sum_weights = ee.Number(weights.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=im1.geometry(),
            scale=30,
            maxPixels=1e9
        ).get('constant'))
        
        B1 = centered.bandNames().get(0)
        n_pixels = ee.Number(centered.reduceRegion(ee.Reducer.count(), scale=30, maxPixels=1e9).get(B1))
        
        covw = centered.multiply(weights.sqrt()).toArray().reduceRegion(
            reducer=ee.Reducer.centeredCovariance(),
            geometry=im1.geometry(),
            scale=30,
            maxPixels=1e9
        ).get('array')
        
        covw = ee.Array(covw).multiply(n_pixels).divide(sum_weights)
        
        s11 = covw.slice(0, 0, n_bands).slice(1, 0, n_bands)
        s22 = covw.slice(0, n_bands).slice(1, n_bands)
        s12 = covw.slice(0, 0, n_bands).slice(1, n_bands)
        s21 = s12.matrixTranspose()
        
        # Solve generalized eigenproblems
        c1 = s12.matrixMultiply(s22.matrixInverse()).matrixMultiply(s21)
        a = geneiv(c1, s11)[1]
        c2 = s21.matrixMultiply(s11.matrixInverse()).matrixMultiply(s12)
        b = geneiv(c2, s22)[1]
        
        # MAD variates
        mad = im1.multiply(ee.Image.constant(ee.Array(a).transpose().toList().get(0))) \
                .subtract(im2.multiply(ee.Image.constant(ee.Array(b).transpose().toList().get(0))))
        
        # Chi-squared distance for new weights
        sigma_mad = mad.reduceRegion(
            reducer=ee.Reducer.stdDev(),
            geometry=im1.geometry(),
            scale=30,
            maxPixels=1e9
        ).values()
        
        chi_squared = mad.pow(2).divide(ee.Image.constant(sigma_mad).pow(2)).reduce(ee.Reducer.sum())
        
        # Update weights using chi-squared distribution
        weights = ee.Image.constant(1).subtract(ee.Image.constant(1).subtract(chi_squared.multiply(-0.5).exp()))
    
    return chi_squared, mad

# --- Run iMAD and Export ---
print("Running iMAD algorithm...")
chi_squared_map, _ = imad(im1, im2)

print("Exporting iMAD chi-squared map...")
task_imad = ee.batch.Export.image.toDrive(
    image=chi_squared_map,
    description='iMAD_Change_Map',
    folder='SandMiningDetection_Exports',
    fileNamePrefix='imad_change_map',
    region=AOI,
    scale=30, # Run at a coarser scale due to computational intensity
    crs='EPSG:4326'
)
task_imad.start()

while task_imad.active():
    print(f"Monitoring iMAD export task... Status: {task_imad.status()['state']}")
    time.sleep(60)

print("iMAD export task submitted. Check your Google Drive.")