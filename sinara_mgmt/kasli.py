# SPDX-FileCopyrightText: 2023 Mikołaj Sowiński for TechnoSystem sp. z o.o.
# SPDX-FileCopyrightText: 2023 Jakub Matyas for Warsaw University of Technology
#
# SPDX-License-Identifier: MIT
import os

import digitalio
from adafruit_blinka.microcontroller.ftdi_mpsse.mpsse.i2c import I2C as _I2C
from adafruit_blinka.microcontroller.ftdi_mpsse.mpsse.pin import Pin
from adafruit_bus_device import i2c_device
from adafruit_mcp230xx.mcp23017 import MCP23017
from busio import I2C

from sinara_mgmt.chips.eeprom_24aa025e48 import EEPROM24AA02E48, EEPROM24AA025E48
from sinara_mgmt.chips.tca9548a import TCA9548A
from sinara_mgmt.sinara import Sinara


# patching ftdi_mpsse.mpsse.i2c.I2C.scan method so it accepts one argument
def patched_scan_method(self, write=False):
    return [addr for addr in range(0x79) if self._i2c.poll(addr, write)]


_I2C.scan = patched_scan_method


class SFPIO:
    def __init__(self, expander: MCP23017, offset: int):
        self.led = expander.get_pin(6 + offset)
        self.led.direction = digitalio.Direction.OUTPUT

        # External pullup
        self.los = expander.get_pin(5 + offset)
        self.los.direction = digitalio.Direction.INPUT

        # External pullup
        self.mod_present = expander.get_pin(4 + offset)
        self.mod_present.direction = digitalio.Direction.INPUT

        # External pulldown
        self.rate_select = expander.get_pin(3 + offset)
        self.rate_select.direction = digitalio.Direction.OUTPUT

        # External pulldown
        self.rate_select1 = expander.get_pin(2 + offset)
        self.rate_select1.direction = digitalio.Direction.OUTPUT

        self.tx_disable = expander.get_pin(1 + offset)
        self.tx_disable.direction = digitalio.Direction.OUTPUT

        # External pullup
        self.tx_fault = expander.get_pin(0 + offset)
        self.tx_fault.direction = digitalio.Direction.INPUT


class KasliI2C(I2C):
    scan_blacklist = [0x70, 0x71]

    def __init__(self, url="ftdi://ftdi:4232:/2", frequency=100000):
        os.environ["BLINKA_FT2232H_2"] = url
        self._i2c = _I2C(2, frequency=frequency)

        enable = Pin(6, 2)
        enable.init(Pin.OUT)
        enable.value(1)

        reset = Pin(5, 2)
        reset.init(Pin.OUT)
        reset.value(0)

        # I2C muxes and bus definitions
        self.tca0 = TCA9548A(self, address=0x70)
        self.tca1 = TCA9548A(self, address=0x71)

        self.bus_eem = [
            self.tca0[7],
            self.tca0[5],
            self.tca0[4],
            self.tca0[3],
            self.tca0[2],
            self.tca0[1],
            self.tca0[0],
            self.tca0[6],
            self.tca1[4],
            self.tca1[5],
            self.tca1[7],
            self.tca1[6],
        ]

        self.bus_shared = self.tca1[3]
        self.bus_sfp = [self.tca1[0], self.tca1[1], self.tca1[2], self.bus_shared]

        # IOs via expanders
        self.expander0 = MCP23017(self.bus_shared, address=0x20, reset=False)
        self.expander1 = MCP23017(self.bus_shared, address=0x21, reset=False)

        self.vbus_present_n = self.expander0.get_pin(7)
        self.vbus_present_n.direction = digitalio.Direction.INPUT

        self.clk_sel = self.expander0.get_pin(15)
        self.clk_sel.direction = digitalio.Direction.OUTPUT

        self.main_dcxo_oe = self.expander1.get_pin(7)
        self.main_dcxo_oe.direction = digitalio.Direction.OUTPUT

        self.helper_dcxo_oe = self.expander1.get_pin(15)
        self.helper_dcxo_oe.direction = digitalio.Direction.OUTPUT

        self.sfpio0 = SFPIO(self.expander0, 0)
        self.sfpio1 = SFPIO(self.expander0, 8)
        self.sfpio2 = SFPIO(self.expander1, 0)
        self.sfpio3 = SFPIO(self.expander1, 8)

        # EEPROM
        self.eeprom = EEPROM24AA025E48(self.bus_shared, 0x57)

    def scan(self, write=False):
        # Override method from busio.i2c.scan, so it accepts one positional
        # argument
        return self._i2c.scan(write)

    @property
    def sinara_eeprom(self):
        return Sinara.unpack(bytes(self.eeprom.contents))

    def print_bus_addresses(self, bus, prefix="\t"):
        for adr in bus.scan(write=True):
            if adr in self.scan_blacklist:
                continue
            print(f"{prefix}- 0x{adr:02x}")

    def print_i2c_tree(self):
        print("SHARED BUS:")
        self.print_bus_addresses(self.bus_shared)
        # for idx, bus in enumerate(self.bus_eem):
        #     print(f"EEM{idx}:")
        #     self.print_bus_addresses(bus)

    def discover_peripherals(self):
        eem_peripherals = []
        for slot, eem_bus in enumerate(self.bus_eem):
            try:
                eem_dev = self.identify_eem(eem_bus)
            except ValueError as e:
                raise ValueError(f"{e} on slot {slot}")
            if eem_dev is not None:
                eem_peripherals.append((eem_dev, slot))

        self.eem_peripherals = eem_peripherals

    def identify_eem(self, eem_bus):
        try:
            # probe for EEPROM on a given EEM
            i2c_device.I2CDevice(eem_bus, 0x50, probe=True)
        except ValueError:
            return None

        ee = EEPROM24AA02E48(eem_bus, address=0x50)
        ee_contents_bytes = bytes(ee.contents)
        try:
            return Sinara.unpack(ee_contents_bytes)
        except ValueError as e:
            raise e
