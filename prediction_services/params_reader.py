import json

json_file = "params.json"


def get_param(name):
    f = open(json_file)
    param = json.load(f)[name]
    f.close()
    return param
