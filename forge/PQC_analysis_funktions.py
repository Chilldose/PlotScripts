import numpy as np
import holoviews as hv
import pandas as pd

from scipy.interpolate import interp1d
from scipy.stats import linregress

def linear_fit(x_Values,y_Values, full=False):
    '''returns array [y_values],slope, standard deviation of slope'''
    coef, cov_matrix = np.polyfit(x_Values, y_Values, 1, cov=True)
    line = coef[0] * x_Values + coef[1]
    variance = cov_matrix[0][0]
    std = np.sqrt(variance)
    if full:
        return line, coef[0], std
    else:
        return line

###############
def first_derivative(x, y):
    dy = np.zeros(len(y))
    dy[0] = (y[0] - y[1]) / (x[0] - x[1])
    dy[-1] = (y[-1] - y[-2]) / (x[-1] - x[-2])
    for i in range(1, len(y) - 1):
        dy[i] = (y[i + 1] - y[i - 1]) / (2 * (x[i] - x[i - 1]))
    return list(dy)

def interpolate(x, y, stepsize=0.01):
    '''smaller stepsize --> more points'''
    xnew = np.arange(x[0], x[-1], stepsize)
    f = interp1d(x, y, kind="cubic")
    ynew = f(xnew)
    return list(xnew), list(ynew)

def line_intersection(line1, line2):
    """Usage: line_intersection((A, B), (C, D))"""
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        print("Lines does not intersect...")
        return None

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y

def fit_analysis(x,y):
    '''uses fit method'''
    RR2 = 0
    fitR2 = 0
    for idx in range(5, len(x) - 5):
        # Right
        slope_right, intercept_right, r_right, _, std_err_right = linregress(x[idx:], y[idx:])
        r2_right = r_right * r_right

        # See if the r2 value has increased and store it
        if r2_right >= RR2:
             RR2 = r2_right
             RightEndPoints = ((x[idx], slope_right * x[idx] + intercept_right),
                               (x[len(x) - 1], slope_right * x[len(x) - 1] + intercept_right))
             Right_stats = [RightEndPoints, slope_right, intercept_right, r_right, _, std_err_right]

    startIndex = y.index(min(y))
    endIndex = len(x) - 1

    # Fit central region
    for idx in range(startIndex + 5, endIndex - 1):
        # Do central fit
        slope_fit, intercept_fit, r_fit, _, _ = linregress(x[startIndex: idx], y[startIndex: idx])
        r2_fit = r_fit * r_fit

        # See if the r2 value has increased and store it
        if r2_fit >= fitR2:
            fitR2 = r2_fit
            fitEndPoints = ((x[startIndex], slope_fit * x[startIndex] + intercept_fit),
                               (x[idx + 1], slope_fit * x[idx + 1] + intercept_fit))
            fit_stats = [fitEndPoints, slope_fit, intercept_fit, r_fit, _, _]

    # Add central slope, -3 on x value so the line doesnt end too soon, fit_line = [[start_x,start_x],[end_x,end_y]]
    xmax = x[endIndex]
    m_start = (x[startIndex - 3], fit_stats[1] * x[startIndex - 3] + fit_stats[2])
    m_end = (xmax + 0.2, fit_stats[1] * (xmax + 0.2) + fit_stats[2])

    # Add right slope
    xmax = x[len(y) - 1]
    r_start = (x[startIndex - 3], Right_stats[1] * x[startIndex - 3] + Right_stats[2])
    r_end = (xmax, Right_stats[1] * xmax + Right_stats[2])

    # intersect lines and store only the voltage
    flatband_voltage = line_intersection(fit_stats[0], Right_stats[0])[0]

    return [flatband_voltage, (m_start, m_end), (r_start, r_end)]

def plot_flatband_v(x, y, ana_type, **kwargs):
    '''
    **kwargs for customizing the plot, ana_type must ether be "fit" or "derivative"
    '''
    x, y = list(x), list(y)
    if ana_type == "fit":
        voltage, middle_line, right_line = fit_analysis(x, y)
    elif ana_type == "derivative":
        voltage = derivative_analysis(x, y)
    else:
        print("ana_type must either be 'derivative' or 'fit'")
        exit(1)
    curve = hv.Curve(zip(x, y), kdims="voltage_hvsrc", vdims="capactiance")

    text_str = "Flatband Voltage: " + str(voltage) + "\nAnalysis Type: " + ana_type
    text = hv.Text(max(x) * (3 / 4), max(y) * (3 / 4), text_str, fontsize=20)
    line = hv.VLine(voltage).opts(color="black", line_width=1.0)

    curve = curve * text * line
    if ana_type == "fit":
        mid = hv.Curve([*middle_line]).opts(color="red", line_width=1.5)
        right = hv.Curve([*right_line]).opts(color="blue", line_width=1.0)
        curve = curve * text * line * mid * right
    curve.opts(ylim=(min(y) - 3 * min(y) / 20, max(y) + max(y) / 10), **kwargs)
    return curve

def derivative_analysis(x, y):
    dy = first_derivative(x, y)
    df = pd.DataFrame({"x": x, "dy": dy})
    df = df.drop_duplicates(subset='x', keep='first')
    df = df[df.dy == df.dy.max()]
    return round(df['x'].iloc[0], 4)


