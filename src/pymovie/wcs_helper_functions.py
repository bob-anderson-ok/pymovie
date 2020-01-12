# These routines ares used during the manual WCS calculation

# For theory: http://spiff.rit.edu/classes/phys373/lectures/astrom/astrom.html

from numpy import cos, sin, pi, sqrt, arcsin

# The parameters to these helper functions are always dictionaries
# with the structure as shown below.

# ra and dec MUST be in degrees
# ref1 = {'ra':98.48722469, 'dec':22.33929379, 'x':170,   'y':185 }
# ref2 = {'ra':97.99874741, 'dec':22.18617554, 'x':260,   'y':393 }
# targ = {'ra':98.13950330, 'dec':22.46275600, 'x':None,  'y':None }


def cos_deg(theta_degrees):
    theta_radians = theta_degrees * pi / 180.0
    return cos(theta_radians)


def sin_deg(theta_degrees):
    theta_radians = theta_degrees * pi / 180.0
    return sin(theta_radians)


def arcsec_distance(star1, star2):
    # Returns distance between star1 and star2 in arcsec
    avg_dec = (star2['dec'] + star1['dec']) / 2.0
    delta_ra = (star2['ra'] - star1['ra']) * cos_deg(avg_dec) * 3600.0
    delta_dec = (star2['dec'] - star1['dec']) * 3600.0
    return sqrt(delta_ra ** 2 + delta_dec ** 2)


def delta_ra_arcsec(star1, star2):
    # Thanks to Michael Richmond's little simple astrometry paper
    # for pointing out the need to scale ra based on dec
    avg_dec = (star2['dec'] + star1['dec']) / 2.0  # avg_dec in degrees

    # Convert answer to arcsec as well as scale based on average dec
    delta_ra = (star2['ra'] - star1['ra']) * cos_deg(avg_dec) * 3600.0
    return delta_ra


def delta_dec_arcsec(star1, star2):
    return (star2['dec'] - star1['dec']) * 3600.0


def pixel_distance(star1, star2):
    dx = star2['x'] - star1['x']
    dy = star2['y'] - star1['y']

    return sqrt(dx * dx + dy * dy)


def angle_ra_dec(star1, star2):
    ra_delta_arcsec = delta_ra_arcsec(star1, star2)
    dec_delta_arcsec = delta_dec_arcsec(star1, star2)
    return calc_theta(ra_delta_arcsec, dec_delta_arcsec)


def angle_xy(star1, star2, xflipped, yflipped):
    delta_x_local = star2['x'] - star1['x']
    delta_y_local = star2['y'] - star1['y']

    if xflipped:
        delta_x_local = -delta_x_local
    if yflipped:
        delta_y_local = -delta_y_local

    return calc_theta(delta_x_local, delta_y_local)  # result is in degrees


def calc_theta(dx, dy):
    # This is the crucial routine for working trig problems.  It
    # returns the angle of the line from 0,0 to dx,dy no matter what
    # quadrant dx,dy may be in. The angle returned is in the range [0...360)
    # It is always positive and represents the ccw rotation from the x axis
    # toward the positive y axis.

    d = sqrt(dx * dx + dy * dy)
    if d == 0:
        return 0.0
    a = arcsin(dy / d)

    # arcsin() will not return an angle in the range[0...360), so we
    # fix that up here before returning the angle.
    if dx >= 0 and dy >= 0:
        theta = a
    elif dx <= 0 <= dy:
        theta = pi - a
    elif dx <= 0 and dy <= 0:
        theta = pi - a
    elif dx >= 0 >= dy:
        theta = pi + pi + a
    else:
        return None
    return theta * 180.0 / pi  # give answer in degrees


def convert_ra_dec_angle_to_xy(angle, ref1, ref2, xflipped, yflipped):
    offset = angle_ra_dec(ref1, ref2) - angle_xy(ref1, ref2, xflipped, yflipped)
    return angle - offset, offset


# def solve_triangle(ref1, ref2, targ, pixel_aspect_ratio, plate_scale=None, xflipped=False, yflipped=False):
#     # rescale references to account for non-square pixels
#     if pixel_aspect_ratio < 1.0:
#         ref1['x'] = pixel_aspect_ratio * ref1['x']
#         ref2['x'] = pixel_aspect_ratio * ref2['x']
#     elif pixel_aspect_ratio > 1.0:
#         ref1['y'] = ref1['y'] / pixel_aspect_ratio
#         ref2['y'] = ref2['y'] / pixel_aspect_ratio
#
#     if plate_scale is None:
#         plate_scale = arcsec_distance(ref2, ref1) / pixel_distance(ref2, ref1)
#
#     targ_theta, ra_dec_x_y_rotation = convert_ra_dec_angle_to_xy(
#         angle_ra_dec(ref1, targ), ref1, ref2, xflipped, yflipped)
#
#     d = arcsec_distance(ref1, targ) / plate_scale
#
#     ref1x = ref1['x']
#     ref1y = ref1['y']
#
#     if xflipped:
#         x_targ = -(d * cos_deg(targ_theta) - ref1x)
#     else:
#         x_targ = d * cos_deg(targ_theta) + ref1x
#
#     if yflipped:
#         y_targ = -(d * sin_deg(targ_theta) - ref1y)
#     else:
#         y_targ = d * sin_deg(targ_theta) + ref1y
#
#     # x_targ = d * cos_deg(targ_theta) + ref1['x']
#     # y_targ = d * sin_deg(targ_theta) + ref1['y']
#
#     # Compensate for pixel aspect ratio.
#     if pixel_aspect_ratio < 1.0:
#         x_targ= x_targ / pixel_aspect_ratio
#     elif pixel_aspect_ratio > 1.0:
#         y_targ = y_targ * pixel_aspect_ratio
#
#     solution = {'ra': targ['ra'], 'dec': targ['dec'], 'x': x_targ, 'y': y_targ}
#
#     return solution, plate_scale, targ_theta, ra_dec_x_y_rotation

def delta_x(star1, star2):
    return star2['x'] - star1['x']

def delta_y(star1, star2):
    return star2['y'] - star1['y']

def error(theta, a1, a2, b1, b2):
    c1 = cos(theta) * a1 - sin(theta) * a2
    c2 = sin(theta) * a1 + cos(theta) * a2
    return (c1 - b1) * (c1 - b1) + (c2 - b2) * (c2 - b2)

def hunt(theta0, dtheta, a1, a2, b1, b2):
    err0 = error(theta0, a1, a2, b1, b2)
    err1 = error(theta0 + dtheta, a1, a2, b1, b2)
    err2 = error(theta0 - dtheta, a1, a2, b1, b2)
    if err2 < err1:
        dtheta = -dtheta
    err = err0
    theta = theta0
    while True:
        theta += dtheta
        cerr = error(theta, a1, a2, b1, b2)
        if cerr > err:
            break
        err = cerr
    return theta

def align_angle(a1, a2, b1, b2):
    """Returns counter-clockwise angle to rotate (a1, a2) into (b1, b2)"""
    t = 0; dt = 0.1
    for i in range(8):
        t = hunt(t, dt, a1, a2, b1, b2)
        dt = dt / 10.0
    return t, t * 180.0 / pi

def rotate(theta, a1, a2):
    b1 = cos(theta) * a1 - sin(theta) * a2
    b2 = sin(theta) * a1 + cos(theta) * a2
    return b1, b2

def new_solve_triangle(ref1, ref2, targ, pixel_aspect_ratio, plate_scale=None):
    # rescale ref1 and ref2 to account for non-square pixels
    if pixel_aspect_ratio < 1.0:
        ref1['x'] = pixel_aspect_ratio * ref1['x']
        ref2['x'] = pixel_aspect_ratio * ref2['x']
    elif pixel_aspect_ratio > 1.0:
        ref1['y'] = ref1['y'] / pixel_aspect_ratio
        ref2['y'] = ref2['y'] / pixel_aspect_ratio

    if plate_scale is None:
        plate_scale = arcsec_distance(ref2, ref1) / pixel_distance(ref2, ref1)

    # Use ref1 and ref2 to determine rotation angle between RA/Dec and x/y systems
    a1 = delta_ra_arcsec(ref1, ref2)  / plate_scale
    a2 = delta_dec_arcsec(ref1, ref2) / plate_scale
    b1 = delta_x(ref1, ref2)
    b2 = delta_y(ref1, ref2)
    rot_radians, rot_degrees = align_angle(a1, a2, b1, b2)

    # Get pixel coords of target from RA/Dec coords of target relative to ref1

    # First: calculate pixel deltas in RA/Dec coords
    delta_t1 = delta_ra_arcsec(ref1, targ)  / plate_scale
    delta_t2 = delta_dec_arcsec(ref1, targ) / plate_scale

    # Then rotate the deltas into alignment with x/y coords
    delta_xtarg, delta_ytarg = rotate(rot_radians, delta_t1, delta_t2)

    # Apply pixel aspect ratio corrections for final report and add ref1 x/y values
    if pixel_aspect_ratio < 1.0:
        x_targ = (delta_xtarg + ref1['x']) / pixel_aspect_ratio
        y_targ = delta_ytarg + ref1['y']
    else:
        x_targ = delta_xtarg + ref1['x']
        y_targ = (delta_ytarg + ref1['y']) * pixel_aspect_ratio

    solution = {'ra': targ['ra'], 'dec': targ['dec'], 'x': x_targ, 'y': y_targ}

    return solution, plate_scale, rot_degrees
