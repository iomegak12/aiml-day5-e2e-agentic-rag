---
kb_id: "KB-NET-1009"
title: "SD-WAN FAQ: Transports, Failover and SLA Reports"
domain: "networking"
article_type: "faq"
product: "NetCore SD-WAN"
version: "5.0"
status: "current"
superseded_by: ""
last_updated: "2026-08-25"
error_codes: []
related: ["KB-NET-1002", "KB-NET-1003"]
tags: ["faq", "sla", "reporting"]
author: "NetCore Systems Technical Support"
format: "md"
---

# SD-WAN FAQ: Transports, Failover and SLA Reports

**KB-NET-1009** | NetCore SD-WAN 5.0 | Last updated: 2026-08-25 | Status: current

## Summary

This FAQ answers common NetCore SD-WAN 5.0 questions about MPLS, Internet broadband, and LTE/5G transports, automatic failover timing, SLA reporting in NetCore Orchestrator, and report export. It also summarizes the operational differences between release 4.2 and 5.0 for SLA breach detection and failover behavior.

**Applies to:** NetCore SD-WAN 5.0, NetCore Orchestrator, NCX-1000 branch edge, NCX-4000 regional hub, NCX-9000 data center edge

## Overview

NetCore SD-WAN 5.0 monitors MPLS, Internet broadband, and LTE/5G transports using BFD probes and application-route SLA measurements. When a transport exceeds the configured SLA class thresholds for three consecutive 120-second polling intervals, NetCore SD-WAN declares an SLA breach after approximately 6 minutes and automatically fails traffic over to the best compliant transport.

Use KB-NET-1002 for the complete SLA class threshold reference and KB-NET-1003 for breach escalation, ticketing, and auto-failover behavior.

## Useful edge CLI checks

The following commands are commonly used with the FAQ answers below when validating local edge state before or after checking NetCore Orchestrator reports.

```text
ncx-edge# show sdwan app-route statistics
ncx-edge# show sdwan bfd sessions
ncx-edge# show sdwan sla-class
ncx-edge# show sdwan control connections
ncx-edge# show policy qos-queue counters
```

## Frequently Asked Questions

**Q: Which transport types can NetCore SD-WAN 5.0 use?**

A: NetCore SD-WAN 5.0 supports MPLS, Internet broadband, and LTE/5G transports. Any of these can be used for active forwarding, backup forwarding, or application-specific steering depending on the site policy configured in NetCore Orchestrator.

**Q: How does NetCore SD-WAN determine whether a transport is healthy?**

A: Tunnels are monitored with BFD probes, and application paths are measured against the assigned SLA class for latency, jitter, and packet loss. On an edge device, use ncx-edge# show sdwan bfd sessions to verify tunnel liveness and ncx-edge# show sdwan app-route statistics to confirm measured latency, jitter, and loss.

**Q: What are the default SLA thresholds in release 5.0?**

A: Voice requires latency <= 150 ms, jitter <= 30 ms, and loss <= 1%. Video requires latency <= 200 ms, jitter <= 40 ms, and loss <= 2%. Business-Critical requires latency <= 250 ms, jitter <= 50 ms, and loss <= 3%. Best-Effort requires latency <= 400 ms and loss <= 5%; jitter is not applicable for Best-Effort. For the full reference, see KB-NET-1002.

**Q: How long does automatic failover take after an SLA problem starts?**

A: In NetCore SD-WAN 5.0, the app-route poll interval is 120 seconds and the multiplier is 3. A breach is declared after 3 consecutive failed intervals, which is approximately 6 minutes. After the breach is declared, traffic is automatically moved to the best compliant transport according to policy. See KB-NET-1003 for escalation and failover details.

**Q: Does failover happen after one bad probe or one brief latency spike?**

A: No. A single bad poll is not enough to trigger an SLA breach. NetCore SD-WAN 5.0 requires 3 consecutive 120-second intervals outside the SLA threshold before declaring the breach. This avoids unnecessary failover caused by short transient spikes.

**Q: What happens if more than one transport is compliant?**

A: NetCore SD-WAN selects the best compliant transport according to the application-route policy and current measurements. For example, if Voice traffic is currently on Internet broadband and both MPLS and LTE/5G meet the Voice SLA, the policy preference decides which compliant path is selected.

**Q: Where can I view SLA status in NetCore Orchestrator?**

A: In NetCore Orchestrator, open the site, select the edge device, and review the application-route or SLA monitoring view for per-transport latency, jitter, loss, and compliance status. For local confirmation on an NCX edge, run ncx-edge# show sdwan app-route statistics and compare the output to the SLA class values shown by ncx-edge# show sdwan sla-class.

**Q: Can I export SLA reports from NetCore Orchestrator?**

A: Yes. In NetCore Orchestrator, open the SLA reporting view, select the site, application or SLA class, transport, and time range, then use the report export option. Common operational exports include daily site SLA summaries, per-transport compliance reports, and incident-window reports for a specific 30-minute or 1-hour period.

**Q: What is the difference between release 4.2 and 5.0 for SLA breach handling?**

A: Release 5.0 uses a 120-second poll interval with multiplier 3, so a breach is declared after approximately 6 minutes. It supports automatic failover to the best compliant transport, opens an ITSM ticket automatically, starts at Sev3, escalates to Sev2 if the breach persists for more than 15 minutes, and escalates to Sev1 if it persists for more than 30 minutes or affects 5 or more sites. Release 4.2 used a 600-second poll interval with multiplier 5, so breach detection took approximately 50 minutes, required manual failover, and sent e-mail notification only with no automatic severity escalation.

**Q: Which alarms or events may appear while investigating transport, failover, or reporting issues?**

A: This FAQ is not driven by a single required alarm code, but related operational events can include NCS-SLA-2001 SLA Violation Detected, NCS-SLA-2002 SLA Restored, NCS-BFD-3004 BFD Session Flap, NCS-BFD-3005 BFD Session Down, NCS-ZTP-4001 ZTP Redirect Failed, NCS-ZTP-4003 Device Certificate Validation Failed, NCS-QOS-5002 Queue Drop Threshold Exceeded, and NCS-ORC-6001 Orchestrator Control Connection Lost. Use SLA and BFD events first for path-health triage; use control, ZTP, and QoS events only when the symptoms point to onboarding, management connectivity, or queue congestion.

**Q: What should I check if Orchestrator reports an SLA breach but users report no outage?**

A: Check whether automatic failover already moved the application to another compliant transport. In Orchestrator, compare the breach start time, selected transport, and restored time. On the edge, run ncx-edge# show sdwan app-route statistics and ncx-edge# show sdwan bfd sessions. If loss or latency is now within the target SLA and the application is on a compliant path, the user impact may have been avoided by the 5.0 auto-failover behavior described in KB-NET-1003.

**Q: What should I collect before opening an internal escalation?**

A: Collect the affected site name, edge model, transport names, application or SLA class, breach start and end timestamps, Orchestrator SLA export, and CLI outputs from ncx-edge# show sdwan app-route statistics, ncx-edge# show sdwan bfd sessions, ncx-edge# show sdwan sla-class, and ncx-edge# show sdwan control connections. If packet drops are suspected, also include ncx-edge# show policy qos-queue counters.

## Related Articles

- KB-NET-1002: SLA Class Thresholds Reference (Latency, Jitter, Loss)
- KB-NET-1003: SLA Breach Policy: Escalation and Auto-Failover
