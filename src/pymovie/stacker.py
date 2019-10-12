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
                 first_frame, last_frame, timestamp_trim_top, timestamp_trim_bottom,
                 fitsReader, serReader,
                 avi_location, out_dir_path, bkg_threshold, hot_pixel_erase):
    # fitsReader is self.getFitsFrame()
    # serReader is self.getSerFrame()
    # pr is self.showMsg() provided by the caller
    # hot_pixel_erase is self.applyHotPixelErasureToImg
    # progress_bar is a reference to the caller's progress bar item so
    # that can update it to show progess

    cap = None

    def read_fits_frame(frame_to_read, trim_top=0, trim_bottom=0):
        try:
            frame = fitsReader(frame_to_read)
            if frame is None:
                pr(f'Problem reading FITS file: frame == None returned')
                return None

            hot_pixel_erase(frame)

            image = frame[:, :].astype('float32')

            if trim_bottom:
                image = image[0:-trim_bottom, :]

            if trim_top:
                image = image[trim_top:, :]
            # if trim > 0:
            #     image = frame[0:-trim, :].astype('float32')
            # else:
            #     image = frame[-trim:, :].astype('float32')

        except Exception as e:
            pr(f'Problem reading FITS file: {e}')
            return None

        return image

    def read_ser_frame(frame_to_read, trim_top=0, trim_bottom=0):
        try:
            frame = serReader(frame_to_read)
            if frame is None:
                pr(f'Problem reading SER file: frame == None returned')
                return None

            hot_pixel_erase(frame)

            image = frame[:, :].astype('float32')

            if trim_bottom:
                image = image[0:-trim_bottom, :]

            if trim_top:
                image = image[trim_top:, :]
            # if trim is None or trim == 0:
            #     image = frame[:, :].astype('float32')
            # else:
            #     if trim > 0:
            #         image = frame[0:-trim, :].astype('float32')
            #     else:
            #         image = frame[-trim:, :].astype('float32')

        except Exception as e:
            pr(f'Problem reading SER file: {e}')
            return None

        return image

    def read_avi_frame(frame_to_read, trim_top=0, trim_bottom=0):
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_read)
            status, frame = cap.read()

            hot_pixel_erase(frame)

            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            image = frame[:, :].astype('float32')

            if trim_bottom:
                image = image[0:-trim_bottom, :]

            if trim_top:
                image = image[trim_top:, :]

            # if trim is None or trim == 0:
            #     image = frame[:, :, 0].astype('float32')
            # else:
            #     image = frame[0:-trim, :, 0].astype('float32')
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

    if fitsReader is None and serReader is None:
        cap = openAviReader(avi_location=avi_location)
        if cap is None:
            return

    next_frame = first_frame + 1

    # Read reference frame image without trimming the timestamp portion off
    # so that we can save the timestamp for later replacement.
    if fitsReader:
        inimage = read_fits_frame(first_frame)
    elif serReader:
        inimage = read_ser_frame(first_frame)
    else:
        inimage = read_avi_frame(first_frame)

    height, width = inimage.shape
    pr(f'image shape: {width} x {height}')

    if timestamp_trim_top > 0:
        # If redact is from the top, this is assumed to be a FITS or SER file for
        # which there is no timestamp to be preserved, just a few 'corrupted' lines at the top.
        timestamp_image_top = inimage[0:timestamp_trim_top,:]
        # timestamp_image = np.zeros_like(timestamp_junk)
    else:
        timestamp_image_top = None

    if timestamp_trim_bottom > 0:
        timestamp_image_bottom = inimage[-timestamp_trim_bottom:,:]
    else:
        timestamp_image_bottom = None

    # Re-read the reference frame with the timestamp trimmed off and use it
    # to initialize the stack sum
    if fitsReader:
        inimage = read_fits_frame(first_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)
    elif serReader:
        inimage = read_ser_frame(first_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)
    else:
        inimage = read_avi_frame(first_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)

    image_sum = inimage[:,:]

    current_row_shift = None
    current_col_shift = None

    row_delta = 0
    col_delta = 0

    frames_skipped = 0

    # g1 is our reference image transform
    # g1 = np.fft.fftshift(np.fft.fft2(inimage))
    ret, th_inimage = cv2.threshold(inimage, bkg_threshold, 0, cv2.THRESH_TOZERO)
    g1 = np.fft.fftshift(np.fft.fft2(th_inimage))

    while next_frame <= last_frame:
        if fitsReader:
            inimage = read_fits_frame(next_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)
        elif serReader:
            inimage = read_ser_frame(next_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)
        else:
            inimage = read_avi_frame(next_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)

        next_frame += 1

        # Calculate progress [1..100]
        fraction_done = (next_frame - first_frame) / (last_frame - first_frame)
        progress_bar.setValue(fraction_done * 100)
        event_process()

        # g2 = np.fft.fftshift(np.fft.fft2(inimage))
        ret, th_inimage = cv2.threshold(inimage, bkg_threshold, 0, cv2.THRESH_TOZERO)
        g2 = np.fft.fftshift(np.fft.fft2(th_inimage))

        g2conj = g2.conj()

        R = g1 * g2conj / abs(g1 * g2conj)

        r = np.fft.fftshift(np.fft.ifft2(R))

        mag_r = abs(r * r.conj())  # mag_r is a matrix of positive reals (not complex)

        mag_r_max = mag_r.max()

        max_row, max_col = np.unravel_index(mag_r.argmax(), mag_r.shape)

        # print(mag_r.shape, max_row, max_col)
        rows_to_roll_to_center = max_row - int(mag_r.shape[0] / 2)
        cols_to_roll_to_center = max_col - int(mag_r.shape[1] / 2)
        # good_row_shift = abs(rows_to_roll_to_center - current_row_shift) % height < 7
        # good_col_shift = abs(cols_to_roll_to_center - current_col_shift) % width  < 7
        good_row_shift = True
        good_col_shift = True
        if good_col_shift and good_row_shift:
            pr(f'row-shift:{rows_to_roll_to_center:4d}  col-shift:{cols_to_roll_to_center:4d}  frame: {next_frame-1}',
               blankLine=False)
            current_row_shift = rows_to_roll_to_center
            current_col_shift = cols_to_roll_to_center
        else:
            frames_skipped += 1
            pr(f'row-shift:{rows_to_roll_to_center:4d}  col-shift:{cols_to_roll_to_center:4d}  frame: {next_frame - 1}'
               f' suppressed',
               blankLine=False)
            continue

        # tracking_list.append([rows_to_roll_to_center, cols_to_roll_to_center])

        # Center the image
        inimage = np.roll(inimage, rows_to_roll_to_center, axis=0)
        inimage = np.roll(inimage, cols_to_roll_to_center, axis=1)

        # ... and add it to the image sum
        image_sum += inimage

    progress_bar.setValue(0)

    # Sharpen the image 2 and 10 were ok  5 and 2 were smudgy
    sharper_image = unsharp_mask(asinhScale(image_sum), radius=2, amount=10.0, preserve_range=True)
    unredacted = sharper_image

    if not timestamp_image_bottom is None:
        unredacted = np.append(unredacted, asinhScale(timestamp_image_bottom), axis=0)
    if not timestamp_image_top is None:
        unredacted = np.append(asinhScale(timestamp_image_top), unredacted, axis=0)

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
    outhdr['COMMENT'] = f'{frames_skipped} frames were not included in the stack'
    outhdr['COMMENT'] = f'Initial frame number: {first_frame}'
    outhdr['COMMENT'] = f'Final frame number: {last_frame}'

    # Write the fits file
    outlist.writeto(outfile, overwrite = True)

def hotPixelStack(pr, progress_bar, event_process,
                 first_frame, last_frame, timestamp_trim_top, timestamp_trim_bottom,
                 fitsReader, serReader,
                 avi_location, out_dir_path, bkg_threshold):

    # fitsReader is self.getFitsFrame()
    # serReader is self.getSerFrame()
    # pr is self.showMsg() provided by the caller
    # progress_bar is a reference to the caller's progress bar item so
    # that can update it to show progess

    pr(f'hot pixel stacker called.')
    # return

    cap = None

    def read_fits_frame(frame_to_read, trim_top=0, trim_bottom=0):
        try:
            frame = fitsReader(frame_to_read)
            if frame is None:
                pr(f'Problem reading FITS file: frame == None returned')
                return None

            image = frame[:, :].astype('float32')

            if trim_bottom:
                image = image[0:-trim_bottom, :]

            if trim_top:
                image = image[trim_top:, :]
            # if trim > 0:
            #     image = frame[0:-trim, :].astype('float32')
            # else:
            #     image = frame[-trim:, :].astype('float32')

        except Exception as e:
            pr(f'Problem reading FITS file: {e}')
            return None

        return image

    def read_ser_frame(frame_to_read, trim_top=0, trim_bottom=0):
        try:
            frame = serReader(frame_to_read)
            if frame is None:
                pr(f'Problem reading SER file: frame == None returned')
                return None

            image = frame[:, :].astype('float32')

            if trim_bottom:
                image = image[0:-trim_bottom, :]

            if trim_top:
                image = image[trim_top:, :]
            # if trim is None or trim == 0:
            #     image = frame[:, :].astype('float32')
            # else:
            #     if trim > 0:
            #         image = frame[0:-trim, :].astype('float32')
            #     else:
            #         image = frame[-trim:, :].astype('float32')

        except Exception as e:
            pr(f'Problem reading SER file: {e}')
            return None

        return image

    def read_avi_frame(frame_to_read, trim_top=0, trim_bottom=0):
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_read)
            status, frame = cap.read()

            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            image = frame[:, :].astype('float32')

            if trim_bottom:
                image = image[0:-trim_bottom, :]

            if trim_top:
                image = image[trim_top:, :]

            # if trim is None or trim == 0:
            #     image = frame[:, :, 0].astype('float32')
            # else:
            #     image = frame[0:-trim, :, 0].astype('float32')
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

    if fitsReader is None and serReader is None:
        cap = openAviReader(avi_location=avi_location)
        if cap is None:
            return

    next_frame = first_frame + 1

    # Read reference frame image without trimming the timestamp portion off
    # so that we can save the timestamp for later replacement.
    if fitsReader:
        inimage = read_fits_frame(first_frame)
    elif serReader:
        inimage = read_ser_frame(first_frame)
    else:
        inimage = read_avi_frame(first_frame)

    if timestamp_trim_top > 0:
        # If redact is from the top, this is assumed to be a FITS or SER file for
        # which there is no timestamp to be preserved, just a few 'corrupted' lines at the top.
        timestamp_image_top = inimage[0:timestamp_trim_top,:]
        # timestamp_image = np.zeros_like(timestamp_junk)
    else:
        timestamp_image_top = None

    if timestamp_trim_bottom > 0:
        timestamp_image_bottom = inimage[-timestamp_trim_bottom:,:]
    else:
        timestamp_image_bottom = None

    # Re-read the reference frame with the timestamp trimmed off and use it
    # to initialize the stack sum
    if fitsReader:
        inimage = read_fits_frame(first_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)
    elif serReader:
        inimage = read_ser_frame(first_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)
    else:
        inimage = read_avi_frame(first_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)

    image_sum = inimage[:,:]

    ret, th_inimage = cv2.threshold(inimage, bkg_threshold, 0, cv2.THRESH_TOZERO)

    while next_frame <= last_frame:
        if fitsReader:
            inimage = read_fits_frame(next_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)
        elif serReader:
            inimage = read_ser_frame(next_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)
        else:
            inimage = read_avi_frame(next_frame, trim_top=timestamp_trim_top, trim_bottom=timestamp_trim_bottom)

        next_frame += 1

        # Calculate progress [1..100]
        fraction_done = (next_frame - first_frame) / (last_frame - first_frame)
        progress_bar.setValue(fraction_done * 100)
        event_process()

        ret, th_inimage = cv2.threshold(inimage, bkg_threshold, 0, cv2.THRESH_TOZERO)
        # ... and add it to the image sum
        image_sum += inimage

    progress_bar.setValue(0)

    avg_image = image_sum / (last_frame - first_frame + 1)

    # if not timestamp_image_bottom is None:
    #     unredacted = np.append(unredacted, asinhScale(timestamp_image_bottom), axis=0)
    # if not timestamp_image_top is None:
    #     unredacted = np.append(asinhScale(timestamp_image_top), unredacted, axis=0)

    # outfile = out_dir_path + r'/enhanced-image.fit'

    # min_pixel = unredacted.min()
    # unredacted = unredacted - min_pixel
    # max_pixel = unredacted.max()
    # unredacted = unredacted * 255 / max_pixel

    return avg_image.astype('uint8')

def find_outlier_pixels(data,tolerance=3,worry_about_edges=True):
    #This function finds the hot or dead pixels in a 2D dataset.
    #tolerance is the number of standard deviations used to cutoff the hot pixels
    #If you want to ignore the edges and greatly speed up the code, then set
    #worry_about_edges to False.
    #
    #The function returns a list of hot pixels and also an image with with hot pixels removed

    from scipy.ndimage import median_filter
    blurred = median_filter(data, size=3)
    difference = data - blurred
    threshold = 10 * np.std(difference)

    #find the hot pixels, but ignore the edges
    hot_pixels = np.nonzero((np.abs(difference[1:-1,1:-1])>threshold) )
    hot_pixels = np.array(hot_pixels) + 1 #because we ignored the first row and first column

    fixed_image = np.copy(data) #This is the image with the hot pixels removed
    for y,x in zip(hot_pixels[0],hot_pixels[1]):
        fixed_image[y,x]=blurred[y,x]

    if worry_about_edges == True:
        height,width = np.shape(data)

        ###Now get the pixels on the edges (but not the corners)###

        #left and right sides
        for index in range(1,height-1):
            #left side:
            med  = np.median(data[index-1:index+2,0:2])
            diff = np.abs(data[index,0] - med)
            if diff>threshold:
                hot_pixels = np.hstack(( hot_pixels, [[index],[0]]  ))
                fixed_image[index,0] = med

            #right side:
            med  = np.median(data[index-1:index+2,-2:])
            diff = np.abs(data[index,-1] - med)
            if diff>threshold:
                hot_pixels = np.hstack(( hot_pixels, [[index],[width-1]]  ))
                fixed_image[index,-1] = med

        #Then the top and bottom
        for index in range(1,width-1):
            #bottom:
            med  = np.median(data[0:2,index-1:index+2])
            diff = np.abs(data[0,index] - med)
            if diff>threshold:
                hot_pixels = np.hstack(( hot_pixels, [[0],[index]]  ))
                fixed_image[0,index] = med

            #top:
            med  = np.median(data[-2:,index-1:index+2])
            diff = np.abs(data[-1,index] - med)
            if diff>threshold:
                hot_pixels = np.hstack(( hot_pixels, [[height-1],[index]]  ))
                fixed_image[-1,index] = med

        ###Then the corners###

        #bottom left
        med  = np.median(data[0:2,0:2])
        diff = np.abs(data[0,0] - med)
        if diff>threshold:
            hot_pixels = np.hstack(( hot_pixels, [[0],[0]]  ))
            fixed_image[0,0] = med

        #bottom right
        med  = np.median(data[0:2,-2:])
        diff = np.abs(data[0,-1] - med)
        if diff>threshold:
            hot_pixels = np.hstack(( hot_pixels, [[0],[width-1]]  ))
            fixed_image[0,-1] = med

        #top left
        med  = np.median(data[-2:,0:2])
        diff = np.abs(data[-1,0] - med)
        if diff>threshold:
            hot_pixels = np.hstack(( hot_pixels, [[height-1],[0]]  ))
            fixed_image[-1,0] = med

        #top right
        med  = np.median(data[-2:,-2:])
        diff = np.abs(data[-1,-1] - med)
        if diff>threshold:
            hot_pixels = np.hstack(( hot_pixels, [[height-1],[width-1]]  ))
            fixed_image[-1,-1] = med

    return hot_pixels, fixed_image.astype('uint8')