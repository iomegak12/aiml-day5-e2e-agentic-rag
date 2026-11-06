---
kb_id: "KB-MTG-2009"
title: "Help: Scheduling and Joining Meetings from Your Calendar"
domain: "meetings"
article_type: "help"
product: "NetCore Meet"
version: "5.0"
status: "current"
superseded_by: ""
last_updated: "2026-05-22"
error_codes: []
related: ["KB-MTG-2007", "KB-MTG-2010"]
tags: ["help", "calendar", "end-user"]
author: "NetCore Systems Technical Support"
format: "md"
---

# Help: Scheduling and Joining Meetings from Your Calendar

**KB-MTG-2009** | NetCore Meet 5.0 | Last updated: 2026-05-22 | Status: current

## Summary

Use the NetCore Meet 5.0 calendar add-in to schedule meetings directly from your calendar, update meeting options, and join with one click when it is time to meet. This article also explains how to join by dial-in, how lobby behavior works, and where to find help if a meeting does not open correctly.

**Applies to:** NetCore Meet 5.0, NetCore Meet desktop app for Windows and macOS, NetCore Meet mobile app, NetCore Meet web client, Meet Starter, Meet Business, and Meet Enterprise licences

## Before You Begin

Make sure you can sign in to NetCore Meet with your organization account. If your organization uses single sign-on, sign in with the same account you use for other internal services.

Install or update the NetCore Meet desktop app before installing the calendar add-in. The calendar add-in works best when the desktop app and calendar client are both current.

Your participant limit depends on your licence: Meet Starter supports up to 100 participants, Meet Business supports up to 300 participants, and Meet Enterprise supports up to 1000 participants. A webinar add-on can support up to 10,000 view-only attendees. For licence and network details, see KB-MTG-2010.

In NetCore Meet 5.0, external participants wait in the lobby by default. The host or a co-host must admit them unless the meeting options are changed by your organization.

## Install the Calendar Add-in for a Desktop Calendar App

Use these steps when you schedule meetings from a desktop calendar application on Windows or macOS.

- 1. Open the NetCore Meet desktop app.
- 2. Select your profile picture, then select Settings.
- 3. Select Calendar add-in.
- 4. Select Install desktop calendar add-in.
- 5. Close and reopen your calendar app when prompted.
- 6. Create a new calendar event and confirm that the Add NetCore Meet button is available in the event toolbar.
- 7. If the button is not visible, restart the NetCore Meet desktop app and your calendar app, then check again.

## Install the Calendar Add-in for a Web Calendar

Use these steps when you schedule meetings from a supported browser-based calendar.

- 1. Open the NetCore Meet web client and sign in.
- 2. Select Settings, then select Calendar add-in.
- 3. Select Install web calendar add-in.
- 4. When the browser prompts for permission, allow the add-in to read and update calendar events so it can insert meeting details.
- 5. Open your web calendar in a new browser tab.
- 6. Create a new calendar event and confirm that the Add NetCore Meet option is available.
- 7. If you do not see the option, sign out of the web calendar, sign in again, and refresh the page.

## Schedule a NetCore Meet Meeting from Your Calendar

After the add-in is installed, you can add meeting details to any calendar event. The invite includes the join link, meeting ID, and dial-in information if dial-in is enabled for your organization.

- 1. Open your calendar and create a new event.
- 2. Enter the meeting title, date, start time, end time, and attendees.
- 3. Select Add NetCore Meet.
- 4. Wait for the add-in to insert the NetCore Meet join details into the invitation body.
- 5. Optional: select Meeting options to review lobby, recording, and participant settings before sending.
- 6. Select Send or Save to deliver the invitation to attendees.
- 7. If you later change the meeting time or attendee list, update the calendar event and send the update. Do not delete the NetCore Meet join details unless you plan to add a new meeting link.

## Set Meeting Options Before Sending the Invite

Meeting options can vary by organization policy and licence. If an option is disabled, your administrator may have locked it in NetCore Control Hub.

*Common NetCore Meet 5.0 meeting options*

| Option | What it does | Typical use |
|---|---|---|
| Lobby for external participants | External participants wait in the lobby by default until admitted by the host or co-host. | Use for customer calls, interviews, and meetings with confidential content. |
| Host join behavior | Controls whether participants can enter before the host. | Use host-controlled entry for sensitive meetings. |
| Mute participants on entry | Participants join muted. | Use for large meetings or presentations. |
| Recording | Allows the host to start a cloud recording if permitted by policy. | Use when attendees need a replay or transcript. |
| Auto-transcripts | Creates a transcript for cloud recordings when recording is enabled. | Use for meeting notes, accessibility, and follow-up. |
| Participant permissions | Controls whether attendees can share content, use chat, or unmute themselves. | Use for webinars, trainings, and moderated sessions. |

## Join a Meeting from Your Calendar

The fastest way to join is from the calendar event. Join a few minutes early if you need to test your audio, camera, or network.

- 1. Open the calendar event.
- 2. Select the NetCore Meet join link or Join NetCore Meet button.
- 3. If prompted, choose whether to open the NetCore Meet desktop app, mobile app, or web client.
- 4. Confirm your display name.
- 5. Select your microphone, speaker, and camera.
- 6. Select Join.
- 7. If you are placed in the lobby, wait for the host or co-host to admit you. This is expected for external participants in NetCore Meet 5.0.

## Join by Dial-in

Dial-in is useful when you cannot use computer audio or have limited network connectivity. Dial-in provides audio only; use the meeting link if you need video, chat, screen sharing, or meeting controls.

- 1. Open the calendar invitation.
- 2. Find the Dial-in section in the NetCore Meet details.
- 3. Call the listed number from your phone.
- 4. When prompted, enter the meeting ID followed by the confirmation key shown in the invite.
- 5. If prompted for an attendee ID and you do not have one, wait or follow the prompt to continue as a phone participant.
- 6. Mute your phone when you are not speaking to reduce background noise.

## Update or Cancel a Scheduled Meeting

Use the original calendar event when you need to change a NetCore Meet meeting. This keeps the join link and attendee list synchronized.

- 1. Open the original calendar event.
- 2. Change the date, time, attendees, or description as needed.
- 3. If you need to change lobby, recording, or participant settings, select Meeting options.
- 4. Send the calendar update to all attendees.
- 5. To cancel the meeting, cancel the calendar event and send the cancellation notice. The join link should no longer be used.

## Tips

For the best meeting experience, use the NetCore Meet desktop app when you can. The web client is helpful when you are on a shared device or cannot install software.

For HD video, plan for about 2.5 Mbps per video stream. NetCore recommends latency below 300 ms, jitter below 40 ms, and packet loss below 3%. For more details, see KB-MTG-2010.

If you are joining from a restricted network, allow TCP 443 for signalling, UDP 9000 for preferred media, and TCP 5004 as the media fallback path. If joining fails or media cannot connect, see KB-MTG-2007.

Join early for important meetings so you can verify your microphone, speaker, and camera before the meeting starts.

If you forward a calendar invitation, the forwarded recipient may still wait in the lobby if they are external to your organization.

If you record a meeting, remember that NetCore Meet 5.0 cloud recordings are retained for 365 days by default, unless your organization has configured a different retention period between 30 and 1825 days or placed content on legal hold.

## Frequently Asked Questions

**Q: Why do external attendees wait in the lobby?**

A: In NetCore Meet 5.0, external participants wait in the lobby by default. The host or a co-host can admit them when the meeting is ready. Your organization may also apply stricter lobby rules through policy.

**Q: Can I schedule a meeting for someone else?**

A: Yes, if your calendar permissions allow you to create or edit events on that person’s calendar. The meeting is still governed by the NetCore Meet account and policies used by the calendar add-in when the meeting is created.

**Q: What happens if I change the meeting time in my calendar?**

A: The NetCore Meet link remains valid when you update the original calendar event. Send the calendar update to attendees so their calendars show the correct time.

**Q: Can attendees join without installing the desktop app?**

A: Yes. Attendees can join from the NetCore Meet web client if your organization allows web access. For the best experience, especially when presenting or using HD video, the desktop app is recommended.

**Q: Why does the add-in button not appear in my calendar?**

A: Restart the calendar app and the NetCore Meet desktop app, then check again. If you use a web calendar, sign out, sign back in, and refresh the page. If the add-in is still missing, your administrator may need to enable calendar add-ins for your account.

**Q: What should I do if I cannot join from the calendar link?**

A: First, try opening the link in the NetCore Meet desktop app or web client. If the meeting is locked, you are waiting in the lobby, or media ports are blocked, follow the troubleshooting steps in KB-MTG-2007.

## Related Articles

- KB-MTG-2007: Troubleshooting Meeting Join Failures (MTG-JOIN-1003 / MTG-JOIN-1007)
- KB-MTG-2010: FAQ: Licensing, Limits and Network Requirements
