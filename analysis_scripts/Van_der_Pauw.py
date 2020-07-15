'Verändert von GCD.py   measurement_name muss in Zeile 3 stehen (wenn man von 0 aus zählt)'

import logging
import holoviews as hv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from forge.tools import customize_plot, holoplot, convert_to_df, config_layout
from forge.tools import twiny, relabelPlot
from forge.tools import plot_all_measurements, convert_to_EngUnits
from forge.tools import plot
from forge.specialPlots import dospecialPlots
from forge.utilities import line_intersection

from copy import deepcopy

from forge.tools import plainPlot


class Van_der_Pauw:
    def __init__(self, data, configs):

        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False)
        self.config = configs
        self.df = []
        self.basePlots = None
        self.fit_plot = None
        self.analysisname = "Van_der_Pauw"
        self.PlotDict = {"Name": self.analysisname}
        self.measurements = self.data["columns"]

        self.table_df = pd.DataFrame(columns= ["Name", "Sheet Resistance [Ohm/m^2]", "Standard deviation"])
        self.measure_names = {"P-stop" : [] , "Polysilicon" : [],"N+" :[]}
        self.PlotDict["All"] = self.basePlots = plot(
            self.data,
            self.config,
            self.measurements[1],
            self.analysisname,
            plot_only=[self.measurements[2]],
        )

    def run(self):
        '''sorts the files after their mesaure_names by insertinge them into the dicitonary'''
        for file_name in self.data["keys"]:
            for name in self.measure_names.keys():
                if name in self.data[file_name]["header"][3]: #(könnte auch eine schleife einbauen das es egal ist wo measurement_name steht, dauert dann halt noch ein bissi länger + wird vllt unübersichtilicher
                    self.measure_names[name].append(file_name)

        for name in self.measure_names.keys():
            self.sheet_resistance(name)
        self.create_barchart()

        table = hv.Table(self.table_df, label="Mean Values")
        table.opts(width=1300, height=800)
        self.PlotDict["All"] = self.PlotDict["All"] + table

        return self.PlotDict

    def sheet_resistance(self,measurement_key):
        '''calculates sheet resistance of given list of files (in practice list of P-stop or Polysilicon or N+)'''
        sheet_r = 0
        std = 0
        for file in self.measure_names[measurement_key]:
            '''Linear regression'''
            x = self.data[file]["data"]["current"]
            y = self.data[file]["data"]["voltage_vsrc"]
            coef, cov_matrix = np.polyfit(x, y, 1, cov=True )
            line = coef[0]*x + coef[1]
            #plt.plot(x, y, 'yo', x, line, '--k')

            fit_data = deepcopy(self.data)
            fit_data[file]["data"]["voltage_vsrc"] = line

            '''calculate sheet Resistance and standard deviation'''
            sheet_r += coef[0]*np.pi/np.log(2)
            variance = cov_matrix[0][0]
            std += np.sqrt(variance)*np.pi/np.log(2)

        '''calculates mean value'''
        sheet_r /= len(self.measure_names[measurement_key])
        std /= len(self.measure_names[measurement_key])

        self.table_df = self.table_df.append({"Name": measurement_key, "Sheet Resistance [Ohm/m^2]": sheet_r, "Standard deviation": std},
                             ignore_index=True)
        self.basePlots = plot(
            self.data,
            self.config,
            self.measurements[1],
            self.analysisname,
            plot_only=[self.measurements[2]],
            keys=self.measure_names[measurement_key]
        )
        self.PlotDict["All"] = self.PlotDict["All"] + self.basePlots

    def create_barchart(self):
        chart_data = [(name,resistance) for name, resistance in zip(self.table_df["Name"],self.table_df["Sheet Resistance [Ohm/m^2]"])]
        error_chart = hv.ErrorBars(self.table_df)
        chart = hv.Bars(chart_data, hv.Dimension("Measurement Names"),"Resistance")
        chart = error_chart * chart
        chart.opts(height=400)
        self.PlotDict["All"] = self.PlotDict["All"] + chart


        # chart_data = self.table_df.melt(id_vars=["Name"], value_vars=["Sheet Resistance [Ohm/m^2]", "Standard deviation"])
        #chart = hv.Bars(chart_data, kdims=['Name', 'variable'], vdims=['value'])
