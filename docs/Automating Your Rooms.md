# Automating Your Rooms

Roomify automates lighting by responding to signals and events that occur within a room.

At its simplest, Roomify performs three jobs:

## Turning Lights On

When permitted, occupancy signals can cause Roomify to activate room lighting.

Examples of occupancy signals include:

- Motion sensors
- Door sensors
- Virtual occupancy devices
- Indigo triggers and actions

You define the signals and the lighting result you want.

## Turning Lights Off

When permitted, Roomify can determine that a room appears vacant and return the room to its inactive state.

This decision is typically based on an absence of occupancy signals over a period of time.

The resulting inactive state may be complete darkness or a reduced lighting level, depending on how the room is configured.

## Recovering From Mistakes

People forget.

Automations fail.

Sensors become unreliable.

For that reason, Roomify optionally provides Dormancy Cutoff.

Dormancy Cutoff acts independently of occupancy and serves as a final safeguard against rooms remaining active indefinitely.

If a room exceeds its configured dormancy limit, Roomify returns it to its inactive state.

————————————————————————

The model above is intentionally simple. Roomify also supports advanced controls governing how occupancy is interpreted, when automations are allowed to act, and how lighting is rendered.

### Your First Optional Feature: Dormancy Management ?

If you’re curious about Roomify’s automation capabilities but want to start with something simple, Dormancy Management is a good place to begin. It requires minimal configuration and simply ensures that rooms are not accidentally left on indefinitely.

[[Room Dormancy Cutoff]]

See Also

[[Basic Occupancy Automation]]