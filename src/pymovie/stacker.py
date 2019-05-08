# Create intesified image by registering a set of frames and summing them

import numpy as np
import astropy.io.fits as pyfits
from time import gmtime, strftime  # for utc
import cv2
from skimage.filters import unsharp_mask


def asinhScale(img, limcut = 0):  # img needs to be float32 type
    # Try an asinh transformation to handle a wide dynamic range
    limg = np.arcsinh(img)
    limg = limg / limg.max()
    limg[limg < limcut] = 0.
    return limg

# # in_dir_path = r'/Users/bob/Dropbox/Wind Shake Project/DunhamJena3-20190326/FITS excerpt/'
# # out_dir_path = r'/Users/bob/Dropbox/Wind Shake Project/DunhamJena3-20190326/'
# out_dir_path = r'/Users/bob/Dropbox/Wind Shake Project/DunhamJena3-20190326/'
#
# avi_location = r'/Users/bob/Dropbox/Wind Shake Project/20190326JenaDunham3compressed.avi'
# # avi_location = r'/Users/bob/Dropbox/Wind Shake Project/2019_04_01_07_18_45_530 Turandot_UCAC4 441-058175.avi'
# # avi_location = r'/Users/bob/Dropbox/Wind Shake Project/Antiope-kiwi.avi'
# # avi_location = r'/Users/bob/Dropbox/Wind Shake Project/Camera comparison RunCam Night Eagle 001.avi'
# # avi_location = r'/Users/bob/Dropbox/Wind Shake Project/M3 Owl 3 spacers Z004_14_2017_04_04_04.avi'
# timestamp_trim = 50


def frameStacker(pr, progress_bar, event_process,
                 first_frame, last_frame, timestamp_trim,
                 avi_location, out_dir_path):
    # pr is self.showMsg() provided by the caller
    # progress_bar is a reference to the caller's progress bar item so
    # that can update it to show progess

    cap = None

    def read_avi_frame(frame_to_read, trim=None):
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_read)
            status, frame = cap.read()
            if trim is None or trim == 0:
                image = frame[:, :, 0].astype('float32')
            else:
                image = frame[0:-trim, :, 0].astype('float32')
            # plt.imshow(asinhScale(image), cmap='gray')
        except Exception as e:
            pr(f'Problem reading avi file: {e}')
        if status:
            return image
        else:
            return None

    def openAviReader(avi_location):
        pr(f'Trying to open: {avi_location}')
        cap = cv2.VideoCapture(avi_location)
        if not cap.isOpened():
            pr(f'  {avi_location} could not be opened!')
            return None
        else:
            pr(f'...file opened just fine.')
            return cap

    cap = openAviReader(avi_location=avi_location)
    if cap is None:
        return
    # else:
    #     cap.release()
    #     return

    next_frame = first_frame + 1
    # tracking_list = []

    # Read reference frame image without trimming the timestamp portion off
    # so that we can save the timestamp for later replacement.
    inimage = read_avi_frame(first_frame)

    if timestamp_trim <= 0:
        timestamp_image = None
    else:
        timestamp_image = inimage[-timestamp_trim:,:]

    # Re-read the reference frame with the timestamp trimmed off and use it
    # to initialize the stack sum
    inimage = read_avi_frame(first_frame, trim=timestamp_trim)
    image_sum = inimage[:,:]

    # g1 is our reference image transform
    g1 = np.fft.fftshift(np.fft.fft2(inimage))

    while next_frame <= last_frame:
        inimage = read_avi_frame(next_frame, trim=timestamp_trim)
        next_frame += 1

        # Calculate progress [1..100]
        fraction_done = (next_frame - first_frame) / (last_frame - first_frame)
        progress_bar.setValue(fraction_done * 100)
        event_process()

        g2 = np.fft.fftshift(np.fft.fft2(inimage))

        g2conj = g2.conj()

        R = g1 * g2conj / abs(g1 * g2conj)

        r = np.fft.fftshift(np.fft.ifft2(R))

        mag_r = abs(r * r.conj())  # mag_r is a matrix of positive reals (not complex)

        mag_r_max = mag_r.max()

        max_row, max_col = np.unravel_index(mag_r.argmax(), mag_r.shape)

        # print(mag_r.shape, max_row, max_col)
        rows_to_roll_to_center = max_row - int(mag_r.shape[0] / 2)
        cols_to_roll_to_center = max_col - int(mag_r.shape[1] / 2)
        # print(rows_to_roll_to_center, cols_to_roll_to_center, next_frame-1)
        # tracking_list.append([rows_to_roll_to_center, cols_to_roll_to_center])

        # Center the image
        inimage = np.roll(inimage, rows_to_roll_to_center, axis=0)
        inimage = np.roll(inimage, cols_to_roll_to_center, axis=1)

        # ... and add it to the image sum
        image_sum += inimage

    progress_bar.setValue(0)

    # Sharpen the image 2 and 10 were ok  5 an2 were smudgy
    sharper_image = unsharp_mask(asinhScale(image_sum), radius=2, amount=10.0, preserve_range=True)

    if timestamp_image is not None:
        unredacted = np.append(sharper_image, asinhScale(timestamp_image), axis=0)
    else:
        unredacted = sharper_image

    # plt.imshow(unredacted, cmap='gray')
    # print(unredacted.shape)

    outfile = out_dir_path + r'/enhanced-image.fit'

    # Create the fits ojbect for this image using the header of the first image

    # max_pixel = image_sum.max()
    # image_sum = image_sum * 30000 / max_pixel
    # outlist = pyfits.PrimaryHDU(image_sum)

    # max_pixel = sharper_image.max()
    # sharper_image = sharper_image * 30000 / max_pixel
    # outlist = pyfits.PrimaryHDU(sharper_image)

    min_pixel = unredacted.min()
    unredacted = unredacted - min_pixel
    max_pixel = unredacted.max()
    unredacted = unredacted * 255 / max_pixel
    outlist = pyfits.PrimaryHDU(unredacted)

    # Provide a new date stamp

    file_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())

    # Update the header

    outhdr = outlist.header
    outhdr['DATE'] = file_time
    outhdr['FILE'] = avi_location
    outhdr['COMMENT'] = f'{last_frame - first_frame + 1} frames were stacked'
    outhdr['COMMENT'] = f'Initial frame number: {first_frame}'
    outhdr['COMMENT'] = f'Final frame number: {last_frame}'

    # Write the fits file
    outlist.writeto(outfile, overwrite = True)

    # # Write the tracking list.
    #
    # with open(out_dir_path + r'/tracking_list.txt', 'w') as f:
    #     frame = first_frame + 1
    #     for entry in tracking_list:
    #         out_str = f'{frame} {entry[0]} {entry[1]}\n'
    #         frame += 1
    #         f.writelines(out_str)
