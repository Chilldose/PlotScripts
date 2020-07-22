import numpy as np
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


def sheet_resistance(slope, SD=None):
    R = slope * np.pi / np.log(2)
    if SD != None:
        return R, SD * np.pi / np.log(2)
    else:
        return R



if __name__ =='__main__':
    mean = 4034.2061792760605 + 4137.872616746932
    mean /= 2
    std = 569.7 * np.log(2) /np.pi
    print(sheet_resistance(mean, SD=std))
