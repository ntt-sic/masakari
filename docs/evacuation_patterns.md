# Masakari's Evacuation Patterns

Masakari starts to evacuate VM instances basing on instance, process and/or
host failures monitored by each process. This documents describes evacuation
patterns executed by masakari-controller.

Each monitoring process notifies indivisual failures to controller based on
what they monitor.
You can choose which kind of failure are rescued by deploying each monitoring
process or not.

## Evacuation patterns

The section shows events that trigger Masakari to call nova API and evacuation patterns
based on the events.
Conditions when the monitoring processes send an event is listed in Detected Failure section.

| Events Types | Monitored by | Previous instance's status | Rescue steps | Post instance's status |
| :--- | :--- | :--- | :--- | :--- |
| instance down | instancemonitor | active | nova.stop -> nova.start | active |
| instance down | instancemonitor | stopped *1 | nova.reset('stopped') | stopped |
| instance down | instancemonitor | resized | nova.reset('error') -> nova.stop -> nova.start | active |
| process down | processmonitor | - *2 | nova.service-disable | - |
| host down | hostmonitor | active | nova.evacuate | active |
| host down | hostmonitor | stopped | nova.evacuate | stopped |
| host down | hostmonitor | resized | nova.reset('error') -> nova.evacuate | active |

*1 Ideally speaking, stopped instances don't exist on hosts, so instancemonitor can't send it.
However, it could happen in some race conditions, so Masakari implements the pattern.

*2 When process down occurs, masakari doesn't change instance status.
It just changes nova-compute status to disable status not to schedule new instance onto the host.

## Detected Failures

The section describes Masakari's processes monitor what failures.

| Monitoring Processes | Failures | Related Event Types |
| :--- | :--- | :--- |
| instancemonitor | VM instance process crash or killing a VM instance | instance down |
| processmonitor | monitored process goes down and unable to restart it | process down |
| hostmonitor | host status in pacemaker is changed to OFFLINE or RemoteOFFLINE | host down |
