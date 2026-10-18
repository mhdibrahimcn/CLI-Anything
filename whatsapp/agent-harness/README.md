# cli-anything-whatsapp

Send WhatsApp messages from the terminal or from an MCP client, using the
WhatsApp app for Mac you're already signed into. It does not log in as a new
device or use an unofficial WhatsApp client.

## How it works

1. Looks the person up in WhatsApp's local databases (read-only): your synced
   address book, plus everyone you have a one-to-one chat with. Most chats are
   stored under a privacy ID instead of a number; the number comes from
   WhatsApp's `LID.sqlite`.
2. Opens `whatsapp://send?phone=<number>&text=<message>`, which opens that
   chat in WhatsApp with the message typed in.
3. Presses Return in WhatsApp.
4. Checks WhatsApp's message database for the outgoing message and reports
   `sent`, or `unconfirmed` if it didn't appear within 15 seconds.

If a name matches more than one contact, nothing is sent and the matches are
listed.

## Setup

```bash
pip install -e whatsapp/agent-harness
```

Give Accessibility permission to the app you run it from (Terminal, iTerm,
T3 Code, Claude...): System Settings > Privacy & Security > Accessibility.
Restart that app afterwards. Without it the tool refuses to send.

## Use

```bash
cli-anything-whatsapp send "Bilal" "On my way"
cli-anything-whatsapp send +447700900003 "On my way"
cli-anything-whatsapp send "Asha Rao" "See you at 6" --dry-run
cli-anything-whatsapp find asha
cli-anything-whatsapp --json send "Bilal" "On my way"
```

Exit codes: `0` sent, `1` error (nothing sent), `2` Return was pressed but the
message wasn't confirmed.

## MCP

```bash
claude mcp add whatsapp -- cli-anything-whatsapp mcp
```

Tools: `send_message(to, message, dry_run=False)` and `find_contact(query)`.

## Limits

- Names come from your address book, or the chat name for people who aren't
  in it. Any number works if you type it with its country code.
- Two different people with the exact same name can't be told apart by name.
  Use the number.
- No groups. WhatsApp's URL scheme can only open chats by phone number.
- WhatsApp comes to the front while sending, and it takes about 2 seconds.
- Text only, no attachments.
