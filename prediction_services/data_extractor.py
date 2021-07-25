from uuid import uuid4
from shapely.geometry import shape, Point, Polygon, MultiPolygon
import fiona
import os
import csv
import rtree
from params_reader import get_param


def remove_subdirectory(shape_path):
    for file in os.listdir(shape_path):
        os.remove(file)
    os.rmdir(shape_path)


def create_subdirectory(location):
    guid = uuid4()
    while os.path.isdir(location + str(guid)):
        guid = uuid4()
    os.mkdir(location + str(guid))
    return str(guid)


def get_shape_name(shape_path):
    for file in os.listdir(shape_path):
        if file.endswith(".shp"):
            return file.split(".")[0]


def extract_csv_findings(csv_file_name):
    x = []

    with open(csv_file_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader, None)  # skip header
        for row in csv_reader:
            x.append(row)
            for i in range(0, len(row)):
                x[len(x) - 1][i] = float(x[len(x) - 1][i])
    return x


def extract(shape_folder):
    shape_path = get_param("main_directory") + shape_folder + "\\"
    shape_name = get_shape_name(shape_path)

    map_shape = fiona.open(shape_path + shape_name + ".shp")
    numeric_attributes = []
    for item in map_shape.schema["properties"]:
        if "str" not in map_shape.schema["properties"][item]:
            numeric_attributes.append(item)

    with open(shape_path + 'attributes.txt', 'w') as f:
        f.write(','.join(numeric_attributes))

    dataset = dict()
    idx = rtree.index.Index()

    for item in map_shape:
        x = []
        valid_coordinates = True
        for att in numeric_attributes:
            if item["properties"][att] <= -9999:
                valid_coordinates = False
                break
            x.append(item["properties"][att])
        if valid_coordinates:
            idx.insert(int(item["id"]), Polygon(shape(item["geometry"])).bounds)
            dataset[int(item["id"])] = x

    all_findings = []
    with open(shape_path + get_param("default_csv_name")) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader, None)  # skip header
        for row in csv_reader:
            all_findings.append(row)

    locations = {}
    for finding in all_findings:
        if finding[0] not in locations.keys():
            locations[finding[0]] = []
        locations[finding[0]].append([float(item) for item in finding[1:]])

    for plant in locations.keys():
        points = []
        for result in locations[plant]:
            points.append(Point(result[0], result[1]))

        x_train = []
        for dot in points:
            intersect_ids = idx.intersection(dot.bounds)
            for i in intersect_ids:
                area = shape(map_shape[i]["geometry"])
                if dot.within(area):
                    x_train.append(dataset[i])

        with open(shape_path + 'data_' + shape_name + '_' + str(plant) + '.csv', mode='w', newline='') as dataFile:
            csv_writer = csv.writer(dataFile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(numeric_attributes)
            for row in x_train:
                csv_writer.writerow(row)

    map_shape.close()


def get_map(shape_path):
    shape_name = get_shape_name(shape_path)
    map_shape = fiona.open(shape_path + shape_name + ".shp")
    map_x = []
    coordinates = []

    with open(shape_path + '\\attributes.txt', 'r') as f:
        numeric_attributes = f.readline().replace('\n', '').split(',')

    for item in map_shape:
        x = []
        for att in numeric_attributes:
            x.append(item["properties"][att])
        map_x.append(x)
        coordinates.append(item["geometry"])

    map_shape.close()
    return MultiPolygon([shape(item) for item in coordinates]), map_x


def create_result_map(shape_path, result_path, species, all_y):
    shape_name = get_shape_name(shape_path)
    map_shape = fiona.open(shape_path + shape_name + ".shp")
    new_schema = map_shape.schema
    for plant in species:
        new_schema["properties"]["prob_" + plant] = 'float'

    with fiona.open(result_path + shape_name + "_prob.shp", 'w',
                    crs=map_shape.crs, schema=new_schema,
                    driver=map_shape.driver) as result_shapefile:
        for i in range(0, len(map_shape)):
            item = map_shape[i]
            for plant in species:
                item['properties']["prob_" + plant] = all_y[plant][i]
            result_shapefile.write({'properties': item['properties'], 'geometry': item['geometry']})

    map_shape.close()
