import glob
from lix.lix import parse_lid_v2_data_file



if __name__ == '__main__':
    path = "/home/kaz/PycharmProjects/ddh/dl_files/f0-5e-cd-25-a0-3d/2699991_BIL_20260809_180420.lid"
    parse_lid_v2_data_file(path, create_csf=True)


    # convert MULTIPLE
    # ls = glob.glob('/home/kaz/nuc3_dl_bil_v5/*.lid')
    # for path in ls:
    #     parse_lid_v2_data_file(path)
