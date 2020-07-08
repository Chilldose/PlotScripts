'Verändert von GCD.py'

import logging
import holoviews as hv

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
        # hv.renderer('bokeh')

        # Convert the units to the desired ones
        for meas in self.measurements:
            unit = (
                self.config[self.analysisname].get(meas, {}).get("UnitConversion", None)
            )
            if unit:
                self.data = convert_to_EngUnits(self.data, meas, unit)

    def run(self):
        """Runs the script"""

        # Plot all Measurements
        self.basePlots = plot(
            self.data,
            self.config,
            self.measurements[1],
            self.analysisname,
            plot_only=[self.measurements[2]]
        )

        self.PlotDict["All"] = self.basePlots
        return self.PlotDict


