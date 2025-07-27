import ee
ee.Initialize(project='coe-aiml-b8')

tasks = ee.batch.Task.list()
for t in tasks:
    print(f"Task: {t.config.get('description')}, State: {t.status()['state']}, Error: {t.status().get('error_message', 'None')}")
