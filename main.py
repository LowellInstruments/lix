from lix.ascii85 import ascii85_to_num, num_to_ascii85
from lix.lix import parse_lid_v2_data_file


if __name__ == '__main__':
    path = "/home/kaz/Downloads/dl_bil_v5/3000004_BIL_20251201_185757.lid"
    parse_lid_v2_data_file(path)


