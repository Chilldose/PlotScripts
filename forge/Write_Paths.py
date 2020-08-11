import argparse, yaml, os

def absoluteFilePaths(directory):
    for dirpath,_,filenames in os.walk(directory):
        return [os.path.join(dirpath, f) for f in filenames]

def write_to_yaml(config_path, data_directory):
    data_paths = absoluteFilePaths(data_directory)
    print(data_paths)
    with open(config_path, 'w') as file:
        dic = yaml.load(file, Loader=yaml.FullLoader)
        dic['Files'] = data_paths
        yaml.dump(dic)

if __name__=="__main__":
    write_to_yaml(r"C:\Users\flohu\OneDrive\Documents\GitHub\PlotScripts\CONFIGS\PQC_analyses.yml",r"C:\Users\flohu\OneDrive\Documents\Uni\Bachelor\BachelorArbeit\Daten\Van-der-Pauw_Probecard")
