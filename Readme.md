## Smart Rooms. Adaptive Lighting.

<p align="center">
  <img src="docs/RoomifyImage.png" width="600">
</p>

<p align="center">
  Room-centric automation for Indigo
</p>

Roomify introduces room-level intelligence to Indigo by treating rooms as first-class automation entities.

A room is more than a collection of lights, sensors, switches, and conditions. It is a living space with occupancy, activity, authority, context, and behavior. Roomify continuously evaluates the devices assigned to each room and maintains a coherent model of what is happening within that space.

By elevating rooms to first-class entities, Roomify enables automations that think in terms of spaces rather than individual devices.

⸻

## Why Roomify?

Indigo provides powerful automation capabilities and excellent support for devices.

But most automations ultimately attempt to answer a larger question:

What is happening in this room?

A room may contain multiple lights, occupancy sensors, contact sensors, switches, virtual devices, environmental sensors, and automation rules.

Traditionally, every automation must interpret those signals independently.

***Roomify centralizes that responsibility.***

Instead of repeatedly reasoning about individual devices, automations can reason about the room itself.

A Roomify room understands:

* Whether it is occupied

* Whether it is active

* Whether automations currently have authority

* Which devices belong to the room

* What lighting state should exist

* Whether occupancy should trigger automation

* Whether lighting should be sustained, reduced, or extinguished

The room itself becomes the automation object.

⸻

## Core Concepts

### Rooms

A Roomify room represents a physical space.

Each room maintains its own derived state based on the devices assigned to it and the automation rules configured for it.

Roomify continuously evaluates those inputs and updates the room’s understanding of occupancy, activity, authority, and lighting conditions.

### Occupancy

Occupancy may be determined using one or more occupancy indicator devices. (You can ALSO declare occupancy explicitly through Indigo methods.)

Additional authority devices may be used to explicitly sustain occupancy or immediately terminate occupancy when desired.

This allows rooms to support a wide range of occupancy strategies, from simple motion detection to more advanced occupancy models.

### Adaptive Lighting

Roomify supports multi-stage lighting automation.

Rather than immediately transitioning from ON to OFF, rooms may progress through multiple lighting phases:

1. Initial Lighting

2. Delayed Lighting

3. Outro Lighting

Occupancy signals can restore a room to its initial state at any time.

This approach allows lighting to gradually adapt to changing activity levels without abruptly removing useful illumination.

### Automation Authority

Automation should be helpful, not stubborn.

When enabled, Roomify monitors for lighting changes that conflict with its automated intent.

Such changes may indicate that an occupant wishes to override automation.

In those situations Roomify can automatically suspend automation authority and allow occupants full control of the room.

When the room eventually becomes vacant and inactive, automation authority can be automatically restored.

### Dormancy Protection

Dormancy protection helps prevent lights from remaining active indefinitely.

Rooms may be configured with maximum active durations, allowing Roomify to gracefully recover from forgotten lights, abandoned spaces, and other situations where lighting would otherwise remain active longer than intended.

### Room Types

Not all rooms should behave the same way.

A stairway, hallway, garage, bedroom, and media room each have different lighting expectations.

Room types establish practical operating boundaries that influence automated lighting behavior while preserving the intended purpose of each space.

### House Modes

Optional house modes can influence automated brightness decisions throughout the home.

Different modes may increase or decrease target brightness levels to better reflect the current context of the household.

Examples include:

* Morning

* Day

* Evening

* Night

* Quiet

* Cleaning

* Bedtime

* Sleep

  
Room types and house modes work together to produce lighting that feels appropriate for both the space and the moment.

### Roomify Observer

An optional device to provide you with visibility to Roomify plugin properties ... hose mode in particular. Availabe for anyone who might find that information useful. Not required by Roomify in any way.

⸻

## Typical Use Cases

* Occupancy-driven lighting

* Hallway and stairway automation

* Bedroom night lighting

* Closet automation

* Utility room automation

* Context-aware lighting

* Automation standby and recovery

* Whole-home lighting consistency

⸻
  
## Design Philosophy


Roomify is intentionally opinionated.

It does not attempt to expose every possible automation primitive.

Instead, it provides a framework for understanding rooms as people actually experience them.

Rooms are occupied or vacant.

Active or dormant.

Automated or manually controlled.

Bright or dim.

Roomify models those realities directly and uses them to guide automation decisions.

**The goal is simple:**

Make automations easier to build by introducing a room-centric automation model in Indigo.

Roomify defines a “Room” as a self-contained automation context that encapsulates state, rules, and coordination logic.

It organizes the devices subject to control within a room, the signals that indicate occupancy or vacancy, and the logic that determines how those signals are interpreted over time within that space.

You provide the intent; Roomify handles the interpretation, state management, and coordination.

⸻

## Requirements

* Indigo Home Automation Server

* Compatible lighting devices

* Compatible occupancy indicators

* A desire to automate spaces rather than individual devices

⸻

## Status

Roomify is an active project and will continue to evolve as new ideas and real-world experience shape its development.

Feedback, suggestions, bug reports, and contributions are welcome.

⸻

## Documentation Set

1. [[Overview]]
2. [[Getting Started]]
3. [[Automating Your Rooms]]
4. [[Room Dormancy Cutoff]]
5. [[Basic Occupancy Automation]]
6. [[Advnaced Occupancy Signals & Permissions]]
7. [[Advanced Lighting Options]]

