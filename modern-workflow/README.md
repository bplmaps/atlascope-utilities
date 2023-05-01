# Geotransforming urban atlases using Allmaps and GDAL

Taking as its argument a Commonwealth ID from LMEC digital collections, `atlascopify.py` will:

1. **Download Inputs** Download all georeference annotations (from Allmaps) and image files (from LMEC collections) associated with the given ID
2. **Transform Pixel Masks** Transform pixel masks for each annotation into a GeoJSON mask
3. **Warp Plates** Use GeoJSON masks to transform image files into GeoTIFFs
4. **Mosaic Plates** Compose warped image files into virtual raster
5. **Create XYZ Tiles** Generate XYZ tilesets

The two outputs---a `plates.geojson` footprint file and a `tiles` directory---will be located in the `output` folder that is created during step 1 of the script.

## Requirements

To run the script, you'll need:

1. [GDAL](https://gdal.org/download.html) (recommended installation using [Anaconda](https://docs.anaconda.com/free/navigator/))
2. [Allmaps CLI](https://github.com/allmaps/allmaps/tree/main/apps/cli)
3. [GeoPandas](https://geopandas.org/en/stable/getting_started/install.html)

## Usage

### Clone this repo

Clone this repository and `cd` into it.

### Create symbolic link to `atlascopify.py`

From inside the repo:

```sh
sudo ln -s pwd usr/local/bin
```

### Update dependencies

From inside the repo:

```sh
yarn install
```

### Commands

Create an empty directory named for the atlas you're georeferencing (e.g., `boston1900`) and `cd` into it. Then:

```sh
atlascopify.py --identifier <commonwealth:id> ## download inputs
atlascopify.py --step allmaps-transform ## transform pixel masks
atlascopify.py --step warp-plates ## warp plates
atlascopify.py --step mosaic-plates ## mosaic plates
atlascopify.py --step create-xyz ## create xyz tiles
```