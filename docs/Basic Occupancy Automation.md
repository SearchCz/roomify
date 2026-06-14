# Basic Occupancy Automation

This feature empowers Roomify to adjust room lighting based on occupancy. Again, after enabling this feature in the plugin, you can pick and choose the rooms in which this feature applies. You then select the devices that signal occupancy, the brightness you want in that room when occupied, and the duration for that lighting (in minutes), and thats it. You can even select multiple devices to signal occupancy. 

For example, consider my home offic. It has an interior entryway plus a door to the exterior of the home. I designate both the motion sensor AND the door open/close sensor as occupancy signals. My office automations begin whenever someone triggers motion by walking through the interior entryway OR should someone open the exterior door to enter from outside. 

BONUS: that exterior door can ALSO be included among the occupancy signals for the exterior space outside the office, so that lighting in that space can be activated in a way appropriate to that exterior space as someone leaves the home through the office door.

No sensors? No problem. Because you can ALSO use Indigo Triggers and Action Groups to inform Roomify when any rooms’ occupancy begins or ends. Or use a smart light that you control as the occupancy indicator for the remaining lights in the room, as if it was a sensor. 



## Step 1: Enable in The Plugin

![[Occuancy Automation Enabled.jpeg]]  

Just check the box that says “Enable Occupancy Triggered Automations”. When you like, you can adjust the remaining automations settings which are covered in detail in the [[Advanced Lighting Options]] and [[Advnaced Occupancy Signals & Permissions]] documentation.

This feature enables Roomify control over room lighting based on occupancy, including terminating lighting whenever a room is determined to be vacant. 

### Permission to Automate is Required

Automations will run only when ALL necessary conditions are met. Specifically:

1. Automatons must be ENABLED in the Indigo plugin configurator.
2. Automations must be ACTIVATED in the Indigo room configuration.
3. Automations must be AUTHORIZED by the transient conditions in the room. Roomify has the ability to suspend and resume automation control whenever it appears that a person or some other automation has taken control of a room.
4. Option gating device(s) specified in a room configuration must be ON. 

Only then will signs of occupancy initiate lighting.

## Step 2: Activate Automations in The Room 

  ![[Room Automation Enabled.jpeg]]

Now check the box that says “Activate” under “Occupancy-Triggered Automations”. This is how Roomily knows which rooms are to be automated. All thats left to do is:

  
2a) Identify the devices that signal occupancy in this room. Motion sensor, occupancy sensors and open/close sensors are typical choices. 

2b) Pick the desired brightness for this room. (In basic modes, this will be the only brightness rendered).

2c) Pick the lighting duration in minutes. This is how long the lights will remain on after no signs of occupancy are present. 

Once you save the room, automation begins.

## See Also:

[[Advanced Lighting Options]]

[[Advnaced Occupancy Signals & Permissions]]

