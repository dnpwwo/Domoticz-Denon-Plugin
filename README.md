# Domoticz-Denon-Plugin
Telnet based Denon / Marantz plugin

Controls a single amplifier on your network.  If you have more than one you can create multiple instances of the plugin via the Hardware page, one per amplifier.

## Key Features

* Creates three Domoticz devices per amplifier
  1. Basic power indicator, On/Off.
  2. Main Zone selector switch for sources, these should match the source names from the documentation that you want to use.
  3. Main Volume level.  Icon mutes/unmutes, slider shows/sets volume.
  4. Tuner preset selector. With selector switch you can select preset 1 to 33. Names can be changed in edit device.
* Devices for additional zones added automatically if detected
* When network connectivity is lost the Domoticz UI will show the device(s) with a red banner
* Amplifier is optionally auto-discovered on the network.

## Installation

Python version 3.4 or higher required & Domoticz version 3.7xxx or greater.

To install:
* Go in your Domoticz directory, open the plugins directory.
* Navigate to the directory using a command line
* Run: ```git clone https://github.com/dnpwwo/Domoticz-Denon-Plugin.git```
* Restart Domoticz.

In the web UI, navigate to the Hardware page.  In the hardware dropdown there will be an entry called "Denon/Marantz Amplifier".

## Updating

To update:
* Go in your Domoticz directory using a command line and open the plugins directory then the Domoticz-Denon-Plugin directory.
* Run: ```git pull```
* Restart Domoticz.

## Configuration

| Field | Information|
| ----- | ---------- |
| Port | The port that the amplifier is listening on. Default 23 (Telnet) |
| Auto-Detect| Dropdown that controls device discovery. If True the Discovery Match field is used, if False the IP Address field is used |
| IP Address | Will handle DNS names and IP V4 addresses (e.g 192.168.xxx.xxx) if not auto-detecting |
| Discovery Match | SSDP attribute match to use if auto-detecting |
| Startup Delay | Time to wait before sending commands when turning on, default 4 seconds|
| Sources | Amplifier source names that are to be used in the Sources selector switches. Selector switch names can be changed after the device is created to something meaningful and the plugin will map back to the values in this field |
| Debug | When true the logging level will be much higher to aid with troubleshooting |

## Change log

| Version | Information|
| ----- | ---------- |
| 3.2.0 | Initial upload version |
| 3.2.1 | Uplift debugging |
| 3.2.2 | Explicitly disconnect UDP socket when Denon is discovered |
| 3.2.3 | Explicitly disconnect UDP socket when Denon is discovery times out |
| 3.2.5 | Improve UDP listener close |
| 3.3.0 | Aaded device for selecting analog tuner preset.
| 3.3.1 | Fixed small bug when selecting tuner preset and source channel was not on tuner. 
