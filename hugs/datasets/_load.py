from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import numpy as np
from astropy.table import Table
yangdir = os.path.join(os.environ.get('DATA_DIR'), 'catalogs/Yang')

__all__ = ['load_yang_groups', 'load_yang_gals',
           'load_yang_bcgs', 'get_group_prop']

def load_yang_groups():
    """
    Return an astropy table of parameters for Yang groups.
    """
    fn = os.path.join(yangdir, 'group_DR7/modelC_group')
    groups = np.loadtxt(fn, skiprows=3, usecols=(0,1,2,3,6,7))
    groups = Table([groups[:,i] for i in range(groups.shape[1])],
                   names=('group_id', 'ra', 'dec', 'z', 'Mh_Lest', 'Mh_Mest'),
                   dtype=(int, 'f8', 'f8', 'f8', 'f8', 'f8'))
    return groups


def load_yang_gals():
    """
    Return an astropy table of parameters for galaxy members of 
    Yang groups. The table is sorted by group id.
    """
    fn = os.path.join(yangdir, 'yang_modelC_all.txt')
    members = Table.read(fn, format='ascii')
    members.remove_column('gal_id')
    members.remove_column('vagc_id')
    members.sort('group_id')
    return members


def load_yang_bcgs():
    """
    Return an astropy table of parameters for BCGs
    Yang groups. The table is sorted by group id.
    """
    fn = os.path.join(yangdir, 'yang_modelC_brightest.txt')
    bcgs = Table.read(fn, format='ascii')
    bcgs.remove_column('gal_id')
    bcgs.remove_column('vagc_id')
    bcgs.sort('group_id')
    return bcgs


def get_group_prop(group_id, keys):
    """
    Get properties of a Yang group.

    Parameters
    ----------
    group_id : int
        The group id number.
    keys : string or list of strings
        Names of desired group properties.

    Returns
    -------
    vals : float or table
        The group properties.
    """
    tab = load_yang_groups()
    return tab[keys][int(group_id)-1]
