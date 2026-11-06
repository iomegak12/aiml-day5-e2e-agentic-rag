---
kb_id: "KB-NET-1006"
title: "Troubleshooting BFD Tunnel Flaps (NCS-BFD-3004)"
domain: "networking"
article_type: "runbook"
product: "NetCore SD-WAN"
version: "5.0"
status: "current"
superseded_by: ""
last_updated: "2026-06-15"
error_codes: ["NCS-BFD-3004", "NCS-BFD-3005"]
related: ["KB-NET-1005", "KB-NET-1008"]
tags: ["troubleshooting", "bfd", "tunnels"]
author: "NetCore Systems Technical Support"
format: "md"
---

# Troubleshooting BFD Tunnel Flaps (NCS-BFD-3004)

**KB-NET-1006** | NetCore SD-WAN 5.0 | Last updated: 2026-06-15 | Status: current

## Summary

This runbook covers diagnosis and remediation for flapping NetCore SD-WAN BFD sessions that raise NCS-BFD-3004 BFD Session Flap and may progress to NCS-BFD-3005 BFD Session Down. It includes symptom checks, command examples, probable causes, corrective actions for timers, MTU/NAT, and transport-provider escalation, plus how BFD instability affects SLA measurement and related NCS-SLA-2001 handling.

**Applies to:** NetCore SD-WAN 5.0, NetCore Orchestrator management plane, NCX-1000 branch edge, NCX-4000 regional hub edge, NCX-9000 data center edge, MPLS, Internet broadband, and LTE/5G transports

## Symptoms

Use this runbook when NetCore Orchestrator reports NCS-BFD-3004 BFD Session Flap for one or more SD-WAN tunnel peers. If the BFD session remains down after repeated flap events, Orchestrator may also raise NCS-BFD-3005 BFD Session Down.

Typical operator-visible symptoms include intermittent path failover, short application brownouts, repeated tunnel state changes, and SLA graphs showing gaps or sudden latency/loss spikes. In release 5.0, affected sites may also generate NCS-SLA-2001 SLA Violation Detected if the degraded path remains noncompliant for 3 consecutive app-route polling intervals of 120 seconds, approximately 6 minutes. When the SLA recovers, NCS-SLA-2002 SLA Restored is generated.

Adjacent alarms can help scope the event. NCS-QOS-5002 Queue Drop Threshold Exceeded can indicate congestion-driven loss, NCS-ORC-6001 Orchestrator Control Connection Lost can indicate a management/control-plane reachability issue, and ZTP alarms such as NCS-ZTP-4001 ZTP Redirect Failed or NCS-ZTP-4003 Device Certificate Validation Failed are not BFD tunnel flap causes but are listed in the alarm reference. For the complete code catalog, see KB-NET-1008.

- Orchestrator alarm: NCS-BFD-3004 BFD Session Flap.
- Possible follow-on alarm: NCS-BFD-3005 BFD Session Down.
- Possible related SLA alarm: NCS-SLA-2001 SLA Violation Detected; see KB-NET-1005.
- User impact: packet loss, voice clipping, video freezes, TCP retransmissions, or automatic path failover.
- Common scope patterns: single tunnel, single transport, all tunnels on one interface, or multiple sites sharing the same upstream transport.

## Impact

BFD is used to monitor SD-WAN tunnels over MPLS, Internet broadband, and LTE/5G transports. When BFD flaps, the edge can temporarily withdraw the affected tunnel from forwarding decisions and select the best compliant transport that remains available.

BFD instability can affect SLA measurement in two ways. First, down or flapping tunnels can produce missing or invalid samples for the affected path. Second, packet loss during flap windows can push latency, jitter, or loss above the SLA class threshold. In NetCore SD-WAN 5.0, SLA breach detection uses an app-route poll interval of 120 seconds with multiplier 3, so NCS-SLA-2001 is declared after 3 consecutive failing intervals, approximately 6 minutes. The event is Sev3 on breach, auto-escalates to Sev2 if the breach persists longer than 15 minutes, and becomes Sev1 if it persists longer than 30 minutes or 5 or more sites are affected. An ITSM ticket is automatically created.

Do not confuse BFD flap detection with application SLA breach declaration. NCS-BFD-3004 can occur immediately when a tunnel loses BFD continuity, while NCS-SLA-2001 depends on the SLA class thresholds and the 3-interval release 5.0 breach policy.

- Voice SLA: latency <= 150 ms, jitter <= 30 ms, loss <= 1%.
- Video SLA: latency <= 200 ms, jitter <= 40 ms, loss <= 2%.
- Business-Critical SLA: latency <= 250 ms, jitter <= 50 ms, loss <= 3%.
- Best-Effort SLA: latency <= 400 ms, jitter not applicable, loss <= 5%.

## Probable Causes

Start by identifying whether the flap is isolated to one tunnel, one transport, one interface, or many sites. The failure domain usually points to the root cause faster than the alarm text alone.

The table below maps common causes to confirming evidence and the first corrective action.

*Cause-to-action matrix for NCS-BFD-3004 and NCS-BFD-3005*

| Probable cause | Evidence to confirm | Recommended action |
|---|---|---|
| Transport packet loss or micro-outage | BFD last-down reason shows timeout; app-route loss spikes; multiple tunnels on same transport flap | Open a transport-provider ticket with timestamps, peer IPs, loss percentage, and BFD flap count; keep automatic failover enabled |
| Physical interface errors | CRC, input errors, drops, or carrier transitions increase on the WAN interface | Replace cable/optic, correct speed/duplex if manually set, move to known-good port, or dispatch field services |
| MTU or fragmentation issue | Small probes pass but larger tunnel packets fail; drops appear after path change; symptoms affect one Internet or LTE/5G path | Set tunnel MTU to a value that passes end-to-end testing; avoid fragmentation for encapsulated SD-WAN traffic |
| NAT idle timeout or state reset | Flaps occur at regular intervals; Internet broadband tunnel affected; control connection remains stable | Adjust upstream NAT session timeout or enable/verify periodic keepalive behavior on the edge path |
| Over-aggressive BFD timers for unstable access circuit | Low latency most of the time but sporadic jitter/loss; flap count rises during congestion windows | Tune BFD hello interval and multiplier for that transport class after confirming no physical fault |
| Congestion or QoS drops | NCS-QOS-5002 Queue Drop Threshold Exceeded; WAN egress queue drops increase; SLA loss/jitter exceeds class thresholds | Correct QoS shaping, reduce oversubscription, or increase access bandwidth |
| Remote edge or hub issue | Many branches flap to the same NCX-4000 or NCX-9000 peer at the same time | Check hub health, interface counters, control connections, and recent policy changes; escalate as shared-infrastructure event |

## Diagnostic Steps

Perform the following steps from the affected edge first, then compare with the remote peer. Capture command output with timestamps before making changes. The examples below use an NCX-1000 branch edge with Internet broadband on ge0/0 and MPLS on ge0/1.

Step 1: Confirm BFD state, flap count, last-down reason, and the affected transport. Look for sessions repeatedly moving between Up and Down, short uptimes, or a recent transition reason of Detect Timer Expired.

Step 2: Confirm whether app-route SLA measurements are also failing. If NCS-SLA-2001 is active, follow KB-NET-1005 after stabilizing BFD.

Step 3: Check control-plane stability. If control connections are also down, investigate management reachability and NCS-ORC-6001 before treating the issue as only a data-plane tunnel flap.

Step 4: Check WAN interface counters. Interface errors increasing at the same time as BFD flaps usually indicate a local physical or access circuit issue.

Step 5: Check QoS queue drops and congestion. Queue drops can mimic transport loss and destabilize BFD on oversubscribed paths.

Step 6: Validate MTU/NAT behavior. If BFD stays up for short intervals and fails during larger packet transfers or at regular idle intervals, test tunnel MTU and upstream NAT state behavior.

```text
ncx-edge# show sdwan bfd sessions
Generated: 2026-03-14T09:22:18Z

Peer System IP  Site     Transport   Local Intf  State  Uptime    Flaps  Last Change          Last Down Reason
10.40.0.11      DC-01    MPLS        ge0/1       Up     12d04h    0      2026-03-02T05:11:04Z -
10.40.0.11      DC-01    Internet    ge0/0       Up     00:01:42  18     2026-03-14T09:20:36Z Detect Timer Expired
10.50.0.21      HUB-02   Internet    ge0/0       Down   00:00:00  23     2026-03-14T09:21:51Z Detect Timer Expired
10.50.0.21      HUB-02   LTE/5G      ce0/0       Up     03d17h    1      2026-03-10T15:03:12Z -

BFD Profile Detail:
Transport   Tx Interval  Rx Interval  Multiplier  Detect Time
MPLS        1000 ms      1000 ms      3           3000 ms
Internet    1000 ms      1000 ms      3           3000 ms
LTE/5G      1500 ms      1500 ms      3           4500 ms

ncx-edge# show sdwan app-route statistics
Generated: 2026-03-14T09:23:05Z

SLA Class           Transport   Peer       Latency  Jitter  Loss   SLA State     Consecutive Fails
Voice               MPLS        DC-01      34 ms    6 ms    0.1%   Compliant     0
Voice               Internet    DC-01      188 ms   47 ms   3.8%   Noncompliant  2
Business-Critical   Internet    HUB-02     n/a      n/a     n/a    No Sample     3
Best-Effort         LTE/5G      HUB-02     91 ms    n/a     0.4%   Compliant     0

ncx-edge# show sdwan sla-class
SLA Class            Max Latency  Max Jitter  Max Loss
Voice                150 ms       30 ms       1%
Video                200 ms       40 ms       2%
Business-Critical    250 ms       50 ms       3%
Best-Effort          400 ms       n/a         5%

ncx-edge# show sdwan control connections
Generated: 2026-03-14T09:23:44Z

Peer              Role          State      Uptime     Last Error
orchestrator-01   Orchestrator  Connected  19d02h     -
orchestrator-02   Orchestrator  Connected  19d02h     -
10.40.0.11        Data Center   Connected  12d04h     -
10.50.0.21        Regional Hub  Connected  08d11h     -

ncx-edge# show interface ge0/0 counters
Interface ge0/0, Transport Internet broadband
  Admin state: up, Oper state: up
  Speed: 1000/full
  Input packets: 982344291
  Input errors: 18422
  CRC errors: 17988
  Output packets: 877320104
  Output drops: 112
  Carrier transitions: 7
  Last counter clear: 2026-03-13T00:00:00Z

ncx-edge# show policy qos-queue counters
Generated: 2026-03-14T09:24:19Z

Interface  Queue              Offered Rate  Drop Pkts  Drop %  Alarm
ge0/0      voice-priority     8.2 Mbps      0          0.00    -
ge0/0      business-critical  42.5 Mbps     884        0.12    -
ge0/0      best-effort        91.0 Mbps     48219      4.70    NCS-QOS-5002
ge0/1      business-critical  19.2 Mbps     0          0.00    -

ncx-edge# show sdwan tunnel detail peer 10.50.0.21 transport Internet
Tunnel to 10.50.0.21 via Internet
  Local interface: ge0/0
  Local tunnel IP: 172.31.18.6
  Remote tunnel IP: 172.31.18.1
  Encapsulation MTU: 1380
  Path MTU discovered: 1340
  Fragmentation observed: yes
  NAT detected: yes
  NAT binding age: 00:04:58
  Last BFD down: 2026-03-14T09:21:51Z
  Last BFD down reason: Detect Timer Expired

ncx-edge# ping sdwan tunnel peer 10.50.0.21 transport Internet size 1340 count 5 do-not-fragment
!!!!!
Success rate is 100 percent, round-trip min/avg/max = 42/51/66 ms

ncx-edge# ping sdwan tunnel peer 10.50.0.21 transport Internet size 1380 count 5 do-not-fragment
!!.!!
Success rate is 80 percent, round-trip min/avg/max = 44/58/91 ms
Note: 1 packet dropped with fragmentation needed
```

## Resolution

Apply the least disruptive fix that matches the evidence. Avoid masking a physical or provider fault by only increasing timers. Timer tuning is appropriate when the transport is inherently variable, such as LTE/5G or congested broadband, and after interface errors, MTU, and NAT state issues have been ruled out or corrected.

For MTU problems, set the tunnel MTU below the largest verified do-not-fragment size and allow room for SD-WAN encapsulation. In the diagnostic example, path MTU discovery reports 1340 while encapsulation MTU is 1380, so reduce the Internet tunnel MTU to 1340 or lower according to the site design standard.

For NAT idle-timeout symptoms, correct the upstream NAT device policy so that the tunnel’s NAT binding remains stable. If the edge is newly installed and ZTP is also failing with NCS-ZTP-4001 ZTP Redirect Failed or NCS-ZTP-4003 Device Certificate Validation Failed, resolve onboarding first; BFD cannot be trusted until the device has a valid configuration and certificate.

After remediation, verify that BFD uptime increases, flap counters stop incrementing, app-route samples return, and related alarms clear. NCS-BFD-3004 should stop recurring; NCS-BFD-3005 should clear when the BFD session is Up. If SLA thresholds are again met, NCS-SLA-2002 SLA Restored is generated for prior NCS-SLA-2001 conditions.

- Physical/interface fault: replace cable or optic, move the circuit to a known-good WAN port, and verify CRC/input error counters stop increasing.
- Transport loss: keep automatic failover active and open an ISP or private-transport provider ticket with the exact UTC timestamps, local/remote tunnel IPs, transport type, and BFD flap count.
- MTU mismatch: reduce tunnel MTU to the verified path MTU and retest with do-not-fragment probes.
- NAT timeout: increase upstream NAT UDP/session timeout and verify the NAT binding age no longer resets at a regular short interval.
- QoS congestion: correct shaping and queue policy so BFD and priority traffic are not starved; investigate NCS-QOS-5002 if present.
- Timer tuning: increase BFD hello interval or multiplier only for the affected transport profile and document the reason in the change record.

```text
ncx-edge# configure terminal
ncx-edge(config)# sdwan transport Internet
ncx-edge(config-sdwan-transport)# tunnel-mtu 1340
ncx-edge(config-sdwan-transport)# bfd hello-interval 1500
ncx-edge(config-sdwan-transport)# bfd multiplier 4
ncx-edge(config-sdwan-transport)# commit comment "KB-NET-1006: stabilize Internet BFD after verified MTU/provider jitter issue"
Commit complete at 2026-03-14T09:47:33Z

ncx-edge# show sdwan bfd sessions
Generated: 2026-03-14T10:08:12Z

Peer System IP  Site     Transport   Local Intf  State  Uptime    Flaps  Last Change          Last Down Reason
10.40.0.11      DC-01    MPLS        ge0/1       Up     12d05h    0      2026-03-02T05:11:04Z -
10.40.0.11      DC-01    Internet    ge0/0       Up     00:20:39  18     2026-03-14T09:47:33Z -
10.50.0.21      HUB-02   Internet    ge0/0       Up     00:20:31  23     2026-03-14T09:47:41Z -
10.50.0.21      HUB-02   LTE/5G      ce0/0       Up     03d18h    1      2026-03-10T15:03:12Z -

ncx-edge# show sdwan app-route statistics
Generated: 2026-03-14T10:09:02Z

SLA Class           Transport   Peer       Latency  Jitter  Loss   SLA State   Consecutive Fails
Voice               Internet    DC-01      72 ms    18 ms   0.2%   Compliant   0
Business-Critical   Internet    HUB-02     81 ms    21 ms   0.3%   Compliant   0
Best-Effort         LTE/5G      HUB-02     94 ms    n/a     0.4%   Compliant   0
```

## Escalation Criteria

Escalate when local remediation does not stabilize BFD, when the blast radius indicates a shared service issue, or when SLA impact reaches release 5.0 severity thresholds. Attach the outputs from the diagnostic commands in this runbook, before-and-after timestamps, and any Orchestrator alarm history for NCS-BFD-3004, NCS-BFD-3005, NCS-SLA-2001, and NCS-SLA-2002.

For SLA-specific handling and ITSM workflow, see KB-NET-1005. For definitions of NCS-BFD-3004 BFD Session Flap, NCS-BFD-3005 BFD Session Down, NCS-SLA-2001 SLA Violation Detected, NCS-SLA-2002 SLA Restored, NCS-ZTP-4001 ZTP Redirect Failed, NCS-ZTP-4003 Device Certificate Validation Failed, NCS-QOS-5002 Queue Drop Threshold Exceeded, and NCS-ORC-6001 Orchestrator Control Connection Lost, see KB-NET-1008.

- Escalate to the transport provider if BFD flaps correlate with packet loss, CRC/input errors on the access handoff, carrier transitions, or simultaneous impact on multiple customers/sites using the same access circuit.
- Escalate to the NetCore SD-WAN operations team if NCS-BFD-3004 continues for more than 15 minutes after MTU, interface, NAT, and QoS checks are clean.
- Escalate as Sev2 if an associated SLA breach persists longer than 15 minutes.
- Escalate as Sev1 if the associated SLA breach persists longer than 30 minutes or 5 or more sites are affected.
- Escalate to the hub/data-center team immediately if many branches flap to the same NCX-4000 or NCX-9000 peer at the same timestamp.
- Include: site ID, edge model, release 5.0 confirmation, transport type, local and remote tunnel IPs, BFD uptime/flap counts, interface counters, app-route statistics, MTU test results, NAT observations, and recent policy changes.

## Related Articles

- KB-NET-1005: Troubleshooting Alarm NCS-SLA-2001 "SLA Violation Detected"
- KB-NET-1008: NCS Alarm and Error Code Reference
