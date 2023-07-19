# SPDX-FileCopyrightText: 2023 Jakub Matyas for Warsaw University of Technology
#
# SPDX-License-Identifier: MIT

"""
`digital_inout`
====================================================

Digital input/output of the PCA9539.

* Author(s): Jakub Matyas
"""

import digitalio
from typing import Optional
from .pca9539_base import PCA9539Base

try:
    from digitalio import Direction, Pull
except ImportError:
    pass


# Internal helpers to simplify setting and getting a bit inside an integer.
def _get_bit(val, bit: int) -> int:
    return val & (1 << bit) > 0


def _enable_bit(val, bit: int) -> int:
    return val | (1 << bit)


def _clear_bit(val, bit: int) -> int:
    return val & ~(1 << bit)


class DigitalInOut:
    """Digital input/output of the PCA9539.  The interface is exactly the
    same as the digitalio.DigitalInOut class, however:

      * PCA9539 family does not support neither pull-down nor pull-up resistors.

    Exceptions will be thrown when attempting to set unsupported pull
    configurations.
    """

    def __init__(self, pin_number: int, PCA9539: PCA9539Base) -> None:
        """Specify the pin number of the PCA9539 (0...15) instance.
        """
        self._pin = pin_number
        self._pca = PCA9539

    # kwargs in switch functions below are _necessary_ for compatibility
    # with DigitalInout class (which allows specifying pull, etc. which
    # is unused by this class).  Do not remove them, instead turn off pylint
    # in this case.
    # pylint: disable=unused-argument
    def switch_to_output(self, value: bool = False, **kwargs) -> None:
        """Switch the pin state to a digital output with the provided starting
        value (True/False for high or low, default is False/low).
        """
        self.direction = digitalio.Direction.OUTPUT
        self.value = value

    def switch_to_input(
        self, invert_polarity: bool = False, **kwargs
    ) -> None:
        """Switch the pin state to a digital input with the provided starting
        pull-up resistor state (optional, no pull-up by default) and input polarity.  Note that
        pull-down resistors are NOT supported!
        """
        self.direction = digitalio.Direction.INPUT
        self.invert_polarity = invert_polarity

    # pylint: enable=unused-argument

    @property
    def value(self) -> bool:
        """The value of the pin, either True for high or False for
        low.  Note you must configure as an output or input appropriately
        before reading and writing this value.
        """
        return _get_bit(self._pca.gpio, self._pin)

    @value.setter
    def value(self, val: bool) -> None:
        if val:
            self._pca.gpio = _enable_bit(self._pca.gpio, self._pin)
        else:
            self._pca.gpio = _clear_bit(self._pca.gpio, self._pin)

    @property
    def direction(self) -> bool:
        """The direction of the pin, either True for an input or
        False for an output.
        """
        if _get_bit(self._pca.conf, self._pin):
            return digitalio.Direction.INPUT
        return digitalio.Direction.OUTPUT

    @direction.setter
    def direction(self, val: Direction) -> None:
        if val == digitalio.Direction.INPUT:
            self._pca.conf = _enable_bit(self._pca.conf, self._pin)
        elif val == digitalio.Direction.OUTPUT:
            self._pca.conf = _clear_bit(self._pca.conf, self._pin)
        else:
            raise ValueError("Expected INPUT or OUTPUT direction!")

    @property
    def pull(self) -> Optional[digitalio.Pull]:
        raise ValueError("Pull-up/pull-down resistors not supported.")

    @pull.setter
    def pull(self, val: Pull) -> None:
            raise ValueError("Pull-up/pull-down resistors not supported.")

    @property
    def invert_polarity(self) -> bool:
        """The polarity of the pin, either True for an Inverted or
        False for an normal.
        """
        if _get_bit(self._pca.ipol, self._pin):
            return True
        return False

    @invert_polarity.setter
    def invert_polarity(self, val: bool) -> None:
        if val:
            self._pca.ipol = _enable_bit(self._pca.ipol, self._pin)
        else:
            self._pca.ipol = _clear_bit(self._pca.ipol, self._pin)
