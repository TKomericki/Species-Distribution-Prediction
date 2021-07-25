import pickle
from os import listdir, remove, path
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from descartes import PolygonPatch
from zipfile import ZipFile, ZIP_DEFLATED
from params_reader import get_param
import data_extractor
import machine_learning


def create_subdirectory(location):
    return data_extractor.create_subdirectory(location)


def remove_subdirectory(location):
    data_extractor.remove_subdirectory(location)


def extract_data(shape_folder):
    location = get_param("main_directory") + shape_folder + "\\"
    for file in listdir(location):
        if file.endswith(".zip"):
            zip_location = location + file
    with ZipFile(zip_location, 'r') as zip_file:
        zip_file.extractall(location)
    remove(zip_location)
    data_extractor.extract(shape_folder)


def generate_models(shape_folder):
    shape_path = get_param("main_directory") + shape_folder + "\\"
    shape_name = data_extractor.get_shape_name(shape_path)

    for file in listdir(shape_path):
        if file.endswith(".csv") and not file == get_param("default_csv_name"):
            class_id = file.split('_')[2].split(".")[0]
            train_x = data_extractor.extract_csv_findings(shape_path + file)

            scaler, pca, ocsvm = machine_learning.generate_model(train_x)

            save_file = shape_path + shape_name + "_" + class_id
            pickle.dump(scaler, open(save_file + "_scaler.pkl", 'wb'))
            pickle.dump(pca, open(save_file + "_pca.pkl", 'wb'))
            pickle.dump(ocsvm, open(save_file + "_model.pkl", 'wb'))


def get_species(shape_folder):
    shape_path = get_param("main_directory") + shape_folder + "\\"
    species = []
    print(shape_path)
    if path.isdir(shape_path):
        for file in listdir(shape_path):
            if file.endswith(".csv") and not file == get_param("default_csv_name"):
                species.append(file.split('_')[2].split(".")[0])
        return ','.join(species)
    return "null"


def generate_predictions(shape_folder, species, color, result_folder):
    shape_path = get_param("main_directory") + shape_folder + "\\"
    shape_name = data_extractor.get_shape_name(shape_path)
    new_shape_path = get_param("result_directory") + result_folder + "\\"

    complete_map, x = data_extractor.get_map(shape_path)
    all_y = {}

    plt.ioff()

    for plant in species:
        save_file = shape_path + shape_name + '_' + plant

        ocsvm = pickle.load(open(save_file + "_model.pkl", 'rb'))
        scaler = pickle.load(open(save_file + "_scaler.pkl", 'rb'))
        pca = pickle.load(open(save_file + "_pca.pkl", 'rb'))

        y = machine_learning.predict(x, scaler, pca, ocsvm)
        all_y[plant] = y

        cm = plt.get_cmap(color)
        fig = plt.figure()
        ax = fig.add_subplot(111)
        minx, miny, maxx, maxy = complete_map.bounds
        w, h = maxx - minx, maxy - miny
        ax.set_xlim(minx - 0.01 * w, maxx + 0.01 * w)
        ax.set_ylim(miny - 0.01 * h, maxy + 0.01 * h)
        ax.set_aspect(1)
        patches = []

        for i in range(0, len(complete_map)):
            colour = cm(y[i])
            patches.append(PolygonPatch(complete_map[i], fc=colour, ec='#555555', alpha=1., zorder=1, linewidth=0))
        picture = PatchCollection(patches, cmap=cm, match_original=True)
        ax.add_collection(picture)
        ax.set_xticks([])
        ax.set_yticks([])
        plt.title(shape_folder + " - " + plant)
        plt.colorbar(picture)
        plt.subplots_adjust(left=0, right=1, bottom=0.01, top=0.97)
        # plt.get_current_fig_manager().window.state('zoomed')
        plt.savefig(new_shape_path + shape_name + '_' + plant + ".png", bbox_inches='tight')

    data_extractor.create_result_map(shape_path, new_shape_path, species, all_y)
    zip_file_name = shape_name + ".zip"

    files_to_zip = [file for file in listdir(new_shape_path)]
    with ZipFile(new_shape_path + zip_file_name, 'w', ZIP_DEFLATED) as zip_file:
        for file in files_to_zip:
            zip_file.write(new_shape_path + file, file)
            remove(new_shape_path + file)
    return result_folder + "\\" + zip_file_name
