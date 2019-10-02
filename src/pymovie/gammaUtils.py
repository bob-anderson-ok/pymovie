import numpy as np

def gammaEncode8bit(x, gamma):
    scale = 255
    return int(scale * np.power(x / scale, gamma))

def gammaEncode16bit(x, gamma):
    scale = 65535
    return int(scale * np.power(x / scale, gamma))

def gammaDecode8bit(x, gamma):
    scale = 255
    return int(scale * np.power(x / scale, 1.0/gamma))

def gammaDecode16bit(x, gamma):
    scale = 65535
    return int(scale * np.power(x / scale, 1.0/gamma))

# Generate lookup table for uint16 image encoded at gamma
def gammaLookUpTableUint16(gamma):
    return np.array([gammaDecode16bit(i, gamma=gamma) for i in range(65536)])

# Generate lookup table for uint8 image encoded at gamma
def gammaLookUpTableUint8(gamma):
    return np.array([gammaDecode8bit(i, gamma=gamma) for i in range(6256)])

def gammaCorrectImg(img, lut):
    # Use given lookup table to remap img pixels
    return lut.take(img)