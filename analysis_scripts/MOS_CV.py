
import logging
import holoviews as hv
import numpy as np
import pandas as pd

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.tools import twiny, relabelPlot
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.tools import plot
from forge.specialPlots import dospecialPlots
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

        self.interpolation = self.config[self.analysisname]["Derivative"]["interpolate"]
        self.do_derivative = self.config[self.analysisname]["Derivative"]["do"]
        self.do_fit = self.config[self.analysisname]["Fit"]["do"]
        self.table_df = pd.DataFrame(columns=['Filename', 'Flatband'])


        self.basePlots = plot(
            self.data,
            self.config,
            self.measurements[1],
            self.analysisname,
            plot_only=[self.measurements[3]]
        )
        self.PlotDict["All"] = self.basePlots

    def run(self):
        if self.do_derivative:
            self.derivative_analysis()
        if self.do_fit:
            self.fit_analysis()
        return self.PlotDict

    def derivative_analysis(self):
        #sollte ich überprüfen ob die werte aufsteigend sind ?
        #sollte ich # Normalize capacity by the Area and set to cm^2 machen ?
        for file in self.data["keys"]:
            '''deletes rows with duplicate in xAxis (prevents division by zero error)'''
            self.data[file]["data"] = self.data[file]["data"].drop_duplicates(subset=[self.measurements[1]], keep='first')
            '''derives and fills df with normal or interpolated data'''
            x, y = list(self.data[file]["data"][self.measurements[1]]), list(self.data[file]["data"][self.measurements[3]])
            if self.interpolation:
                x, y = self.interpolate(x, y)
            dy = self.first_derivative(x, y)
            self.fill_df(file, x, y, dy, "derivative")
            self.find_max_der(file)
            self.plot_derivative(file)


    def first_derivative(self, x, y):
        dy = np.zeros(len(y))
        dy[0] = (y[0]-y[1])/(x[0]-x[1])
        dy[-1] = (y[-1] - y[-2]) / (x[-1] - x[-2])
        for i in range(1, len(y)-1):
            dy[i] = (y[i+1]-y[i-1])/(x[i]-x[i-1])
        return list(dy)

    def interpolate(self, x, y):
        xnew = np.arange(x[0], x[-1], 0.001)
        f = interp1d(x, y, kind="cubic")
        ynew = f(xnew)
        return list(xnew), list(ynew)

    def fill_df(self,file, x, y, dy, name):
        '''creates key "derivative" in data[file], with a Dataframe as value, in wich interpolated or normal data + derivative is stored'''
        dic = {"x": x, "y": y, "dy": dy}
        df = pd.DataFrame(dic)
        self.data[file][name] = {"dataframe" : df}

    def find_max_der(self, file):
        '''finds flatbandvoltage (with derivative) and puts it under '''
        df = self.data[file]["derivative"]["dataframe"]
        df = df[df.dy == df.dy.max()]
        self.data[file]["derivative"]["flatband"] = round(df['x'].iloc[0], 6)

    def plot_derivative(self, file):
        x, y = self.data[file]["derivative"]["dataframe"]['x'], self.data[file]["derivative"]["dataframe"]['dy']
        curve = hv.Curve(zip(x, y))
        curve.opts(**self.config["MOS_CV"].get("General", {}))
        text = hv.Text(x.max()*(3/4), y.max()*(3/4), "Flatband Voltage: " + str(self.data[file]["derivative"]["flatband"]),fontsize=20)
        curve = curve * text
        self.PlotDict["All"] = self.PlotDict["All"] + curve

    def fit_analysis(self):
        for file in self.data["keys"]:
            '''deletes rows with duplicate in xAxis (prevents division by zero error)'''
            self.data[file]["data"] = self.data[file]["data"].drop_duplicates(subset=[self.measurements[1]], keep='first')

            x, y = list(self.data[file]["data"][self.measurements[1]]), list(
                self.data[file]["data"][self.measurements[3]])
            if self.interpolation:
                x, y = self.interpolate(x, y)
            self.fill_df(file, x, y, np.zeros(len(y)), "fit")











