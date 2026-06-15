# Home Connect Local

The **Home Connect Local** allows users to integrate their home appliances supporting the  [Home Connect](https://www.home-connect.com/global) standard for Bosch and Siemens using direct communication over the local network.

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

You'll know if you have successfully done it if you see the line between your appliance and their cloud grayed out and disconnected.
>[!NOTE]
>Do note that your device will **not** get firmware updates once disconnected, if you want to, you can occasionally (once every 1-3 months) reenable the cloud connection for 1-2 days so the device can check for an update.

## Actions

This integration provides the following actions:

- `homeconnect_ws.start_program`: Start the currently selected program. Optionally set a start delay and/or a target finish time.
- `homeconnect_ws.set_start_in`: Set the start delay of the currently selected program.
- `homeconnect_ws.set_finish_in`: Set the target finish time of the currently selected program.

## Known Limitations

- While this integration can (in theory) support all the functions supported in the Home Connect app, in reality, the functions have to reverse engineered
- The mDNS on Home Connect devices is wonky and fail to connect. The best example of this is that in the App, unless if I'm on the same Wireless Access Point as the device theres a chance a local connection may fail to establish.
- Home Assistant may overload the device's local capacity causing it to not accept new connections for 24 hours.

## Trouble Shooting

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
         4. If the device does have a wifi signal then Home Assistant may have overloaded the device's local capacity causing it to not accept new connections for 24 hours. Check back in 24 hours to see if the signal relights up.

 If you recieve an error related to the device not accepting commands then this could mean.
 - Depending on what device you have remote start or remote control may not be enabled.
 - You cannot perform that action right now.
       


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
