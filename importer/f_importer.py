"""An example how a custom importer works"""

from forge.tools import read_in_ASCII_measurement_files

#settings {'header_lines': 31, 'measurement_description': 32, 'units_line': 32, 'data_start': 33}
def myImporter(filepathes, **kwargs):
    """The importer gets one positional argument, which is a list with the passed filepathes.
    Then kwargs are passed, the ones stated in the config file! If you do not pass any, then there are no kwargs!"""
    ana_types = {"MOS": [], "FET": [], "Van_der_pauw": []}
    settings_M = {'header_lines': 13, 'measurement_description': 14, 'units_line': 14, 'data_start': 15}
    settings_F = {'header_lines': 31, 'measurement_description': 32, 'units_line': 32, 'data_start': 33}
    settings_V = {'header_lines': 11, 'measurement_description': 12, 'units_line': 12, 'data_start': 13}
    settings_list = [settings_M, settings_F, settings_V]
    for file in filepathes:
        with open(file, "r") as fp:
            for line in fp:
                if "MOS capacitor" in line:
                    ana_types["MOS"].append(file)
                    break
                elif "Van-der-Pauw" in line:
                    ana_types["Van_der_pauw"].append(file)
                    break
                elif "FET" in line:
                    ana_types["FET"].append(file)
                    break

    final_data, final_order = {}, []
    for i, key in enumerate(ana_types.keys()):
        all_data, load_order = read_in_ASCII_measurement_files(ana_types[key], settings_list[i])
        final_data.update(all_data)
        final_order += load_order

    return final_data