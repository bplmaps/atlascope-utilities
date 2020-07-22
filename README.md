# Atlascope workflow tools

## New workflow atlas-tools.py

### Install

```
git clone https://github.com/nblmc/atlascope-assets.git
cd atlascope-assets
chmod +x ./new-workflow/atlas-tools.py
ln $PWD/new-workflow/atlas-tools.py /usr/local/bin/atlas-tools
```

### Use

Navigate to the root directory of the atlas you want to process; it should have subdirectories with `/spatial_imagery/{files}.tif` and `/footprint/Boundary.geojson`.

```
atlas-tools -h
atlas-tools --step check
atlas-tools --step mask-transform
atlas-tools --step all
```