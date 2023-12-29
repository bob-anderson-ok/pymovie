# An even better way is to locate and remove stars from the field, then apply sigma clipping

from astropy.stats import sigma_clipped_stats, SigmaClip
from photutils.segmentation import detect_threshold, detect_sources
from photutils.utils import circular_footprint, NoDetectionsWarning

import warnings
warnings.filterwarnings('ignore', category=NoDetectionsWarning)

def starsRemovedBkgd(data):
    sigma_num = 3.2

    # To get an inital estimate of std (needed by detect_threshold()), we use sigma clipping, already a pretty good estimator
    sigma_clip = SigmaClip(sigma=sigma_num, maxiters=10)

    threshold = detect_threshold(data, nsigma=sigma_num, sigma_clip=sigma_clip)

    # print(threshold)

    # Then, using the threshold, we find all pixel groups that are above the threshold with a given number of connected pixels
    segment_img = detect_sources(data, threshold, npixels=10)

    if segment_img is None:
        mean, median, std = sigma_clipped_stats(data, sigma=sigma_num)
        return mean, std

    # The footprint is used to expand the boudary of each pixel patch. Here we create the 'footprint'
    footprint = circular_footprint(radius=10)

    # ... and here we apply the footprint to the pixel groups and form a binary mask
    mask = segment_img.make_source_mask(footprint=footprint)

    mean, median, std = sigma_clipped_stats(data, sigma=sigma_num, mask=mask)

    return mean, std
