#Sets all layers that are not named openstreetmap, index, or boundary to 60%
#opacity. Change 0.6 to your desired value for opacity. 
#Also removes black borders for all these files by changing nodata value to 0
#TO RUN: go to qgis>plugins>python console>show editor> either open this script
#or copy and paste it into the new panel editor panel. Press run
#contributed by Leventhal Map & Education Center intern, Brian Kominick 


for layer in [layer for layer in QgsProject.instance().mapLayers().values()]:
    if layer.name().lower() in ["openstreetmap", "index", "boundary"]:
        continue
    layer.renderer().setOpacity(0.6) #can change 6 for different opacity value
    provider = layer.dataProvider()
    provider.setNoDataValue(1,0) 
    layer.triggerRepaint()
