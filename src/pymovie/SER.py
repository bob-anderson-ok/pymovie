import numpy as np
import os
from astropy.time import Time
from datetime import datetime, timedelta


SER_HEADER_SIZE = 178

def sharpCapTimestamp(datetime64):

    usecs = int(datetime64 // 10)
    extra_digit = datetime64 - 10 * usecs
    ts = (datetime(1, 1, 1) + timedelta(microseconds=usecs))

    timestamp = (f'{ts.year}-{ts.month}-{ts.day}T{ts.hour:02d}:{ts.minute:02d}:{ts.second:02d}.{ts.microsecond:06d}'
                f'{extra_digit}')
    return timestamp

def convertNETdatetimeToJD(datetime64):
    jd = datetime64 / 864000000000 + 1721424.5
    return jd


def convertJDtoTimestamp(jd):
    t = Time(jd, format='jd', precision=4)
    return t.isot


def stringFromByteArray(byteArray):
    listOfCharacters = ""
    for byte in byteArray:
        listOfCharacters += chr(byte)
    return "".join(listOfCharacters)


def getMetaData(fpath):
    # Using the SER format description version 3 by Gischa Hahn 2014 Feb 06,
    # this function puts the meta-data into a dictionary and the timestamps (if any)
    # into a list and returns both.  All 'endian' requirements are followed EXCEPT
    # that the prevailing convention now is to treat a value of 0 in the LittleEndian
    # field is specifying little-endian byte order in 16 bit image data (opposite of 'spec').

    with open(fpath, 'rb') as f:

        ans = {}
        timestamps = []

        raw_file_ID = np.fromfile(f, dtype='uint8', count=14)
        FileID = stringFromByteArray(raw_file_ID)
        ans.update(FileID=FileID)

        # '<i4' specifies a little-endian 32 bit int
        LuID = np.fromfile(f, dtype='<i4', count=1)[0]
        ans.update(LuID=LuID)

        ColorID = np.fromfile(f, dtype='<i4', count=1)[0]
        ans.update(ColorID=ColorID)

        if not ColorID == 0:  # monochrome image
            raise ValueError("Color SER files not supported.  Only mono")

        LittleEndian = np.fromfile(f, dtype='<i4', count=1)[0]
        ans.update(LittleEndian=LittleEndian)

        ImageWidth = np.fromfile(f, dtype='<i4', count=1)[0]
        ans.update(ImageWidth=ImageWidth)

        ImageHeight = np.fromfile(f, dtype='<i4', count=1)[0]
        ans.update(ImageHeight=ImageHeight)

        PixelDepthPerPlane = np.fromfile(f, dtype='<i4', count=1)[0]
        ans.update(PixelDepthPerPlane=PixelDepthPerPlane)

        FrameCount = np.fromfile(f, dtype='<i4', count=1)[0]
        ans.update(FrameCount=FrameCount)

        raw_observer = np.fromfile(f, dtype='uint8', count=40)
        Observer = stringFromByteArray(raw_observer)
        ans.update(Observer=Observer)

        raw_instrument = np.fromfile(f, dtype='uint8', count=40)
        Instrument = stringFromByteArray(raw_instrument)
        ans.update(Instrument=Instrument)

        raw_telescope = np.fromfile(f, dtype='uint8', count=40)
        Telescope = stringFromByteArray(raw_telescope)
        ans.update(Telescope=Telescope)

        # '<i8' specifies a little-endian 64 bit integer
        datetimeLocal = np.fromfile(f, dtype='<i8', count=1)[0]
        # DateTimeLocal = convertJDtoTimestamp(convertNETdatetimeToJD(datetimeLocal))
        DateTimeLocal = sharpCapTimestamp(datetimeLocal)
        ans.update(DateTimeLocal=DateTimeLocal)

        datetimeUTC = np.fromfile(f, dtype='<i8', count=1)[0]
        # DateTimeUTC = convertJDtoTimestamp(convertNETdatetimeToJD(datetimeUTC))
        DateTimeUTC = sharpCapTimestamp(datetimeUTC)

        ans.update(DateTimeUTC=DateTimeUTC)

        if PixelDepthPerPlane > 8:
            BytesPerPixel = 2
        else:
            BytesPerPixel = 1
        ans.update(BytesPerPixel=BytesPerPixel)

        ImageDataSize = int(FrameCount) * int(ImageWidth) * int(ImageHeight) * int(BytesPerPixel)
        ans.update(ImageDataSize=ImageDataSize)

        # Two ways to get file size
        # f.seek(0,2)           # set position to offset=0 from end of file
        # fileSize = f.tell()   # tell what that position is
        FileSize = os.path.getsize(fpath)
        ans.update(FileSize=FileSize)

        NumTimestamps = (FileSize - SER_HEADER_SIZE - ImageDataSize) / 8
        ans.update(NumTimestamps=NumTimestamps)

        PositionOfTimestamps = ImageDataSize + SER_HEADER_SIZE
        ans.update(PositionOfTimestamps=PositionOfTimestamps)

        if NumTimestamps > 0:
            f.seek(PositionOfTimestamps)
            for i in range(int(NumTimestamps)):
                datetimeUTC = np.fromfile(f, dtype='<i8', count=1)[0]
                DateTimeUTC = sharpCapTimestamp(datetimeUTC)
                # DateTimeUTC = convertJDtoTimestamp(convertNETdatetimeToJD(datetimeUTC))
                timestamps.append(DateTimeUTC)

    return ans, timestamps

def getSerImage(f, frameNum, bytes_per_pixel, image_width, image_height, little_endian):
    # height is y axis   width is x axis
    num_pixels_in_frame = image_height * image_width
    frame_size = bytes_per_pixel * num_pixels_in_frame
    frame_start = int(frame_size) * int(frameNum) + SER_HEADER_SIZE
    f.seek(frame_start)
    if bytes_per_pixel == 1:
        img = np.fromfile(f, dtype='uint8', count=num_pixels_in_frame)
    elif bytes_per_pixel == 2:
        if little_endian == 0:
            img = np.fromfile(f, dtype='<u2', count=num_pixels_in_frame)
        else:
            img = np.fromfile(f, dtype='>u2', count=num_pixels_in_frame)
    else:
        raise ValueError("bytes_per_pixel must be 1 or 2")
    return img.reshape(image_height, image_width)

#   test_file = r'/Users/bob/Dropbox/SER project/ser-files-from-jan/FireCapture/190822_212734.ser'
#   meta_data, timestamps = getMetaData(test_file)
#
#   f = open(test_file, 'rb') # Leave file handle open to speed repeat reads from file
#   image = getSerImage(f, 43, meta_data['BytesPerPixel'], meta_data['ImageWidth'], meta_data['ImageHeight'], meta_data['LittleEndian'])
#   f.close() # Remember to close the file handle when no more images need to read from the file