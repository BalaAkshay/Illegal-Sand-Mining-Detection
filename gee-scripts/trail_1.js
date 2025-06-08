// Replace these coordinates with your AOI!
var aoi = ee.Geometry.Rectangle([
  [79.8, 18.9],
  [79.9, 18.7]
]);

// Visualize AOI
Map.centerObject(aoi, 10);  // Zoom level 10
Map.addLayer(aoi, {color: 'red'}, 'Study Area');

// Function to mask clouds
function maskS2Clouds(image) {
  var qa = image.select('QA60');
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
             .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask);
}

// Load Sentinel-2 data
var s2 = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
  .filterBounds(aoi)
  .filterDate('2023-04-04', '2023-06-06')
  .map(maskS2Clouds)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 5));
  
  
  // Function to calculate MNDWI
function addMNDWI(image) {
  var mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI');
  return image.addBands(mndwi);
}

// Apply to the collection
var s2WithMndwi = s2.map(addMNDWI);



// Get median composites for two periods
var before = s2WithMndwi.filterDate('2023-04-04', '2023-05-05').median();
var after = s2WithMndwi.filterDate('2023-05-05', '2023-06-06').median();

// Compute MNDWI difference
var mndwiBefore = before.select('MNDWI');
var mndwiAfter = after.select('MNDWI');
var mndwiChange = mndwiAfter.subtract(mndwiBefore);  // Negative = sand exposure


// Areas where MNDWI decreased significantly (sand exposure)
var sandExposure = mndwiChange.lt(-0.2);  // Adjust threshold as needed

// Visualize
var palette = ['black', 'yellow'];  // Black=no change, Yellow=sand exposure
Map.addLayer(sandExposure, {min: 0, max: 1, palette: palette}, 'Sand Exposure');



Export.image.toDrive({
  image: sandExposure,
  description: 'SandExposure_2023',
  scale: 10,  // Sentinel-2 resolution
  region: aoi,
  fileFormat: 'GeoTIFF',
  maxPixels: 1e13
});