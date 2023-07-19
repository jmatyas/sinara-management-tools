# SPDX-FileCopyrightText: 2023 Jakub Matyas for Warsaw University of Technology
#
# SPDX-License-Identifier: MIT


from adafruit_bus_device import i2c_device
from busio import I2C
from typing import List

class Si5324:
    class FrequencySettings:
        n31 = None
        n32 = None
        n1_hs = None
        nc1_ls = None
        nc2_ls = None
        n2_hs = None
        n2_ls = None
        bwsel = None

        def map(self, settings):
            if settings.nc1_ls != 0 and (settings.nc1_ls % 2) == 1:
                raise ValueError("NC1_LS must be 0 or even")
            if settings.nc1_ls > (1 << 20):
                raise ValueError("NC1_LS is too high")
            if settings.nc2_ls != 0 and (settings.nc2_ls % 2) == 1:
                raise ValueError("NC2_LS must be 0 or even")
            if settings.nc2_ls > (1 << 20):
                raise ValueError("NC2_LS is too high")
            if (settings.n2_ls % 2) == 1:
                raise ValueError("N2_LS must be even")
            if settings.n2_ls > (1 << 20):
                raise ValueError("N2_LS is too high")
            if settings.n31 > (1 << 19):
                raise ValueError("N31 is too high")
            if settings.n32 > (1 << 19):
                raise ValueError("N32 is too high")
            if not 4 <= settings.n1_hs <= 11:
                raise ValueError("N1_HS is invalid")
            if not 4 <= settings.n2_hs <= 11:
                raise ValueError("N2_HS is invalid")
            self.n1_hs = settings.n1_hs - 4
            self.nc1_ls = settings.nc1_ls - 1
            self.nc2_ls = settings.nc2_ls - 1
            self.n2_hs = settings.n2_hs - 4
            self.n2_ls = settings.n2_ls - 1
            self.n31 = settings.n31 - 1
            self.n32 = settings.n32 - 1
            self.bwsel = settings.bwsel
            return self

    def __init__(self, bus, addr=0x68):
        self.bus = bus
        self.addr = addr

    def write(self, addr, data):
        self.bus.write_many(self.addr, addr, [data])

    def read(self, addr):
        return self.bus.read_many(self.addr, addr, 1)[0]

    def ident(self):
        return self.bus.read_many(self.addr, 134, 2)

    def has_xtal(self):
        return self.read(129) & 0x01 == 0  # LOSX_INT=0

    def has_clkin1(self):
        return self.read(129) & 0x02 == 0  # LOS1_INT=0

    def has_clkin2(self):
        return self.read(129) & 0x04 == 0  # LOS2_INT=0

    def locked(self):
        return self.read(130) & 0x01 == 0  # LOL_INT=0

    def wait_lock(self, timeout=20):
        t = time.monotonic()
        while not self.locked():
            if time.monotonic() - t > timeout:
                raise ValueError("lock timeout")
        logger.info("locking took %g s", time.monotonic() - t)

    def select_input(self, inp):
        self.write(3, self.read(3) & 0x3f | (inp << 6))
        self.wait_lock()

    def setup(self, s):
        s = self.FrequencySettings().map(s)
        assert self.ident() == bytes([0x01, 0x82])

        # try:
        #     self.write(136, 0x80)  # RST_REG
        # except I2cNackError:
        #     pass
        # time.sleep(.01)
        self.write(136, 0x00)
        time.sleep(.01)

        self.write(0,   self.read(0) | 0x40)  # FREE_RUN=1
        # self.write(0,   self.read(0) & ~0x40)  # FREE_RUN=0
        self.write(2,   (self.read(2) & 0x0f) | (s.bwsel << 4))
        self.write(21,  self.read(21) & 0xfe)  # CKSEL_PIN=0
        self.write(22,  self.read(22) & 0xfd)  # LOL_POL=0
        self.write(19,  self.read(19) & 0xf7)  # LOCKT=0
        self.write(3,   (self.read(3) & 0x3f) | (0b01 << 6) | 0x10)  # CKSEL_REG=b01 SQ_ICAL=1
        self.write(4,   (self.read(4) & 0x3f) | (0b00 << 6))  # AUTOSEL_REG=b00
        self.write(6,   (self.read(6) & 0xc0) | 0b101101)  # SFOUT2_REG=b101 SFOUT1_REG=b101
        self.write(25,  (s.n1_hs  << 5 ))
        self.write(31,  (s.nc1_ls >> 16))
        self.write(32,  (s.nc1_ls >> 8 ))
        self.write(33,  (s.nc1_ls)      )
        self.write(34,  (s.nc2_ls >> 16))
        self.write(35,  (s.nc2_ls >> 8 ))
        self.write(36,  (s.nc2_ls)      )
        self.write(40,  (s.n2_hs  << 5 ) | (s.n2_ls  >> 16))
        self.write(41,  (s.n2_ls  >> 8 ))
        self.write(42,  (s.n2_ls)       )
        self.write(43,  (s.n31    >> 16))
        self.write(44,  (s.n31    >> 8) )
        self.write(45,  (s.n31)         )
        self.write(46,  (s.n32    >> 16))
        self.write(47,  (s.n32    >> 8) )
        self.write(48,  (s.n32)         )
        self.write(137, self.read(137) | 0x01)  # FASTLOCK=1
        self.write(136, self.read(136) | 0x40)  # ICAL=1

        if not self.has_xtal():
            raise ValueError("Si5324 misses XA/XB oscillator signal")
        if not self.has_clkin2():
            raise ValueError("Si5324 misses CLKIN2 signal")
        self.wait_lock()

    def dump(self):
        for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 19, 20, 21, 22, 23, 24,
                25, 31, 32, 33, 34, 35, 36, 40, 41, 42, 43, 44, 45, 46, 47, 48,
                55, 131, 132, 137, 138, 139, 142, 143, 136):
            print("{: 4d}, {:02X}h".format(i, self.read(i)))

    def report(self):
        logger.info("SI5324(DCXO): has_xtal: %s, has_clkin1: %s, "
                    "has_clkin2: %s, locked: %s",
                    self.has_xtal(), self.has_clkin1(),
                    self.has_clkin2(), self.locked())
