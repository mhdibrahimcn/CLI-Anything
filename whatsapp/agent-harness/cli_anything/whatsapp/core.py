"""Send WhatsApp messages through the WhatsApp Mac app.

Contacts are looked up in the app's local database (read-only). Sending opens
``whatsapp://send?phone=...&text=...`` and presses Return in WhatsApp, then
checks the app's message database to confirm the message was recorded.
"""

import os
import re
import sqlite3
import subprocess
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

BUNDLE_ID = "net.whatsapp.WhatsApp"
DATA_DIR = Path.home() / "Library" / "Group Containers" / "group.net.whatsapp.WhatsApp.shared"
APPLE_EPOCH = 978307200  # 2001-01-01, Core Data timestamps


class WhatsAppError(Exception):
    pass


@dataclass
class Contact:
    name: str
    phone: str  # digits only, with country code

    def to_dict(self):
        return {"name": self.name, "phone": self.phone}


def data_dir():
    return Path(os.environ.get("WA_DATA_DIR", DATA_DIR))


def _connect(name):
    path = data_dir() / name
    if not path.exists():
        raise WhatsAppError(f"{path} not found. Is WhatsApp for Mac installed and signed in?")
    return sqlite3.connect(f"file:{urllib.parse.quote(str(path))}?mode=ro", uri=True)


def _digits(value):
    return re.sub(r"\D", "", value or "")


def load_contacts():
    conn = _connect("ContactsV2.sqlite")
    try:
        rows = conn.execute(
            "SELECT ZFULLNAME, ZGIVENNAME, ZBUSINESSNAME, ZWHATSAPPID FROM ZWAADDRESSBOOKCONTACT "
            "WHERE ZWHATSAPPID LIKE '%@s.whatsapp.net'"
        ).fetchall()
    finally:
        conn.close()
    contacts = {}
    for full, given, business, jid in rows:
        name = full or given or business
        phone = _digits(jid.split("@")[0])
        if name and phone:
            contacts[phone] = Contact(name=name.strip(), phone=phone)
    return sorted(contacts.values(), key=lambda c: c.name.lower())


def find_contacts(query):
    q = query.strip().lower()
    contacts = load_contacts()
    for test in (
        lambda n: n == q,
        lambda n: n.startswith(q),
        lambda n: any(w.startswith(q) for w in n.split()),
        lambda n: q in n,
    ):
        hits = [c for c in contacts if test(c.name.lower())]
        if hits:
            return hits
    return []


def resolve(target):
    """Return the Contact a name or phone number refers to."""
    digits = _digits(target)
    if digits and len(digits) >= 8 and not re.search(r"[A-Za-z]", target):
        match = next((c for c in load_contacts() if c.phone == digits), None)
        return match or Contact(name=f"+{digits}", phone=digits)
    hits = find_contacts(target)
    if not hits:
        raise WhatsAppError(f'No WhatsApp contact matches "{target}". Use a phone number with country code.')
    if len(hits) > 1:
        listing = "\n".join(f"  {c.name}  +{c.phone}" for c in hits[:15])
        raise WhatsAppError(f'"{target}" matches {len(hits)} contacts. Be more specific:\n{listing}')
    return hits[0]


def send_url(phone, text):
    return f"whatsapp://send?phone={phone}&text={urllib.parse.quote(text, safe='')}"


def _osascript(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True)


def check_accessibility():
    result = _osascript('tell application "System Events" to get UI elements enabled')
    if result.stdout.strip() != "true":
        raise WhatsAppError(
            "This app needs Accessibility permission to press Return in WhatsApp.\n"
            "System Settings > Privacy & Security > Accessibility: turn on the app you run this from "
            "(Terminal, iTerm, T3 Code, Claude...), then restart that app."
        )


def _whatsapp_frontmost():
    result = _osascript(
        f'tell application "System Events" to get frontmost of '
        f'(first process whose bundle identifier is "{BUNDLE_ID}")'
    )
    return result.stdout.strip() == "true"


def _press_return():
    result = _osascript(
        f'tell application "System Events" to tell '
        f'(first process whose bundle identifier is "{BUNDLE_ID}") to keystroke return'
    )
    if result.returncode != 0:
        raise WhatsAppError(f"Could not press Return in WhatsApp: {result.stderr.strip()}")


def _find_sent(text, since):
    """Return the chat JID of an outgoing message with this text recorded after `since`."""
    try:
        conn = _connect("ChatStorage.sqlite")
    except WhatsAppError:
        return None
    try:
        row = conn.execute(
            "SELECT s.ZCONTACTJID FROM ZWAMESSAGE m JOIN ZWACHATSESSION s ON s.Z_PK = m.ZCHATSESSION "
            "WHERE m.ZISFROMME = 1 AND m.ZTEXT = ? AND m.ZMESSAGEDATE >= ? "
            "ORDER BY m.ZMESSAGEDATE DESC LIMIT 1",
            (text, since - APPLE_EPOCH - 2),
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return row[0] if row else None


def send(target, text, *, dry_run=False, load_delay=1.5, confirm_timeout=15.0):
    if not text.strip():
        raise WhatsAppError("Message is empty.")
    contact = resolve(target)
    result = {"to": contact.name, "phone": contact.phone}
    if dry_run:
        return {**result, "status": "dry-run"}

    check_accessibility()
    started = time.time()
    opened = subprocess.run(["open", send_url(contact.phone, text)], capture_output=True, text=True)
    if opened.returncode != 0:
        raise WhatsAppError(f"Could not open WhatsApp: {opened.stderr.strip()}")

    deadline = time.time() + 10
    while not _whatsapp_frontmost():
        if time.time() > deadline:
            raise WhatsAppError("WhatsApp did not come to the front. Nothing was sent.")
        time.sleep(0.2)
    time.sleep(load_delay)
    _press_return()

    deadline = time.time() + confirm_timeout
    while time.time() < deadline:
        chat = _find_sent(text, started)
        if chat:
            return {**result, "status": "sent", "chat": chat}
        time.sleep(0.5)
    return {
        **result,
        "status": "unconfirmed",
        "note": "Return was pressed but the message did not show up in WhatsApp's database. Check the app.",
    }
