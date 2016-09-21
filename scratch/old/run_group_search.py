#!/usr/bin/env python 

from __future__ import print_function

import os
import numpy as np
from sex import runsex, kernals, config

def run(group_id, kernal):
    """
    Run sextractor on images associated with galaxy group.
    """
    relpath = 'group_'+str(group_id)
    imgfiles = [d for d in os.listdir('sexin/'+relpath) if 'img' in d]
    wtsfiles = [d for d in os.listdir('sexin/'+relpath) if 'wts_bad' in d]

    kern_name = kernal[0]
    size = int(kernal[1])
    width_param = float(kernal[2])
    
    kern = {'gauss':kernals.gauss, 'exp':kernals.exp}[kern_name]
    convfile = kern(size, width_param, write=True)

    config['CHECKIMAGE_TYPE'] = 'NONE'
    config['FILTER_NAME'] = convfile

    for img_file, wts_file in zip(imgfiles, wtsfiles):
        prefix = img_file[:-8]
        config['WEIGHT_IMAGE'] = wts_file
        runsex(img_file, cat=prefix+'sex.cat', relpath=relpath, **config)

def combine_cats(group_id, min_sep=0.7):
    """
    Combine the catalogs into one master cat. 
    min_sep = separation at which two objects are 
    considered the same. Default is 0.7", which is 
    roughly the FWHM. 
    """
    from astropy.table import Table, vstack
    from toolbox.utils import read_sexout
    from toolbox.astro import angsep
    path = 'sexout/group_'+str(group_id)+'/'
    catfiles = [d for d in os.listdir(path) if 'sex.cat' in d]
    tract = catfiles[0].split('_')[1]
    patch = catfiles[0].split('_')[2]
    cat = read_sexout(path+catfiles[0])
    cat['tract'] = [int(tract)]*len(cat)
    cat['patch'] = [patch]*len(cat)
    for f in catfiles[1:]:
        tempcat = read_sexout(path+f)
        tract = f.split('_')[1]
        patch = f.split('_')[2]
        tempcat['tract'] = [int(tract)]*len(tempcat)
        tempcat['patch'] = [patch]*len(tempcat)
        cat = vstack([cat, tempcat])
    print(len(cat), 'objects in initial master catalog')

    ###############################################
    # build mask for double entries. consider 
    # object within min_sep arcsec the same object
    ###############################################
    mask = np.ones(len(cat), dtype=bool)
    for i, (ra, dec) in enumerate(cat['ALPHA_J2000','DELTA_J2000']):
        # don't search objects flagged as double entries
        if mask[i]==True:
            seps = angsep(ra, dec, cat['ALPHA_J2000'], cat['DELTA_J2000'])
            unique = seps > min_sep
            unique[i] = True # it will certainly match itself
            mask &= unique   # double entries set to False
    cat = cat[mask]
    print(len(cat), 'objects after removing double entries with min sep =',
          min_sep, 'arcsec')
    cat.write(path+'master.cat', format='ascii')

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run sextractor on group')
    parser.add_argument('group_id', type=int, help='galaxy group id')
    parser.add_argument('-m', '--min_sep', type=float, help='min sep btw'
            ' catalog objects in arcsec', default=0.7)
    parser.add_argument('-k', '--kernal', nargs=3, default=['gauss', 9, 5.0],
            help='kernal: name, size, width_param')
    parser.add_argument('-r', '--run_only', help='only call run function',
            action='store_true')
    parser.add_argument('-c', '--combine_only', help='only call combine_cats function',
            action='store_true')
    args = parser.parse_args()
    if not args.combine_only:
        print('searching around group', args.group_id)
        run(args.group_id, kernal=args.kernal)
    if not args.run_only:
        print('combining catalogs into master.cat')
        combine_cats(args.group_id, min_sep=args.min_sep)