# SPDX-FileCopyrightText: 2023 Jakub Matyas for TechnoSystem sp. z o.o.
#
# SPDX-License-Identifier: MIT

import time

from adafruit_bus_device import i2c_device

try:
    from busio import I2C
except ImportError:
    pass

SI549_REGISTER_DEVICE_TYPE = 0x00
SI549_REGISTER_RESET = 0x07
SI549_REGISTER_OUTPUT_EN = 0x11
SI549_REGISTER_HSDIV = 0x17
SI549_REGISTER_LSDIV = 0x18
SI549_REGISTER_FBDIV_0 = 0x1A
SI549_REGISTER_FBDIV_1 = 0x1B
SI549_REGISTER_FBDIV_2 = 0x1C
SI549_REGISTER_FBDIV_3 = 0x1D
SI549_REGISTER_FBDIV_4 = 0x1E
SI549_REGISTER_FBDIV_5 = 0x3F
SI549_REGISTER_FCAL = 0x45
SI549_REGISTER_PAGE = 0xFF

SI549_FBDIV_REGS = [
    SI549_REGISTER_FBDIV_0,
    SI549_REGISTER_FBDIV_1,
    SI549_REGISTER_FBDIV_2,
    SI549_REGISTER_FBDIV_3,
    SI549_REGISTER_FBDIV_4,
    SI549_REGISTER_FBDIV_5,
]

SI549_DEFAULT_ADDRESS = 0x67

SI549_FOSC = 152.6e6


LSDIV_RANGE = [i for i in range(8)]
HSDIV_RANGE = [*[i for i in range(5, 34)], *[i for i in range(34, 2046, 2)]]
FBDIV_INT_RANGE = [i for i in range(60, 2046)]
FVCO_RANGE = {
    "A": [10.8e9, 12.511886114e9],
    "B": [10.8e9, 12.206718160e9],
    "C": [10.8e9, 12.206718160e9],
}
FOUT_RANGE = {"A": [0.2e6, 1500e6], "B": [0.2e6, 800e6], "C": [0.2e6, 325e6]}


class Si549:
    def __init__(self, i2c: I2C, address: int = SI549_DEFAULT_ADDRESS) -> None:
        self._device = i2c_device.I2CDevice(i2c, address, probe=False)

    def _read_u8(self, address: int) -> int:
        with self._device as i2c:
            write_buffer = bytearray([address & 0xFF])
            read_buffer = bytearray(1)
            i2c.write_then_readinto(write_buffer, read_buffer)
        return read_buffer[0]

    def _write_u8(self, address: int, value: int) -> None:
        write_buffer = bytearray([address & 0xFF, value & 0xFF])
        with self._device as i2c:
            i2c.write(write_buffer)

    def compute_config(self, frequency):
        raise NotImplementedError

    def write_config(self, hsdiv_val, lsdiv_val, fbdiv_val):
        # get device ready for update
        self._write_u8(SI549_REGISTER_PAGE, 0)  # set page register to 0
        self._write_u8(SI549_REGISTER_FCAL, 0)  # disable FCAL override
        self._write_u8(SI549_REGISTER_OUTPUT_EN, 0)  # synchronously disable output

        # update dividers
        register_value = hsdiv_val & 0xFF  # contains only 8 lower bits of HSDIV
        self._write_u8(SI549_REGISTER_HSDIV, register_value)
        register_value = (lsdiv_val << 4) | ((hsdiv_val >> 8) & 0b11)
        self._write_u8(SI549_REGISTER_LSDIV, register_value)
        for i, reg_address in enumerate(SI549_FBDIV_REGS):
            register_value = (fbdiv_val >> 8 * i) & 0xFF

        # startup device
        register_value = 1 << 3  # initiate FCAL
        self._write_u8(SI549_REGISTER_RESET, register_value)
        time.sleep(0.5)  # internal FCAL VCO calibration; 30 ms delay required
        self._write_u8(SI549_REGISTER_OUTPUT_EN, 0x01)  # enable output
