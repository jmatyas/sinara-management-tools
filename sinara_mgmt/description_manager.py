# SPDX-FileCopyrightText: 2023 Jakub Matyas for Warsaw University of Technology
#
# SPDX-License-Identifier: MIT


import json
from typing import List, Tuple

from sinara_mgmt.sinara import Sinara, _SinaraTuple

SINARA_KEYS = _SinaraTuple._fields


class DescGenerationManager:
    _comm_desc = {
        "type": None,
        "board": (None, "board_fmt"),
        "hw_rev": (None, "hw_rev"),
        "vendor": (None, "vendor_fmt"),
        "ports": [],
    }
    _controller_desc = {
        "target": None,
        "variant": (None, "variant_fmt"),
        "hw_rev": (None, "hw_rev"),
        "base": "standalone",  # [standalone, master, satellite]
        "vendor": (None, "vendor_fmt"),
    }

    @classmethod
    def get_comm_desc(cls, board_type: str, dev: Sinara, ports: List[int]):
        description = dict(cls._comm_desc)
        for key, params in description.items():
            if key == "type":
                description[key] = board_type.lower()
            elif isinstance(params, tuple):
                property_name = params[1]
                description[key] = getattr(dev, property_name)
            elif key == "ports":
                description[key] = ports
        return description

    @classmethod
    def gen_desc_header(cls, controller: Sinara):
        controller_name = controller.board_fmt.lower()
        controller_desc = dict(cls._controller_desc)
        if controller_name not in ("kasli", "kasli_soc"):
            raise NotImplementedError
        else:
            for key, params in controller_desc.items():
                if key == "target":
                    controller_desc[key] = controller_name
                elif isinstance(params, tuple):
                    property_name = params[1]
                    controller_desc[key] = getattr(controller, property_name)

        return controller_desc


class SystemDescription(DescGenerationManager):
    def __init__(self, controller: Sinara, devs: List[Tuple[Sinara, List[int]]]):
        DescGenerationManager().__init__()
        self.devs = devs
        self.controller = controller

        self.peripherals = []
        self.description = {}
        self.eem_processors = {
            "dio": self.gen_dio,
            "fastino": self.gen_fastino,
            "grabber": self.gen_generic,
            "hvamp": self.gen_generic,
            "mirny": self.gen_mirny,
            "novogorny": self.gen_generic,
            "phaser": self.gen_generic,
            "sampler": self.gen_generic,
            "urukul": self.gen_urukul,
            "zotino": self.gen_generic,
        }

        self.controller_additional_desc = {
            "_description": None,
            "min_artiq_version": None,
            "core_addr": None,
            "ext_ref_frequency": None,
            "rtio_frequency": None,
            "core_addr": None,
            "enable_sata_drtio": None,
            "sed_lanes": None,
        }

    def gen_system_description(self):
        if not self.peripherals:
            # no peripherals' description was generated
            self.gen_peripherals_description()

        self.description = self.gen_desc_header(self.controller)
        self.description["peripherals"] = self.peripherals

    def gen_peripherals_description(self):
        peripherals_desc = []
        for device, ports in self.devs:
            device_type = (
                "dio" if device.name.lower().startswith("dio") else device.name.lower()
            )
            try:
                peripherals_desc.append(self.eem_processors[device_type](device, ports))
            except KeyError:
                pass
        self.peripherals = peripherals_desc
        return peripherals_desc

    def gen_generic(self, device, ports):
        device_type = device.name.lower()
        device_desc = self.get_comm_desc(device_type, device, ports)
        return device_desc

    def gen_dio(self, device, ports):
        dio_special = {
            # === UNDISCOVERABLE FROM EEPROM ===
            # however bank directions are required
            "bank_direction_low": "input",
            "bank_direction_high": "output",
            "edge_counter": False,
        }

        dio_desc = self.get_comm_desc("dio", device, ports)
        dio_desc.update(dio_special)
        return dio_desc

    def gen_fastino(self, device, ports):
        fastino_special = {
            "log2_width": 0,
        }
        fastino_desc = self.get_comm_desc("fastino", device, ports)
        fastino_desc.update(fastino_special)
        return fastino_desc

    def gen_mirny(self, device, ports):
        mirny_special = {
            "refclk": 0,
            "clk_sel": 0,
            "almazny": True,  # from eeprom variant
        }

        mirny_desc = self.get_comm_desc("mirny", device, ports)
        mirny_special["almazny"] = True if device.variant_fmt == "Alamzny" else False
        mirny_desc.update(mirny_special)
        return mirny_desc

    def gen_urukul(self, device, ports):
        urukul_special = {
            # === UNDISCOVERABLE FROM EEPROM ===
            "synchronization": "false",
            "refclk": 0,
            "clk_sel": 0,
            "clk_div": 0,
            "pll_n": 0,
            "pll_en": 0,
            "pll_vco": 0,
            # ===
            "dds": None,
        }

        urukul_desc = self.get_comm_desc("urukul", device, ports)
        urukul_special["dds"] = device.variant_fmt
        urukul_desc.update(urukul_special)
        return urukul_desc

    def dump_description(self, filename):
        with open("{}.json".format(filename), "w") as f:
            f.write(json.dumps(self.description, indent=4))
