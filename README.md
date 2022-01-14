# BHSTools-MQTT
This is an MQTT client built on top of the [BHSTools](https://github.com/flarn2006/BHSTools) project. My goal with it was to be able to interface my home automation system ([Home Assistant](https://www.home-assistant.io/)) with the Brinks security system that is installed in my house.

I built it to fit my needs with a minimal amount of configuration, so it might not be as flexible as it could be for general use. However, it should suffice for most simple uses.

## Requirements and Limitations
- The code assumes it is running on a device that has a serial connection to the security system as described in [the BHSTools documentation](https://github.com/flarn2006/BHSTools#using-rs-485). 
- There is currently no way to connect to the MQTT server with credentials. 

## Setup and Running the Client

### Dependencies
1. This code depends on the [BHSTools](https://github.com/flarn2006/BHSTools) source. You will need to clone that repository into a folder named `BHSTools` in the root directory of this project. Runing `git clone https://github.com/flarn2006/BHSTools.git` in the root directory should accomplish that.
2. MQTT functionality is provided by the Paho MQTT library. It should be installed with `pip install paho-mqtt` if it isn't already available.

### Configuration
There is a configuration file named `mqtt_config.json` which you will need to modify for your particular setup. 

| Field  | Type | Description |
| ------------- | ------------- | ------------- |
| mqtt.server_address | string | The address of the MQTT server. (Only tested with a server on the local network) |
| mqtt.client_id | string | A unique name to identify the MQTT client to the server |
| mqtt.topic_root | string | A prefix that is added to all of the topics both subscribed to and published so they can be grouped together. |
| zone_names | string[] | The names of the zones in your security system. Their position in the array should correspond with their zone number - 1 (i.e. the name for zone 1 is in array index 0) Because the names are used in a topic, they should not contain spaces, slashes, or other special characters. |
| intellibus_port | string | The name of the COM port that is connected to the security system bus. |

### Startup
To start the client, run the `mqtt_client.py` file.

## MQTT Topics

### Published

| Topic  | Payload |
| ------------- | ------------- |
| \${topic_root}/zone/${zone_name}  | "ready" \| "not_ready" |
| \${topic_root}/system  | "ready" \| "not_ready"  |
| ${topic_root}/arm | "armed_home" \| "armed_away" \| "disarmed" \| "pending" \| "triggered" |
| ${topic_root}/time | current system time <br/> format: `%a, %b %d, %Y %I:%M %p` |
| ${topic_root}/command/result| human-readable result of most recently executed command <br />ex: `"command: ${opcode} (${args}) completed [with ${result}]."` |


### Consumed
These topics allow you to execute commands on the system by publishing messages to them in the given format.

| Topic  | Payload | Description/Notes |
| ------------- | ------------- | ------------- |
| \${topic_root}/command  | `{"op": number, "args": string[]}` | Execute an arbitrary command. Supports all commands that `command.py` from BHSTools supports as of Jan 2022 |
| \${topic_root}/command/query  | `zone_number` | Queries the ready status of the specified zone. The corresponding topic above is published with the result |
| ${topic_root}/command/arm | `{"op": "ARM_AWAY"\|"ARM_HOME"\|"DISARM", "args": []}` | Arms or disarms the system depending on the provided `op` payload value.<br/><ul><li>`ARM_AWAY`: Arms the system in normal mode</li><li>`ARM_HOME`: Arms the system in Instant mode</li><li>`DISARM`: Disarms the system</li></ul> For the arm away command, you can provide a custom countdown as the first value in the `args` array. It should be a number and not a string. If none is provided, the default is 60 seconds. The system will not arm if any zones are fualted. |
| ${topic_root}/command/code |  | Returns the installer access code |

## Notes
This is not great code. I wrote it while sitting on my couch and being continually pestered by a 4-year-old. I am also not a Python developer, but since it's what BHSTools was written in, it only made sense to work with it. What I've written could likely have been done MUCH better, but again, being a personal project, I just wanted it to work.
