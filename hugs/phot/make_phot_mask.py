"""
Tools for mask making for photometry.
SEP is used extensively throughout: https://sep.readthedocs.io

The logic and structure of these functions were heavily inspired 
by Song Huang's work: https://github.com/dr-guangtou/hs_hsc/py
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import numpy as np
import scipy.ndimage as ndimage

import sep

from .._utils import bit_flag_dict

__all__ = ['meas_back', 'detect_sources', 'make_seg_mask', 
           'make_obj_mask', 'make_phot_mask']


def _byteswap(arr):
    """
    If array is in big-endian byte order (as astropy.io.fits
    always returns), swap to little-endian for SEP.
    """
    if arr.dtype.byteorder is '>':
        arr = arr.byteswap().newbyteorder()
    return arr


def _outside_circle(cat, xc, yc, r):
    """
    Returns a mask of all objectes that fall outside a 
    circle centered at (xc, yc) of radius r. 
    """
    return np.sqrt((cat['x']-xc)**2 + (cat['y']-yc)**2) > r


def make_seg_mask(seg, grow_sig=6.0, mask_thresh=0.01, mask_max=1000.0):
    """
    Make mask from segmentation image. The mask is convolved with 
    a Gaussian to "grow the mask".

    Parameters
    ----------
    seg : 2D ndarray
        Segmentation map from SEP.
    grow_sig : float, optional
        Sigma of Gaussian kernel in pixels. 
    mask_thresh : float, optional
        All pixels above this value will be masked.
    mask_max : float, optional
        All pixels >0 will be set to this value 
        prior to the convolution. 

    Returns
    -------
    mask : 2D ndarray
        Mask with same shape as seg.
    """
    mask = seg.copy()
    mask[mask>0] = mask_max
    mask = ndimage.gaussian_filter(mask, sigma=grow_sig)
    mask = mask > (mask_max*mask_thresh)
    return mask.astype(int)


def make_obj_mask(cat, img_shape, grow_r=1.0):
    """
    Use SEP to build a mask based on objects in input catalog.

    Parameters
    ----------
    cat : astropy.table.Table
        Source catalog form SEP.
    img_shape : array-like
        The shape of the image to be masked.
    grow_r : float, optional
        Fraction to grow the objects sizes.  

    Returns
    -------
    mask : 2D ndarray
        Mask with same shape as img_shape.
    """
    mask = np.zeros(img_shape, dtype='uint8')
    sep.mask_ellipse(mask, cat['x'], cat['y'], cat['a'],
                     cat['b'], cat['theta'], grow_r)
    return mask


def meas_back(img, backsize, backffrac=0.5, mask=None, sub_from_img=True):
    """
    Measure the sky background of image.

    Parameters
    ----------
    img : ndarray
        2D numpy array of image.
    backsize : int
        Size of background boxes in pixels.
    backffrac : float, optional
        The fraction of background box size for the 
        filter size for smoothing the background.
    mask : ndarray, optional
        Mask array for pixels to exclude from background
        estimation. 
    sub_from_img : bool, optional
        If True, also return background subtracted image.

    Returns
    -------
    bkg : sep.Background object 
       See SEP documentation for methods & attributes. 
    img_bsub : ndarray, if sub_from_img is True
    """
    img = _byteswap(img)
    mask = mask if mask is None else mask.astype(bool)
    bw = bh = backsize
    fw = fh = int(backffrac*backsize)
    bkg = sep.Background(img, mask=mask,  bw=bw, bh=bh, fw=fw, fh=fh)
    if sub_from_img:
        bkg.subfrom(img)
        return bkg, img
    else:
        return bkg


def detect_sources(img, thresh, backsize, backffrac=0.5, sig=None, 
                   mask=None, return_all=False, **kwargs):
    """
    Detect sources to construct a mask for photometry. 

    Parameters
    ----------
    img : 2D ndarray
        Image to be masked.
    thresh : float
        Detection threshold with respect to background 
        for source extraction. 
    backsize : int
        Size of background boxes in pixels.
    backffrac : float, optional
        The fraction of background box size for the 
        filter size for smoothing the background.
    sig : 2D ndarray, optional
        Simga image. Must have same shape as img.
    mask : ndarray, optional
        Mask to apply before background estimation.
        Must have same shape as img.
    return_all : bool, optional
        If True, return the catalog objects, seg map, 
        background image, and the background subtracted
        image. 

    Returns
    -------
    obj : astropy.table.Table
        Source catalog from SEP.
    seg : 2D ndarray
        Segmentation map from the source extraction. 
        Same shape as input image.
    bck : 2D ndarray, if return_all=True
        Background image measured by SEP. 
    img : 2D ndarray, if return_all=True
        Background subtracted image.
    """
    img = _byteswap(img)
    bkg, img = meas_back(img, backsize, backffrac, mask)
    if sig is None:
        thresh *= bkg.globalrms
    else:
        sig = _byteswap(sig)
    obj, seg = sep.extract(img, thresh, err=sig,
                           segmentation_map=True, **kwargs)

    return (obj, seg, bkg, img) if return_all else (obj, seg)


def make_phot_mask(img, thresh, backsize, backffrac=0.5, sig=None, mask=None,
                   gal_pos='center', seg_rmin=100.0, obj_rmin=15.0, 
                   grow_sig=5.0, mask_thresh=0.01, grow_obj=4.5, 
                   mask_from_hsc=True, sep_extract_params={}):
    """
    Generate a mask for galaxy photometry using SEP. Many of these
    parameters are those of SEP, so see its documentation for 
    more info.

    Parameters
    ----------
    img : 2D ndarray
        Image to be masked.
    thresh : float
        Detection threshold for source extraction.  
    backsize : int
        Size of box for background estimation.
    backffrac : float, optional
        Fraction of backsize to make the background median filter.
    sig : 2D ndarray, optional
        Simga image. Must have same shape as img.
    mask : ndarray, optional
        Mask to apply before background estimation.
        Must have same shape as img.
    gal_pos : array-like, optional
        (x,y) position of galaxy in pixels. If 'center', the 
        center of the image is assumed.
    seg_rmin : float, optional
        Minimum radius with respect to gal_pos for the 
        segmentation mask. 
    obj_rmin : float, optional
        Minimum radius with respect to gal_pos for the 
        object mask. 
    grow_sig : float, optional
        Sigma of the Gaussian that the segmentation mask
        is convolved with to 'grow' the mask. 
    mask_thresh : float, optional
        All pixels above this threshold will be masked 
        in the seg mask. 
    grow_obj : float, optional
        Fraction to grow the objects of the obj mask. 
    mask_from_hsc : bool, optional
        If True, the input mask is from the HSC pipeline. 
    sep_extract_params : dict, optional
        Extra parameters for SEP's extract function. By extra, 
        we mean parameters that are not given as input to 
        this function: 
        (http://sep.readthedocs.io/en/v0.6.x/api/sep.extract.html)
        
    Returns
    -------
    final_mask : 2D ndarray
        Final mask to apply to img, where 0 represents good pixels
        and 1 masked pixels. The final mask is a combination of 
        a segmentation, object, and (if given) HSC's bad pixel 
        mask. 
    """

    if gal_pos=='center':
        gal_x, gal_y = (img.shape[1]/2, img.shape[0]/2)
    else:
        gal_x, gal_y = gal_pos

    #################################################################
    # If an HSC mask is given, use the non-detection bits as a bad 
    # pixel map. 
    #################################################################

    if (mask is not None) and mask_from_hsc:
        hsc_bad_mask = mask.copy()
        detected = bit_flag_dict['DETECTED']
        hsc_bad_mask[hsc_bad_mask==detected] = 0
    else:
        hsc_bad_mask = np.zeros(img.shape, dtype=int)
    
    #################################################################
    # Detect sources in image to mask before we do photometry.
    #################################################################

    obj, seg, bkg, img = detect_sources(img, thresh, backsize, backffrac, sig, 
                                        mask, True, **sep_extract_params)

    #################################################################
    # Exclude objects inside seg_rmin and obj_rmin. Note that the 
    # segmentation label of the object at index i is i+1.
    #################################################################

    exclude_labels = np.where(~_outside_circle(obj, gal_x, gal_y, seg_rmin))[0] 
    exclude_labels += 1
    for label in exclude_labels:
        seg[seg==label] = 0

    keepers = _outside_circle(obj, gal_x, gal_y, obj_rmin)
    obj = obj[keepers]

    #################################################################
    # Generate segmentation and object masks. Combine with HSC bad 
    # pixel mask (if given) to form the final mask.
    #################################################################
    
    seg_mask = make_seg_mask(seg, grow_sig, mask_thresh)
    obj_mask = make_obj_mask(obj, img.shape, grow_obj)
    final_mask = (seg_mask | obj_mask | hsc_bad_mask).astype(int)

    return final_mask