import os


# file size, sample length, min. mask length, chunk size
SL = 18
MML = 1
CS = 256
MASK_TIME_EXTENDED = 0x40





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
    bb_c = bb[10:]
    c0 = int.from_bytes(bb_c[0:2], byteorder='big', signed=False)
    c1 = int.from_bytes(bb_c[2:4], byteorder='big', signed=False)
    c2 = int.from_bytes(bb_c[4:6], byteorder='big', signed=False)
    c3 = int.from_bytes(bb_c[6:8], byteorder='big', signed=False)
    print('c2 = 0x{:02x}'.format(c1))
    fo.write(f'{t},{c0},{c1},{c2},{c3}\n')





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
    # useful during development
    path_csv = f'{os.getcwd()}/{os.path.basename(path_csv)}'
    print(path_csv)

    print(f'output csv file = {path_csv}')
    f_csv = open(path_csv, 'w')
    f_csv.write('time,c0,c1,c2,c3\n')


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



if __name__ == '__main__':
    path = '/home/kaz/Downloads/dl_bil_v2/F0-5E-CD-25-92-EA/2222222_TST_20250910_152135.lid'
    parse_file_lidxv5(path)
    
