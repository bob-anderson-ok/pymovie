"""
This module implements a routine to open an avi, read some number
of frames from that avi, clipping off the lower portion that contains
the timestamps.

Each frame is then written as a fits file into a folder named from a
supplied folder name.
"""


def writeAviToFits(avi_file_path, fits_folder_name, num_frames, clipping_level):
    pass