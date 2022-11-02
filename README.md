# ZOA-Helper
ZOA Helper is a command line tool for use by members of the Virtual Oakland ARTCC (https://oakartcc.org/) on the VATSIM Network.

Command-line features include:
- Retrieve real-world IFR flightplans from the FlightAware IFR Analyzer
- Quick-open routes in SkyVector in the default web browser
- Search ZOA TEC routes for flights originating and terminating within ZOA
- Search LOAs for applicable routing rules for flights originating in ZOA and terminating in ZLA, ZSE or ZLC
- Retrieve SIDs and STARs for a given airport, and open a selected chart in the default web browser
- Convert ICAO codes to "full names" for airports, airlines and aircraft
---

## How to Run
### Executable
1. Download latest release: https://github.com/kengreim/ZOA-Helper/releases/tag/v0.1.0
2. Unzip to location of your choice
3. Run zoa_helper.exe, which should open a command line / terminal prompt. On Windows, I suggest you install Windows Terminal (https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701?hl=en-us&gl=us)

### From Source
1. Clone the repository using `git clone https://github.com/kengreim/ZOA-Helper.git`
2. Create and activate a Python virtual environment
3. Use `pip install -r requirements.txt` to install the required packages
4. Use the virtual enviroment's Python interpreter to run `zoa_helper.py`
---

## How to Build from Source
1. Clone the repository using `git clone https://github.com/kengreim/ZOA-Helper.git`
2. Create and activate a Python virtual environment
3. Use `pip install -r requirements.txt` to install the required packages
4. Inside your virtual environment's `Scripts` folder there should be a file called `auto-py-to-exe`. Run this with the following settings: _TBD_
