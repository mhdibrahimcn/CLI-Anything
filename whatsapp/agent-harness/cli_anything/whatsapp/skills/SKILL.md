---
name: cli-anything-whatsapp
description: >-
  Send a WhatsApp message to a contact or phone number through the WhatsApp
  Mac app. Use when the user asks to WhatsApp, text, or message someone.
---

# cli-anything-whatsapp

Sends text messages through the signed-in WhatsApp app on this Mac.

## Commands

- `cli-anything-whatsapp --json send "<name or +number>" "<message>"`
- `cli-anything-whatsapp --json send "<name>" "<message>" --dry-run`: shows who
  would receive it without sending.
- `cli-anything-whatsapp --json find "<name>"`: lists matching contacts.

## Rules

- Messages go to real people. Send only what the user asked for, to the person
  they named.
- If a name could fit more than one person, run `find` or `--dry-run` first
  and confirm the recipient with the user.
- `"status": "sent"` means WhatsApp recorded the outgoing message.
  `"unconfirmed"` means it may not have gone out, so tell the user and don't
  resend without asking.
- An "Accessibility" error means the user has to grant permission in System
  Settings. Nothing was sent.
