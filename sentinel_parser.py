# Copyright 2020 GHGSat inc.
# Authors: analytics@ghgsat.com
# This software is not for distribution outside GHGSat organization

from os import listdir
import errno
import os
import rasterio
from rasterio.warp import transform

class Tile:
    def __init__(self, cache, name, date, bands):
        self.tifs = dict()
        self.bands = dict()
        #self._BANDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8a", "B09", "B10", "B11", "B12", "AOT", "SCL", "WVP"]
        #self._BANDS = ["B11", "B12", "B02", "B03", "B04"]
        #self._BANDS = ["B01", "B02", "B04", "B05", "B08", "B8A", "B09", "B10", "B11", "B12"]
        self._BANDS = bands
        date = date.replace('-', '')

        # Find all the images
        tile_dir = f'{cache}/{name}'
        product_list = listdir(tile_dir)
        for prod in product_list:
            if date in prod: break
        if len(product_list) == 0 or (prod == product_list[-1] and date not in prod):
            # Since we don't have a filename to include in the error, just print search parameters
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), f'For tile: {name}, date: {date}, cache: {cache}') 
        prod_dir = f'{tile_dir}/{prod}/GRANULE'
        if listdir(prod_dir)[0] == '.DS_Store':
            img_dir = f'{prod_dir}/{listdir(prod_dir)[1]}/IMG_DATA'
        else:
            img_dir = f'{prod_dir}/{listdir(prod_dir)[0]}/IMG_DATA'
        
        # Open GeoTIFFs for all bands, highest res available
        #img_filenames = listdir(f'{img_dir}/R10m') + listdir(f'{img_dir}/R20m') + listdir(f'{img_dir}/R60m')
        img_filenames = listdir(img_dir)
        
        for i in img_filenames:
            b = i.split('_')[2].split('.')[0]
            #if b == "B8A": b = "B8a"
            #res = i.split('_')[-1].split('.')[0]
            if b in self._BANDS and b not in self.tifs.keys():
                #self.tifs[b] = rasterio.open(f'{img_dir}/R{res}/{i}')
                self.tifs[b] = rasterio.open(f'{img_dir}/{i}')

        # Load bands as numpy arrays
        for b, tif in self.tifs.items():
            self.bands[b] = tif.read(1)
        
    def geodetictorowcol(self, band, lat, lon):
        ew_utm, ns_utm = transform('EPSG:4326', self.tifs[band].crs, [lon], [lat]) 
        row, col = self.tifs[band].index(ew_utm[0], ns_utm[0])
        return row, col
    
    def rowcoltogeodetic(self, band, row, col):
        ew_utm, ns_utm = self.tifs[band].xy(row, col)
        lon, lat = transform(self.tifs[band].crs, 'EPSG:4326', [ew_utm], [ns_utm]) 
        return lat[0], lon[0]

    def geodetictorowcol_utm(self, band, ew_utm, ns_utm):
        row, col = self.tifs[band].index(ew_utm, ns_utm)
        return row, col

if __name__ == "__main__":
    import logging
    import argparse
    import matplotlib.pyplot as plt

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="sentinel2.py")
    parser.add_argument("--name", type=str, help="tile name")
    parser.add_argument("--band", type=str, help="tile band")
    parser.add_argument("--date", type=str, help="download date")
    parser.add_argument("--cache", type=str, help="path to cache dir")
    parser.add_argument("--coord", type=float, nargs=2, help="lat/lon coordinates of point of interest")
    parser.add_argument("--radius", type=int, help="radius of subimage of interest")
    args = parser.parse_args()

    try: tile = Tile(args.cache, args.name, args.date)
    except Exception as e: raise e

    lat = args.coord[0]
    lon = args.coord[1]

    row, col = tile.geodetictorowcol(args.band, lat, lon)
    print(f"{lat}, {lon} -> {row}, {col} in {args.band}")

    lap, lop = tile.rowcoltogeodetic(args.band, row, col)
    print(f"{row}, {col} -> {lap}, {lop} in {args.band}")

    data = tile.bands[args.band]
    nrows, ncols = data.shape

    if row - args.radius < 0: rowmin = 0
    else: rowmin = row - args.radius

    if nrows < row + args.radius: rowmax = nrows
    else: rowmax = row + args.radius

    if ncols - args.radius < 0: colmin = 0
    else: colmin = col - args.radius

    if ncols < col + args.radius: colmax = ncols
    else: colmax = col + args.radius

    img = data[rowmin:rowmax, colmin:colmax]
    plt.imshow(img)
    plt.colorbar()
    plt.savefig(f"band_{args.band}.png")

