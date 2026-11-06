---
kb_id: "KB-NET-1010"
title: "QoS and Traffic Steering for Voice and Video"
domain: "networking"
article_type: "config"
product: "NetCore SD-WAN"
version: "5.0"
status: "current"
superseded_by: ""
last_updated: "2026-07-08"
error_codes: ["NCS-QOS-5002"]
related: ["KB-NET-1001", "KB-NET-1005"]
tags: ["qos", "voice", "video", "dscp"]
author: "NetCore Systems Technical Support"
format: "md"
---

# QoS and Traffic Steering for Voice and Video

**KB-NET-1010** | NetCore SD-WAN 5.0 | Last updated: 2026-07-08 | Status: current

## Summary

This article provides a baseline configuration for prioritizing voice and video on NetCore SD-WAN 5.0, including DSCP marking, QoS queue assignment, and app-route steering for NetCore Meet traffic on UDP 9000. It also includes verification steps and queue-drop monitoring for NCS-QOS-5002 Queue Drop Threshold Exceeded.

**Applies to:** NetCore SD-WAN 5.0, NetCore Orchestrator, NCX-1000 branch edge, NCX-4000 regional hub, NCX-9000 data center edge, Transports: MPLS, Internet broadband, LTE/5G

## Overview

Use this configuration to keep interactive voice and video traffic inside the NetCore SD-WAN 5.0 SLA classes and to steer flows to the best compliant transport. Voice must meet latency <= 150 ms, jitter <= 30 ms, and loss <= 1%. Video must meet latency <= 200 ms, jitter <= 40 ms, and loss <= 2%.

The example marks voice with DSCP EF 46, marks video with DSCP AF41 34, classifies NetCore Meet media on UDP 9000 as Video, places traffic into priority QoS queues, and binds traffic to app-route policy decisions based on BFD-probed transport health.

In release 5.0, app-route SLA polling runs every 120 seconds with multiplier 3, so a breach is declared after 3 consecutive intervals, approximately 6 minutes. Automatic failover selects the best compliant transport. A breach raises Sev3, auto-escalates to Sev2 if it persists for more than 15 minutes, and Sev1 if it persists for more than 30 minutes or affects 5 or more sites. An ITSM ticket is created automatically.

This article directly covers NCS-QOS-5002 Queue Drop Threshold Exceeded. Related operational alarms that can affect or be observed during validation include NCS-SLA-2001 SLA Violation Detected, NCS-SLA-2002 SLA Restored, NCS-BFD-3004 BFD Session Flap, NCS-BFD-3005 BFD Session Down, NCS-ZTP-4001 ZTP Redirect Failed, NCS-ZTP-4003 Device Certificate Validation Failed, and NCS-ORC-6001 Orchestrator Control Connection Lost. For SLA class design, see KB-NET-1001. For SLA violation troubleshooting, see KB-NET-1005.

*Recommended classification used in this article*

| Traffic type | Match condition | DSCP marking | SLA class | Queue |
|---|---|---|---|---|
| Voice | SIP/RTP voice prefixes or existing voice ACL | EF 46 | Voice | q-voice-priority |
| Video | Enterprise video prefixes or existing video ACL | AF41 34 | Video | q-video-priority |
| NetCore Meet media | UDP destination port 9000 | AF41 34 | Video | q-video-priority |
| Business applications | Application list defined by policy | Preserve or mark AF21 18 | Business-Critical | q-business |
| Default traffic | No specific match | Preserve | Best-Effort | q-default |

## Prerequisites

Complete these checks before applying the policy. The examples assume that the edge device is already onboarded to NetCore Orchestrator and has working transports for MPLS, Internet broadband, and optionally LTE/5G.

Apply the same policy object consistently to NCX-1000 branch edges and any NCX-4000 or NCX-9000 hub devices that participate in the voice/video service path.

- Confirm the site is running NetCore SD-WAN 5.0. Do not use this procedure for release 4.2 policy behavior, because release 4.2 used 600-second polling, multiplier 5, manual failover only, e-mail notification only, and no automatic severity escalation.
- Confirm control connectivity to NetCore Orchestrator with show sdwan control connections before making changes. If NCS-ORC-6001 Orchestrator Control Connection Lost is active, restore management connectivity first.
- Confirm BFD sessions are stable with show sdwan bfd sessions. If NCS-BFD-3004 BFD Session Flap or NCS-BFD-3005 BFD Session Down is active, resolve transport instability before relying on app-route steering.
- Confirm ZTP and device identity are complete. If NCS-ZTP-4001 ZTP Redirect Failed or NCS-ZTP-4003 Device Certificate Validation Failed is active, complete onboarding remediation before applying centralized policy.
- Confirm that any LAN switching or endpoint policy preserves DSCP markings where required, or that the edge policy below is allowed to remark traffic at ingress.
- Review existing SLA classes and app-route policy. For the baseline SLA configuration, see KB-NET-1001.

```text
ncx-edge# show sdwan control connections
CONTROLLER        STATE       LOCAL-SITE     SYSTEM-IP       LAST-UP
orc-primary       connected   BR-142         10.50.142.2     2026-11-06 08:12:04
orc-secondary     connected   BR-142         10.50.142.2     2026-11-06 08:12:09

ncx-edge# show sdwan bfd sessions
SITE     TRANSPORT   PEER           STATE  LAT(ms)  JIT(ms)  LOSS(%)  UPTIME
BR-142   mpls        DC-9000-A      up     42       3        0.0      4d 02:17:11
BR-142   internet    DC-9000-A      up     71       8        0.1      4d 02:16:58
BR-142   lte5g       DC-9000-A      up     96       12       0.2      2d 18:44:21
```

## Step-by-step Procedure

The following example shows a site-local policy applied on an NCX edge. In production, create equivalent centralized policy objects in NetCore Orchestrator and attach them to the intended device group. Use the CLI snippets for controlled change windows, lab validation, or emergency site-level correction.

- 1. Enter configuration mode and create traffic match objects for voice, video, and NetCore Meet UDP 9000.
- 2. Apply DSCP marking so voice is marked EF 46 and video, including NetCore Meet UDP 9000, is marked AF41 34.
- 3. Define QoS queue mapping so voice uses the strict priority voice queue and video uses the video priority queue. Keep a separate default queue for Best-Effort traffic to avoid unnecessary contention.
- 4. Confirm or create the Voice and Video SLA class references. In NetCore SD-WAN 5.0, Voice is latency <= 150 ms, jitter <= 30 ms, loss <= 1%; Video is latency <= 200 ms, jitter <= 40 ms, loss <= 2%.
- 5. Create app-route policy rules to prefer MPLS for Voice and Video when compliant, then Internet broadband, then LTE/5G. The system automatically fails over to the best compliant transport when the selected transport breaches the SLA.
- 6. Attach the QoS and app-route policies to the service VPN or segment used for collaboration traffic.
- 7. Commit the change and save the running configuration.

```text
ncx-edge# configure terminal

! 1. Traffic match objects
policy application-list APP-VOICE
 match dscp 46
 match udp destination-port range 16384 32767
 exit

policy application-list APP-VIDEO
 match dscp 34
 match udp destination-port range 50000 59999
 exit

policy application-list APP-NETCORE-MEET
 match udp destination-port 9000
 exit

! 2. DSCP marking policy
policy qos-marking MARK-COLLAB-DSCP
 rule 10
  match application-list APP-VOICE
  set dscp 46
  set traffic-class voice
  exit
 rule 20
  match application-list APP-NETCORE-MEET
  set dscp 34
  set traffic-class video
  exit
 rule 30
  match application-list APP-VIDEO
  set dscp 34
  set traffic-class video
  exit
 exit

! 3. Queue mapping
policy qos-queue COLLAB-QUEUES
 queue q-voice-priority
  traffic-class voice
  scheduler strict-priority
  dscp 46
  exit
 queue q-video-priority
  traffic-class video
  scheduler weighted-priority
  dscp 34
  exit
 queue q-business
  traffic-class business-critical
  scheduler weighted
  exit
 queue q-default
  traffic-class best-effort
  scheduler weighted
  exit
 exit

! 4. SLA class references for release 5.0
sdwan sla-class Voice
 latency 150
 jitter 30
 loss 1
 exit
sdwan sla-class Video
 latency 200
 jitter 40
 loss 2
 exit

! 5. App-route steering for voice and video
policy app-route COLLAB-APP-ROUTE
 rule 10
  match application-list APP-VOICE
  sla-class Voice
  preferred-transport mpls
  fallback-transport internet
  fallback-transport lte5g
  exit
 rule 20
  match application-list APP-NETCORE-MEET
  sla-class Video
  preferred-transport mpls
  fallback-transport internet
  fallback-transport lte5g
  exit
 rule 30
  match application-list APP-VIDEO
  sla-class Video
  preferred-transport mpls
  fallback-transport internet
  fallback-transport lte5g
  exit
 exit

! 6. Attach policies to the collaboration service segment
sdwan segment COLLAB-SERVICES
 qos-marking-policy MARK-COLLAB-DSCP ingress
 qos-queue-policy COLLAB-QUEUES egress
 app-route-policy COLLAB-APP-ROUTE
 exit

! 7. Commit and save
commit comment "KB-NET-1010 voice video qos and steering"
write memory
end
```

## Verification

Run the following checks after committing the policy. Validate first on one representative branch, then on a larger device group through NetCore Orchestrator.

The key outcomes are: DSCP is applied, traffic is mapped to the expected queues, SLA classes show the release 5.0 thresholds, app-route statistics show compliant transport selection, and queue drops are not increasing. If queue drops increase and the alarm NCS-QOS-5002 Queue Drop Threshold Exceeded is raised, review queue counters and reduce congestion before treating the issue as an app-route problem.

- 1. Verify SLA class thresholds.
- 2. Verify BFD measurements are inside the Voice and Video SLA targets on at least one available transport.
- 3. Verify app-route statistics for voice and NetCore Meet UDP 9000 flows.
- 4. Verify QoS queue counters and watch for drops.
- 5. If NCS-SLA-2001 SLA Violation Detected appears while the queue counters are also dropping, follow KB-NET-1005 after confirming whether congestion is local to the egress queue.

```text
ncx-edge# show sdwan sla-class
SLA CLASS            LATENCY(ms)  JITTER(ms)  LOSS(%)
Voice                150          30          1
Video                200          40          2
Business-Critical    250          50          3
Best-Effort          400          n/a         5

ncx-edge# show sdwan bfd sessions
SITE     TRANSPORT   PEER           STATE  LAT(ms)  JIT(ms)  LOSS(%)  SLA-VOICE  SLA-VIDEO
BR-142   mpls        DC-9000-A      up     39       4        0.0      pass       pass
BR-142   internet    DC-9000-A      up     68       9        0.1      pass       pass
BR-142   lte5g       DC-9000-A      up     118      18       0.4      pass       pass

ncx-edge# show sdwan app-route statistics
APP              SLA-CLASS  SELECTED-TRANSPORT  LAT(ms)  JIT(ms)  LOSS(%)  STATE       LAST-CHANGE
APP-VOICE        Voice      mpls                39       4        0.0      compliant   2026-11-06 09:10:22
APP-NETCORE-MEET Video      mpls                39       4        0.0      compliant   2026-11-06 09:10:23
APP-VIDEO        Video      mpls                39       4        0.0      compliant   2026-11-06 09:10:23

ncx-edge# show policy qos-queue counters
POLICY          QUEUE              TX-PKTS     TX-BYTES       DROPS  LAST-DROP
COLLAB-QUEUES   q-voice-priority   884231      172301992      0      never
COLLAB-QUEUES   q-video-priority   2129044     2851044401     0      never
COLLAB-QUEUES   q-business         645001      510882221      3      2026-11-06 08:43:12
COLLAB-QUEUES   q-default          19200442    11930021001    44     2026-11-06 09:02:01

ncx-edge# show policy qos-queue counters | include q-video-priority
COLLAB-QUEUES   q-video-priority   2129044     2851044401     0      never
```

## Rollback

Use rollback if the policy causes unexpected classification, incorrect DSCP marking, or queue drops after deployment. Rollback removes the policy attachment first, then removes the policy objects. If the configuration was deployed from NetCore Orchestrator, perform the equivalent policy detach and redeploy from Orchestrator so the local device is not overwritten on the next policy push.

- 1. Remove policy attachments from the collaboration segment.
- 2. Remove app-route, queue, marking, and application-list objects created by this procedure.
- 3. Commit the rollback and verify that traffic returns to the previous policy behavior.
- 4. Continue monitoring for NCS-QOS-5002 Queue Drop Threshold Exceeded after rollback, because existing congestion can persist after policy removal.

```text
ncx-edge# configure terminal
sdwan segment COLLAB-SERVICES
 no qos-marking-policy MARK-COLLAB-DSCP ingress
 no qos-queue-policy COLLAB-QUEUES egress
 no app-route-policy COLLAB-APP-ROUTE
 exit

no policy app-route COLLAB-APP-ROUTE
no policy qos-queue COLLAB-QUEUES
no policy qos-marking MARK-COLLAB-DSCP
no policy application-list APP-NETCORE-MEET
no policy application-list APP-VIDEO
no policy application-list APP-VOICE

commit comment "Rollback KB-NET-1010 voice video qos and steering"
write memory
end

ncx-edge# show sdwan app-route statistics
APP              SLA-CLASS  SELECTED-TRANSPORT  LAT(ms)  JIT(ms)  LOSS(%)  STATE       LAST-CHANGE
-- no entries for COLLAB-APP-ROUTE --

ncx-edge# show policy qos-queue counters | include COLLAB-QUEUES
-- no counters found --
```

## Known Limitations

QoS does not create additional WAN capacity. If the physical transport is saturated, priority queues protect interactive media first, but other queues can still drop traffic. If the voice or video priority queues show increasing drops and NCS-QOS-5002 Queue Drop Threshold Exceeded is active, investigate offered load, access bandwidth, and traffic classification.

App-route steering depends on BFD measurements and control connectivity. If NCS-BFD-3004 BFD Session Flap, NCS-BFD-3005 BFD Session Down, or NCS-ORC-6001 Orchestrator Control Connection Lost is active, steering decisions might not reflect the intended transport state until the underlying condition is resolved.

SLA alarms are separate from queue-drop alarms. NCS-SLA-2001 SLA Violation Detected means the SLA class has breached based on the release 5.0 polling policy; NCS-SLA-2002 SLA Restored confirms the class has returned to compliance. Use KB-NET-1005 when investigating NCS-SLA-2001, especially when queue drops are not present.

This procedure assumes release 5.0 behavior. Release 4.2 used a 600-second poll interval and multiplier 5, resulting in breach declaration after approximately 50 minutes, with manual failover only, e-mail notification only, and no automatic severity escalation.

ZTP-related alarms NCS-ZTP-4001 ZTP Redirect Failed and NCS-ZTP-4003 Device Certificate Validation Failed are not caused by QoS policy, but they can prevent a new edge from receiving centralized policy from NetCore Orchestrator until onboarding is corrected.

## Related Articles

- KB-NET-1001: Configuring App-Aware Routing SLA Classes
- KB-NET-1005: Troubleshooting Alarm NCS-SLA-2001 "SLA Violation Detected"
