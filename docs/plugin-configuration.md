Configuring Roomify

Before creating rooms, take a few moments to configure Roomify’s global preferences.

These settings establish the default behavior for newly created rooms and enable optional Roomify features.

Most settings can be adjusted later, so don’t worry about getting everything perfect the first time.

<img src=plugin-configuration.png>
⸻

Room Dormancy Cutoff

Room Dormancy Cutoffs enforce a maximum duration for unchanged lighting.

This feature exists to correct situations where lights have been left on longer than intended, regardless of how that state occurred.

Examples include:

* A person forgets to turn lights off
* An automation fails to complete
* A manual override is never restored

Enable Room Dormancy Cutoff

Enables dormancy protection globally.

When enabled, newly created rooms may optionally participate in dormancy management.

Default Duration

Specifies the default dormancy cutoff applied to new rooms.

This value can be customized on a room-by-room basis.

⸻

Occupancy-Triggered Automations

Occupancy automation allows Roomify to adjust room lighting in response to occupancy changes.

Enable Occupancy-Triggered Automations

Enables occupancy-based room automation throughout Roomify.

When disabled, rooms may still be controlled manually through their Roomify room devices.

Default Occupancy Grace Period

Determines how long Roomify waits after occupancy is lost before considering a room vacant.

This delay helps prevent unwanted lighting changes caused by brief sensor dropouts or temporary departures.

Enable 3-Phase Lighting

Allows rooms to define multiple lighting phases that occur over time.

For example:

* Initial arrival lighting
* Sustained occupancy lighting
* Extended occupancy lighting

This feature enables lighting that adapts as occupancy duration increases.

⸻

Automatic Authority Standby and Recovery

Authority Standby and Recovery allows Roomify to coexist gracefully with manual control and external automation systems.

Automatic Authority Standby and Recovery

When enabled, Roomify monitors participating devices for changes that appear inconsistent with Roomify intent.

When such changes occur, Roomify may temporarily suspend automation for the affected room.

Authority is automatically restored when the room returns to an idle state.

Automation Calming Allowance

Specifies the amount of time Roomify allows for automation instructions to settle before evaluating resulting device state changes.

This helps prevent normal device reporting delays from being interpreted as disruption.

⸻

House Modes

House Modes allow Roomify to adapt room behavior to changing expectations throughout the day.

Examples include:

* Day
* Evening
* Night
* Sleep

House Modes act as a policy layer that influences how room lighting preferences are interpreted.

Enable House Modes

Enables House Mode support throughout Roomify.

Default House Mode @ Startup

Determines the House Mode used when Roomify starts.

This setting provides a known initial operating state.

⸻

Observer Device

The Observer Device provides visibility into Roomify-wide state.

Unlike room devices, which represent individual spaces, the Observer represents the Roomify system itself.

Create Observer Device in Indigo Device List

Creates a read-only Indigo device that publishes Roomify runtime information.

Examples may include:

* Current House Mode
* Last publish timestamp
* Diagnostic information

The Observer is particularly useful for Control Pages, scripts, triggers, and troubleshooting.

⸻

Logging

Roomify provides several optional logging categories.

Most users should begin with Error Logging enabled and additional logging disabled.

Additional logging can be enabled when troubleshooting specific behaviors.

Available categories include:

* Verbose Logging
* Heartbeat Logging
* Device Event Logging
* Automation Decision Logging
* Authority Decision Logging
* Error Logging

⸻

Recommended First-Time Settings

For most installations, the default settings are a good starting point.

Recommended configuration:

✓ Room Dormancy Cutoff

✓ Occupancy-Triggered Automations

✓ Automatic Authority Standby and Recovery

✓ House Modes

✓ Observer Device

✓ Error Logging

Once Roomify is operating successfully, additional features can be enabled and refined as desired.
