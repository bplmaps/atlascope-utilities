# Atlascope workflow tools

## New workflow atlas-tools.py

### Install

```
git clone https://github.com/nblmc/atlascope-assets.git
cd atlascope-assets
chmod +x ./new-workflow/atlas-tools.py
ln -s $PWD/new-workflow/atlas-tools.py /usr/local/bin/atlas-tools
```

### Use

Navigate to the root directory of the atlas you want to process.

The command must be run in a directory with the following subdirectories present:

* /archival_imagery
* /gcps
* /footprint

Valid commands:

```
atlas-tools -h
atlas-tools --step check
atlas-tools --step mask-transform
atlas-tools --step vrt-mosaic 
```

