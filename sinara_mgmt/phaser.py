from adafruit_bus_device import i2c_device
from busio import I2C
from typing import List
from sinara_mgmt.eeprom_24aa025e48 import EEPROM24AA025E48

class LM75:
    def __init__(self, i2c_bus: I2C, address: int):
        self._i2c = i2c_device.I2CDevice(i2c_bus, address, False)


class Phaser:
    def __init__(self, bus_device: List[I2C]) -> None:
        assert len(bus_device) == 2
        self._eem0_i2c, self._eem1_i2c = bus_device
        self.eeprom0 = EEPROM24AA025E48(self._eem0_i2c, 0x50)
        self.eeprom1 = EEPROM24AA025E48(self._eem1_i2c, 0x50)

        self.temp0 = LM75(self._eem0_i2c, 0x48)
        self.temp1 = LM75(self._eem1_i2c, 0x49)

