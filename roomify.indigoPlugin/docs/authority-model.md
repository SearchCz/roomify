Authority Management

Authority management is an optional Roomify feature that allows Roomify to coexist gracefully with manual control and external automation systems.

Roomify continuously monitors the state of participating devices.

When device behavior diverges from Roomify’s intended state, Roomify may determine that another actor has taken control of the room.

In these situations, Roomify can temporarily yield authority.

Authority States

Authority Granted

Roomify is permitted to execute automation decisions for the room.

Authority Yielded

Roomify temporarily suspends automation activity for the room, allowing manual adjustments or external automation systems to operate without interference.

Authority Recovery

Authority is automatically restored when the room reaches an inactive state.

In the default implementation, authority is restored when the room becomes both:

* Off
* Vacant

This creates a natural transition back into automated operation without requiring user intervention.

Key Principle

Roomify respects manual intent.

When someone takes control of a room, Roomify can step aside. When the room naturally returns to an idle state, Roomify resumes responsibility.