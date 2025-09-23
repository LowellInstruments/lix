import os
import subprocess as sp
import sys
from ascii85 import ascii85_to_num
from temperature import LixFileConverterT



# file size, sample length, min. mask length, chunk size
MML = 1
CS = 256
MASK_TIME_EXTENDED = 0x40
g_glt = ''



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



def _parse_macro_header(bb):
    global g_glt
    g_glt = ''
    g_glt = bb[:3].decode()
    print('glt', g_glt)



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

    temp = ''
    temp_as_celsius = ''
    pres = ''
    ac_x = ''
    ac_y = ''
    ac_z = ''

    if g_glt in ('TDO', 'CTD'):
        bb_t = bb[0:2]
        temp = _decode_sensor_measurement('T', bb_t)
        temp_as_celsius = '{:06.3f}'.format(float(lct.convert(temp)))
        bb_p = bb[2:4]
        pres = _decode_sensor_measurement('P', bb_p)
        bb_a = bb[4:10]
        ac_x = _decode_sensor_measurement('A', bb_a[0:2])
        ac_y = _decode_sensor_measurement('A', bb_a[2:4])
        ac_z = _decode_sensor_measurement('A', bb_a[4:6])

    if g_glt == 'TDO':
        fo.write(f'{t},{temp},{temp_as_celsius},{pres},{ac_x},{ac_y},{ac_z}\n')

    if g_glt == 'CTD':
        bb_c = bb[10:]
        c0 = int.from_bytes(bb_c[0:2], byteorder='big', signed=False)
        c1 = int.from_bytes(bb_c[2:4], byteorder='big', signed=False)
        c2 = int.from_bytes(bb_c[4:6], byteorder='big', signed=False)
        c3 = int.from_bytes(bb_c[6:8], byteorder='big', signed=False)
        fo.write(f'{t},{temp},{temp_as_celsius},{pres},{ac_x},{ac_y},{ac_z},{c0},{c1},{c2},{c3}\n')




def parse_file_lid_v5(p):
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
    _parse_macro_header(bb_macro_header)


    # get variables depending on logger type
    sl = 0
    csv_column_titles = ''
    suffix = ''
    if g_glt == 'TDO':
        sl = 10
        csv_column_titles = f't,temp,temp(c),pres,Ax,Ay,Az\n'
        suffix = 'TDO'
    elif g_glt == 'CTD':
        sl = 18
        csv_column_titles = f't,temp,temp(c),pres,Ax,Ay,Az,c0,c1,c2,c3\n'
        suffix = 'CTD'
    elif g_glt.startswith('DO'):
        csv_column_titles = f'dotheseones'
        sl = 6
        suffix = 'DissolvedOxygen'
    else:
        sys.exit(1)


    # start CSV file
    path_csv = p.replace('.lid', f'_{suffix}.csv')
    print(path_csv)
    print(f'output csv file = {path_csv}')
    f_csv = open(path_csv, 'w')
    f_csv.write(csv_column_titles)


    # separate rest of file
    bb = bb[CS:-n_pad]
    data_size = len(bb)


    # parse it measurement by measurement
    while 1:
        if i + sl + MML > data_size:
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


        # mask first
        n_mask, t = _parse_mask(bb[i:i+2])

        if (i % CS) + n_mask + sl > CS:
            n_pre = CS - (i % CS)
            n_post = sl + n_mask - n_pre
            j = i + n_pre + 8
            s = bb[i:i+n_pre] + bb[j:j+n_post]
            print(f'{i} - {i+n_pre} ({n_pre}) + {j}:{j+n_post} ({n_post})')
            j += n_post
            need_parse_mini = 1
        else:
            j = i + n_mask + sl
            s = bb[i:j]
            print(f'{i} - {j} ({j - i})')
            need_parse_mini = 0


        # sample second
        _parse_sample(s[n_mask:], t, f_csv)
        i = j

    f_csv.close()


    # useful during development, copy converted file here
    c = f'cp {path_csv} .'
    sp.run(c, shell=True)




if __name__ == '__main__':
    path = '/home/kaz/Downloads/2508703_LAB_20250820_161106.lid'
    parse_file_lid_v5(path)
    
