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

# def erase_current_character_boxes():
#     # Get current ax from current plot (plt)
#     ax = plt.gca()
#     # Get all the lines that have been drawn (the character box lines)
#     box_lines = ax.get_lines()
#     # Erase all the lines
#     while len(box_lines):
#         box_lines.pop(0).remove()

def setup_for_iota1_vti():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters
    xW = 24  # 'width of character
    yH = 32  # height of character box

    yS = int(yH / 2)  # Height of field digits

    # This is used during training to show an image of a missing template.
    blank = np.zeros((yS, xW), dtype='uint8')

    field_box_xorg_lower = 77

    # Define xy coordinates of lower field character box corners
    xcL = [77, 101, 149, 173, 221, 245, 413, 437, 461, 485]
    ycL = [198] * 10

    field_box_xorg_upper = 77

    # Define xy coordinates of upper field character box corners
    xcU = [77, 101, 149, 173, 221, 245, 293, 317, 341, 365]
    ycU = [199] * 10

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 15))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 15))

    return upper_field_boxes, lower_field_boxes, blank, field_box_xorg_upper, field_box_xorg_lower