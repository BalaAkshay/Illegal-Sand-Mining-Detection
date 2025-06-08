// 1. Define Area of Interest (AOI)


Map.centerObject(aoi, 12);

// 2. Load Sentinel-2 Image Collections (cloud-filtered)
// function maskClouds(image) {
//   var qa = image.select('QA60');
//   var cloudBitMask = 1 << 10;
//   var cirrusBitMask = 1 << 11;
//   var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
//               .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
//   return image.updateMask(mask).divide(10000);
// }


// Cloud mask using Scene Classification (SCL)
function maskS2Clouds(image) {
  var scl = image.select('SCL');
  // Keep pixels that are not cloud or shadow
  var mask = scl.neq(3)  // cloud shadow
               .and(scl.neq(8))  // medium probability cloud
               .and(scl.neq(9))  // high probability cloud
               .and(scl.neq(10)); // thin cirrus
  return image.updateMask(mask).divide(10000);
}


// Time ranges (you can change these)
var before = ee.ImageCollection('COPERNICUS/S2_SR')
  .filterBounds(aoi)
  .filterDate('2025-01-01', '2025-03-10')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
  .map(maskS2Clouds)
  .median();

var after = ee.ImageCollection('COPERNICUS/S2_SR')
  .filterBounds(aoi)
  .filterDate('2025-03-10', '2025-05-15')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
  .map(maskS2Clouds)
  .median();

// 3. Compute MNDWI: (Green - SWIR1) / (Green + SWIR1)
function getMNDWI(image) {
  return image.normalizedDifference(['B3', 'B11']).rename('MNDWI');
}

var mndwiBefore = getMNDWI(before).clip(aoi);
var mndwiAfter = getMNDWI(after).clip(aoi);

// 4. Create water masks (MNDWI > 0.3)
var waterBefore = mndwiBefore.gt(0.3).rename('water_before');
var waterAfter = mndwiAfter.gt(0.3).rename('water_after');

// 5. Change Detection: water lost or gained
var waterLoss = waterBefore.and(waterAfter.not()).rename('water_loss');
var waterGain = waterAfter.and(waterBefore.not()).rename('water_gain');

// 6. Visualization
Map.addLayer(mndwiBefore, {min: -1, max: 1, palette: ['brown', 'white', 'blue']}, 'MNDWI Before');
Map.addLayer(mndwiAfter, {min: -1, max: 1, palette: ['brown', 'white', 'blue']}, 'MNDWI After');
Map.addLayer(waterLoss, {palette: ['red']}, 'Water Lost');
Map.addLayer(waterGain, {palette: ['green']}, 'Water Gained');

// 7. (Optional) Export change map to Drive
Export.image.toDrive({
  image: waterLoss.add(waterGain.multiply(2)), // 1=loss, 2=gain
  description: 'SandMiningChangeMap',
  scale: 10,
  region: aoi,
  maxPixels: 1e13
});
