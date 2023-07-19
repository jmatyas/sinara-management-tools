# SPDX-FileCopyrightText: 2023 Jakub Matyas
#
# SPDX-License-Identifier: MIT


from adafruit_bus_device import i2c_device
try:
    from typing import List
    from busio import I2C
except ImportError:
    pass


# Global buffer for reading and writing registers with the devices.  
_BUFFER = bytearray(3)


class PCA9539Base:
    def __init__ (
            self, 
            bus_device: I2C,
            address: int,
    ) -> None:
        self._device = i2c_device.I2CDevice(bus_device, address)

    def _read_u16le(self, register: int) -> int:
        # Read an unsigned 16 bit little endian value from the specified 8-bit
        # register.
        with self._device as bus_device:
            _BUFFER[0] = register & 0xFF

            bus_device.write_then_readinto(
                _BUFFER, _BUFFER, out_end=1, in_start=1, in_end=3
            )
            return (_BUFFER[2] << 8) | _BUFFER[1]

    def _write_u16le(self, register: int, val: int) -> None:
        # Write an unsigned 16 bit little endian value to the specified 8-bit
        # register.
        with self._device as bus_device:
            _BUFFER[0] = register & 0xFF
            _BUFFER[1] = val & 0xFF
            _BUFFER[2] = (val >> 8) & 0xFF
            bus_device.write(_BUFFER, end=3)

    def _read_u8(self, register: int) -> int:
        # Read an unsigned 8 bit value from the specified 8-bit register.
        with self._device as bus_device:
            _BUFFER[0] = register & 0xFF

            bus_device.write_then_readinto(
                _BUFFER, _BUFFER, out_end=1, in_start=1, in_end=2
            )
            return _BUFFER[1]

    def _write_u8(self, register: int, val: int) -> None:
        # Write an 8 bit value to the specified 8-bit register.
        with self._device as bus_device:
            _BUFFER[0] = register & 0xFF
            _BUFFER[1] = val & 0xFF
            bus_device.write(_BUFFER, end=2)