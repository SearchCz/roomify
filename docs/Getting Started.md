# Getting Started with Roomify

## Welcome to Roomify.

Roomify allows Indigo users to treat collections of devices as rooms and interact directly with the aggregate device directly, rather than managing every device individually. 

A Roomify room can be controlled like any other Indigo device, while also providing visibility into the aggregate state of all devices that belong to it.

The bonus?

**You do not need to configure any plugin options to get started.**

Roomify’s core function works immediately after installation. Optional automation susbsytems can be enabled whenever you like. 

  

## Step 1: Install the Plugin

Install Roomify like any other Indigo plugin.

Advanced features are available any time you want them, but they are disabled by default keeping device configuration as tidy as possible . If no advanced features are needed, no plugin configuration is required!

  

## Step 2: Create a Room

Create a new Indigo device using:

**Devices → New Device → Roomify → Room**

![](roomDefinitionBasic.jpeg)

### 2a) Select The Room Type  

This is initially used only to help organize room definitions, and provide clearer messaging in Indigo log files. It also factors into limiting the lighting changes Roomify makes when automations are enabled and active.

Examples:

- Living Room
- Kitchen
- Office
- Bedroom

### 2b) Add Devices

Select the controlled devices that belong to the room.

For example, a Living Room might include:

- Floor Lamp
- Table Lamp
- Ceiling Lights

Here’s my Office, for example.

  ![](office.png)

Once saved, Roomify immediately begins tracking the room.

### Step 3: Use the Room

Your new room behaves like an Indigo dimmer device.

You can:

- Turn the room on
- Turn the room off
- Set room brightness
- Trigger the room from Action Groups
- Use the room in Indigo Control Pages
- Expose the room to HomeKit
- Control the room using Siri  
    
Roomify automatically calculates and reports the room’s aggregate state based on its member devices.

**That’s It**

At this point Roomify is already useful, by providing:

- A single control point for multiple devices
- Aggregate room state reporting
- Simplified automation design
- A room-centric view of your home  

## Quick Tip #1

When getting started with Roomify, especially if you plan to enable the optional features, you may find it beneficial to limit your configuration to just one or two rooms in your smart home until you are comfortable with what the various settings do.

![](images/RoomifyLogo215.png)
### See Also:
[Automating Your Rooms](Automating%20Your%20Rooms.md)
[Device States](DeviceStates.md)
[Roomify Actions](Roomify%20Actions.md)