# Roomify Overview

## A Different Way to Think About Lighting

Most home automation systems focus on individual devices.

A lamp turns on.  
A switch turns off.  
A motion sensor detects movement.

But people rarely think about their homes that way.

We think in terms of rooms.

When you walk into a kitchen, you generally don’t care which particular lights should turn on. You care that the kitchen is appropriately lit.

When you leave a bedroom, you don’t think about turning off three lamps, a ceiling fixture, and an accent light individually. You think about leaving the bedroom.

Roomify is built around this idea.

Rather than treating each device as an independent automation target, Roomify allows you to define collections of devices as rooms and interact with those rooms as single entities.

## Rooms as First-Class Citizens

A Roomify room behaves like a standard Indigo device.

It can be:

- Turned on
- Turned off
- Dimmed
- Used in Action Groups
- Referenced in Triggers
- Displayed on Control Pages
- Exposed to HomeKit

At the same time, Roomify continuously monitors the devices that belong to the room and calculates an aggregate room state.

This allows the room itself to become a meaningful automation target.

## Start Simple

At its simplest, Roomify functions as a room abstraction layer.

Create a room.  
Assign devices to it.  
Use the room as a single control point.

No automation is required.  
No occupancy sensors are required.  
No plugin configuration is required.

Many users will find this capability useful all by itself.

## Automation Is Optional

Roomify can also automate room lighting when desired.

It can:

- Respond to signs of occupancy
- Respond to apparent vacancy
- Adjust lighting based on house conditions
- Gradually transition through multiple lighting phases
- Protect against forgotten lights

This is not traditional motion-activated lighting.

In traditional motion lighting, motion is often treated as the command: motion detected, light on.

Roomify treats motion differently.

Motion does not trigger lights directly. It signals possible occupancy. Other events, such as a door opening, may also signal occupancy.

That signal is sent to Roomify, where it becomes part of a decision process. Roomify considers the room, the current house mode, the room’s configuration, and the lighting rules you have chosen before deciding whether automation is appropriate.

Only then does Roomify calculate the correct lighting level and send instructions to the devices in the room.

These capabilities are entirely optional and can be enabled only where they are useful.

You decide which rooms participate and which features apply.

## Built to Cooperate

One of Roomify’s design goals is to cooperate with the people and automations already present in your home.

When Roomify is controlling a room, it continuously monitors the devices that belong to that room.

If a person, voice assistant, Indigo automation, HomeKit automation, or another system changes those devices, Roomify can recognize that another actor has taken control and temporarily yield control. . 

Roomify is designed to help manage your lighting, not fight over it.

## A Layered Approach

Roomify is intentionally designed so that complexity is optional.

You can begin with simple room definitions and stop there.

Or you can gradually enable additional capabilities as your needs evolve.

Whether you want a simple room abstraction, protection against forgotten lights, occupancy-driven automation, or a sophisticated room-aware lighting system, Roomify allows you to adopt only the features that make sense for your home.

The goal is not to replace the automations you already have. 

The goal is to make rooms first-class participants in your smart home.

[[Getting Started]]