import numpy as np


def jog_character_boxes(deltax, deltay, upper_field_boxes, lower_field_boxes):
    for i, box in enumerate(lower_field_boxes):
        xL, xR, yL, yU = box
        xL += deltax
        xR += deltax
        yL += deltay
        yU += deltay
        lower_field_boxes[i] = (xL, xR, yL, yU)

    for i, box in enumerate(upper_field_boxes):
        xL, xR, yL, yU = box
        xL += deltax
        xR += deltax
        yL += deltay
        yU += deltay
        upper_field_boxes[i] = (xL, xR, yL, yU)


def reset_character_boxes(xorg_upper, xorg_lower, yorg_upper, yorg_lower, upper_field_boxes, lower_field_boxes):
    xL, xR, yL, yU = lower_field_boxes[0]
    deltax = xorg_lower - xL
    deltay = yorg_lower - yL
    for i, box in enumerate(lower_field_boxes):
        xL, xR, yL, yU = box
        xL += deltax
        xR += deltax
        yL += deltay
        yU += deltay
        lower_field_boxes[i] = (xL, xR, yL, yU)

    xL, xR, yL, yU = upper_field_boxes[0]
    deltax = xorg_upper - xL
    deltay = yorg_upper - yL

    for i, box in enumerate(upper_field_boxes):
        xL, xR, yL, yU = box
        xL += deltax
        xR += deltax
        yL += deltay
        yU += deltay
        upper_field_boxes[i] = (xL, xR, yL, yU)


def setup_for_iota_safe_mode():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in safe mode

    # Define xy coordinates of lower field character box corners
    xcL = [72, 96, 146, 170, 220, 244, 417, 441, 465, 490]
    ycL = [199] * 10

    # Define xy coordinates of upper field character box corners
    xcU = [72, 96, 146, 170, 220, 244, 294, 318, 343, 367]
    ycU = [199] * 10

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 21, ycU[i], ycU[i] + 14)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 21, ycL[i], ycL[i] + 14)

    return upper_field_boxes, lower_field_boxes


def setup_for_iota_full_screen_mode():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in full screen mode

    # Define xy coordinates of lower field character box corners
    xcL = [72, 96, 146, 170, 220, 244, 416, 441, 465, 490]
    ycL = [199+18] * 10

    # Define xy coordinates of upper field character box corners
    xcU = [72, 96, 146, 170, 220, 244, 293, 318, 343, 367]
    ycU = [199+18] * 10

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 21, ycU[i], ycU[i] + 14)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 21, ycL[i], ycL[i] + 14)

    return upper_field_boxes, lower_field_boxes


def setup_for_kiwi_vti_720():
    # Do initializations needed for KIWI VTI timestamp extraction

    # Define xy coordinates of lower field character box corners
    xcL = [60, 84, 130, 154, 201, 225, 414, 438, 462]
    ycL = [204] * 9

    # Define xy coordinates of upper field character box corners
    xcU = [59, 83, 129, 153, 200, 224, 295, 319, 343]
    ycU = [205] * 9

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)
    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 13))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 13))

    return upper_field_boxes, lower_field_boxes

def setup_for_kiwi_vti_640():
    # Do initializations needed for KIWI VTI timestamp extraction

    # Define xy coordinates of lower field character box corners
    xcL = [61, 84, 124, 147, 189, 212, 376, 399, 419]
    ycL = [204] * 9

    # Define xy coordinates of upper field character box corners
    xcU = [60, 83, 123, 146, 188, 211, 272, 294, 314]
    ycU = [205] * 9

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)
    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 13))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 13))

    return upper_field_boxes, lower_field_boxes


def setup_for_boxsprite3_640():
    # Parameters for BOXSPRITE3 VTI timestamp characters width = 640

    # Define xy coordinates of lower field character box corners
    xcL = [122, 132, 150, 160, 178, 188, 205, 215, 225, 235, 253]
    ycL = [210] * len(xcL)

    # Define xy coordinates of upper field character box corners
    xcU = [122, 132, 150, 160, 178, 188, 205, 215, 225, 235, 253]
    ycU = [211] * len(xcL)

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 9, ycU[i], ycU[i] + 14))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 9, ycL[i], ycL[i] + 14))

    return upper_field_boxes, lower_field_boxes


def setup_for_boxsprite3_720():
    # Parameters for BOXSPRITE3 VTI timestamp characters width = 720

    # Define xy coordinates of lower field character box corners
    xcL = [180, 192, 216, 228, 252, 264, 288, 300, 312, 324, 348]
    ycL = [202] * len(xcL)

    # Define xy coordinates of upper field character box corners
    xcU = [180, 192, 216, 228, 252, 264, 288, 300, 312, 324, 348]
    ycU = [202] * len(xcL)

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 10, ycU[i], ycU[i] + 14))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 10, ycL[i], ycL[i] + 14))

    return upper_field_boxes, lower_field_boxes


# def setup_for_old_iota_safe_mode():
#     # Do initializations needed for older model IOTA VTI timestamp extraction
#     # Parameters for IOTA VTI timestamp characters when in safe mode
#
#     # Define xy coordinates of lower field character box corners
#     xcL = [77, 101, 149, 173, 220, 244, 414, 438, 462, 487]
#     ycL = [199] * 10
#
#     # Define xy coordinates of upper field character box corners
#     xcU = [77, 101, 149, 173, 220, 244, 293, 317, 342, 366]
#     ycU = [200] * 10
#
#     upper_field_boxes = [None] * len(xcL)
#     lower_field_boxes = [None] * len(xcL)
#
#     # Turn box corners into full box coordinate tuples
#     for i in range(len(xcL)):
#         upper_field_boxes[i] = (xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 14)
#         lower_field_boxes[i] = (xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 14)
#
#     return upper_field_boxes, lower_field_boxes


# def setup_for_old_iota_full_screen_mode():
#     # Do initializations needed for older model IOTA VTI timestamp extraction
#     # Parameters for IOTA VTI timestamp characters when in safe mode
#
#     # Define xy coordinates of lower field character box corners
#     xcL = [77, 101, 149, 173, 222, 246, 414, 438, 462, 486]
#     ycL = [199 + 18] * 10
#
#     # Define xy coordinates of upper field character box corners
#     xcU = [77, 101, 149, 173, 222, 246, 294, 318, 342, 366]
#     ycU = [200 + 18] * 10
#
#     upper_field_boxes = [None] * len(xcL)
#     lower_field_boxes = [None] * len(xcL)
#
#     # Turn box corners into full box coordinate tuples
#     for i in range(len(xcL)):
#         upper_field_boxes[i] = (xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 14)
#         lower_field_boxes[i] = (xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 14)
#
#     return upper_field_boxes, lower_field_boxes