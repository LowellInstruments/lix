import glob
from lix.lix import parse_lid_v2_data_file



if __name__ == '__main__':
    # bad one
    path = "/home/kaz/Downloads/2603701_BIL_20260401_182623.lid"

    # good one
    # path = "/home/kaz/Downloads/2603713_BIL_20260401_143006.lid"
    # parse_lid_v2_data_file(path)

    # test these
    ls = glob.glob('/home/kaz/nuc3_dl_bil_v5/keep/*.lid')
    for path in ls:
        parse_lid_v2_data_file(path)
