# Sinara Management Tools

This repo contains basic set of tools that allow to perform management operations
on Sinara devices. Currently, development was focued on (amongst others):
  * support for Kasli;
  * support for management of DIOT interface for Kasli and EEM modules;
  * EEM modules discovery;


## Installation and usage
Tools were developed using python 3.8.5 and use Adafruit's CircuitPython as a base for drivers support and communication with hardware. To set up environemt one can use their favourite virtualenv management tool (*requirements.txt* for `pip` and *Pipfile* for `pipenv` are provided).

`demo.py` contains simple example of how one can facilitate tools and access desired devices or nodes. Running `python -m demo` will read EUI from Kasli's on-board EEPROM, as well as the EEPROM's contents and print them to the console. It will also perform EEM modules discovery and generate a JSON file with the setup description.