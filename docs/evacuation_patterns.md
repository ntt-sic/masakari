# Masakari's Evacuation Patterns

Masakari starts to evacuate VM instances basing on instance, process and/or
host failures monitored by each process. This documents describes patterns about
the evacuations executed by masakari-controller.

Each monitor notifies indivisual failures to controller based on what they
monitor. You can choose which falures of instances are rescued by Masakari,
deploying which monitoring process or not.

## Evacuation patterns

The section shows events that tigger Masakari to call which nova API.

| Events | Monitored by | Previous instance's status | Rescue steps | Post instance's status |
| :--- | :--- | :--- | :--- | :--- |
| instance down | instancemonitor | active | nova.stop -> nova.start | active |
| instance down | instancemonitor | stopped | nova.reset('stopped') | stopped |
| instance down | instancemonitor | resized | nova.reset('error') -> nova.stop -> nova.start | active |
| host down | hostmonitor | active | nova.evacuate | active |
| host down | hostmonitor | stopped | nova.evacuate | stopped |
| host down | hostmonitor | resized | nova.reset('error') -> nova.evacuate | active |

TBD: The table doesn't show all patterns for the evacuation now.
Feel free to fill it out :-)

## Detected Failures

The section describes what event monitored by Masakari's monitoring processes.

TBD