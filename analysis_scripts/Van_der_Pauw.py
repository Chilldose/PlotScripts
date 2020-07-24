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


class Van_der_Pauw:
    def __init__(self, data, configs):
        self.log = logging.getLogger(__name__)
        self.data = convert_to_df(data, abs=False)
        self.config = configs
        self.df = []
        self.basePlots = None
        self.analysisname = "Van_der_Pauw"
        self.PlotDict = {"Name": self.analysisname}
        self.measurements = self.data["columns"]

        self.sort_parameter = self.config["Van_der_Pauw"]["Bar_chart"]["CreateBarChart"]
        self.Substrate_Type = ["P-stop", "Polysilicon", "N+"]
        self.filename_df = pd.DataFrame(
            columns=["Filename", "Substrate Type", "_", "Batch", "Wafer No.", "_", "_", "HM location",
                     "Test structure", "_", "Sheet Resistance [Ohm/sq]", "Standard deviation"])
        self.PlotDict["All"] = None
        self.limits = {"P-stop": 25000, "Polysilicon": 3000, "N+": 50}
        self.files_to_fit = self.config["files_to_fit"]



    def list_to_dict(self, rlist):
        return dict(map(lambda s: map(str.strip, s.split(':', 1)), rlist))

    def run(self):
        '''turns all headers into dictionaries and fills file_name_df'''
        for file in self.data["keys"]:
            self.data[file]["header"] = self.list_to_dict(self.data[file]["header"])
            sheet_r, std = self.sheet_resistance(file)
            self.fill_filename_df(file, sheet_r, std)
        del self.filename_df["_"]
        self.counter = 0
        '''groups barcharts by Substrate Type and then by given parameter'''
        for substrate in self.filename_df.groupby("Substrate Type"):
            for group in substrate[1].groupby(self.sort_parameter):
                self.create_barchart(group[1], group[0], substrate[0])

        self.create_table()
        if self.files_to_fit:
            for file in self.files_to_fit:
                self.create_fit(file)
        return self.PlotDict

    def sheet_resistance(self, file, fit=False):
        '''calculates sheet resistance of given file, returns sheet_r and correspondinge standard deviation'''
        sheet_r = 0
        '''Linear regression'''
        x = self.data[file]["data"]["current"]
        y = self.data[file]["data"]["voltage_vsrc"]
        coef, cov_matrix = np.polyfit(x, y, 1, cov=True)
        line = coef[0] * x + coef[1]

        '''calculate sheet Resistance and standard deviation'''
        sheet_r += coef[0] * np.pi / np.log(2)
        variance = cov_matrix[0][0]
        std = np.sqrt(variance) * np.pi / np.log(2)
        plt.plot(x, y, 'yo', x, line, '--k')
        #plt.show()
        if fit:
            return sheet_r, std, line
        return sheet_r, std

    def create_barchart(self, group_df, group_name, substrate):
        '''Calculates mean if all labels are equivalent'''
        labels = ["Batch", "Wafer No.", "HM location", "Test structure"]
        labels.remove(self.sort_parameter)
        innermost_groups = group_df.groupby(labels)
        r_mean = innermost_groups["Sheet Resistance [Ohm/sq]"].mean() ##calculate the error that happens here

        '''creates chart data and BarChart Object'''
        keys = ["/".join(key) for key in innermost_groups.groups.keys()]
        chart_data = [(label, resistance) for label, resistance in zip(keys, r_mean)]
        labels = "/".join(labels)
        chart = hv.Bars(chart_data, hv.Dimension(labels), "Sheet Resistance [Ohm/sq]")

        '''calculates std_mean with error propagation'''
        std_mean_l = []
        for group in innermost_groups: #each group corresponds to a bar
            std_mean2 = 0
            for i in group[1]["Standard deviation"]:
                std_mean2 += (i/len(group[1]["Standard deviation"]))**2
                self.counter += 1 #
                print(self.counter) #
            print("----------------")
            std_mean2 = np.sqrt(std_mean2)
            std_mean_l.append(std_mean2) #
            #std_mean_l.append((std_mean2, "len(group):",len(group[1]["Standard deviation"]))) #
        std_mean = innermost_groups["Standard deviation"].mean() #


        '''calculate error of r_mean '''
        r_mean_error = []
        for index, group in enumerate(innermost_groups):
            diff_from_mean = 0
            group_mean = r_mean[index]
            for i in group[1]["Sheet Resistance [Ohm/sq]"]:
                if len(group[1]["Sheet Resistance [Ohm/sq]"]) > 1:
                    diff_from_mean += ((i - group_mean)**2/(len(group[1]["Sheet Resistance [Ohm/sq]"])-1))
            diff_from_mean = np.sqrt(diff_from_mean)
            r_mean_error.append(diff_from_mean)

        error = [max(i, j) for i, j in zip(r_mean_error, std_mean_l)]

        print(std_mean)  #
        print("######################")
        print(std_mean_l)
        print(r_mean_error)

        '''creates errorbars and configures the plot'''
        error_bars = hv.ErrorBars((keys, r_mean, error))
        error_bars.opts(line_width=5)
        chart = chart * error_bars
        #chart = error_bars

        chart.opts(title=substrate + " " + group_name, **self.config["Van_der_Pauw"].get("General", {}),
                   ylim=(0, self.limits[substrate]), xrotation=45)

        if self.PlotDict["All"] is None:
            self.PlotDict["All"] = chart
        else:
            self.PlotDict["All"] = self.PlotDict["All"] + chart

    def fill_filename_df(self, file, sheet_r, std):
        '''fills the data frame so data can later be grouped by keyword ("Vendor", "Batch" etc.)'''
        value_list = [key for key in self.data[file]["header"]["sample_name"].split("_")]
        value_list2 = [key for key in self.data[file]["header"]["sample_type"].split("_")]
        for subs in self.Substrate_Type:
            if subs in self.data[file]["header"]["measurement_name"]:
                value_list = [file, subs] + value_list + value_list2

        dic = dict(zip(self.filename_df.keys(), value_list))
        dic["Sheet Resistance [Ohm/sq]"] = sheet_r
        dic["Standard deviation"] = std
        self.filename_df = self.filename_df.append(dic, ignore_index=True)

    def create_table(self):
        table = hv.Table(self.filename_df)
        table.opts(width=1300, height=800)
        self.PlotDict["All"] = self.PlotDict["All"] + table

    def create_fit(self, filename):
        sheet_r, std, fit = self.sheet_resistance(filename, fit=True)
        x = self.data[filename]["data"]["current"]
        y = self.data[filename]["data"]["voltage_vsrc"]
        scatter = hv.Scatter((x, y), kdims=self.measurements[1], vdims=self.measurements[2])
        scatter.opts(color='green')
        curve = scatter * hv.Curve((x, fit))
        curve.opts(**self.config["Van_der_Pauw"].get("General", {}), xrotation=45, title="Index: " + str(self.filename_df.loc[self.filename_df['Filename'] == filename].index[0]))
        self.PlotDict["All"] = self.PlotDict["All"] + curve



'''
self.basePlots = plot(
            self.data,
            self.config,
            self.measurements[1],
            self.analysisname,
            plot_only=[self.measurements[2]],
            keys=self.measure_names[measurement_key]
        )
        self.PlotDict["All"] = self.PlotDict["All"] + self.basePlots
        self.table_df = self.table_df.append({"Name": file, "Sheet Resistance [Ohm/sq]": sheet_r, "Standard deviation": std},
                             ignore_index=True)
        
        
        
        table = hv.Table(self.table_df, label="Mean Values")
        table.opts(width=1300, height=800)
        self.PlotDict["All"] = self.PlotDict["All"] + table
        
    
    def create_barchart(self):
        chart_data = [(name,resistance) for name, resistance in zip(self.table_df["Name"],self.table_df["Sheet Resistance [Ohm/sq]"])]

        error_chart = hv.ErrorBars(self.table_df)
        chart = hv.Bars(chart_data, hv.Dimension("Measurement Names"),"Resistance")
        chart = error_chart * chart
        chart.opts(height=400)
        self.PlotDict["All"] = self.PlotDict["All"] + chart
        # chart_data = self.table_df.melt(id_vars=["Name"], value_vars=["Sheet Resistance [Ohm/sq]", "Standard deviation"])
        #chart = hv.Bars(chart_data, kdims=['Name', 'variable'], vdims=['value']) 
                
                
                
        std_mean = group_df.groupby(self.BarChart_XAxis)["Sheet Resistance [Ohm/sq]"].mean()
# error_data = [(label, std) for label, std in
        # zip(self.filename_df[self.BarChart_XAxis], self.filename_df["Standard deviation"])
        # error_chart = hv.ErrorBars(error_data)
        # chart = error_chart * chart        
                
                
                
                
                
        
                
                '''
