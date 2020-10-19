# Data prep for Ellsworth Preserve files
# Script written in Python 3.7

import config as config
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio import features
from pathlib import Path
import importlib
importlib.reload(config)
# ======================================================================================================================

# =======================================================================
# Convert Ellsworth stand vector to raster
# =======================================================================

# Edit species names to be VELMA appropriate and fill nulls
stand_shp = str(config.stand_shp)
stand_shp = gpd.read_file(config.stand_shp)
stand_shp['STAND_TYPE'] = stand_shp['STAND_TYPE'].str.replace('/', '_')
stand_shp['STAND_TYPE'] = stand_shp['STAND_TYPE'].str.replace('-', '_')
stand_shp.loc[pd.isnull(stand_shp['STAND_TYPE']), 'STAND_TYPE'] = 'NONE'

# Assign numbers to unique species names
unique_species = stand_shp['STAND_TYPE'].unique().tolist()
unique_numbers = (np.arange(len(unique_species))+1).tolist()
species_num_dict = {unique_species[i]: unique_numbers[i] for i in range(len(unique_species))}
stand_shp['SPECIES_ID'] = stand_shp['STAND_TYPE'].map(species_num_dict)
key = pd.DataFrame(np.column_stack([unique_species, unique_numbers]), columns=['stand_type', 'species_ID'])  # Save species/number key
key.to_csv(config.stand_shp.parents[0] / 'stand_ID_key.csv', index=False)

# Convert ages from strings to numbers
stand_shp['Age_2020'].replace('200+', '200', inplace=True)
stand_shp['Age_2020'] = stand_shp['Age_2020'].astype(int)
stand_shp.loc[pd.isnull(stand_shp['Age_2020']), 'Age_2020'] = 0

# Assign unique numbers to each stand+type combo (some stands have multiple stands, so we can't use STAND_ID)
stand_shp.insert(0, 'VELMA_ID', range(1, len(stand_shp)+1))
# Export shp as csv for creating disturbance map based on stand IDs
stand_shp_csv = pd.DataFrame(stand_shp.drop(columns='geometry'))
stand_shp_csv.to_csv(config.stand_id_velma.parents[0] / 'disturbance_map.csv', index=False)

# Reproject to DEM crs
dem_file = str(config.dem)
with rasterio.open(dem_file, 'r') as src:
    dem_crs = src.crs.to_string()
stand_shp = stand_shp.to_crs(dem_crs)
updated_shp = config.stand_shp.parents[0] / 'Ellsworth_Stands_updated.shp'
stand_shp.to_file(updated_shp)

# Convert vector to raster (stand type)
stand_type = str(config.stand_type)
# Take DEM and set all values to NaN, then burn species shp into empty DEM raster
with rasterio.open(dem_file, 'r') as src:
    in_arr = src.read(1)
    in_arr[:] = -9999
    meta = src.meta.copy()
    meta = src.meta
    with rasterio.open(stand_type, 'w+', **meta) as out:
        shapes = ((geom, value) for geom, value in zip(stand_shp.geometry, stand_shp.SPECIES_ID))
        burned = features.rasterize(shapes=shapes, fill=np.nan, out=in_arr, transform=out.transform)
        out.write_band(1, burned)

# Convert vector to raster (stand age)
stand_age = str(config.stand_age)
# Take DEM and set all values to NaN, then burn species shp into empty DEM raster
with rasterio.open(dem_file, 'r') as src:
    in_arr = src.read(1)
    in_arr[:] = -9999
    meta = src.meta.copy()
    meta = src.meta
    with rasterio.open(stand_age, 'w+', **meta) as out:
        shapes = ((geom, value) for geom, value in zip(stand_shp.geometry, stand_shp.Age_2020))
        burned = features.rasterize(shapes=shapes, fill=np.nan, out=in_arr, transform=out.transform)
        out.write_band(1, burned)

# Convert vector to raster (stand ID)
stand_id = str(config.stand_id)
# Take DEM and set all values to NaN, then burn species shp into empty DEM raster
with rasterio.open(dem_file, 'r') as src:
    in_arr = src.read(1)
    in_arr[:] = -9999
    meta = src.meta.copy()
    meta = src.meta
    with rasterio.open(stand_id, 'w+', **meta) as out:
        shapes = ((geom, value) for geom, value in zip(stand_shp.geometry, stand_shp.VELMA_ID))
        burned = features.rasterize(shapes=shapes, fill=np.nan, out=in_arr, transform=out.transform)
        out.write_band(1, burned)

