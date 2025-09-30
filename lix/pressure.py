import bisect
from functools import lru_cache

from numpy import array


DEFAULT_PRA = 3
DEFAULT_PRB = 0.0016
DEFAULT_PRC = 0
DEFAULT_PRD = 0




class Pressure:
    def __init__(self, calibration,
                 prc=DEFAULT_PRC, prd=DEFAULT_PRD):
        coefficients = calibration.coefficients
        pra = coefficients.get('PRA', DEFAULT_PRA)
        prb = coefficients.get('PRB', DEFAULT_PRB)
        self.pressure_slope = array([prb], dtype='float')
        self.pressure_offset = array([pra], dtype='float')

    def convert(self, raw_pressure):
        # raw_pressure: single value such as 64723
        # slope: [0.00163531]
        # offset: [2.84902716]
        # v: [74.94014981]
        v = ((self.pressure_slope * raw_pressure + self.pressure_offset)
             * 0.689475728)

        # print('prb ', self.pressure_slope)
        # print('rawp', raw_pressure)
        # print('pra ', self.pressure_offset)

        return v




class LixFileConverterP:
    def __init__(self, a, b):
        # the converter outputs decibars
        # 1 dbar = 1.45 psi
        self.coefficients = dict()
        self.coefficients['PRA'] = a
        self.coefficients['PRB'] = b
        self.cnv = Pressure(self)

    @lru_cache
    def convert(self, raw_pressure):
        return self.cnv.convert(raw_pressure)






def prf_compensate_pressure(rp, rt, prc, prd):
    # rp: raw Pressure ADC counts
    # rt: raw Temperature ADC counts
    # prc: temperature coefficient of pressure sensor = counts / °C
    # prd: reference temperature for pressure sensor = °C
    # cp: corrected Pressure ADC counts
    # ct: closest Temperature = °C

    # define lookup table, from -20°C to 50°C
    lut = [
       56765, 56316, 55850, 55369, 54872, 54359,
       53830, 53285, 52724, 52148, 51557, 50951,
       50331, 49697, 49048, 48387, 47714, 47028,
       46331, 45623, 44906, 44179, 43445, 42703,
       41954, 41199, 40440, 39676, 38909, 38140,
       37370, 36599, 35828, 35059, 34292, 33528,
       32768, 32012, 31261, 30517, 29780, 29049,
       28327, 27614, 26909, 26214, 25530, 24856,
       24192, 23541, 22900, 22272, 21655, 21051,
       20459, 19880, 19313, 18759, 18218, 17689,
       17174, 16670, 16180, 15702, 15236, 14782,
       14341, 13912, 13494, 13088, 12693
    ]

    # bisect needs a sorted list
    lut.reverse()

    # use vt to look up the closest temperature in degrees C, indexed T, i_t
    i_t = len(lut) - bisect.bisect(lut, rt)

    # use index of closest value (i_m) to get the T in °C, aka ct
    ct = i_t - 20

    # corrected pressure ADC counts
    cp = rp - (prc * (ct - prd))

    # _p('\n\nprfCompnsatePressure')
    # _p(f'rp {rp}')
    # _p(f'rt {rt}')
    # _p(f'prc {prc}')
    # _p(f'prd {prd}')
    # _p(f'i_t {i_t}')
    # _p(f'ct {ct}')
    # _p(f'cp {cp}')


    return cp
