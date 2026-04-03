def scale_battery(mv_vd, glt) -> int:
    # mv_vd: millivolts from voltage divider
    v = mv_vd
    if glt == 'TDO':
        v /= (12 / 22)
    if glt == 'CTD':
        v /= (10 / 22)
    if glt.startswith('DO'):
        v /= (8 / 20)

    # these are real mV
    return int(v)
