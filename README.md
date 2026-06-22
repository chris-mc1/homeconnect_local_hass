# Home Connect Local

The **Home Connect Local** allows users to integrate their home appliances supporting the  [Home Connect](https://www.home-connect.com/global) standard for Bosch and Siemens using direct communication over the local network.

## Use Cases
[comment]: <> (Stolen directly from the Core Home Connect integration)
- Monitor the multiple sensors of the appliance and trigger automations based on these sensors.
- Start programs on your appliances from your dashboard.
- Monitor the program status of the appliances.
- Control the light of your appliances.
- Adjust the appliance settings.

## Install the Integration

1. Go to the HACS -> Custom Repositories and add this repository as a Custom Repository [See HACS Documentation for help](https://hacs.xyz/docs/faq/custom_repositories/)

2. Click the button bellow and click 'Download' to install the Integration:

    [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=homeconnect_local_hass&owner=chris-mc1)

3. Restart Home Assistant.

## Supported Devices

Any Home Connect device that 
1. Allows a local connection (not all do) (View trouble shooting for more info to make sure your device supports a local connection)
2. On the same local network as your Home Assistant instance

## Prerequisites

To use this integration, you must first create a Home Connect account and connect your appliances.

## Setup

1. Use the [Home Connect Profile Downloader](https://github.com/bruestel/homeconnect-profile-downloader) to download your Appliance profiles, select "openHAB" as target. The downloaded ZIP-file contains each Appliance encryption Key and feature descriptions
2. Click the button below or use "Add Integration" in Home Assistant and select "Home Connect Local".

    [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=homeconnect_ws)

3. Upload the downloaded Profile file.
4. Select the Appliance you want to setup.
5. When the initial connection to the Appliance fails, your asked to manually enter your Appliance IP-Address.
6. Repeat from Step 2 if you want to setup more than one Appliances.

> [!IMPORTANT]
> Do <ins> **NOT**</ins> delete your Home Connect account after this. If you do then
> 
> - The device may disconnect itself from your Wi-Fi
> - You cannot troubleshoot if the appliance does not connect to Home Assistant
> - You cannot connect any more devices to it
>
> If you value your privacy you can instead go to the app settings an disable all the data collection stuff in the "Privacy and Legal" section of the app

### Configuration parameters

- Profile file: The Profile File you've downloaded with the [Home Connect Profile Downloader](https://github.com/bruestel/homeconnect-profile-downloader)
- Select Appliance: Select the Appliance you want to setup
- Host / IP-Address: Manually enter your Appliance Hostname or IP-Address if auto discovery did not work

### Protip!

If you want to, once you have connected the appliance to Home Assistant you can disable its cloud access.

1. Open the Home Connect app and go to your appliance's settings.
2. Scroll down until you get the "network" and tap the details button.
3. (OPTIONAL) Make sure the bottom line (direct connection between your phone and device is green in case if something goes wrong.
4. Scroll down (again) until you see the connection to the server toggle.
5. Turn off the toggle and ignore the scare screen (they have it there so they can continue collecting your data)
6. Then save

You'll know if you have successfully done it if you see the line between your appliance and their cloud is grayed out and disconnected.

>[!NOTE]
>Do note that your device will **not** get firmware updates once disconnected, if you want to, you can occasionally (once every 1-3 months) reenable the cloud connection for 1-2 days so the device can check for an update.

## Data Updates

This integration is soley pushed based with it reciving updates from the appliance the moment something happens to it. Post setup, this integration can work completely offline, unlike the Home Connect app.

## Supported Functions

The following entities are available. Which ones appear depends on the appliance type and its feature set — not every device supports every entity listed here.

### All Appliances

| Entity | Type | Description |
| --- | --- | --- |
| Active Program | Sensor | Currently running program |
| Operation State | Sensor | Device state (e.g. Ready, Running, Finished) |
| Remaining Program Time | Sensor | Time left in the current program |
| Program Progress | Sensor | Progress as a percentage |
| Start In | Sensor / Number | Delay before the program starts |
| Finish In | Sensor / Number | Target time until the program finishes |
| Select Program | Select | Choose a program to run |
| Start / Abort / Pause / Resume | Button | Control the active program |
| Power State | Switch / Select | Turn the appliance on or off |
| Child Lock | Switch | Lock the physical controls |
| Remote Start Allowed | Binary Sensor | Whether remote control is enabled on the device |
| Door State | Binary Sensor / Sensor | Whether the door is open or closed |
| Program Finished | Binary Sensor | Turns on when the current cycle completes |
| Wi-Fi Signal Strength | Sensor | Device's Wi-Fi signal strength |

### Dishwasher

Wash program selection and options (half load, hygiene plus, extra dry, extra rinse, speed-on-demand, silence-on-demand), FlexSpray zone configuration, rinse aid and salt level sensors, maintenance reminders (filter check, machine care, smart filter), water hardness and rinse aid dose settings.

### Washing Machine / Dryer

Program options including temperature, spin speed, prewash, rinse plus, gentle cycle, and hygienic steam; iDos automatic dosing (levels 1 & 2); drum light and door ring LED control (brightness and color mode); anti-wrinkle guard; maintenance reminders (drum clean, lint filter full); condensate container alert (dryer).

### Oven / Hob / Hood

Oven current and setpoint temperature, meat probe temperature, heating mode selection, fast preheat, sabbath mode; hood fan speed control, ambient and work lighting, automatic shutoff delay, interval ventilation, grease and carbon filter saturation sensors and one-tap reset buttons; hob ventilation level.

### Coffee Maker

Bean container and amount, grind coarseness, coffee strength, temperature, brew size, shot count, milk ratio; cup warmer; maintenance countdowns for cleaning, descaling, and water filter replacement; water tank and drip tray level sensors; per-drink brew counters (coffee, espresso, milk-based drinks, and more).

### Refrigerator / Freezer

Fridge, freezer, and chiller setpoint temperatures (°C and °F); door open and door alarm binary sensors; super-freeze and super-cool modes; eco, vacation, and fresh-food modes; interior light with brightness control; water filter alert.

## Actions

This integration provides the following actions:

- `homeconnect_ws.start_program`: Start the currently selected program. Optionally set a start delay and/or a target finish time.
- `homeconnect_ws.set_start_in`: Set the start delay of the currently selected program.
- `homeconnect_ws.set_finish_in`: Set the target finish time of the currently selected program.

## Automation examples

Get started with these automation examples

### Send a notification when the appliance ends the program
[comment]: <> (Also stolen directly from the Core Home Connect integration)
```yaml
alias: "Notify when program ends"
triggers:
  - trigger: state
    entity_id:
      - sensor.appliance_operation_state
    to: finished
actions:
  - action: notify.notify
    data:
      message: "The appliance has finished the program."
```


### Start a program when electricity is cheap
[comment]: <> ( Also also stolen directly from the Core Home Connect integration)
Because electricity is typically cheaper at night, this automation will activate the silent mode when starting the program at night.

```yaml
alias: "Start program when electricity is cheap"
triggers:
  - trigger: state
    entity_id: sensor.electricity_price
    to: "0.10"
conditions:
  - condition: state
    entity_id: sensor.diswasher_door
    state: closed
actions:
  - if:
      - condition: time
        after: '22:00:00'
        before: '06:00:00'
    then:
      - action: home_connect.set_program_and_options
        data:
          device_id: "your_device_id"
          affects_to: "active_program"
          program: "dishcare_dishwasher_program_eco_50"
          dishcare_dishwasher_option_silence_on_demand: true
    else:
      - action: home_connect.set_program_and_options
        data:
          device_id: "your_device_id"
          affects_to: "active_program"
          program: "dishcare_dishwasher_program_eco_50"
```

## Known Limitations

- While this integration can (in theory) support all the functions supported in the Home Connect app, in reality, the functions have to reverse engineered
- The mDNS on Home Connect devices is wonky and fail to connect. The best example of this is that in the App, unless if the phone is on the same Wireless Access Point as the appliance theres a chance a local connection may fail to establish.
- Home Assistant may overload the device's local capacity causing it to not accept new connections for 24 hours. This is called a **Websocket Shutdown**.
- The Appliance must be online and reachable on your local network during initial setup. The config flow actively tests the connection before letting you finish adding the device, so it cannot be added while powered off or unreachable. Once added, the appliance can go offline/online freely and its entities will simply go unavailable and recover automatically. See issues (https://github.com/chris-mc1/homeconnect_local_hass/issues/274 and https://github.com/chris-mc1/homeconnect_local_hass/issues/293 for info about why it is like this.

## Trouble Shooting

### Home Assistant cannot connect to my Appliance, what should I do?
If Home Assistant cannot connect to your appliance (during setup) despite correctly entering the right profile file and ip address here are some tips
- Try to see if Home connect can establish a local connection on the same network as Home Assistant
- To do this Open the Home Connect App go to you appliance(s), then to it's settings, then scroll down to the network section
   - If you see the bottom line lit up green then this could mean two things.
         1. You have the wrong/outdated profile file, make sure you have the correct file and if it's outdated get a new one.
         2. As noted in the known limiations the mDNS on the device is wonky, and if mDNS fails, even a direct IP connection may fail.
   - If you dont see the bottom line lit up green then this could mean two things.
         1. If you're on the same wireless access point as the device then your device is most likely offline or does not support a local connection.
         2. If you're not on the same wireless access point then make sure you are.
         3. If the device may be offline check it physically to see if theres no wifi signal indicator on it.
         4. If the device does have a wifi signal then Home Assistant may have overloaded the device's local capacity causing a websocket shutdown, see below on how to resolve it.

### How to resolve a websocket shutdown
[comment]: <> (I do not know the exact causes of a websocket shutdown nor do I know why these tricks fix it, but when I [@vemboy200] asked Gemini about it gave a pretty good theory about it. It said that the device can only accept a certain number of unique users, and that if theres too many it will stop accepting new ones. However when no users are connected to the appliance for 24 hours, the appliance runs some kind of internal cleaning cycle that clear all these unique users and starts accepting new ones. I think what Gemini has said so far seems to be lining up with my experience, however the websocket shutdown only seems to happen my Thermador Oven [PRG486WDH] and Freezer[T36IF905SP], but not [as in ive never seen it happen] my Dishwasher [DWHD660WFP]. Right before Home Assistant gives me connection error [which happen next restart of Home Assistant or a reload of the config entry], the Home Connect App always fails to establish a local connection with the appliance, showing that Gemini's theory makes sense.

Update: looked into this further. The "inject websession" Platinum rule isn't the cause — that's about sharing Home Assistant's aiohttp ClientSession for resource tracking, not about how many websocket connections reach the appliance or whether they're closed cleanly. What was actually missing: this integration never closed its connection to the appliance on a full Home Assistant restart (only on a manual reload/disable of the config entry), so every HA restart could leave a half-dead connection sitting in the appliance's connection table instead of a clean close. Premium appliances with cheap WiFi chips (small connection tables) would hit that limit fastest, which matches what I'm seeing. Added a Home Assistant shutdown listener in 1.0.6 to close the connection cleanly on every HA stop, not just on entry unload. Leaving the workarounds below in place until this is confirmed to actually fix it in practice.)
There are 3 ways to resolve a websocket shutdown
1. Disable the cloud: Disabling the cloud (follow the Protip section on how to do it), then waiting 24 hours, can allow the device to reopen it's local websocket. Do note that since you're doing this during a local websocket shutdown, the smart features of the device will be inoperable until the device reopens it's websocket. The device will still stay connected to your Wi-Fi
2. Power cycle the appliance: Cutting the power from your appliance for 1-5 minutes then reappling it can help resolve the issue.
3. Repair the apppliance (not recommended): Reseting the device's network settings and repairing to the Home Connect App resolves the issue. However doing that is not only time consuming, but also you have to get a new profile file, and remove the entry and readd it with teh new file.
     
###  Reporting Issues and Bugs

- A full debug log of at least reloading the config entry and any actions leading to an error
- The [Diagnostics](https://www.home-assistant.io/docs/configuration/troubleshooting/#download-diagnostics) of the Config Entry
- For reports relating to adding a new Appliance: the `*_DeviceDescription.xml` and `*_FeatureMapping.xml` files from the Profile File

### Enabling debug logging

Use one of these two methods enable debug logging:

- Through the UI:
    1. [Enable Debug logging](<https://www.home-assistant.io/docs/configuration/troubleshooting>) on the detail page of the integration
    2. Reload the config entry
    3. Perform the actions that lead to an error
    4. [Disable Debug logging](https://www.home-assistant.io/docs/configuration/troubleshooting/#disable-debug-logging-and-download-logs) on the detail page of the integration

- OR -

- Through configuration.yaml:
    1. Add the following to your [configuration.yaml](https://www.home-assistant.io/docs/configuration/) file:

        ```yaml
        logger:
        logs:
            custom_components.homeconnect_ws: debug # Home Connect Local Integration
            homeconnect_ws: debug
            homeconnect_websocket: debug # Homeconnect websocket Python package
        ```

    2. Restart Home Assistant
    3. Perform the actions that lead to an error
    4. Click the button below or navigate to "Settings" -> "Logs".

        [![Open your Home Assistant instance and show your Home Assistant logs.](https://my.home-assistant.io/badges/logs.svg)](https://my.home-assistant.io/redirect/logs/?)

    5. Download the log file using download button on the left

## Integration Removal

This integration follows standard integration removal, no extra steps are required.
1. Select the Config entry you want to delete
2. Click the 3 dots in the top right of the entry
3. Click the delete button
