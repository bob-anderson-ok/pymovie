import numpy as np
import cv2
import matplotlib.pyplot as plt


def setup_for_iota_720_safe_mode3():
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


def setup_for_iota_640_safe_mode3():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in safe mode

    # Define xy coordinates of upper field character box corners
    xcU = [64, 87, 129, 151, 194, 217, 260, 282, 303, 325, 369, 391, 413, 435]
    ycU = [199] * 14

    # Define xy coordinates of lower field character box corners
    xcL = [64, 87, 129, 151, 194, 217, 260, 282, 303, 325, 369, 391, 413, 435]
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


def setup_for_iota_720_full_screen_mode3():
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


def setup_for_iota_640_full_screen_mode3():
    # Do initializations needed for IOTA VTI timestamp extraction
    # Parameters for IOTA VTI timestamp characters when in full screen mode

    # Define xy coordinates of upper field character box corners
    xcU = [62, 85, 129, 151, 193, 216, 259, 281, 303, 325, 368, 390, 412, 434]
    ycU = [217] * 14

    # Define xy coordinates of lower field character box corners
    xcL = [62, 85, 129, 151, 193, 216, 259, 281, 303, 325, 368, 390, 412, 434]
    ycL = [217] * 14

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


def kiwi_720_boxes(dx):
    # Define xy coordinates of upper field character box corners
    xcU = [59, 83, 130, 154, 200, 224, 295, 320, 345, 414, 438, 462]
    ycU = [205] * 12

    # Define xy coordinates of lower field character box corners
    xcL = [60, 84, 130, 154, 201, 225, 295, 320, 343, 414, 438, 462]
    ycL = [204] * 12

    xcU = [x + dx for x in xcU]
    xcL = [x + dx for x in xcL]

    return xcU, ycU, xcL, ycL


def setup_for_kiwi_vti_720_left():

    xcU, ycU, xcL, ycL = kiwi_720_boxes(0)

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)
    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 13))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 13))

    return upper_field_boxes, lower_field_boxes


def setup_for_kiwi_vti_720_right():

    xcU, ycU, xcL, ycL = kiwi_720_boxes(11)

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)
    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 13))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 13))

    return upper_field_boxes, lower_field_boxes


def kiwi_640_boxes(dx):
    # Define xy coordinates of upper field character box corners
    xcU = [49, 72, 112, 135, 177, 197, 261, 282, 302, 365, 388, 408]
    ycU = [205] * 12

    # Define xy coordinates of lower field character box corners
    xcL = [50, 73, 113, 136, 178, 198, 261, 282, 303, 365, 388, 408]
    ycL = [204] * 12

    xcU = [x + dx for x in xcU]
    xcL = [x + dx for x in xcL]

    return xcU, ycU, xcL, ycL


def setup_for_kiwi_vti_640_left():
    xcU, ycU, xcL, ycL = kiwi_640_boxes(0)

    # Turn box corners into full box coordinate tuples
    upper_field_boxes = [None] * len(xcL)
    lower_field_boxes = [None] * len(xcL)
    for i in range(len(xcL)):
        upper_field_boxes[i] = ((xcU[i], xcU[i] + 23, ycU[i], ycU[i] + 13))
        lower_field_boxes[i] = ((xcL[i], xcL[i] + 23, ycL[i], ycL[i] + 13))

    return upper_field_boxes, lower_field_boxes

def setup_for_kiwi_vti_640_right():
    xcU, ycU, xcL, ycL = kiwi_640_boxes(11)

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
    return timestamp, time, ts, scores, intcumscore


def format_iota_timestamp(ts):
    assert (len(ts) == 14), "len(ts) not equal to 14 in iota timestamp formatter"

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


def format_kiwi_timestamp(ts_str):
    assert (len(ts_str) == 12), "len(ts_str) not equal to 12 in kiwi timestamp formatter"
    ts = [0] * 12
    try:
        for i, value in enumerate(ts_str):
            if value == ' ':
                ts[i] = 0
            else:
                ts[i] = int(value)

        hh = 10 * ts[0] + ts[1]
        mm = 10 * ts[2] + ts[3]
        ss = 10 * ts[4] + ts[5]
        ff_left = 100 * ts[6] + 10 * ts[7] + ts[8]
        ff_right = 100 * ts[9] + 10 * ts[10] + ts[11]

        if ff_left > ff_right:
            delta = ff_left - ff_right
            if delta < 33:
                ff = ff_left
                time = 3600 * hh + 60 * mm + ss + ff / 1000
                return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[6]}{ts[7]}{ts[8]}]', time
            else:
                ff = ff_right
                time = 3600 * hh + 60 * mm + ss + ff / 1000
                return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[9]}{ts[10]}{ts[11]}]', time


        else:
            delta = ff_right - ff_left
            if delta < 33:
                ff = ff_right
                time = 3600 * hh + 60 * mm + ss + ff / 1000
                return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[9]}{ts[10]}{ts[11]}]', time
            else:
                ff = ff_left
                time = 3600 * hh + 60 * mm + ss + ff / 1000
                return f'[{ts[0]}{ts[1]}:{ts[2]}{ts[3]}:{ts[4]}{ts[5]}.{ts[6]}{ts[7]}{ts[8]}]', time

    except ValueError:
        return f'[00:00:00.000]', -1.0  # Indicate invalid timestamp by returning negative time


def format_boxsprite3_timestamp(ts):
    assert (len(ts) == 11), "len(ts) not equal to 11 in boxsprite timestamp formatter"
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


def locate_timestamp_vertically(img, fig, showplot=False):
    vert_profile = []
    for i in range(img.shape[0]):
        vert_profile.append(np.mean(img[i, :]))

    med_val = np.median(vert_profile)
    max_val = np.max(vert_profile)
    thresh = (max_val - med_val) / 2 + med_val

    top = None
    bottom = None

    for i in range(len(vert_profile)):
        if vert_profile[i] >= thresh:
            top = i
            break

    for i in range(len(vert_profile) - 1, 0, -1):
        if vert_profile[i] >= thresh:
            bottom = i
            break

    if showplot:
        plt.figure(fig, figsize=(10, 6))
        plt.plot(vert_profile, 'bo')
        plt.xlabel('y (row) coordinate within field')
        plt.ylabel('Pixel averages across row')
        plt.title('The red lines show where, on the y axis, the timestamp characters are located')
        plt.vlines([top, bottom], ymin=np.min(vert_profile), ymax=np.max(vert_profile), color='r')
        plt.grid()
        plt.show()

    return top, bottom
