// 1. Define your polygon
var aoi = /* color: #98ff00 */geometry2;

// 2. Cloud masking function
function maskS2Clouds(image) {
  var qa = image.select('QA60');
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
             .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask);
}

// 3. Load and preprocess Sentinel-2 data
var s2 = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
  .filterBounds(aoi)
  .filterDate('2023-01-01', '2023-05-05')  // Adjust dates
  .map(maskS2Clouds)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 5));

// 4. Calculate MNDWI
var s2WithMndwi = s2.map(function(image) {
  return image.addBands(image.normalizedDifference(['B3', 'B11']).rename('MNDWI'));
});

// 5. Compare two time periods (adjust dates)
var before = s2WithMndwi.filterDate('2023-01-01', '2023-03-03').median();
var after = s2WithMndwi.filterDate('2023-03-03', '2023-05-05').median();
var mndwiChange = after.select('MNDWI').subtract(before.select('MNDWI'));

// 6. Thresholding (adjust -0.2 based on your region)
var sandExposure = mndwiChange.lt(-0.2);  // Negative change = sand exposure

// 7. Visualize
Map.addLayer(sandExposure, {min: 0, max: 1, palette: ['black', 'yellow']}, 'Sand Exposure');

// 8. Export results
Export.image.toDrive({
  image: sandExposure,
  description: 'SandExposure_YourArea',
  scale: 10,
  region: aoi,
  fileFormat: 'GeoTIFF'
});

// 9. Calculate affected area (hectares)
var areaHa = sandExposure.multiply(ee.Image.pixelArea()).divide(10000)
  .reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: aoi,
    scale: 10,
    maxPixels: 1e13
  });
print('Exposed sand area (ha):', areaHa);