# SPDX-FileCopyrightText: 2023 Jakub Matyas for Warsaw University of Technology
#
# SPDX-License-Identifier: MIT

import digitalio
from adafruit_bus_device import i2c_device

from sinara_mgmt.chips.eeprom_24aa025e48 import EEPROM24AA02E48, EEPROM24AA025E48
from sinara_mgmt.chips.pca9539 import PCA9539
from sinara_mgmt.kasli import KasliI2C
from sinara_mgmt.sinara import Sinara


def map_to_eem(slot_no, diot_peripheral):
    diot_slots_map = [
        (0, 1),
        (2, 3),
        (4, 5),
        (6, 7),
        (8, 9),
        (9,),
        (10, 11),
        (11,),
    ]
    ports = []
    for ix, eem in enumerate(diot_peripheral.identified_eems):
        if eem:
            ports.append(diot_slots_map[slot_no][ix])
    return ports


def unwrap_from_diot(diot_peripherals):
    peripherals = []
    for eem_diot_adapter, ports in diot_peripherals:
        if eem_diot_adapter.device is not None:
            peripherals.append((eem_diot_adapter.device, ports))
    return peripherals


class KasliDIOT(KasliI2C):
    def __init__(self, url="ftdi://ftdi:4232:/2", frequency=100000):
        super().__init__(url=url, frequency=frequency)

        self.mon_i2c = self.tca1[4]
        self.cpcis_i2c = self.tca1[5]
        self.adapter_logic_i2c = self.tca1[6]

        self.adapter_expander0 = PCA9539(
            self.adapter_logic_i2c, address=0x74, reset=False
        )
        self.adapter_expander1 = PCA9539(
            self.adapter_logic_i2c, address=0x75, reset=False
        )

        self.adapter_eeprom0 = EEPROM24AA025E48(self.adapter_logic_i2c, address=0x50)
        self.adapter_eeprom1 = EEPROM24AA02E48(self.adapter_logic_i2c, address=0x57)

        self.servmods = [self.adapter_expander1.get_pin(slot + 1) for slot in range(8)]
        self.ext9_mux_sel, self.ext11_mux_sel = self.adapter_expander1.get_pin(
            9
        ), self.adapter_expander1.get_pin(10)
        self.diot_peripherals = [None for i in range(8)]

    def probe_diot_slot(self, slot):
        """check if a peripheral is inserted in the given slot
        by reading the state of the correpsonding servmod pin
        on Kasli DIOT Adapter
        """

        assert slot in range(8)
        servmod = self.adapter_expander1.get_pin(slot + 1)
        servmod.direction = digitalio.Direction.INPUT

        # if a board is inserted it should pull the servmod
        # line LOW
        return not servmod.value

    def probe_peripheral(self, slot):
        assert slot in range(8)
        servmod = self.servmods[slot]
        servmod.direction = digitalio.Direction.INPUT

        if servmod.value is False:  # peripheral board inserted in a given slot
            # make sure that shared I2C bus is enabled
            en_i2c0, en_i2c1 = self.adapter_expander0.get_pin(
                16
            ), self.adapter_expander0.get_pin(15)
            en_i2c0.direction = digitalio.Direction.OUTPUT
            en_i2c1.direction = digitalio.Direction.OUTPUT
            en_i2c0.value = False
            en_i2c1.value = False

            servmod.direction = digitalio.Direction.OUTPUT
            servmod.value = True

            edapter = EemDiotAdapter(self.cpcis_i2c, en_i2c0, en_i2c1)

            # release pins
            servmod.direction - digitalio.Direction.INPUT
            en_i2c0.direction = digitalio.Direction.INPUT
            en_i2c1.direction = digitalio.Direction.INPUT

            return edapter
        else:
            return None

    def discover_peripherals(self):
        for slot in range(8):
            edapter = self.probe_peripheral(slot)
            if edapter is not None:
                edapter.probe_for_eems()  # in case not sinara compatible device
                edapter.identify_devices()
                self.diot_peripherals[slot] = (edapter, map_to_eem(slot, edapter))

    def set_slot_mux(self, ext_no, value: bool):
        # accept number of EXT connector for which MUX_sel should be set as an argument
        assert ext_no in (9, 11)
        mux_sel = getattr(self, f"ext{ext_no}_mux_sel", None)
        if mux_sel is None:
            raise ValueError(f"Failed to get EXT{ext_no}_MUX_sel")
        mux_sel.directin = digitalio.Direction.OUTPUT
        mux_sel.value = value

    def read_slot_mux(self, ext_no):
        assert ext_no in (9, 11)
        mux_sel = getattr(self, f"ext{ext_no}_mux_sel", None)
        if mux_sel is None:
            raise ValueError(f"Failed to get EXT{ext_no}_MUX_sel")

        return mux_sel.value


class EemDiotAdapter:
    def __init__(self, i2c_bus, en_i2c0, en_i2c1):
        self._i2c_bus = i2c_bus
        self._en_i2c0 = en_i2c0
        self._en_i2c1 = en_i2c1

        # make sure that shared I2C bus is enabled
        en_i2c0.direction = digitalio.Direction.OUTPUT
        en_i2c1.direction = digitalio.Direction.OUTPUT
        en_i2c0.value = False
        en_i2c1.value = False

        self.adapter_eeprom = EEPROM24AA025E48(self._i2c_bus, address=0x50)
        self.eui48 = self.adapter_eeprom

        self.eems = [None, None]
        self.identified_eems = [None, None]

    @property
    def device_name(self):
        if self.identified_eems[0] is None:
            return None
        return getattr(self.identified_eems[0], "name", None)

    @property
    def device(self):
        if self.identified_eems[0] is None:
            return None

        return self.identified_eems[0]

    def enable_eem_i2c(self, eem_no):
        assert eem_no in [0, 1]
        # make sure that corresponding I2C bus is enabled on EEM DIOT Adapter
        if eem_no == 0:
            self._en_i2c0.value, self._en_i2c1.value = True, False
        else:
            self._en_i2c0.value, self._en_i2c1.value = False, True

    def release_eem_i2c(self):
        self._en_i2c0.value, self._en_i2c1.value = False, False

    def probe_for_eems(self):
        # create i2c_device but do not probe for EEPROM yet - bus needs to be enabled first
        _i2c_dev = i2c_device.I2CDevice(self.cpcis_i2c, 0x50)
        for eem_n in range(2):
            self.eems[eem_n] = self.probe_for_eem(_i2c_dev, eem_n)

        # release both buses
        self.release_eem_i2c()

    def probe_for_eem(self, _i2c_dev: i2c_device.I2CDevice, eem_no):
        # make sure that corresponding I2C bus is enabled on EEM DIOT Adapter
        self.enable_eem_i2c(eem_no)
        try:
            _i2c_dev.__probe_for_device()
            return True
        except OSError:
            return None
        finally:
            self.release_eem_i2c()

    def identify_devices(self):
        for eem_no in range(2):
            self.identified_eems[eem_no] = self.identify_eem(eem_no)

    def identify_eem(self, eem_no):
        if self.eems[eem_no] is None:
            return None
        self.enable_eem_i2c(eem_no)
        ee = EEPROM24AA02E48(self._i2c_bus, address=0x50)
        ee_contents_bytes = bytes(ee.contents)
        try:
            return Sinara.unpack(ee_contents_bytes)
        except ValueError as e:
            raise e
        finally:
            self.release_eem_i2c()
