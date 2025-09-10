import os
import subprocess as sp
from functools import lru_cache

from mat.ascii85 import ascii85_to_num
from mat.temperature import Temperature



# file size, sample length, min. mask length, chunk size
SL = 18
MML = 1
CS = 256
MASK_TIME_EXTENDED = 0x40



class LixFileConverterT:
    def __init__(self, a, b, c, d, r):
        self.coefficients = dict()
        self.coefficients['TMA'] = a
        self.coefficients['TMB'] = b
        self.coefficients['TMC'] = c
        self.coefficients['TMD'] = d
        self.coefficients['TMR'] = r
        self.cnv = Temperature(self)

    @lru_cache
    def convert(self, raw_temperature):
        # _p(f'\nLixFileConverterT coefficients {self.coefficients}')
        # _p(f'raw T {raw_temperature} converted T {self.cnv.convert(raw_temperature)}')
        return self.cnv.convert(raw_temperature)



# todo: do this non-default
DEF_TMR = "7VZ<2"
DEF_TMA = "3g?gQ"
DEF_TMB = "3HFKd"
DEF_TMC = "1S#M`"
DEF_TMD = "1ps%'"
tmr = ascii85_to_num(DEF_TMR)
tma = ascii85_to_num(DEF_TMA)
tmb = ascii85_to_num(DEF_TMB)
tmc = ascii85_to_num(DEF_TMC)
tmd = ascii85_to_num(DEF_TMD)
lct = LixFileConverterT(tma, tmb, tmc, tmd, tmr)



def _lix_raw_sensor_measurement_to_int(x):
    return int.from_bytes(x, "big")



def _decode_sensor_measurement(s, x):
    # s: 'T', 'P', 'Ax'...
    # x: b'\xff\xeb'
    def _c2_to_decimal(n):
        if not (n & 0x8000):
            # detect positive numbers
            return n
        c2 = (-1) * (65535 + 1 - n)
        return c2

    # big endian to int
    v = _lix_raw_sensor_measurement_to_int(x)
    if 'A' in s:
        # v: 65515
        v = _c2_to_decimal(v)
    return v





def _parse_mini_header(bb):
    pass



def _parse_mask(bb):

    # marks if 1 or 2 bytes of time
    f_te = bb[0] & MASK_TIME_EXTENDED

    # lm: len_mask
    if f_te == 0:
        t = 0x3F & bb[0]
        lm = 1
        # print('len. mask = 1 -> ts = 0x{:02x} = {}'.format(t, t))
    else:
        t = ((0x3F & bb[0]) << 8) + bb[1]
        lm = 2
        # print('len. mask = 2 -> te = 0x{:04x} = {}'.format(t, t))

    return lm, t



def _parse_sample(bb, t, fo):
    # CTD bytes 2P, 2T, 6A, 8C
    bb_t = bb[0:2]
    temp = _decode_sensor_measurement('T', bb_t)
    temp_as_celsius = '{:06.3f}'.format(float(lct.convert(temp)))
    bb_p = bb[2:4]
    pres = _decode_sensor_measurement('P', bb_p)
    bb_a = bb[4:10]
    ac_x = _decode_sensor_measurement('A', bb_a[0:2])
    ac_y = _decode_sensor_measurement('A', bb_a[2:4])
    ac_z = _decode_sensor_measurement('A', bb_a[4:6])
    bb_c = bb[10:]
    c0 = int.from_bytes(bb_c[0:2], byteorder='big', signed=False)
    c1 = int.from_bytes(bb_c[2:4], byteorder='big', signed=False)
    c2 = int.from_bytes(bb_c[4:6], byteorder='big', signed=False)
    c3 = int.from_bytes(bb_c[6:8], byteorder='big', signed=False)
    print('c2 = 0x{:02x}'.format(c1))
    fo.write(f'{t},{temp},{temp_as_celsius},{pres},{ac_x},{ac_y},{ac_z},{c0},{c1},{c2},{c3}\n')





def parse_file_lidxv5(p):
    i = 0
    need_parse_mini = 1


    # read the whole data file
    with open(p, 'rb') as f:
        bb = f.read()
    bn = os.path.basename(p)
    raw_file_size = len(bb)


    # know real size of file by subtracting last padding
    n_pad = bb[-253]
    file_size = raw_file_size - 256 + (256 - n_pad)
    print(f'{bn}, raw size {raw_file_size}, real size {file_size}')


    # separate macro_header
    bb_macro_header = bb[:CS]
    bb = bb[CS:-n_pad]
    data_size = len(bb)

    path_csv = p.replace('.lid', '_CTD.csv')
    print(path_csv)

    print(f'output csv file = {path_csv}')
    f_csv = open(path_csv, 'w')
    f_csv.write(f't,temp,temp(c),pres,Ax,Ay,Az,c0,c1,c2,c3\n')


    # parse it measurement by measurement
    while 1:
        if i + SL + MML > data_size:
            # real or padded
            print(f'end at {i}, data_size {data_size}, remain {data_size - i}')
            break

        if i % CS == 0:
            need_parse_mini = 1
            i += 8
            print(f'{i - 8} - {i} (8)')

        if need_parse_mini:
            m = (i // CS) * CS
            _parse_mini_header(bb[m:m+8])

        n_mask, t = _parse_mask(bb[i:i+1])

        if (i % CS) + n_mask + SL > CS:
            n_pre = CS - (i % CS)
            n_post = SL + n_mask - n_pre
            j = i + n_pre + 8
            s = bb[i:i+n_pre] + bb[j:j+n_post]
            print(f'{i} - {i+n_pre} ({n_pre}) + {j}:{j+n_post} ({n_post})')
            j += n_post
            need_parse_mini = 1
        else:
            j = i + n_mask + SL
            s = bb[i:j]
            print(f'{i} - {j} ({j - i})')
            need_parse_mini = 0

        _parse_sample(s[n_mask:], t, f_csv)
        i = j

    f_csv.close()

    # useful during development
    c = f'cp {path_csv} .'
    sp.run(c, shell=True)




if __name__ == '__main__':
    path = '/home/kaz/Downloads/dl_bil_v2/F0-5E-CD-25-92-EA/2222222_TST_20250910_160915.lid'
    parse_file_lidxv5(path)
    
