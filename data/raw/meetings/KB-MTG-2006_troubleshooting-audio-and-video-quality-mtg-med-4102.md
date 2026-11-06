---
kb_id: "KB-MTG-2006"
title: "Troubleshooting Audio and Video Quality (MTG-MED-4102)"
domain: "meetings"
article_type: "runbook"
product: "NetCore Meet"
version: "5.0"
status: "current"
superseded_by: ""
last_updated: "2026-09-18"
error_codes: ["MTG-MED-4102", "MTG-MED-4105"]
related: ["KB-MTG-2007", "KB-MTG-2010"]
tags: ["troubleshooting", "media", "quality"]
author: "NetCore Systems Technical Support"
format: "md"
---

# Troubleshooting Audio and Video Quality (MTG-MED-4102)

**KB-MTG-2006** | NetCore Meet 5.0 | Last updated: 2026-09-18 | Status: current

## Summary

This runbook helps administrators isolate and resolve poor audio and video quality in NetCore Meet 5.0 when users report choppy audio, frozen video, or the alarm MTG-MED-4102 Media Path Degraded (high packet loss). It also covers MTG-MED-4105 No Audio Device Detected when the symptom is missing microphone or speaker input rather than network impairment.

**Applies to:** NetCore Meet 5.0, NetCore Meet desktop app for Windows, NetCore Meet desktop app for macOS, NetCore Meet mobile app, NetCore Meet web client, Meet Starter, Meet Business, Meet Enterprise

## Symptoms

Users may report degraded media quality during a NetCore Meet session even though they can join the meeting successfully. The most common alarm is MTG-MED-4102 Media Path Degraded (high packet loss), which is raised when the client detects media loss or instability on the active media path.

If the user can see the meeting but cannot send or receive audio from a local device, validate whether the issue is actually MTG-MED-4105 No Audio Device Detected rather than a network-quality issue.

For join failures or media path establishment failures, use KB-MTG-2007. That article covers MTG-JOIN-1003 Meeting Locked or Host Lobby Active and MTG-JOIN-1007 Media Ports Blocked by Firewall. For licensing limits and baseline network requirements, see KB-MTG-2010.

- Audio symptoms: robotic speech, one-way audio, delayed audio, clipping, repeated reconnect tones, or audio that drops for several seconds.
- Video symptoms: frozen video, low resolution, delayed screen share, black participant tile after join, or rapid changes between HD and low-bandwidth mode.
- In-meeting statistics show packet loss at or above 3%, jitter at or above 40 ms, or latency at or above 300 ms.
- The meeting quality panel or client log shows MTG-MED-4102 Media Path Degraded (high packet loss).
- The audio device picker is empty, disabled, or shows no microphone/speaker device, and the client log shows MTG-MED-4105 No Audio Device Detected.
- Out of scope for this runbook: MTG-SSO-6001 SAML Assertion Invalid or Expired, MTG-SSO-6004 IdP Certificate Mismatch, MTG-CALL-7002 Number Not Provisioned, and MTG-CALL-7010 Emergency Address Missing.

## Impact

Media degradation directly affects meeting usability. Participants may remain connected over TCP 443 signalling while media degrades or falls back from the preferred UDP 9000 path to TCP 5004 fallback for media.

The business impact increases with meeting size because each HD video stream requires approximately 2.5 Mbps. For example, a user receiving four active HD video streams may require roughly 10 Mbps of stable downstream bandwidth, plus upstream capacity for the user’s own camera and microphone.

- Single-user impact usually points to local access, endpoint device, client, Wi-Fi, VPN, or audio device conditions.
- Multiple users at the same site usually points to WAN congestion, firewall policy, UDP 9000 handling, QoS marking, or an upstream provider path.
- Multiple users across unrelated sites may indicate a regional service issue and should be escalated after local requirements are validated.
- A user with MTG-MED-4105 No Audio Device Detected may appear as muted or silent to other participants, but network packet loss may be normal.

## Probable Causes

Use the following cause-to-action table to determine the fastest remediation path. Always compare observed values with NetCore Meet 5.0 requirements: latency below 300 ms, jitter below 40 ms, packet loss below 3%, TCP 443 for signalling, UDP 9000 preferred for media, and TCP 5004 fallback for media.

*Cause-to-action mapping for MTG-MED-4102 and MTG-MED-4105*

| Observed condition | Likely cause | Immediate action | Expected result |
|---|---|---|---|
| Packet loss 3% or higher in in-meeting statistics | Congestion, lossy Wi-Fi, overloaded access circuit, or impaired WAN path | Move to wired access if possible, reduce active HD video streams, check site interface utilization, and validate QoS handling | Packet loss drops below 3% and MTG-MED-4102 clears |
| Jitter 40 ms or higher with variable audio delay | Queueing delay, asymmetric routing, or unstable wireless signal | Prioritize media traffic, validate DSCP preservation, and remove unnecessary tunneling from the media path | Jitter drops below 40 ms and audio stabilizes |
| Latency 300 ms or higher | Long network path, suboptimal egress location, or remote access hairpinning | Route the client through the nearest approved internet egress and avoid backhauling media through distant sites | Latency drops below 300 ms |
| UDP 9000 blocked or inconsistent; media uses TCP 5004 fallback | Firewall, proxy, or security policy not permitting preferred media | Permit outbound UDP 9000 for NetCore Meet media and keep TCP 5004 as fallback | Client uses UDP 9000 and quality improves |
| Audio device list empty; no local input or output | Missing, disabled, or unavailable microphone/speaker device | Select or reconnect the device, verify operating system permissions, and restart the NetCore Meet client | MTG-MED-4105 No Audio Device Detected clears |
| Only screen share or video degrades when many cameras are pinned | Insufficient endpoint or access bandwidth for active HD streams | Reduce pinned video tiles, turn off HD video where operationally acceptable, and verify approximately 2.5 Mbps per HD stream | Receive bitrate stabilizes and frame drops decrease |

## Diagnostic Steps

Start with the affected user’s in-meeting statistics, then confirm the client log, local device status, and network path. Capture values while the problem is happening; post-call averages may hide short loss bursts.

In the NetCore Meet client, open the meeting quality panel and record send/receive bitrate, packet loss, jitter, latency, media transport, device name, and timestamp. If the transport shows TCP 5004 instead of UDP 9000, do not assume it is a failure, but treat it as a strong signal that the preferred media path may be unavailable.

Client log locations for NetCore Meet 5.0 are typically: Windows desktop app: C:\Users\<user>\AppData\Local\NetCore\Meet\logs\meet-client.log; macOS desktop app: /Users/<user>/Library/Logs/NetCore/Meet/meet-client.log. For mobile and web clients, export diagnostics from the client Help > Send diagnostics workflow and attach the diagnostic bundle to the escalation case.

- Step 1: Confirm whether the issue is media quality, join failure, SSO, or device detection. Use this runbook for MTG-MED-4102 Media Path Degraded (high packet loss) and MTG-MED-4105 No Audio Device Detected.
- Step 2: Check in-meeting statistics against requirements: latency < 300 ms, jitter < 40 ms, packet loss < 3%.
- Step 3: Confirm port reachability: TCP 443 for signalling, UDP 9000 for preferred media, TCP 5004 for media fallback.
- Step 4: Confirm whether media is using UDP 9000 or TCP 5004 fallback.
- Step 5: Review client logs for timestamps matching the reported issue.
- Step 6: Check local CPU, access link utilization, and audio device enumeration.
- Step 7: Validate QoS/DSCP marking and preservation across the site edge.

```bash
# 1) Export current NetCore Meet client diagnostics from the affected endpoint
ncmeetctl diagnostics collect --since "2026-02-18T09:00:00Z" --output ./mtg-2006-case-18422.zip

Collecting NetCore Meet diagnostics...
Client version        : 5.0.318
Meeting ID           : 784-221-903
Active transport     : UDP/9000
Statistics included  : yes
Logs included        : yes
Output file          : ./mtg-2006-case-18422.zip
Result               : complete

# 2) Show the last media-quality events from the local client log
ncmeetctl logs grep --code MTG-MED --last 30m

2026-02-18T09:14:22.118Z WARN  media path=udp/9000 loss_rx=4.8% jitter_rx=56ms rtt=184ms code=MTG-MED-4102 message="Media Path Degraded (high packet loss)"
2026-02-18T09:15:04.902Z INFO  media adaptation="reduced receive resolution" rx_bitrate=1460kbps
2026-02-18T09:16:31.447Z INFO  media path=udp/9000 loss_rx=1.2% jitter_rx=22ms rtt=176ms message="media recovered"

# 3) Check local audio device enumeration when users report no audio device
ncmeetctl devices audio --verbose

Audio input devices:
  [0] NC-Array Microphone            status=available default=true  sample_rate=48000
Audio output devices:
  [0] NC-Desk Speakers               status=available default=true  sample_rate=48000
Result: OK

# Example failure output for MTG-MED-4105
ncmeetctl devices audio --verbose

Audio input devices:
  none
Audio output devices:
  none
Result: ERROR code=MTG-MED-4105 message="No Audio Device Detected"

# 4) Validate signalling to the NetCore Meet service over TCP 443
ncnetcheck tcp --host meet-edge.netcore.example --port 443 --count 3

Target                 Port  Attempt  Result   RTT
meet-edge.netcore.example 443   1        open     38 ms
meet-edge.netcore.example 443   2        open     37 ms
meet-edge.netcore.example 443   3        open     39 ms
Summary: tcp/443 reachable, avg_rtt=38 ms

# 5) Validate preferred media path over UDP 9000
ncnetcheck udp --host media-edge.netcore.example --port 9000 --duration 20s --rate 100pps

Target                  Port  Sent  Received  Loss   Avg jitter  Avg RTT
media-edge.netcore.example 9000  2000  1988      0.6%   11 ms       42 ms
Result: PASS thresholds latency<300ms jitter<40ms packet_loss<3%

# Example failed UDP 9000 test
ncnetcheck udp --host media-edge.netcore.example --port 9000 --duration 20s --rate 100pps

Target                  Port  Sent  Received  Loss    Avg jitter  Avg RTT
media-edge.netcore.example 9000  2000  1716      14.2%   67 ms       91 ms
Result: FAIL reason="packet_loss>=3%; jitter>=40ms"

# 6) Validate fallback media path over TCP 5004
ncnetcheck tcp --host media-edge.netcore.example --port 5004 --count 3

Target                  Port  Attempt  Result   RTT
media-edge.netcore.example 5004  1        open     45 ms
media-edge.netcore.example 5004  2        open     44 ms
media-edge.netcore.example 5004  3        open     46 ms
Summary: tcp/5004 reachable, avg_rtt=45 ms

# 7) Capture an active flow summary during the meeting
ncmeetctl session stats --meeting 784-221-903 --interval 5s --samples 3

Time                  Transport  Send kbps  Recv kbps  Loss Rx  Jitter Rx  RTT   Video Rx
2026-02-18T09:20:05Z  UDP/9000    820        7420       0.8%     18 ms      52 ms  3x HD
2026-02-18T09:20:10Z  UDP/9000    836        7488       0.7%     17 ms      51 ms  3x HD
2026-02-18T09:20:15Z  UDP/9000    811        7362       0.9%     19 ms      53 ms  3x HD
Result: PASS

# 8) Check site-edge QoS markings on an uplink interface
ncedge qos counters show interface xe-0/0/1 class media

Interface: xe-0/0/1
Class: media
Recommended marking: DSCP 46 for real-time media, DSCP 24 for meeting signalling
Packets matched      : 1842392
Packets remarked     : 0
Packets dropped      : 0
Queue depth current  : 7
Queue depth peak     : 34
Last clear           : 2026-02-18T08:00:00Z
Result: PASS
```

## Resolution

Apply the resolution that matches the diagnostic result. After each change, ask the user to remain in the same meeting for at least five minutes and confirm that packet loss remains below 3%, jitter remains below 40 ms, and latency remains below 300 ms.

For MTG-MED-4102 Media Path Degraded (high packet loss), prioritize stabilizing UDP 9000 media. TCP 5004 is a supported fallback, but it should not be the preferred steady-state path for high-quality meetings when UDP 9000 can be permitted.

For QoS, NetCore recommends marking real-time media with DSCP 46 and meeting signalling with DSCP 24 on managed enterprise networks. Preserve markings across access, distribution, WAN, and internet-edge policies where the organization controls those hops. Do not remark all meeting traffic to a single best-effort class if the site is congested.

- If packet loss is high on Wi-Fi, move the endpoint to wired access or a stronger access point, then re-test UDP 9000.
- If site utilization is high, reduce non-critical bulk traffic during the meeting window or increase access/WAN capacity.
- If UDP 9000 is blocked, update firewall policy to allow outbound UDP 9000 for NetCore Meet media and retain TCP 5004 fallback.
- If TCP 443 signalling is unstable, correct the firewall, inspection, or routing policy before troubleshooting media adaptation.
- If the client is using TCP 5004 even though UDP 9000 tests pass, restart the client and rejoin the meeting to re-establish the preferred media path.
- If bandwidth is insufficient, reduce active HD video streams. Estimate approximately 2.5 Mbps per HD stream received or sent.
- If MTG-MED-4105 No Audio Device Detected appears, reconnect the device, confirm operating system microphone/speaker permissions, select the correct device in NetCore Meet, and restart the desktop or web client.
- If only one participant is affected, update the NetCore Meet 5.0 client, collect diagnostics, and compare with a known-good endpoint on the same network.
- If multiple participants at one location are affected, check the site edge interface, QoS queues, firewall session table, and UDP 9000 policy.
- If a join failure is observed instead of degraded in-meeting media, stop this runbook and use KB-MTG-2007.

*Resolution verification checklist*

| Check | Passing value | Where to verify |
|---|---|---|
| Signalling | TCP 443 reachable | ncnetcheck tcp or site firewall logs |
| Preferred media | UDP 9000 reachable and selected by client | In-meeting statistics or ncmeetctl session stats |
| Fallback media | TCP 5004 reachable | ncnetcheck tcp |
| Latency | Below 300 ms | In-meeting statistics |
| Jitter | Below 40 ms | In-meeting statistics |
| Packet loss | Below 3% | In-meeting statistics |
| HD stream bandwidth | Approximately 2.5 Mbps per HD video stream available | Client statistics and access link utilization |
| Audio device | At least one input and one output device available | NetCore Meet device picker or ncmeetctl devices audio |

```text
Example firewall policy intent for a managed site edge:

policy NETCORE-MEET-OUTBOUND
  source-zone inside
  destination-zone internet
  applications:
    netcore-meet-signalling tcp/443
    netcore-meet-media-udp udp/9000
    netcore-meet-media-fallback tcp/5004
  action allow
  log session-start session-end

qos-policy NETCORE-MEET-QOS
  match application netcore-meet-media-udp set-dscp 46 queue real-time
  match application netcore-meet-signalling set-dscp 24 queue control
  preserve-dscp true

Expected post-change validation:
2026-02-18T10:05:00Z client=NC-WIN-042 transport=UDP/9000 loss_rx=0.4% jitter_rx=13ms rtt=48ms alarm=none
```

## Escalation Criteria

Escalate to NetCore Meet platform support only after local endpoint, device, and network requirements have been validated. Include objective measurements and timestamps so support can correlate client diagnostics with service-side media telemetry.

If the issue involves meeting capacity, licence limits, or expected bandwidth planning rather than a fault condition, consult KB-MTG-2010 before escalation.

- Escalate immediately if multiple unrelated sites report MTG-MED-4102 Media Path Degraded (high packet loss) during the same time window and local tests show UDP 9000, TCP 5004, and TCP 443 are reachable.
- Escalate if packet loss remains at or above 3%, jitter remains at or above 40 ms, or latency remains at or above 300 ms after firewall, QoS, and access-network remediation.
- Escalate if the client reports UDP 9000 selected, measured path quality is within requirements, but users still experience persistent frozen video or unusable audio.
- Escalate if MTG-MED-4105 No Audio Device Detected persists after confirming the device is present in the operating system, selected in NetCore Meet, and functional in a local test recording.
- Attach the diagnostic bundle, meeting ID, affected user ID, client version, client type, endpoint hostname, local timezone, site name, public egress address, and exact timestamps of user impact.
- Include in-meeting statistics showing send/receive bitrate, loss, jitter, latency, transport, and active HD stream count.
- Include firewall and QoS evidence showing TCP 443, UDP 9000, and TCP 5004 handling, plus any DSCP remarking or drops on the site edge.

```text
Escalation data example:

Case title: MTG-MED-4102 at NYC-03 site during executive meeting
Product/release: NetCore Meet 5.0
Meeting ID: 784-221-903
Impact window: 2026-02-18 09:12-09:21 UTC
Affected clients: NC-WIN-042, NC-MAC-117, NC-WIN-088
Client versions: 5.0.318 desktop app
Observed alarm: MTG-MED-4102 Media Path Degraded (high packet loss)
Statistics at impact: loss_rx=4.8%, jitter_rx=56ms, rtt=184ms, transport=UDP/9000
Post-remediation stats: loss_rx=0.6%, jitter_rx=11ms, rtt=42ms, transport=UDP/9000
Ports validated: TCP/443 pass, UDP/9000 pass after policy change, TCP/5004 pass
QoS: DSCP 46 media preserved, DSCP 24 signalling preserved, no queue drops after 09:30 UTC
Attachments: mtg-2006-case-18422.zip, site-edge-qos-20260218.txt, firewall-sessions-20260218.csv
```

## Related Articles

- KB-MTG-2007: Troubleshooting Meeting Join Failures (MTG-JOIN-1003 / MTG-JOIN-1007)
- KB-MTG-2010: FAQ: Licensing, Limits and Network Requirements
