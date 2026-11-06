---
kb_id: "KB-NET-1005"
title: "Troubleshooting Alarm NCS-SLA-2001 \"SLA Violation Detected\""
domain: "networking"
article_type: "runbook"
product: "NetCore SD-WAN"
version: "5.0"
status: "current"
superseded_by: ""
last_updated: "2026-09-21"
error_codes: ["NCS-SLA-2001", "NCS-SLA-2002", "NCS-QOS-5002"]
related: ["KB-NET-1003", "KB-NET-1006", "KB-NET-1010"]
tags: ["troubleshooting", "sla", "noc"]
author: "NetCore Systems Technical Support"
format: "md"
---

# Troubleshooting Alarm NCS-SLA-2001 "SLA Violation Detected"

**KB-NET-1005** | NetCore SD-WAN 5.0 | Last updated: 2026-09-21 | Status: current

## Summary

This runbook helps NOC engineers triage and remediate NetCore SD-WAN 5.0 alarm NCS-SLA-2001 "SLA Violation Detected". It covers expected symptoms, impact, CLI diagnostics, common root causes such as ISP congestion, QoS mis-marking, and LTE/5G fallback, plus escalation criteria aligned with the 5.0 SLA breach policy.

**Applies to:** NetCore SD-WAN 5.0, NetCore Orchestrator, NCX-1000 branch edge, NCX-4000 regional hub, NCX-9000 data center edge, Transports: MPLS, Internet broadband, LTE/5G

## Symptoms

Alarm NCS-SLA-2001 "SLA Violation Detected" is raised when an application route exceeds the configured SLA class thresholds for 3 consecutive app-route polling intervals. In NetCore SD-WAN 5.0, the poll interval is 120 seconds and the multiplier is 3, so the breach is declared after approximately 6 minutes.

The alarm normally appears in NetCore Orchestrator and on the affected edge device with the impacted site, SLA class, transport, tunnel, and measured latency, jitter, or loss. When measurements return within threshold, NetCore SD-WAN raises NCS-SLA-2002 "SLA Restored".

- Voice SLA threshold: latency <= 150 ms, jitter <= 30 ms, loss <= 1%.
- Video SLA threshold: latency <= 200 ms, jitter <= 40 ms, loss <= 2%.
- Business-Critical SLA threshold: latency <= 250 ms, jitter <= 50 ms, loss <= 3%.
- Best-Effort SLA threshold: latency <= 400 ms, jitter n/a, loss <= 5%.
- Related alarms may include NCS-QOS-5002 "Queue Drop Threshold Exceeded" if local queuing or marking contributes to the breach.
- If tunnel instability is present, also check for NCS-BFD-3004 "BFD Session Flap" and NCS-BFD-3005 "BFD Session Down"; see KB-NET-1006.
- If control-plane visibility is incomplete, check for NCS-ORC-6001 "Orchestrator Control Connection Lost".
- During device onboarding only, unrelated provisioning issues may appear as NCS-ZTP-4001 "ZTP Redirect Failed" or NCS-ZTP-4003 "Device Certificate Validation Failed".

## Impact

In release 5.0, NCS-SLA-2001 is created at Sev3 and an ITSM ticket is automatically opened. NetCore SD-WAN automatically steers affected application traffic to the best compliant transport when one is available.

If the breach persists for more than 15 minutes, severity auto-escalates to Sev2. If the breach persists for more than 30 minutes or affects 5 or more sites, severity auto-escalates to Sev1. For the full policy, see KB-NET-1003.

- Voice impact: one-way audio, clipping, robotic audio, delayed call setup, or call drops if no compliant path remains.
- Video impact: freezes, resolution downshift, lip-sync issues, or meeting disconnects.
- Business-Critical impact: transaction latency, application timeout, or degraded user experience.
- Best-Effort impact: slower downloads or SaaS page loads; jitter is not evaluated for Best-Effort in release 5.0.
- Failover impact: short application steering change while flows are moved to the best compliant transport.

## Probable Causes

Use the following cause-to-action table to map the first observable condition to the next troubleshooting action.

*Common causes of NCS-SLA-2001 and recommended actions*

| Observable condition | Likely cause | Primary action | Related reference |
|---|---|---|---|
| High latency or loss on Internet broadband only; MPLS and LTE/5G are compliant | ISP congestion or last-mile impairment | Keep traffic on compliant transport, collect app-route and BFD evidence, open provider case if sustained | KB-NET-1003 |
| High jitter and drops on the Voice or Video queue; NCS-QOS-5002 present | QoS mis-marking, oversubscription, or incorrect queue policy | Validate DSCP classification, queue counters, and traffic steering policy | KB-NET-1010 |
| Traffic has moved to LTE/5G and now violates Voice or Video SLA | Primary transport outage or brownout caused LTE/5G fallback; LTE/5G path is impaired or capacity-limited | Confirm primary transport health, reduce non-critical load on LTE/5G, restore primary path | KB-NET-1003 |
| SLA measurements intermittently fail with tunnel state changes; NCS-BFD-3004 or NCS-BFD-3005 present | Tunnel instability or underlay packet loss | Troubleshoot BFD session and underlay reachability before tuning app-route policy | KB-NET-1006 |
| Orchestrator data is stale or the site is not reporting current statistics; NCS-ORC-6001 present | Management/control connection interruption | Restore control connection before making policy conclusions | KB-NET-1003 |
| Only newly staged devices are affected and ZTP alarms are present | Onboarding/certificate or redirect problem, not an SLA policy issue | Resolve NCS-ZTP-4001 or NCS-ZTP-4003 before SLA validation | Internal staging procedure |

## Diagnostic Steps

Run the diagnostics from the affected NCX edge. Capture the command output before making changes so the ITSM ticket has baseline evidence. In the examples below, site BR-042 is an NCX-1000 branch edge with MPLS, Internet broadband, and LTE/5G transports.

- 1. Confirm the configured SLA thresholds with show sdwan sla-class.
- 2. Identify the violated SLA class, transport, peer, and metric using show sdwan app-route statistics.
- 3. Verify whether the BFD-monitored tunnel is stable using show sdwan bfd sessions.
- 4. Confirm that the edge still has Orchestrator control connectivity using show sdwan control connections.
- 5. Check QoS queue counters for local congestion or mis-marking using show policy qos-queue counters.
- 6. Correlate findings with active alarms: NCS-SLA-2001, NCS-SLA-2002, NCS-QOS-5002, NCS-BFD-3004, NCS-BFD-3005, NCS-ORC-6001, NCS-ZTP-4001, and NCS-ZTP-4003.

```text
ncx-edge# show sdwan sla-class
SLA Class            Latency(ms)   Jitter(ms)   Loss(%)
---------------------------------------------------------
Voice                <=150         <=30         <=1
Video                <=200         <=40         <=2
Business-Critical    <=250         <=50         <=3
Best-Effort          <=400         n/a          <=5

ncx-edge# show sdwan app-route statistics
Timestamp: 2026-11-06 09:42:18 UTC
Site: BR-042  Device: NCX-1000  System-IP: 10.42.0.11
App-Route Poll Interval: 120s  Multiplier: 3

SLA-Class  Peer        Transport  Tunnel        Lat(ms)  Jit(ms)  Loss(%)  Consecutive  State       Alarm
---------------------------------------------------------------------------------------------------------------
Voice      DC-01       MPLS       mpls0-to-dc1  91       11       0.1      0            COMPLIANT   -
Voice      DC-01       Internet   inet0-to-dc1  188      44       1.8      3            VIOLATED    NCS-SLA-2001
Voice      DC-01       LTE5G      lte0-to-dc1   126      27       0.7      0            COMPLIANT   -
Video      DC-01       Internet   inet0-to-dc1  171      36       1.2      0            COMPLIANT   -
Business-Critical DC-01 Internet  inet0-to-dc1  233      42       2.1      0            COMPLIANT   -
Best-Effort DC-01     Internet   inet0-to-dc1  312      n/a      1.9      0            COMPLIANT   -

Active Steering Decision:
SLA-Class  Current-Path  Previous-Path  Reason
---------------------------------------------------------------
Voice      MPLS          Internet       Internet violated Voice SLA; best compliant path selected

ncx-edge# show sdwan bfd sessions
Timestamp: 2026-11-06 09:42:33 UTC
Peer   Transport  Tunnel        State  Uptime      Last-Change              Tx(ms)  Rx(ms)  Mult
-------------------------------------------------------------------------------------------------
DC-01  MPLS       mpls0-to-dc1  UP     18d06h21m   2026-10-19 03:21:04 UTC 300     300     3
DC-01  Internet   inet0-to-dc1  UP     2d04h12m    2026-11-04 05:30:16 UTC 300     300     3
DC-01  LTE5G      lte0-to-dc1   UP     09h18m      2026-11-06 00:24:11 UTC 300     300     3

Recent BFD Events:
Time                      Tunnel        Event
------------------------------------------------------------
2026-11-06 08:57:03 UTC   inet0-to-dc1  No BFD flap recorded in last 60 minutes

ncx-edge# show sdwan control connections
Timestamp: 2026-11-06 09:42:45 UTC
Controller           Role           State      Uptime      Last-Error
---------------------------------------------------------------------
orc-ctrl-01          Primary        UP         18d06h03m   -
orc-ctrl-02          Secondary      UP         18d06h02m   -

ncx-edge# show policy qos-queue counters
Timestamp: 2026-11-06 09:43:02 UTC
Interface: inet0  Policy: BRANCH-WAN-OUT
Queue              DSCP Match        Tx-Pkts       Drops      Drop%   Threshold  Alarm
------------------------------------------------------------------------------------------
voice-priority     46                2,846,992     18,422     0.65    0.50       NCS-QOS-5002
video              34,36             1,112,440     1,906      0.17    1.00       -
business-critical  18,26             4,901,330     7,774      0.16    1.00       -
best-effort        0                 28,440,115    42,008     0.15    2.00       -

Interpretation for this sample:
- NCS-SLA-2001 is active for Voice on Internet because latency 188 ms, jitter 44 ms, and loss 1.8% exceed Voice thresholds.
- BFD is stable, so this is not currently a tunnel flap condition.
- Control connections are healthy, so Orchestrator data should be current.
- NCS-QOS-5002 is active on the voice-priority queue on inet0, indicating local queue drops may be contributing to the Voice SLA violation.
```

## Resolution

Start with the least disruptive action. NetCore SD-WAN 5.0 should already steer affected traffic to the best compliant transport after NCS-SLA-2001 is declared. Do not force a manual path change unless the automatic steering decision is incorrect or no compliant path exists.

- For ISP congestion or last-mile impairment: keep the affected SLA class on a compliant transport such as MPLS or LTE/5G; collect app-route statistics showing latency, jitter, and loss; open a provider case if the Internet broadband path remains non-compliant beyond the normal transient period.
- For QoS mis-marking or NCS-QOS-5002: verify that Voice traffic is classified into the voice-priority queue and Video traffic into the video queue. Correct DSCP marking or queue policy in NetCore Orchestrator, then monitor show policy qos-queue counters for drop reduction. See KB-NET-1010.
- For LTE/5G fallback capacity issues: verify why primary MPLS or Internet broadband was bypassed, reduce Best-Effort load on LTE/5G, and restore the primary transport. LTE/5G may be compliant for low-volume traffic but may fail Voice or Video under congestion.
- For BFD-related instability: if NCS-BFD-3004 or NCS-BFD-3005 is present, troubleshoot BFD and underlay loss before changing SLA policy. See KB-NET-1006.
- For control-plane issues: if NCS-ORC-6001 is present, restore Orchestrator control connectivity first; stale control data can delay validation of NCS-SLA-2002.
- After remediation, confirm that the affected SLA class has 0 consecutive violating intervals and that NCS-SLA-2002 has been generated.

```text
ncx-edge# show sdwan app-route statistics
Timestamp: 2026-11-06 09:54:31 UTC
Site: BR-042  Device: NCX-1000  System-IP: 10.42.0.11
App-Route Poll Interval: 120s  Multiplier: 3

SLA-Class  Peer   Transport  Tunnel        Lat(ms)  Jit(ms)  Loss(%)  Consecutive  State       Alarm
---------------------------------------------------------------------------------------------------------
Voice      DC-01  Internet   inet0-to-dc1  118      22       0.4      0            COMPLIANT   NCS-SLA-2002
Voice      DC-01  MPLS       mpls0-to-dc1  89       10       0.1      0            COMPLIANT   -
Voice      DC-01  LTE5G      lte0-to-dc1   130      29       0.8      0            COMPLIANT   -

Active Steering Decision:
SLA-Class  Current-Path  Previous-Path  Reason
---------------------------------------------------------------
Voice      Internet      MPLS           Internet restored; policy-preferred compliant path selected

ncx-edge# show policy qos-queue counters
Timestamp: 2026-11-06 09:54:44 UTC
Interface: inet0  Policy: BRANCH-WAN-OUT
Queue              DSCP Match        Tx-Pkts       Drops      Drop%   Threshold  Alarm
------------------------------------------------------------------------------------------
voice-priority     46                2,912,884     18,425     0.01    0.50       -
video              34,36             1,141,772     1,907      0.00    1.00       -
business-critical  18,26             4,998,431     7,781      0.01    1.00       -
best-effort        0                 29,033,221    42,210     0.04    2.00       -
```

## Escalation Criteria

Follow the NetCore SD-WAN 5.0 severity model for SLA breaches. NCS-SLA-2001 starts at Sev3 and creates an ITSM ticket automatically. Update the ticket with CLI evidence, affected SLA class, affected transport, number of sites, start time, and whether NCS-SLA-2002 has occurred.

- Escalate to the regional network engineering queue if NCS-SLA-2001 persists for more than 15 minutes; this aligns with Sev2 auto-escalation.
- Escalate as Sev1 if the breach persists for more than 30 minutes or affects 5 or more sites.
- Escalate to the access provider if one transport shows sustained non-compliance while alternate transports remain compliant and BFD is stable.
- Escalate to the collaboration/application team when the network path is compliant but users still report Voice or Video symptoms.
- Escalate to the QoS policy owner if NCS-QOS-5002 is present after traffic has been moved to a compliant transport or after DSCP classification has been verified.
- Escalate to the SD-WAN platform team if automatic failover does not select the best compliant transport after the 3 consecutive polling intervals.
- Reference KB-NET-1003 for escalation and auto-failover policy details, KB-NET-1006 for NCS-BFD-3004 tunnel flap troubleshooting, and KB-NET-1010 for QoS and traffic steering validation.

## Related Articles

- KB-NET-1003: SLA Breach Policy: Escalation and Auto-Failover
- KB-NET-1006: Troubleshooting BFD Tunnel Flaps (NCS-BFD-3004)
- KB-NET-1010: QoS and Traffic Steering for Voice and Video
