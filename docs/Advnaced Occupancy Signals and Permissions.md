# Advanced Occupancy Signals & Permissions

In each Roomify room, there are several advanced options for signalling when occupancy begins, ends and is permitted to invoke lighting. These are all revealed by checking “Show Advanced Settings” in the room configurations. (You may need to expand or scroll the window to see the advanced settings).

![[images/officeConfigFullScreen.png]]



The advanced settings allow you to set:

## 1) Occupancy Authority

For rooms that offer a signal that indicates continued occupancy, you can specify a single Occupancy Authority device. Once selected, an ON from this device tells Roomify to tell treat the room as occupied without regard to the passing of time. ( The Room Dormancy Cuttoff subsystem, if activated, prevent a sustained ON from keeping the room lit forever. )
## 2) Vacancy Authority

Occupancy and vacancy are both inferences. We can begin to treat a room as “occupied” with high confidence (but not absolute certainty) whenever a fresh occupancy signal arrives for that room. But vacancy is rarely this deterministic, so we usually rely on the absence of occupancy signals over a span of time to infer vacancy.

But sometimes a room offers a signal that can be treated as authoritative, and processed with maximum confidence that the room has been vacated. For example, consider a lighted closet that isn’t ever really “occupied” and needs no light when the door is closed. 

For situations like this, Roomify accommodates a single Vacancy Authority. A fresh OFF signal from such a device tells Roomify to classify the room as unoccupied and adjust the lighting accordingly - if currently permitted to do so.

## 3) Permission to Automate

**Roomify automations only act when Roomify considers itself permitted to do so.** 

In Roomify, that means that automations must be:

- ENABLED in the plugin
- ACTIVATED in the room
- AUTHORIZED by transient conditions

But imagine a space where you want Roomify to have automate, but only *sometimes*. Maybe you want automations only at night. Or only when you are home. Or only if you are not in bed. For any rooms like this, you can identify device(s) that must be ON in order for Roomify automations to execute. 

### Gating Device(s)  
As long as you FIRST configure an Indigo device (or virtual device) that uses its ON state to indicate a permissive state, you can use that device as the final permission “gate” in Roomify automations.  

**IMPORTANT NOTE: Room Dormancy Cutoff doesn’t care about gating devices. When the time is up, the room turns off.** 


## A Note About Permission to Automate

Roomify is not meant to replace the scenes or automations you already enjoy. It is internally built to cooperate with all other lighting choices. 

When Roomify detects that a person, voice assistant, Indigo automation, HomeKit automation, or another system has changed a controlled device, Roomify treats that change as evidence that another actor has taken control of the room. To avoid competing with that actor, Roomify temporarily surrenders automation authority, resuming authority after a disrupted room settles into an OFF and vacant state. 

If you should prefer that Roomify hold on to authority regardless of disruptions, just de-select “Automatic Authority Standby and Recovery” in the plugin configuration. Thereafter, you can still suspend and resume automation authority per room using Indigo triggers and action groups, but Roomify will no longer surrender and resume that authority autonomously.

## Footnote:

These mechanisms all exist so that Roomify can make better decisions about when and whether occupancy signals should initiative actions. The goal is to automate only when Bothe permission to act and signs of occupancy are sufficient.

## See Also:

[Advnaced Lighting Options](Advnaced%20Lighting%20Options.md)
