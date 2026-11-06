---
kb_id: "KB-MTG-2007"
title: "Troubleshooting Meeting Join Failures (MTG-JOIN-1003 / MTG-JOIN-1007)"
domain: "meetings"
article_type: "runbook"
product: "NetCore Meet"
version: "5.0"
status: "current"
superseded_by: ""
last_updated: "2026-08-27"
error_codes: ["MTG-JOIN-1003", "MTG-JOIN-1007", "MTG-SSO-6001"]
related: ["KB-MTG-2003", "KB-MTG-2006", "KB-MTG-2010"]
tags: ["troubleshooting", "join", "firewall"]
author: "NetCore Systems Technical Support"
format: "md"
---

# Troubleshooting Meeting Join Failures (MTG-JOIN-1003 / MTG-JOIN-1007)

**KB-MTG-2007** | NetCore Meet 5.0 | Last updated: 2026-08-27 | Status: current

## Summary

Runbook for NetCore Meet 5.0 meeting join failures reported as MTG-JOIN-1003, MTG-JOIN-1007, or MTG-SSO-6001. Use these checks to separate policy/lobby conditions, media firewall failures, proxy/TCP 443 signalling problems, and SSO assertion issues before escalating.

**Applies to:** NetCore Meet 5.0, NetCore Meet desktop app for Windows and macOS, NetCore Meet mobile app, NetCore Meet web client, NetCore Control Hub, Meet Starter, Meet Business, Meet Enterprise

## Symptoms

Users cannot enter a NetCore Meet meeting or remain stuck at the pre-join screen. The client may show one of the following primary join errors: MTG-JOIN-1003 Meeting Locked or Host Lobby Active, MTG-JOIN-1007 Media Ports Blocked by Firewall, or MTG-SSO-6001 SAML Assertion Invalid or Expired.

A user may also report that sign-in succeeds but the Join button loops, the browser prompts repeatedly for authentication, or the client joins the meeting shell but cannot establish media. For post-join audio/video quality problems, including MTG-MED-4102 Media Path Degraded (high packet loss), see KB-MTG-2006.

Related codes not covered by this runbook include MTG-MED-4105 No Audio Device Detected, MTG-SSO-6004 IdP Certificate Mismatch, MTG-CALL-7002 Number Not Provisioned, and MTG-CALL-7010 Emergency Address Missing.

- MTG-JOIN-1003: User is blocked by a locked meeting, active host lobby, or expected lobby behavior for external participants.
- MTG-JOIN-1007: Client cannot establish the required media path, usually because UDP 9000 is blocked and TCP 5004 fallback is also unavailable or impaired.
- MTG-SSO-6001: The SAML assertion used to authenticate the user is invalid, expired, has a clock-skew issue, or does not match the expected user/session context.
- Proxy-related symptom: TCP 443 signalling appears intermittent, the client cannot retrieve meeting metadata, or authentication loops occur when the proxy challenges or rewrites session traffic.

## Impact

Impact depends on where the join process fails. MTG-JOIN-1003 is usually isolated to a meeting policy or host action, while MTG-JOIN-1007 and proxy issues can affect multiple users at the same site or subnet. MTG-SSO-6001 usually affects a user population tied to the same identity configuration or a device with incorrect time.

NetCore Meet 5.0 requires TCP 443 for signalling, UDP 9000 for preferred media, and TCP 5004 as media fallback. Recommended network conditions are latency below 300 ms, jitter below 40 ms, and packet loss below 3%. Each HD video stream uses approximately 2.5 Mbps.

- Single user affected: check meeting state, user authentication session, client cache, local firewall, and device clock.
- Multiple users on one network affected: check egress policy for TCP 443, UDP 9000, TCP 5004, proxy authentication, and packet filtering.
- All external guests affected: review lobby and meeting policy behavior in NetCore Control Hub; external participants wait in the lobby by default in release 5.0.
- All users in one identity domain affected: validate SAML assertion lifetime, signing configuration, and system time alignment.

## Probable Causes

Use the cause-to-action table to select the fastest remediation path. Do not assume that all join failures are network failures; MTG-JOIN-1003 is commonly a meeting state or lobby policy condition.

*Cause-to-action matrix for NetCore Meet 5.0 join failures*

| Observed condition | Probable cause | Primary action | Reference |
|---|---|---|---|
| Client displays MTG-JOIN-1003 Meeting Locked or Host Lobby Active | Meeting is locked, host has not admitted the user, or external participant is waiting in the lobby by default | Ask host to unlock the meeting or admit the user; verify lobby policy in NetCore Control Hub | KB-MTG-2003 |
| Client displays MTG-JOIN-1007 Media Ports Blocked by Firewall | UDP 9000 blocked and TCP 5004 fallback blocked or failing | Allow outbound UDP 9000 and TCP 5004; keep TCP 443 open for signalling | KB-MTG-2010 |
| Join page loads, then loops or stalls before lobby | Proxy challenges, session rewriting, or TCP 443 inspection interferes with signalling | Bypass authentication/inspection for NetCore Meet signalling over TCP 443 or apply the approved enterprise proxy exception | KB-MTG-2010 |
| User is redirected to sign in repeatedly; client logs show MTG-SSO-6001 SAML Assertion Invalid or Expired | Expired assertion, incorrect system time, stale session, or invalid SAML audience/session context | Correct device time, clear cached sign-in state, and validate SAML assertion lifetime with the identity team | This article |
| User joins but audio/video later degrades | Network quality issue after join, such as high packet loss | Troubleshoot MTG-MED-4102 Media Path Degraded (high packet loss) separately | KB-MTG-2006 |

## Diagnostic Steps

Run diagnostics from the affected user endpoint first, then from a known-good endpoint on the same subnet. Capture timestamps in UTC where possible so that client logs, Control Hub audit events, and network firewall logs can be correlated.

The following examples use the fictional diagnostic utility ncmeetdiag and standard shell commands. Replace the meeting ID, user, and interface names with the affected values.

- Confirm the exact error string and timestamp shown to the user.
- Record client type: desktop app, mobile app, or web client.
- Record source network: office, home, VPN, guest wireless, or cellular.
- Confirm meeting ID, host, user account, and whether the user is internal or external.
- Check whether the issue reproduces from another network. If it works from cellular but fails on office LAN, prioritize firewall or proxy checks.

```bash
# 1. Capture client and meeting context
ncmeetdiag client-info

# Sample output
NetCore Meet Diagnostic Utility 5.0.118
Client: NetCore Meet desktop app
OS: NetCore Workstation 12.4
User: alex.rivera@example.internal
UTC time: 2026-11-06T14:22:31Z
Network interface: en0
Client session ID: ncm-5f34a0c9-8b6e-4a31-b4ef-1027d9fbd892

# 2. Check meeting join state for policy/lobby causes
ncmeetdiag meeting-check --meeting 847-552-019 --user alex.rivera@example.internal

# Sample output for MTG-JOIN-1003
Meeting ID: 847-552-019
Host: dana.cho@example.internal
Meeting state: active
Lock state: locked
Lobby state: host_lobby_active
Participant classification: external
Result: BLOCKED
Error: MTG-JOIN-1003 Meeting Locked or Host Lobby Active
Recommended action: Ask host to admit participant or unlock meeting.

# 3. Check signalling over TCP 443
ncmeetdiag path-test --service meet-signalling --tcp 443 --count 5

# Sample healthy output
Target service: meet-signalling
Protocol/port: TCP/443
Attempt 1: connected in 42 ms
Attempt 2: connected in 45 ms
Attempt 3: connected in 43 ms
Attempt 4: connected in 44 ms
Attempt 5: connected in 43 ms
Result: PASS

# Sample proxy/interception symptom
Target service: meet-signalling
Protocol/port: TCP/443
Attempt 1: proxy_auth_required
Attempt 2: tls_session_rewritten
Attempt 3: proxy_auth_required
Result: FAIL
Finding: Signalling session cannot be established reliably through configured proxy.

# 4. Check media reachability on UDP 9000 and TCP 5004 fallback
ncmeetdiag path-test --service meet-media --udp 9000 --tcp-fallback 5004 --count 10

# Sample output for MTG-JOIN-1007
Target service: meet-media
Preferred media: UDP/9000
Fallback media: TCP/5004
UDP/9000: blocked, 0/10 responses
TCP/5004: blocked, connection timeout after 3000 ms
Result: FAIL
Error: MTG-JOIN-1007 Media Ports Blocked by Firewall
Recommended action: Permit outbound UDP/9000 and TCP/5004 to NetCore Meet media services.

# 5. Validate current path quality when ports are open
ncmeetdiag media-probe --duration 30 --interface en0

# Sample healthy output
Probe duration: 30 seconds
Interface: en0
Latency avg/max: 58 ms / 82 ms
Jitter avg/max: 9 ms / 16 ms
Packet loss: 0.4%
Estimated HD streams supported: 3
Result: PASS

# 6. Inspect SSO assertion status for MTG-SSO-6001
ncmeetdiag sso-check --user alex.rivera@example.internal

# Sample output
Identity method: SAML
Assertion issue time: 2026-11-06T13:18:02Z
Assertion expiry: 2026-11-06T13:23:02Z
Endpoint UTC time: 2026-11-06T14:24:18Z
Clock skew: +00:00:04
Audience: netcore-meet-5
Result: FAIL
Error: MTG-SSO-6001 SAML Assertion Invalid or Expired
Recommended action: Clear cached sign-in state and obtain a new assertion; verify SAML assertion lifetime if recurrence is reported.
```

## Diagnostic Steps - Endpoint Network Commands

If ncmeetdiag is unavailable, use endpoint commands to confirm the same findings. These commands do not replace firewall logs, but they quickly show whether the endpoint can initiate required outbound sessions.

- TCP 443 must be reachable for signalling.
- UDP 9000 is the preferred media path.
- TCP 5004 is the fallback media path when UDP media cannot be used.
- If both UDP 9000 and TCP 5004 fail, expect MTG-JOIN-1007.
- If TCP 443 requires proxy authentication or is rewritten, the user may see join loops or SSO failures before media is attempted.

```bash
# macOS/Linux-style endpoint checks
nc -vz meet-edge.netcore.example 443
# expected: Connection to meet-edge.netcore.example 443 port [tcp/https] succeeded!

nc -vz meet-media.netcore.example 5004
# expected: Connection to meet-media.netcore.example 5004 port [tcp/*] succeeded!

# UDP does not establish a TCP-style session; send a probe and check for a response in ncmeetdiag or firewall logs.
nc -vzu meet-media.netcore.example 9000
# expected from an allowed path: UDP probe sent without local block; confirm pass with ncmeetdiag media probe.

# Windows-style endpoint checks
Test-NetConnection meet-edge.netcore.example -Port 443

# Sample output
ComputerName     : meet-edge.netcore.example
RemotePort       : 443
InterfaceAlias   : Ethernet0
SourceAddress    : 10.40.18.72
TcpTestSucceeded : True

Test-NetConnection meet-media.netcore.example -Port 5004

# Sample output when fallback is blocked
ComputerName     : meet-media.netcore.example
RemotePort       : 5004
InterfaceAlias   : Ethernet0
SourceAddress    : 10.40.18.72
TcpTestSucceeded : False
```

## Diagnostic Steps - Log Collection

Collect logs before restarting the client if the issue is intermittent. For enterprise incidents, collect the client session ID, meeting ID, user ID, public source IP, local source IP, and exact UTC timestamp of the failed join attempt.

- Desktop app logs are preferred for MTG-JOIN-1007 because they include media path negotiation details.
- Web client logs are preferred for proxy and SSO loop investigations because they show browser session handling and TCP 443 failures.
- NetCore Control Hub audit events are preferred for MTG-JOIN-1003 because they show host lock/unlock actions and lobby admission events.

```bash
# Export desktop client logs
ncmeetdiag collect-logs --since "2026-11-06T14:00:00Z" --output ./ncm-join-failure-847552019.zip

# Sample output
Collecting NetCore Meet logs...
Included: client-info.json
Included: signalling.log
Included: media-negotiation.log
Included: sso-events.log
Included: policy-cache.json
Archive: ./ncm-join-failure-847552019.zip
SHA256: 7b6c1df0b1f5d0a4a0f2b5a0cba9814c70f9b118ed72c6a51c91306d3a0e5a22
Result: COMPLETE

# Query Control Hub audit events for meeting state
nccontrol audit search --product meet --meeting 847-552-019 --from 2026-11-06T14:00:00Z --to 2026-11-06T14:30:00Z

# Sample output
2026-11-06T14:03:11Z  dana.cho@example.internal  meeting.lock.enabled   meeting=847-552-019
2026-11-06T14:19:46Z  alex.rivera@example.internal lobby.waiting          meeting=847-552-019
2026-11-06T14:21:02Z  dana.cho@example.internal  lobby.admit.denied      meeting=847-552-019
2026-11-06T14:22:08Z  client-session=ncm-5f34a0c9 error=MTG-JOIN-1003
```

## Resolution

Apply the resolution that matches the confirmed cause. After each change, retest using the same meeting if still active, or use a new test meeting with the same host, participant type, and network path.

- For MTG-JOIN-1003 Meeting Locked or Host Lobby Active: Ask the host to admit the participant from the lobby or unlock the meeting. In NetCore Control Hub, review the meeting policy that controls lobby behavior. External participants wait in the lobby by default in NetCore Meet 5.0; for policy details, see KB-MTG-2003.
- For MTG-JOIN-1007 Media Ports Blocked by Firewall: Permit outbound UDP 9000 for preferred media and TCP 5004 for fallback media. Keep TCP 443 open for signalling. Retest with ncmeetdiag path-test and confirm that UDP 9000 passes or, at minimum, TCP 5004 fallback succeeds.
- For proxy-related join loops: Ensure the endpoint can establish stable TCP 443 signalling sessions. Configure the enterprise proxy so NetCore Meet signalling traffic is not blocked by authentication challenges, session rewriting, or policy that changes during the join flow. Retest from the same user and subnet.
- For MTG-SSO-6001 SAML Assertion Invalid or Expired: Correct the endpoint clock if inaccurate, clear the user’s cached sign-in state, and have the user sign in again to obtain a fresh assertion. If many users are affected, ask the identity administration team to verify SAML assertion lifetime and audience/session configuration for NetCore Meet 5.0.
- For network quality problems after successful join: Do not continue this join-failure runbook. Use KB-MTG-2006 for MTG-MED-4102 Media Path Degraded (high packet loss).
- For licensing and participant-limit questions, including Meet Starter 100 participants, Meet Business 300 participants, Meet Enterprise 1000 participants, and webinar add-on capacity up to 10,000 view-only attendees, see KB-MTG-2010.

```bash
# Example enterprise edge policy snippet for NetCore Meet 5.0 egress
# Apply to user VLANs that host NetCore Meet clients.
policy NETCORE-MEET-EGRESS
  rule 10 permit tcp any service meet-signalling destination-port 443 log enable
  rule 20 permit udp any service meet-media destination-port 9000 log enable
  rule 30 permit tcp any service meet-media destination-port 5004 log enable
  rule 90 deny ip any any log enable
commit

# Validate after change
ncmeetdiag path-test --service meet-signalling --tcp 443 --count 5
ncmeetdiag path-test --service meet-media --udp 9000 --tcp-fallback 5004 --count 10

# Expected post-change summary
Signalling TCP/443: PASS
Media UDP/9000: PASS
Media TCP/5004 fallback: PASS
Overall join readiness: PASS
```

## Escalation Criteria

Escalate when the local remediation path is complete but the user still cannot join, or when logs indicate a service-side policy or identity state that cannot be corrected by the meeting host, network team, or collaboration administrator.

- Escalate to the collaboration administration team if MTG-JOIN-1003 continues after the host confirms the meeting is unlocked and the participant has been admitted from the lobby. Include Control Hub audit output and the meeting ID.
- Escalate to the enterprise network team if MTG-JOIN-1007 is reproduced from two or more endpoints on the same network, or if UDP 9000 and TCP 5004 fail from the endpoint. Include source IP, subnet, firewall rule IDs, and ncmeetdiag path-test output.
- Escalate to the identity administration team if MTG-SSO-6001 affects multiple users or recurs after clearing cached sign-in state and correcting endpoint time. Include sso-check output, assertion issue/expiry timestamps, and affected user IDs.
- Escalate to NetCore Systems support if the issue reproduces on a compliant network where TCP 443, UDP 9000, and TCP 5004 pass; the client logs show the same join error across desktop and web clients; or Control Hub audit records show contradictory meeting state.
- Attach the log archive created by ncmeetdiag collect-logs, the client session ID, meeting ID, user ID, UTC timestamps, client version, network test output, and a statement of whether the user is internal or external.

```text
Escalation packet example

Product: NetCore Meet 5.0
Error: MTG-JOIN-1007 Media Ports Blocked by Firewall
Meeting ID: 847-552-019
Client session ID: ncm-5f34a0c9-8b6e-4a31-b4ef-1027d9fbd892
User: alex.rivera@example.internal
Client: NetCore Meet desktop app 5.0.118
Failure time: 2026-11-06T14:22:08Z
Source IP: 10.40.18.72
Network: HQ-USER-VLAN-40
TCP 443 signalling: PASS
UDP 9000 media: FAIL before change, PASS after rule update
TCP 5004 fallback: FAIL before change, PASS after rule update
Logs: ncm-join-failure-847552019.zip
Related KBs reviewed: KB-MTG-2003, KB-MTG-2006, KB-MTG-2010
```

## Related Articles

- KB-MTG-2003: Meeting Policy Reference: Recording, Lobby and Retention
- KB-MTG-2006: Troubleshooting Audio and Video Quality (MTG-MED-4102)
- KB-MTG-2010: FAQ: Licensing, Limits and Network Requirements
