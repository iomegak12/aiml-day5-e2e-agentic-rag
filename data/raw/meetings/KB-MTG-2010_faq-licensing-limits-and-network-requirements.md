---
kb_id: "KB-MTG-2010"
title: "FAQ: Licensing, Limits and Network Requirements"
domain: "meetings"
article_type: "faq"
product: "NetCore Meet"
version: "5.0"
status: "current"
superseded_by: ""
last_updated: "2026-08-11"
error_codes: []
related: ["KB-MTG-2006", "KB-MTG-2007"]
tags: ["faq", "licensing", "network"]
author: "NetCore Systems Technical Support"
format: "md"
---

# FAQ: Licensing, Limits and Network Requirements

**KB-MTG-2010** | NetCore Meet 5.0 | Last updated: 2026-08-11 | Status: current

## Summary

This FAQ summarizes NetCore Meet 5.0 licensing limits, webinar capacity, required network ports, media bandwidth planning, and recommended latency, jitter, and packet-loss targets. It also highlights operational differences between release 4.2 and 5.0 that affect recording retention, legal hold, transcripts, and external participant lobby behavior.

**Applies to:** NetCore Meet 5.0, NetCore Control Hub, Meet Starter, Meet Business, Meet Enterprise, Webinar add-on, NetCore Meet desktop app for Windows and macOS, NetCore Meet mobile app, NetCore Meet web client

## Overview

Use this FAQ when planning NetCore Meet 5.0 licence assignment, meeting capacity, webinar sizing, firewall rules, and WAN readiness. Participant limits are enforced by licence tier, while media quality depends on allowing the required signalling and media paths and keeping latency, jitter, and packet loss within recommended values.

This article is informational and does not diagnose specific alarms. For media-quality troubleshooting, see KB-MTG-2006. For join and firewall-related meeting access failures, see KB-MTG-2007.

*NetCore Meet 5.0 quick reference*

| Item | Requirement or limit |
|---|---|
| Meet Starter | Up to 100 participants |
| Meet Business | Up to 300 participants |
| Meet Enterprise | Up to 1000 participants |
| Webinar add-on | Up to 10,000 view-only attendees |
| Signalling | TCP 443 |
| Preferred media | UDP 9000 |
| Media fallback | TCP 5004 |
| Recommended latency | < 300 ms |
| Recommended jitter | < 40 ms |
| Recommended packet loss | < 3% |
| HD video bandwidth | ~2.5 Mbps per HD video stream |

```text
netcore-edge01# show policy NETCORE-MEET-EGRESS
Policy: NETCORE-MEET-EGRESS
  10 permit tcp any service 443    remark NetCore Meet signalling
  20 permit udp any service 9000   remark NetCore Meet media preferred
  30 permit tcp any service 5004   remark NetCore Meet media fallback
  90 deny   ip any any log

netcore-edge01# test path-monitor meet-probe branch-sfo01
Timestamp: 2026-11-06T09:15:22Z
Target service: NetCore Meet
TCP/443: pass, rtt 42 ms
UDP/9000: pass, rtt 39 ms, jitter 8 ms, loss 0.2%
TCP/5004: pass, rtt 43 ms
Result: ready
```

## Error and alarm code references

No error or alarm code is covered as a primary diagnostic in this FAQ. If an operator is redirected here from an alert, use the code-specific article instead.

Relevant NetCore Meet codes include MTG-JOIN-1003 Meeting Locked or Host Lobby Active, MTG-JOIN-1007 Media Ports Blocked by Firewall, MTG-MED-4102 Media Path Degraded (high packet loss), MTG-MED-4105 No Audio Device Detected, MTG-SSO-6001 SAML Assertion Invalid or Expired, and MTG-SSO-6004 IdP Certificate Mismatch. NetCore Calling codes MTG-CALL-7002 Number Not Provisioned and MTG-CALL-7010 Emergency Address Missing are not used for NetCore Meet meeting-capacity or media-readiness checks.

For MTG-MED-4102 Media Path Degraded (high packet loss), see KB-MTG-2006. For MTG-JOIN-1003 Meeting Locked or Host Lobby Active and MTG-JOIN-1007 Media Ports Blocked by Firewall, see KB-MTG-2007.

## Frequently Asked Questions

**Q: What are the participant limits for each NetCore Meet 5.0 licence tier?**

A: Meet Starter supports up to 100 participants, Meet Business supports up to 300 participants, and Meet Enterprise supports up to 1000 participants in a meeting. These limits are enforced by the licensed host’s assigned tier in NetCore Control Hub.

**Q: Does the webinar add-on increase the standard interactive meeting participant limit?**

A: No. The webinar add-on provides webinar capacity for up to 10,000 view-only attendees. It does not convert all attendees into interactive meeting participants; the host’s Meet Starter, Meet Business, or Meet Enterprise participant limit still applies to the interactive meeting portion.

**Q: How much bandwidth should I plan for HD video?**

A: Plan for approximately 2.5 Mbps per HD video stream. For example, a room endpoint or desktop client sending one HD stream and receiving four active HD streams should be budgeted at roughly 12.5 Mbps for media, before adding normal LAN/WAN overhead and other business traffic.

**Q: Which ports must be allowed through the firewall?**

A: Allow TCP 443 for signalling, UDP 9000 for preferred media, and TCP 5004 for media fallback. UDP 9000 should be permitted whenever possible because it is the preferred media path for NetCore Meet.

**Q: Can NetCore Meet operate if UDP 9000 is blocked?**

A: NetCore Meet can fall back to TCP 5004 for media, provided TCP 5004 is allowed. However, UDP 9000 remains the preferred media path. If users report join failures or blocked media symptoms, validate the firewall policy and then use KB-MTG-2007 for MTG-JOIN-1007 Media Ports Blocked by Firewall.

**Q: What latency, jitter, and packet-loss values are recommended?**

A: For NetCore Meet 5.0, keep one-way or measured path latency below 300 ms, jitter below 40 ms, and packet loss below 3%. If packet loss rises above the recommended level and users report degraded audio or video, use KB-MTG-2006 for MTG-MED-4102 Media Path Degraded (high packet loss).

**Q: Do the network requirements differ between the desktop app, mobile app, and web client?**

A: The documented service requirements are the same: TCP 443 for signalling, UDP 9000 for preferred media, and TCP 5004 for media fallback. The practical bandwidth consumed still depends on how many HD video streams the client sends and receives, with planning based on approximately 2.5 Mbps per HD video stream.

**Q: What changed from NetCore Meet 4.2 to 5.0 for recordings and retention?**

A: In release 5.0, cloud recordings are retained for 365 days by default, retention is configurable from 30 to 1825 days, legal hold is supported, and auto-transcripts are enabled. In release 4.2, retention was fixed at 180 days, legal hold was not supported, and transcripts were not available.

**Q: What changed from NetCore Meet 4.2 to 5.0 for external participant access?**

A: In NetCore Meet 5.0, external participants wait in the lobby by default. If a participant cannot enter because the meeting is locked or the host is using the lobby, troubleshoot with KB-MTG-2007 for MTG-JOIN-1003 Meeting Locked or Host Lobby Active.

**Q: Where do administrators verify licence assignment and capacity?**

A: Administrators verify and assign Meet Starter, Meet Business, Meet Enterprise, and webinar add-on entitlements in NetCore Control Hub. Confirm the host’s assigned licence before treating a capacity rejection as a network or client problem.

## Related Articles

- KB-MTG-2006: Troubleshooting Audio and Video Quality (MTG-MED-4102)
- KB-MTG-2007: Troubleshooting Meeting Join Failures (MTG-JOIN-1003 / MTG-JOIN-1007)
