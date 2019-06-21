import numpy as np
import cv2


def setup_for_iota_safe_mode():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in safe mode

    # Define xy coordinates of upper field character box corners
    xcU = [72, 96, 146, 170, 220, 244, 294, 318, 343, 367]
    ycU = [199] * 10

    # Define xy coordinates of lower field character box corners
    xcL = [72, 96, 146, 170, 220, 244, 417, 441, 465, 490]
    ycL = [199] * 10

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

    # Define xy coordinates of upper field character box corners
    xcU = [72, 96, 146, 170, 220, 244, 293, 318, 343, 367]
    ycU = [199+18] * 10

    # Define xy coordinates of lower field character box corners
    xcL = [72, 96, 146, 170, 220, 244, 416, 441, 465, 490]
    ycL = [199+18] * 10

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 21, ycU[i], ycU[i] + 14)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 21, ycL[i], ycL[i] + 14)

    return upper_field_boxes, lower_field_boxes


def setup_for_kiwi_vti_720():
    # Do initializations needed for KIWI VTI timestamp extraction

    # Define xy coordinates of upper field character box corners
    xcU = [59, 83, 129, 153, 200, 224, 295, 319, 343]
    ycU = [205] * 9

    # Define xy coordinates of lower field character box corners
    xcL = [60, 84, 130, 154, 201, 225, 414, 438, 462]
    ycL = [204] * 9

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)
    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 13))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 13))

    return upper_field_boxes, lower_field_boxes


def setup_for_kiwi_vti_640():
    # Do initializations needed for KIWI VTI timestamp extraction

    # Define xy coordinates of upper field character box corners
    xcU = [60, 83, 123, 146, 188, 211, 272, 294, 314]
    ycU = [205] * 9

    # Define xy coordinates of lower field character box corners
    xcL = [61, 84, 124, 147, 189, 212, 376, 399, 419]
    ycL = [204] * 9

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


method = eval('cv2.TM_CCOEFF_NORMED')


def cv2_score(image, field_digits):
    img = cv2.copyMakeBorder(image, 2,2,2,2, cv2.BORDER_CONSTANT, value=0)
    max_found = 0.0
    ans = None
    max_vals = [None] * 10
    for i in range(10):
        # Apply template Matching
        res = cv2.matchTemplate(img, field_digits[i], method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        max_vals[i] = max_val
        if max_val > max_found:
            max_found = max_val
            ans = i
    return (ans, max_found, max_vals)


def extract_timestamp(field, field_boxes, field_digits, formatter):
    ts = ''  # ts 'means' timestamp
    q_factor = 0
    for k in range(len(field_boxes)):
        t_img = timestamp_box_image(field, field_boxes[k])
        ans, score, _ = cv2_score(t_img, field_digits)
        # KIWI timestamp character can be blank.  We detect that as a low score
        if score < 0.5:
            ans = 0
        ts += f'{ans}'
        q_factor += score
    timestamp, time = formatter(ts)
    return timestamp, time, ts, q_factor / len(field_boxes)


def format_iota_timestamp(ts):
    assert len(ts) == 10
    hh = 10 * int(ts[0]) + int(ts[1])
    mm = 10 * int(ts[2]) + int(ts[3])
    ss = 10 * int(ts[4]) + int(ts[5])
    ff = 1000 * int(ts[6]) + 100 * int(ts[7]) + 10 * int(ts[8]) + int(ts[9])
    time = 3600 * hh + 60 * mm + ss + ff / 10000
    return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[6]}{ts[7]}{ts[8]}{ts[9]}]', time


def format_kiwi_timestamp(ts):
    assert len(ts) == 9
    hh = 10 * int(ts[0]) + int(ts[1])
    mm = 10 * int(ts[2]) + int(ts[3])
    ss = 10 * int(ts[4]) + int(ts[5])
    ff = 100 * int(ts[6]) + 10 * int(ts[7]) + int(ts[8])
    time = 3600 * hh + 60 * mm + ss + ff / 1000
    return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[6]}{ts[7]}{ts[8]}]', time


def format_boxsprite3_timestamp(ts):
    assert len(ts) == 11
    hh = 10 * int(ts[0]) + int(ts[1])
    mm = 10 * int(ts[2]) + int(ts[3])
    ss = 10 * int(ts[4]) + int(ts[5])
    ff = 1000 * int(ts[7]) + 100 * int(ts[8]) + 10 * int(ts[9]) + int(ts[10])
    time = 3600 * hh + 60 * mm + ss + ff / 10000
    return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[7]}{ts[8]}{ts[9]}{ts[10]}]', time


# def extract_timestamps(frame, upper_field_boxes, lower_field_boxes,
#                        field_digits, formatter=None, watch=False):
#     ts, q_factor_lower = extract_lower_field_timestamp(frame, lower_field_boxes, field_digits)
#     s1, t1 = formatter(ts)
#     ts, q_factor_upper = extract_upper_field_timestamp(frame, upper_field_boxes, field_digits)
#     s2, t2 = formatter(ts)
#     if watch:
#         print(f'q_lower={q_factor_lower:4.2f}  q_upper={q_factor_upper:4.2f}')
#     return s1, t1, q_factor_lower, s2, t2, q_factor_upper


# Note: img must be in field mode
def timestamp_box_image(img, box):
    (xL, xR, yL, yU) = box
    return img[yL:yU+1, xL:xR+1].copy()