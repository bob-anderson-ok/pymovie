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
    xcL = [72, 96, 146, 170, 220, 244, 416, 440, 464, 489]
    ycL = [199] * 10

    # Define xy coordinates of upper field character box corners
    xcU = [72, 96, 146, 170, 220, 244, 293, 317, 342, 366]
    ycU = [199] * 10

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 15)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 15)

    return upper_field_boxes, lower_field_boxes


def setup_for_iota_full_screen_mode():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in full screen mode

    # Define xy coordinates of lower field character box corners
    xcL = [72, 96, 146, 170, 220, 244, 416, 440, 464, 489]
    ycL = [199+18] * 10

    # Define xy coordinates of upper field character box corners
    xcU = [72, 96, 146, 170, 220, 244, 293, 317, 342, 366]
    ycU = [199+18] * 10

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 15)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 15)

    return upper_field_boxes, lower_field_boxes