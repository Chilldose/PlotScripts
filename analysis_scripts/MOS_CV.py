import logging
import holoviews as hv
import numpy as np
import pandas as pd

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.tools import convert_to_EngUnits

from forge.utilities import line_intersection
from scipy.interpolate import interp1d
from scipy.stats import linregress


class MOS_CV:
    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False)
        self.config = configs
        self.basePlots = None
        self.analysisname = "MOS_CV"
        self.PlotDict = {"Name": self.analysisname}
        self.measurements = self.data["columns"]

        self.interpolation_der = self.config[self.analysisname]["Derivative"]["interpolate"]
        self.do_derivative = self.config[self.analysisname]["Derivative"]["do"]
        self.plot_der = self.config[self.analysisname]["Derivative"]["plot"]
        self.interpolation_fit = self.config[self.analysisname]["Fit"]["interpolate"]
        self.do_fit = self.config[self.analysisname]["Fit"]["do"]

        self.PlotDict["All"] = None


    def run(self):
        if self.do_derivative:
            self.derivative_analysis()
        if self.do_fit:
            self.fit_analysis()
        return self.PlotDict

    def derivative_analysis(self):
        # sollte ich überprüfen ob die werte aufsteigend sind ?
        # sollte ich # Normalize capacity by the Area and set to cm^2 machen ?
        for file in self.data["keys"]:
            '''deletes rows with duplicate in xAxis (prevents division by zero error)'''
            self.data[file]["data"] = self.data[file]["data"].drop_duplicates(subset=[self.measurements[1]],keep='first')

            '''derives and fills df with normal or interpolated data'''
            x, y = list(self.data[file]["data"][self.measurements[1]]), list(self.data[file]["data"][self.measurements[3]])
            if self.interpolation_der:
                x, y = self.interpolate(x, y)
            dy = self.first_derivative(x, y)
            self.fill_df(file, x, y, dy, "derivative")

            '''finds Flatband Voltage and plots everything'''
            self.find_max_der(file)
            self.plot_flatband(file, "derivative", self.interpolation_der)
            if self.plot_der:
                self.plot_derivative(file)

    @staticmethod
    def first_derivative(x, y):
        dy = np.zeros(len(y))
        dy[0] = (y[0] - y[1]) / (x[0] - x[1])
        dy[-1] = (y[-1] - y[-2]) / (x[-1] - x[-2])
        for i in range(1, len(y) - 1):
            dy[i] = (y[i + 1] - y[i - 1]) / (x[i] - x[i - 1])
        return list(dy)

    @staticmethod
    def interpolate(x, y):
        xnew = np.arange(x[0], x[-1], 0.01)
        f = interp1d(x, y, kind="cubic")
        ynew = f(xnew)
        return list(xnew), list(ynew)

    def fill_df(self, file, x, y, dy, name):
        '''creates key "derivative" in data[file], with a Dataframe as value, in wich interpolated or normal data + derivative is stored'''
        dic = {"x": x, "y": y, "dy": dy}
        df = pd.DataFrame(dic)
        self.data[file][name] = {"dataframe": df}

    def find_max_der(self, file):
        '''finds flatbandvoltage (with derivative) and puts it under '''
        df = self.data[file]["derivative"]["dataframe"]
        df = df[df.dy == df.dy.max()]
        self.data[file]["derivative"]["flatband"] = round(df['x'].iloc[0], 4)

    def plot_derivative(self, file):
        x, y = self.data[file]["derivative"]["dataframe"]['x'], self.data[file]["derivative"]["dataframe"]['dy']
        curve = hv.Curve(zip(x, y), kdims=self.measurements[1], vdims=self.measurements[3])
        curve.opts(**self.config["MOS_CV"].get("General", {}), title="derivative")
        self.PlotDict["All"] = self.PlotDict["All"] + curve

    def plot_flatband(self, file, ana_type, interpol):
        x, y = self.data[file][ana_type]["dataframe"]['x'], self.data[file][ana_type]["dataframe"]['y']
        curve = hv.Curve(zip(x, y), kdims=self.measurements[1], vdims=self.measurements[3])

        text_str = "Flatband Voltage: " + str(self.data[file][ana_type]["flatband"]) + "\nAnalysis Type: " + ana_type + "\nInterpolated: " + str(interpol)
        text = hv.Text(x.max() * (3 / 4), y.max() * (3 / 4), text_str, fontsize=20)
        line = hv.VLine(self.data[file][ana_type]["flatband"]).opts(color="black", line_width=1.0)

        curve = curve * text * line
        if ana_type == "fit":
            curve = curve * text * line * self.data[file]["fit"]["lines"][0] * self.data[file]["fit"]["lines"][1]
        curve.opts(**self.config["MOS_CV"].get("General", {}), ylim=(y.min() - 3*y.min()/20, y.max() + y.max()/10))

        if self.PlotDict["All"] is None:
            self.PlotDict["All"] = curve
        else:
            self.PlotDict["All"] = self.PlotDict["All"] + curve

    def fit_analysis(self):
        for file in self.data["keys"]:
            # deletes rows with duplicate in xAxis (prevents division by zero error)
            self.data[file]["data"] = self.data[file]["data"].drop_duplicates(subset=[self.measurements[1]], keep='first')

            x, y = list(self.data[file]["data"][self.measurements[1]]), list(self.data[file]["data"][self.measurements[3]])
            if self.interpolation_fit:
                x, y = self.interpolate(x, y)
            self.fill_df(file, x, y, np.zeros(len(y)), "fit")
            self.find_flatBand_voltage(file)
            self.plot_flatband(file, "fit", self.interpolation_fit)
            self.calculate_paramteres(file, "fit")

    def find_flatBand_voltage(self, file):
        RR2 = 0
        fitR2 = 0
        df = self.data[file]["fit"]["dataframe"]
        for idx in range(5, len(df) - 5):
            # Right
            slope_right, intercept_right, r_right, p_value, std_err_right = linregress(df["x"][idx:], df["y"][idx:])
            r2_right = r_right * r_right

            # See if the r2 value has increased and store it
            if r2_right >= RR2:
                RR2 = r2_right
                RightEndPoints = ((df["x"][idx], slope_right * df["x"][idx] + intercept_right), #speichert einfach die (x,y) werte des anfangs und end punkts
                                  (df["x"][len(df["x"]) - 1], slope_right * df["x"][len(df["x"]) - 1] + intercept_right))
                Right_stats = [RightEndPoints, slope_right, intercept_right, r_right, p_value, std_err_right]

        startIndex = df['y'].idxmin()
        endIndex = len(df) - 1

        # Fit central region
        for idx in range(startIndex + 5, endIndex - 1):
            # Do central fit
            slope_fit, intercept_fit, r_fit, p_valuefit, std_err_fit = linregress(df["x"][startIndex: idx], df["y"][startIndex: idx])
            r2_fit = r_fit * r_fit

            # See if the r2 value has increased and store it
            if r2_fit >= fitR2:
                fitR2 = r2_fit
                fitEndPoints = ((df["x"][startIndex], slope_fit * df["x"][startIndex] + intercept_fit),
                                (df["x"][idx + 1], slope_fit * df["x"][idx + 1] + intercept_fit))
                fit_stats = [fitEndPoints, slope_fit, intercept_fit, r_fit, p_valuefit, std_err_fit]

        # Add central slope, -3 on x value so the line doesnt end too soon, fit_line = [[start_x,start_x],[end_x,end_y]]
        xmax = df["x"][endIndex]
        fit_line = np.array([[df["x"][startIndex - 3], fit_stats[1] * df["x"][startIndex - 3] + fit_stats[2]],
                             [xmax + 0.2, fit_stats[1] * (xmax + 0.2) + fit_stats[2]]])
        fit_line = hv.Curve(fit_line).opts(color="red", line_width=1.5)
        self.data[file]["fit"]["lines"] = [fit_line, None]

        # Add right slope
        xmax = df["x"][len(df["y"]) - 1]
        right_line = np.array([[df["x"][startIndex - 3], Right_stats[1] * df["x"][startIndex - 3] + Right_stats[2]],
                               [xmax, Right_stats[1] * xmax + Right_stats[2]]])
        right_line = hv.Curve(right_line).opts(color="blue", line_width=1.0)
        self.data[file]["fit"]["lines"][1] = right_line

        # intersect lines and store only the voltage
        flatband_voltage = line_intersection(fit_stats[0], Right_stats[0])
        self.data[file]["fit"]["flatband"] = round(flatband_voltage[0], 4)

    def calculate_paramteres(self, file, ana_type):
        prameter = self.config["MOS_CV"]["parameter"]
        Cac = self.data[file][ana_type]["dataframe"]['y'].max()
        area = prameter["mos_area"]
        #oxide thickness e0/10 --> F/cm
        t = (prameter["epsilon0"]/10) * (prameter["epsilonR"]/10) * area / Cac

        Nox = Cac * (prameter["phi_m"] + self.data[file][ana_type]["flatband"]) / (area * prameter["q"])
