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
    delta_x = star2['x'] - star1['x']
    delta_y = star2['y'] - star1['y']

    if xflipped:
        delta_x = -delta_x
    if yflipped:
        delta_y = -delta_y

    return calc_theta(delta_x, delta_y)  # result is in degrees


def calc_theta(dx, dy):
    # This is the crucial routine for working trig problems.  It
    # returns the angle of the line from 0,0 to dx,dy no matter what
    # quadrant dx,dy may be in. The angle returned is in the range [0...360)
    # It is always positive and represents the ccw rotation from the axis
    # toward the positive y axis.
    d = sqrt(dx * dx + dy * dy)
    if d == 0:
        return 0.0
    a = arcsin(dy / d)

    # arcsin() will not return an angle in the range[0...360), so we
    # fix that up here before returning the angle.
    if dx >= 0 and dy >= 0:
        theta = a
    elif dx <= 0 and dy >= 0:
        theta = pi - a
    elif dx <= 0 and dy <= 0:
        theta = pi - a
    elif dx >= 0 and dy <= 0:
        theta = pi + pi + a
    else:
        return None
    return theta * 180.0 / pi  # give answer in degrees


def convert_ra_dec_angle_to_xy(angle, ref1, ref2, xflipped, yflipped):
    offset = angle_ra_dec(ref1, ref2) - angle_xy(ref1, ref2, xflipped, yflipped)
    return angle - offset


def solve_triangle(ref1, ref2, targ, plate_scale=None, xflipped=False, yflipped=False):

    if plate_scale is None:
        plate_scale = arcsec_distance(ref2, ref1) / pixel_distance(ref2, ref1)

    targ_theta = convert_ra_dec_angle_to_xy(
        angle_ra_dec(ref1, targ), ref1, ref2, xflipped, yflipped)

    d = arcsec_distance(ref1, targ) / plate_scale

    if xflipped:
        x_targ = -(d * cos_deg(targ_theta) - ref1['x'])
    else:
        x_targ = d * cos_deg(targ_theta) + ref1['x']
    if yflipped:
        y_targ = -(d * sin_deg(targ_theta) - ref1['y'])
    else:
        y_targ = d * sin_deg(targ_theta) + ref1['y']

    # x_targ = d * cos_deg(targ_theta) + ref1['x']
    # y_targ = d * sin_deg(targ_theta) + ref1['y']

    solution = {'ra': targ['ra'], 'dec': targ['dec'], 'x': x_targ, 'y': y_targ}

    return solution, plate_scale, targ_theta
