# How to use this script

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
4. [MapShaper](https://www.npmjs.com/package/mapshaper#installation)

## Usage

### Clone this repo

Clone this repository and `cd` into it.

### Update path so that you can run the script globally

Open a terminal window at the `modern-workflow` folder in this repository and:

```sh
pwd
```

The terminal will print your present working directory, which should end in `modern-workflow`. Copy the output and then:

```sh
sudo nano /etc/paths
```

Finally, follow these instructions, which are [old](https://www.architectryan.com/2012/10/02/add-to-the-path-on-mac-os-x-mountain-lion/) but work for me on Sonoma 14.7.1:

1. Enter your password, if prompted
2. Use the arrow key to navigate to the bottom of the file
3. Paste using `command+v` the path ending in `modern-workflow`
4. Hit `ctrl+X` to quit
5. Enter `Y` to save
6. Restart your terminal session for the new path to take effect
7. Test your new path with `echo $PATH`

You should see something like this:

```sh
/opt/anaconda3/bin:/opt/anaconda3/condabin:/usr/local/bin:/usr/local/sbin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/geoprocessing/Documents/GitHub/atlascope-utilities/modern-workflow:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin
```

Basically, a big jumble of paths, which include the `modern-workflow` repository.

<!-- ### Update dependencies

From inside the repo:

```sh
yarn install
``` -->

### Commands

Create an empty directory named for the atlas you're georeferencing (e.g., `boston1900`) and `cd` into it. Then:

```sh
atlascopify.py --identifier <commonwealth:id> ## download inputs
atlascopify.py --step allmaps-transform ## transform pixel masks
atlascopify.py --step warp-plates ## warp plates
atlascopify.py --step mosaic-plates ## mosaic plates
atlascopify.py --step create-xyz ## create xyz tiles
```