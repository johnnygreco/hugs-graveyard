#!/usr/bin/env python 

from __future__ import print_function

import os
import numpy as np
import pipeline
from sexpy import SEX_IO_DIR

def run(group_id, band='I'):
    """
    Run sextractor on images associated with galaxy group.
    """
    band = band.upper()
    results_dir = '../results/group_'+str(group_id)
    if not os.path.isdir(results_dir):
        print('creating', results_dir)
        os.mkdir(results_dir)
    group_dir = os.path.join(SEX_IO_DIR, 'sexin/group_'+str(group_id)+'/HSC-'+band)
    tracts = os.listdir(group_dir)
    for t in tracts:
        patches = os.listdir(os.path.join(group_dir, t))
        for p in patches:
            relpath = 'group_'+str(group_id)+'/HSC-'+band+'/'+t+'/'+p
            run_label = 'HSC-'+band+'_'+t+'_'+p
            pipeline.main(relpath, run_label, results_dir, clean='all', verbose=True)

def doubles_mask(cat, min_sep=0.7):
    """
    build mask for double entries. consider 
    object within min_sep arcsec the same object
    """
    from toolbox.astro import angsep
    mask = np.ones(len(cat), dtype=bool)
    for i, (ra, dec) in enumerate(cat['ALPHA_J2000','DELTA_J2000']):
        # don't search objects flagged as double entries
        if mask[i]==True:
            seps = angsep(ra, dec, cat['ALPHA_J2000'], cat['DELTA_J2000'])
            unique = seps > min_sep
            unique[i] = True # it will certainly match itself
            mask &= unique   # double entries set to False
    return mask

def combine_cats(group_id, min_sep=0.7):
    """
    Combine the catalogs into one master cat. 
    min_sep = separation at which two objects are 
    considered the same. Default is 0.7", which is 
    roughly the FWHM. 
    """
    import hugs
    from astropy.table import Table, vstack

    results_dir = '../results/group_'+str(group_id)
    files_full_cat = [f for f in os.listdir(results_dir) if 'full' in f]
    full_cat = Table()

    for f in files_full_cat:
        band, tract, patch = f.split('_')[0][-1], f.split('_')[1], f.split('_')[2]
        temptab = Table.read(os.path.join(results_dir, f), format='ascii')
        temptab['band'] = [band]*len(temptab)
        temptab['tract'] = [int(tract)]*len(temptab)
        temptab['patch'] = [patch]*len(temptab)
        full_cat = vstack([full_cat, temptab])
    print(len(full_cat), 'objects in full cat')
    mask = doubles_mask(full_cat, min_sep)
    cat = full_cat[mask]
    print(len(cat), 'object after cutting doubles')
    cat.write(os.path.join(results_dir, 'master_cat.txt'), format='ascii')
    cat = hugs.apply_cuts(cat)
    cat.write(os.path.join(results_dir, 'selection_cat.txt'), format='ascii')

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('group_id', type=int)
    parser.add_argument('-b', '--band', help='HSC band', default='I')
    parser.add_argument('--min_sep', default=0.7)
    parser.add_argument('-r', '--run_only', action='store_true')
    parser.add_argument('-c', '--combine_only', action='store_true')
    args = parser.parse_args()
    if not args.combine_only:
        run(args.group_id, args.band)
    if not args.run_only:
        combine_cats(args.group_id, args.min_sep)
