import glob
from lix.lix import parse_lid_v2_data_file



if __name__ == '__main__':
    path = "/home/kaz/Downloads/2699991_APP_20260430_210129.lid"
    parse_lid_v2_data_file(path)

    # # run all these
    # ls = glob.glob('/home/kaz/nuc3_dl_bil_v5/*.lid')
    # for path in ls:
    #     parse_lid_v2_data_file(path)
