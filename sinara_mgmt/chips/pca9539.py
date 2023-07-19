# SPDX-FileCopyrightText: 2023 Jakub Matyas
#
# SPDX-License-Identifier: MIT

"""
`pca9539`
====================================================

CircuitPython module for the PCA9539 I2C I/O extenders.

* Author(s): Jakub Matyas
"""


try:
    from busio import I2C
except ImportError:
    pass

from .digital_inout import DigitalInOut
from micropython import const
from .pca9539_base import PCA9539Base



_PCA9539_ADDRESS = const(0x74)
_PCA9539_IPORT0 = const(0x00)
_PCA9539_IPORT1 = const(0x01)
_PCA9539_OPORT0 = const(0x02)
_PCA9539_OPORT1 = const(0x03)
_PCA9539_POLINV0 = const(0x04)
_PCA9539_POLINV1 = const(0x05)
_PCA9539_CONF0 = const(0x06)
_PCA9539_CONF1 = const(0x07)

class PCA9539(PCA9539Base):
    """Supports PCA9539 instance on specified I2C bus and optionally
    at the specified I2C address.
    """

    def __init__(
        self, i2c: I2C, address: int = _PCA9539_ADDRESS, reset: bool = True
    ) -> None:
        super().__init__(bus_device=i2c, address=address)
        if reset:
            # Reset to all inputs with no pull-ups and no inverted polarity.
            self.conf = 0xFFFF
            self.polinv = 0x0000
            self._write_u16le(_PCA9539_POLINV0, 0x0000)

    @property
    def gpio(self) -> int:
        """The raw GPIO input register.  Each bit represents the
        incoming logic value of the associated pin (0 = low, 1 = high), regardless of
        whether the pin has been configured as an output or an input.
        """
        return self._read_u16le(_PCA9539_IPORT0)

    @gpio.setter
    def gpio(self, val: int) -> None:
        """The raw GPIO output register.  Each bit represents the
        value of the associated output pin (0 = low, 1 = high), assuming 
        the pin has been configured as an output. Otherwise, bit values have no
        effect on pins defined as inputs.
        """
        self._write_u16le(_PCA9539_OPORT0, val)

    @property
    def gpio0(self) -> int:
        """The raw GPIO 0 input register.  Each bit represents the
        input value of the associated pin (0 = low, 1 = high), regardless of
        whether the pin has been configured as an output or an input.
        """
        return self._read_u8(_PCA9539_IPORT0)

    @gpio0.setter
    def gpio0(self, val: int) -> None:
        self._write_u8(_PCA9539_OPORT0, val)

    @property
    def gpio1(self) -> int:
        """The raw GPIO 1 output register.  Each bit represents the
        input value of the associated pin (0 = low, 1 = high), regardless of
        whether the pin has been configured as an output or an input.
        """
        return self._read_u8(_PCA9539_IPORT1)

    @gpio1.setter
    def gpio1(self, val: int) -> None:
        self._write_u8(_PCA9539_OPORT1, val)

    @property
    def conf(self) -> int:
        """The raw CONFIGURATION direction register.  Each bit represents
        direction of a pin, either 1 for an input or 0 for an output mode.
        """
        return self._read_u16le(_PCA9539_CONF0)

    @conf.setter
    def conf(self, val: int) -> None:
        self._write_u16le(_PCA9539_CONF0, val)

    @property
    def conf0(self) -> int:
        """The raw CONFIGURATION 0 direction register.  Each bit represents
        direction of a pin, either 1 for an input or 0 for an output mode.
        """
        return self._read_u8(_PCA9539_CONF0)

    @conf0.setter
    def conf0(self, val: int) -> None:
        self._write_u8(_PCA9539_CONF0, val)

    @property
    def conf1(self) -> int:
        """The raw CONFIGURATION 1 direction register.  Each bit represents
        direction of a pin, either 1 for an input or 0 for an output mode.
        """
        return self._read_u8(_PCA9539_CONF1)

    @conf1.setter
    def conf1(self, val: int) -> None:
        self._write_u8(_PCA9539_CONF1, val)

    def get_pin(self, pin: int) -> DigitalInOut:
        """Convenience function to create an instance of the DigitalInOut class
        pointing at the specified pin of this PCA9539 device.
        """
        if not 0 <= pin <= 15:
            raise ValueError("Pin number must be 0-15.")
        return DigitalInOut(pin, self)

    @property
    def polinv(self) -> int:
        """The raw POLARITY INVERSION register.  Each bit represents the
        polarity value of the associated input pin (0 = normal, 1 = inverted).
        """
        return self._read_u16le(_PCA9539_POLINV0)

    @polinv.setter
    def polinv(self, val: int) -> None:
        self._write_u16le(_PCA9539_POLINV0, val)

    @property
    def polinv0(self) -> int:
        """The raw POLARITY INVERSION 0 register.  Each bit represents the
        polarity value of the associated input pin (0 = normal, 1 = inverted).
        """
        return self._read_u8(_PCA9539_POLINV0)

    @polinv0.setter
    def polinv0(self, val: int) -> None:
        self._write_u8(_PCA9539_POLINV0, val)

    @property
    def polinv1(self) -> int:
        """The raw POLARITY INVERSION 1 register.  Each bit represents the
        polarity value of the associated input pin (0 = normal, 1 = inverted).
        """
        return self._read_u8(_PCA9539_POLINV1)

    @polinv1.setter
    def polinv1(self, val: int) -> None:
        self._write_u8(_PCA9539_POLINV1, val)
