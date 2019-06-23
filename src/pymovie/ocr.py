import numpy as np
import cv2


def setup_for_iota_safe_mode3():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in safe mode

    # Define xy coordinates of upper field character box corners
    xcU = [72, 96, 146, 170, 220, 244, 294, 318, 343, 367, 417, 441, 465, 490]
    ycU = [199] * 14

    # Define xy coordinates of lower field character box corners
    xcL = [72, 96, 146, 170, 220, 244, 294, 318, 343, 367, 417, 441, 465, 490]
    ycL = [199] * 14

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 21, ycU[i], ycU[i] + 14)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 21, ycL[i], ycL[i] + 14)

    return upper_field_boxes, lower_field_boxes


def setup_for_iota_720_safe_mode2():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in safe mode

    # Define xy coordinates of upper field character box corners
    xcU = [78, 102, 150, 174, 222, 246, 293, 318, 341, 366, 413, 438, 462, 487]
    ycU = [200] * 14

    # Define xy coordinates of lower field character box corners
    xcL = [78, 102, 150, 174, 222, 246, 293, 318, 341, 366, 413, 438, 462, 487]
    ycL = [199] * 14

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 21, ycU[i], ycU[i] + 14)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 21, ycL[i], ycL[i] + 14)

    return upper_field_boxes, lower_field_boxes


def setup_for_iota_640_safe_mode2():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in safe mode

    # Define xy coordinates of upper field character box corners
    xcU = [63, 85, 129, 151, 194, 216, 260, 282, 304, 326, 369, 390, 411, 434]
    ycU = [199] * 14

    # Define xy coordinates of lower field character box corners
    xcL = [63, 85, 129, 151, 194, 216, 260, 282, 304, 326, 369, 390, 411, 434]
    ycL = [199] * 14

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 21, ycU[i], ycU[i] + 14)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 21, ycL[i], ycL[i] + 14)

    return upper_field_boxes, lower_field_boxes


def setup_for_iota_full_screen_mode3():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in full screen mode

    # Define xy coordinates of upper field character box corners
    xcU = [72, 96, 146, 170, 220, 244, 293, 318, 343, 367, 416, 441, 465, 490]
    ycU = [199+18] * 14

    # Define xy coordinates of lower field character box corners
    xcL = [72, 96, 146, 170, 220, 244, 293, 318, 343, 367,416, 441, 465, 490]
    ycL = [199+18] * 14

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 21, ycU[i], ycU[i] + 14)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 21, ycL[i], ycL[i] + 14)

    return upper_field_boxes, lower_field_boxes


def setup_for_iota_720_full_screen_mode2():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in full screen mode

    # Define xy coordinates of upper field character box corners
    xcU = [78, 102, 151, 175, 223, 247, 295, 318, 343, 366, 415, 439, 462, 486]
    ycU = [218] * 14

    # Define xy coordinates of lower field character box corners
    xcL = [78, 102, 151, 175, 223, 247, 295, 318, 343, 366, 415, 439, 462, 486]
    ycL = [217] * 14

    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)

    # Turn box corners into full box coordinate tuples
    for i in range(len(xcL)):
        upper_field_boxes[i] = (xcU[i], xcU[i] + 21, ycU[i], ycU[i] + 14)
        lower_field_boxes[i] = (xcL[i], xcL[i] + 21, ycL[i], ycL[i] + 14)

    return upper_field_boxes, lower_field_boxes


def setup_for_iota_640_full_screen_mode2():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in full screen mode

    # Define xy coordinates of upper field character box corners
    xcU = [62, 86, 127, 151, 191, 215, 258, 282, 303, 326, 368, 391, 413, 435]
    ycU = [199+18] * 14

    # Define xy coordinates of lower field character box corners
    xcL = [62, 86, 127, 151, 191, 215, 258, 282, 303, 326, 368, 391, 413, 435]
    ycL = [199+18] * 14

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


def extract_timestamp(field, field_boxes, field_digits, formatter, thresh):
    ts = ''  # ts 'means' timestamp
    cum_score = 0
    scores = ''
    for k in range(len(field_boxes)):
        t_img = timestamp_box_image(field, field_boxes[k])
        if not thresh == 0:
            _, t_img = cv2.threshold(t_img, thresh - 1, 1, cv2.THRESH_BINARY)
        ans, score, _ = cv2_score(t_img, field_digits)
        # KIWI timestamp character can be blank.  We detect that as a low score
        # IOTA can also have empty selection boxes
        if score < 0.5:
            ans = ' '
        cum_score += score
        ts += f'{ans}'
        intscore = int(score * 100)
        if intscore > 99:
            intscore = 99
        scores += f'{intscore:02d} '
    intcumscore = int(cum_score * 100)
    scores += f'sum: {intcumscore}'
    timestamp, time = formatter(ts)
    # return timestamp, time, ts, q_factor / len(field_boxes)
    return timestamp, time, ts, scores


def format_iota_timestamp(ts):
    assert len(ts) == 14
    try:
        hh = 10 * int(ts[0]) + int(ts[1])
        mm = 10 * int(ts[2]) + int(ts[3])
        ss = 10 * int(ts[4]) + int(ts[5])
        if not ts[6] == ' ':
            ff = 1000 * int(ts[6]) + 100 * int(ts[7]) + 10 * int(ts[8]) + int(ts[9])
        else:
            ff = 1000 * int(ts[10]) + 100 * int(ts[11]) + 10 * int(ts[12]) + int(ts[13])

        time = 3600 * hh + 60 * mm + ss + ff / 10000
        # return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[6]}{ts[7]}{ts[8]}{ts[9]}]', time
        return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ff:04d}]', time
    except ValueError:
        return f'[00:00:00.0000]', -1.0  # Indicate invalid timestamp by returning negative time


def format_kiwi_timestamp(ts):
    assert len(ts) == 9
    try:
        for i, value in enumerate(ts):
            if value == ' ':
                ts[i] = '0'
        hh = 10 * int(ts[0]) + int(ts[1])
        mm = 10 * int(ts[2]) + int(ts[3])
        ss = 10 * int(ts[4]) + int(ts[5])
        ff = 100 * int(ts[6]) + 10 * int(ts[7]) + int(ts[8])
        time = 3600 * hh + 60 * mm + ss + ff / 1000
        return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[6]}{ts[7]}{ts[8]}]', time
    except ValueError:
        return f'[00:00:00.000]', -1.0  # Indicate invalid timestamp by returning negative time


def format_boxsprite3_timestamp(ts):
    assert len(ts) == 11
    try:
        hh = 10 * int(ts[0]) + int(ts[1])
        mm = 10 * int(ts[2]) + int(ts[3])
        ss = 10 * int(ts[4]) + int(ts[5])
        ff = 1000 * int(ts[7]) + 100 * int(ts[8]) + 10 * int(ts[9]) + int(ts[10])
        time = 3600 * hh + 60 * mm + ss + ff / 10000
        return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[7]}{ts[8]}{ts[9]}{ts[10]}]', time
    except ValueError:
        return f'[00:00:00.0000]', -1.0  # Indicate invalid timestamp by returning negative time


def timestamp_box_image(img, box):
    # Note: img must be in field mode
    (xL, xR, yL, yU) = box
    return img[yL:yU+1, xL:xR+1].copy()


def print_confusion_matrix(field_digits, printer):
    # Compute a 'confusion matrix' which compares the match coefficient
    # of each sample digit against all the other sample digits.

    c = np.ndarray((10,10))
    for sample in range(10):
        img = field_digits[sample].copy()
        #imgb = cv2.GaussianBlur(img.copy(), (3,3), 0)
        ans = cv2_score(img, field_digits)
        c[sample,:] = ans[2]

    # Pretty print the matrix
    printer(msg=f'Confusion matrix (scores sample digits against sample digits)', blankLine=False)
    printer(msg=f'     0    1    2    3    4    5    6    7    8    9', blankLine=False)
    for i in range(10):
        line_format = f'{i} '
        line_format += f'{c[i,0]:5.2f}{c[i,1]:5.2f}'
        line_format += f'{c[i,2]:5.2f}{c[i,3]:5.2f}'
        line_format += f'{c[i,4]:5.2f}{c[i,5]:5.2f}'
        line_format += f'{c[i,6]:5.2f}{c[i,7]:5.2f}'
        line_format += f'{c[i,8]:5.2f}{c[i,9]:5.2f}'
        printer(msg=line_format, blankLine=False)