# SPDX-FileCopyrightText: 2023 Jakub Matyas for Warsaw University of Technology
#
# SPDX-License-Identifier: MIT


from unittest.mock import Mock

from sinara_mgmt.description_manager import SystemDescription
from sinara_mgmt.kasli_diot import EemDiotAdapter, map_to_eem, unwrap_from_diot
from sinara_mgmt.sinara import Sinara

KASLI = Sinara(
    name="Kasli",
    board=Sinara.boards.index("Kasli"),
    data_rev=0,
    major=2,
    minor=0,
    variant=0,
    port=0,
    vendor=Sinara.vendors.index("Technosystem"),
    eui48=Sinara.parse_eui48("04-91-62-f1-d3-3b"),
)


def generate_mock_boards(boards):
    """Generating mock eeprom contents; for development purpose"""
    eui48 = [
        "54-10-ec-a9-15-fe",
        "54-10-ec-a8-bd-3b",
        "80-1f-12-47-45-2c",
        "54-20-ec-a8-00-00",
        "87-1f-ef-42-45-99",
        "54-10-ec-a8-bd-3b",
        "80-1f-ff-47-00-2c",
        "ff-ff-ff-ff-ff-ff",
    ]
    devs = []
    for i, x in zip(eui48, boards):
        s = Sinara(
            name="{}".format(x),
            board=Sinara.boards.index("{}".format(x)),
            data_rev=0,
            major=1,
            minor=1,
            variant=0,
            port=0,
            vendor=Sinara.vendors.index("Technosystem"),
            eui48=Sinara.parse_eui48(i),
        )
        devs.append(s)

    return devs


def main_kasli():
    dev_names = ["Zotino", "DIO_BNC", "Sampler", "Stabilizer", "Fastino"]
    devs = generate_mock_boards(dev_names)
    eem_peripherals = [(device, eem_slot) for (eem_slot, device) in enumerate(devs)]
    SD = SystemDescription(KASLI, eem_peripherals)
    SD.gen_system_description()
    print(SD.description)


def main_diot():
    dev_names = ["Zotino", "DIO_BNC", "Sampler", "Stabilizer", "Fastino"]
    devs = generate_mock_boards(dev_names)
    _i2c_bus = Mock()
    _en_i2c0 = Mock()
    _en_i2c1 = Mock()
    diot_devices = [EemDiotAdapter(_i2c_bus, _en_i2c0, _en_i2c1) for i in range(8)]
    board_index = 0

    for ix, eem_diot_adapter in enumerate(diot_devices):
        if ix == 0 or ix == 1:
            # simulate that a DIOT module is present on a given DIOT slot
            # (with both EEMs connected)
            eem_diot_adapter.eems = [True, True]
        elif ix != 5:
            # simulte that a DIOT module is present on a given DIOT slot
            # with only first (out of two) EEM connected
            eem_diot_adapter.eems = [True, None]

        if ix == 0:
            euis = [
                "54-10-ec-a9-15-fe",
                "54-10-ec-a9-15-ab",
            ]
            urukuls = [
                Sinara(
                    name="Urukul",
                    board=Sinara.boards.index("Urukul"),
                    data_rev=0,
                    major=1,
                    minor=5,
                    variant=0,
                    port=i,
                    vendor=Sinara.vendors.index("Technosystem"),
                    eui48=Sinara.parse_eui48(euis[i]),
                )
                for i in range(2)
            ]
            eem_diot_adapter.identified_eems = urukuls
        elif ix == 1:
            euis = [
                "54-10-ec-a9-1f-ae",
                "54-10-ec-09-05-fc",
            ]
            samplers = [
                Sinara(
                    name="Sampler",
                    board=Sinara.boards.index("Sampler"),
                    data_rev=0,
                    major=1,
                    minor=3,
                    variant=0,
                    port=i,
                    vendor=Sinara.vendors.index("Technosystem"),
                    eui48=Sinara.parse_eui48(euis[i]),
                )
                for i in range(2)
            ]
            eem_diot_adapter.identified_eems = samplers
        else:
            if ix != 5:
                eem_diot_adapter.identified_eems = [devs[board_index], None]
                board_index += 1

    def map_to_diot_devs(peripherals):
        kasli_diot_periphs = [None for i in range(8)]
        for slot_no, eem_adapter in enumerate(peripherals):
            kasli_diot_periphs[slot_no] = (
                eem_adapter,
                map_to_eem(slot_no, eem_adapter),
            )
        return kasli_diot_periphs

    kasli_diot_peripehrals = map_to_diot_devs(diot_devices)
    kasli_eem_peripherals = unwrap_from_diot(kasli_diot_peripehrals)
    SD = SystemDescription(KASLI, kasli_eem_peripherals)
    SD.gen_system_description()
    print(SD.description)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--diot", action="store_true")
    args = parser.parse_args()
    if args.diot:
        print("KASLI DIOT variant chosen...")
        main_diot()
    else:
        print("KASLI standard variant chosen...")
        main_kasli()
