import datetime
import os
from lix.ascii85 import ascii85_to_num as a2n
from lix.pressure import LixFileConverterP, prf_compensate_pressure
from lix.temperature import LixFileConverterT
from dateutil.tz import tzlocal, tzutc
import gsw



# file size, sample length, min. mask length, chunk size
MML = 1
CS = 256
MASK_TIME_EXTENDED = 0x40
g_glt = ''
LEN_LIX_FILE_CC_AREA = 5 * 33
LEN_LIX_FILE_CF_AREA = 5 * 9
LEN_LIX_FILE_CONTEXT = 64
MORE_COLUMNS = 1
g_epoch = 0
g_last_ct = 0



def _p(s):
    print(s)




def _time_mah_str_to_seconds(s: str) -> int:
    # s: '231103190012' embedded in macro_header
    dt = datetime.datetime.strptime(s, "%y%m%d%H%M%S")
    # set dt as UTC since objects are 'naive' by default
    dt_utc = dt.replace(tzinfo=tzutc())
    dt_utc.astimezone(tzlocal())
    rv = dt_utc.timestamp()
    # rv: 1699038012
    return int(rv)



def _time_bytes_to_str(b: bytes) -> str:
    # b: b'\x24\x01\x31\x12\x34\x56'
    s = ''
    for v in b:
        high = (v & 0xf0) >> 4
        low = (v & 0x0f) >> 0
        s += f'{high}{low}'
    # s: '240131123456'
    return s



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
    v = int.from_bytes(x, "big")
    if 'A' in s:
        # v: 65515
        v = _c2_to_decimal(v)
    return v



def decode_accelerometer_measurement(x):
    return _decode_sensor_measurement('A', x)



def _parse_macro_header(bb):
    global g_glt
    g_glt = ''
    g_glt = bb[:3].decode()
    file_type = bb[:3]
    file_version = bb[3]
    timestamp = bb[4:10]
    battery = bb[10:12]
    hdr_idx = bb[12]
    # HSA macro-header must match firmware hsa.h
    i_mah = 13
    cc_area = bb[i_mah: i_mah + LEN_LIX_FILE_CC_AREA]
    # context
    i = CS - LEN_LIX_FILE_CONTEXT
    gfv = bb[i:i + 4]
    i += 4
    rvn = bb[i]
    i += 1
    pfm = bb[i]
    i += 1
    spn = bb[i]
    i += 1
    spt = bb[i:i + 5].decode()
    i += 5
    dro = bb[i:i + 5].decode()
    i += 5
    dru = bb[i:i + 5].decode()
    i += 5
    # DRF does not take 5 characters but 2
    drf = bb[i:i + 2].decode()
    i += 2
    dso = bb[i:i + 5].decode()
    i += 5
    dsu = bb[i:i + 5].decode()

    # display all this info
    _p(f"\n\tMACRO header \t|  logger type {file_type.decode()}")
    _p(f"\tfile version \t|  {file_version}")
    timestamp_str = _time_bytes_to_str(timestamp)

    _p(f"\tdatetime is   \t|  {timestamp_str}")
    bat = int.from_bytes(battery, "big")
    _p("\tbattery level \t|  0x{:04x} = {} mV".format(bat, bat))
    _p(f"\theader index \t|  {hdr_idx}")
    if b"00004" != cc_area[:5]:
        return
    _p("\tcc_area \t\t|  detected")
    pad = '\t\t\t\t\t   '
    _p(f'{pad}tmr = {a2n(cc_area[10:15].decode())}')
    _p(f'{pad}tma = {a2n(cc_area[15:20].decode())}')
    _p(f'{pad}tmb = {a2n(cc_area[20:25].decode())}')
    _p(f'{pad}tmc = {a2n(cc_area[25:30].decode())}')
    _p(f'{pad}tmd = {a2n(cc_area[30:35].decode())}')
    _p(f'{pad}pra = {a2n(cc_area[125:130].decode())}')
    _p(f'{pad}prb = {a2n(cc_area[130:135].decode())}')
    # PRC / PRD are not ascii85, also, we need them
    prc = float(cc_area[135:140].decode()) / 100
    prd = float(cc_area[140:145].decode()) / 100
    _p(f'{pad}prc = {prc}')
    _p(f'{pad}prd = {prd}')
    _p(f'{pad}dco = {a2n(cc_area[145:150].decode())}')
    _p(f'{pad}nco = {a2n(cc_area[150:155].decode())}')
    _p(f'{pad}dhu = {a2n(cc_area[155:160].decode())}')
    _p(f'{pad}dcd = {a2n(cc_area[160:165].decode())}')
    _p("\n\tcontext \t\t|  detected")
    _p(f'{pad}gfv = {gfv}')
    _p(f'{pad}rvn = {rvn}')
    _p(f'{pad}pfm = {pfm}')
    _p(f'{pad}spn = {spn}')
    _p(f'{pad}spt = {spt}')
    _p(f'{pad}dro = {dro}')
    _p(f'{pad}dru = {dru}')
    _p(f'{pad}drf = {drf}')
    _p(f'{pad}dso = {dso}')
    _p(f'{pad}dsu = {dsu}')

    # get first time ever
    global g_epoch
    g_epoch = _time_mah_str_to_seconds(timestamp_str)
    print('g_epoch', g_epoch)




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


def _parse_sample(bb, t, fo, lct, lcp, prc, prd):

    # rt:  temperature raw ADC counts
    # rp:  pressure raw ADC counts
    # rpd: pressure raw decibar using PRA, PRB
    # cp:  compensated pressure ADC counts
    # cpd: compensated pressure decibar using PRA, PRB
    # vt:  temperature as Celsius
    rt = ''
    rp = ''
    cp = ''
    ac_x = ''
    ac_y = ''
    ac_z = ''
    vt = ''
    rpd = ''
    cpd = ''
    vax = ''
    vay = ''
    vaz = ''


    # all of them
    global g_last_ct
    g_last_ct += t
    t_str = datetime.datetime.utcfromtimestamp(g_epoch + g_last_ct).isoformat()
    t_str = t_str + '.000Z'


    if g_glt in ('TDO', 'CTD'):
        bb_t = bb[0:2]
        rt = _decode_sensor_measurement('T', bb_t)
        vt = '{:06.3f}'.format(float(lct.convert(rt)))
        bb_p = bb[2:4]
        rp = _decode_sensor_measurement('P', bb_p)
        cp = prf_compensate_pressure(rp, rt, prc, prd)
        rpd = '{:06.3f}'.format(lcp.convert(rp)[0])
        cpd = '{:06.3f}'.format(lcp.convert(cp)[0])
        bb_a = bb[4:10]
        vax = _decode_sensor_measurement('A', bb_a[0:2])
        vay = _decode_sensor_measurement('A', bb_a[2:4])
        vaz = _decode_sensor_measurement('A', bb_a[4:6])


    if g_glt == 'TDO':
        if MORE_COLUMNS:
            # et: elapsed time
            et = t
            # ct: cumulative time
            s = f'{t_str},{et},{g_last_ct},{rt},{rp},{vt},{rpd},{cp},' \
                f'{cpd},{vax},{vay},{vaz}\n'
            fo.write(s)
        else:
            fo.write(f'{t_str},{vt},{rpd},{vax},{vay},{vaz}\n')


    if g_glt == 'CTD':
        bb_c = bb[10:]
        c2c1 = int.from_bytes(bb_c[0:2], byteorder='big', signed=False)
        c1c2 = int.from_bytes(bb_c[2:4], byteorder='big', signed=False)
        v1v2 = int.from_bytes(bb_c[4:6], byteorder='big', signed=False)
        v2v1 = int.from_bytes(bb_c[6:8], byteorder='big', signed=False)
        if v1v2 + v2v1 == 0:
            s = f'warning, v1v2 + v2v1 == 0, skipping this sample'
            print(f"\033[93m{s}\033[0m")
            return

        ratio_cv = '{:.4f}'.format((c2c1 + c1c2) / (v1v2 + v2v1))


        # calculate psu
        hardcoded_cell_constant = 2.0
        conductivity = float(ratio_cv) * hardcoded_cell_constant
        psu = gsw.conversions.SP_from_C(conductivity, float(vt), float(cpd))
        print(f"Salinity: {psu} psu")

        if MORE_COLUMNS:
            # et: elapsed time
            et = t
            # ct: cumulative time
            s = f'{t_str},{et},{g_last_ct},{rt},{rp},{vt},{rpd},{cp},' \
                f'{cpd},{vax},{vay},{vaz},{c2c1},{c1c2},{v1v2},{v2v1},{ratio_cv},{psu}\n'
        else:
            s = f'{t_str},{vt},{rpd},{vax},{vay},{vaz},{c2c1},{c1c2},{v1v2},{v2v1},{ratio_cv},{psu}\n'
        fo.write(s)




class ExceptionLixFileConversion(Exception):
    pass




def parse_lid_v2_data_file(p):

    # read ALL bytes in LID data file
    with open(p, 'rb') as f:
        bb = f.read()
    bn = os.path.basename(p)
    raw_file_size = len(bb)


    # know real size of LID file by subtracting last padding
    n_pad = bb[-253]
    # file_size = raw_file_size - 256 + (256 - n_pad)
    file_size = raw_file_size - n_pad
    print(f'{bn}, raw size {raw_file_size}, real size {file_size}')


    # separate macro_header
    bb_macro_header = bb[:CS]
    _parse_macro_header(bb_macro_header)


    # get variables depending on logger type
    if g_glt == 'TDO':
        sl = 10
        csv_column_titles = 'ISO 8601 Time,' \
               'Temperature (C),Pressure (dbar),Ax,Ay,Az\n'
        if MORE_COLUMNS:
            csv_column_titles = 'ISO 8601 Time,elapsed time (s),agg. time(s),' \
                   'raw ADC Temp,raw ADC Pressure,' \
                   'Temperature (C),Pressure (dbar),Compensated ADC Pressure,' \
                   'Compensated Pressure (dbar),Ax,Ay,Az\n'
        suffix = 'TDO'
    elif g_glt == 'CTD':
        sl = 18
        csv_column_titles = 'ISO 8601 Time,' \
               'Temperature (C),Pressure (dbar),Ax,Ay,Az,c2c1,c1c2,v1v2,v2v1,ratio_cv,Salinity (psu)\n'
        if MORE_COLUMNS:
            csv_column_titles = 'ISO 8601 Time,elapsed time (s),agg. time(s),' \
                   'raw ADC Temp,raw ADC Pressure,' \
                   'Temperature (C),Pressure (dbar),Compensated ADC Pressure,' \
                   'Compensated Pressure (dbar),Ax,Ay,Az,c2c1,c1c2,v1v2,v2v1,ratio_cv,Salinity (psu)\n'
        suffix = 'CTD'
    elif g_glt.startswith('DO'):
        csv_column_titles = f'dotheseones'
        sl = 6
        suffix = 'DissolvedOxygen'
    else:
        e = 'lix: parse_lid_v2_data_file, cannot get logger type'
        raise ExceptionLixFileConversion(e)


    # start CSV file with its column titles
    path_csv = p.replace('.lid', f'_{suffix}.csv')
    print(f'output csv file = {path_csv}')
    f_csv = open(path_csv, 'w')
    f_csv.write(csv_column_titles)


    # grab the cc area in the macro_header
    lct = 0
    lcp = 0
    prc = 0
    prd = 0
    if g_glt in ('TDO', 'CTD'):
        cc_area = bb[13: 13 + LEN_LIX_FILE_CC_AREA]
        tmr = a2n(cc_area[10:15].decode())
        tma = a2n(cc_area[15:20].decode())
        tmb = a2n(cc_area[20:25].decode())
        tmc = a2n(cc_area[25:30].decode())
        tmd = a2n(cc_area[30:35].decode())
        pra = a2n(cc_area[125:130].decode())
        prb = a2n(cc_area[130:135].decode())
        prc = float(cc_area[135:140].decode()) / 100
        prd = float(cc_area[140:145].decode()) / 100
        lct = LixFileConverterT(tma, tmb, tmc, tmd, tmr)
        lcp = LixFileConverterP(pra, prb)


    # separate DATA section from rest of file
    bb = bb[CS:-n_pad]
    data_size = len(bb)


    # initialize variables to parse data section
    global g_last_ct
    g_last_ct = 0
    i = 0
    need_parse_mini = 1


    # parse data measurement by measurement
    nm = 0
    while 1:
        if i + sl + MML > data_size:
            # real or padded
            # print(f'end at {i}, data_size {data_size}, remain {data_size - i}')
            break

        if i % CS == 0:
            need_parse_mini = 1
            i += 8
            # print(f'{i - 8} - {i} (8)')

        if need_parse_mini:
            m = (i // CS) * CS
            _parse_mini_header(bb[m:m+8])


        # parse mask first
        n_mask, t = _parse_mask(bb[i:i+2])

        if t == 0 and nm > 0:
            # useful to detect badly finished files when memory errors
            print(f'finished parsing file: {nm} samples')
            break

        if (i % CS) + n_mask + sl > CS:
            n_pre = CS - (i % CS)
            n_post = sl + n_mask - n_pre
            j = i + n_pre + 8
            s = bb[i:i+n_pre] + bb[j:j+n_post]
            # print(f'{i} - {i+n_pre} ({n_pre}) + {j}:{j+n_post} ({n_post})')
            j += n_post
            need_parse_mini = 1
        else:
            j = i + n_mask + sl
            s = bb[i:j]
            # print(f'{i} - {j} ({j - i})')
            need_parse_mini = 0


        # parse sample after mask
        _parse_sample(s[n_mask:], t, f_csv, lct, lcp, prc, prd)
        i = j

        # number of measurements
        nm += 1

    f_csv.close()


    # useful during development, copy converted file here
    # c = f'cp {path_csv} .'
    # sp.run(c, shell=True)


    # success
    return 0