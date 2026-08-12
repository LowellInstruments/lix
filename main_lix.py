import glob
from lix.lix import parse_lid_v2_data_file



if __name__ == '__main__':
    path = "/home/kaz/Downloads/dl_bil_v5/3000012_BIL_20260812_143556.lid"
    parse_lid_v2_data_file(path)


    # convert MULTIPLE
    # ls = glob.glob('/home/kaz/nuc3_dl_bil_v5/*.lid')
    # for path in ls:
    #     parse_lid_v2_data_file(path)
