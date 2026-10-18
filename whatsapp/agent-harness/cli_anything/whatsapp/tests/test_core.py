import json
import sqlite3
import subprocess
import time

import pytest
from click.testing import CliRunner

from cli_anything.whatsapp import core
from cli_anything.whatsapp.whatsapp_cli import cli

CONTACTS = [
    ("Asha Rao", "Asha", None, "919800000001@s.whatsapp.net"),
    ("Asha Menon", "Asha", None, "919800000002@s.whatsapp.net"),
    ("Bilal Khan", "Bilal", None, "447700900003@s.whatsapp.net"),
    (None, None, "Corner Bakery", "14155550004@s.whatsapp.net"),
    ("Group-ish", None, None, "1203630000@g.us"),
]


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("WA_DATA_DIR", str(tmp_path))
    c = sqlite3.connect(tmp_path / "ContactsV2.sqlite")
    c.execute("CREATE TABLE ZWAADDRESSBOOKCONTACT (ZFULLNAME, ZGIVENNAME, ZBUSINESSNAME, ZWHATSAPPID)")
    c.executemany("INSERT INTO ZWAADDRESSBOOKCONTACT VALUES (?,?,?,?)", CONTACTS)
    c.commit()
    c.close()
    c = sqlite3.connect(tmp_path / "ChatStorage.sqlite")
    c.execute("CREATE TABLE ZWACHATSESSION (Z_PK INTEGER PRIMARY KEY, ZCONTACTJID)")
    c.execute("CREATE TABLE ZWAMESSAGE (ZCHATSESSION, ZISFROMME, ZTEXT, ZMESSAGEDATE)")
    c.execute("INSERT INTO ZWACHATSESSION VALUES (1, '447700900003@s.whatsapp.net')")
    c.commit()
    c.close()
    return tmp_path


def record_sent(path, text, chat=1, when=None):
    c = sqlite3.connect(path / "ChatStorage.sqlite")
    c.execute("INSERT INTO ZWAMESSAGE VALUES (?, 1, ?, ?)", (chat, text, (when or time.time()) - core.APPLE_EPOCH))
    c.commit()
    c.close()


class FakeMac:
    """Stands in for `open` and `osascript`. Records what would have happened."""

    def __init__(self, data_path, accessibility=True, deliver=True):
        self.data_path = data_path
        self.accessibility = accessibility
        self.deliver = deliver
        self.opened = []
        self.returns = 0
        self.text = None

    def __call__(self, args, **kwargs):
        if args[0] == "open":
            self.opened.append(args[1])
            return subprocess.CompletedProcess(args, 0, "", "")
        script = args[2]
        if "UI elements enabled" in script:
            return subprocess.CompletedProcess(args, 0, "true\n" if self.accessibility else "false\n", "")
        if "frontmost" in script:
            return subprocess.CompletedProcess(args, 0, "true\n", "")
        if "keystroke return" in script:
            self.returns += 1
            if self.deliver:
                record_sent(self.data_path, self.text)
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(script)


@pytest.fixture
def mac(data, monkeypatch):
    fake = FakeMac(data)
    monkeypatch.setattr(core.subprocess, "run", fake)
    return fake


def test_contacts_skip_groups_and_use_business_name(data):
    names = [c.name for c in core.load_contacts()]
    assert "Corner Bakery" in names
    assert "Group-ish" not in names


def test_resolve_by_unique_name(data):
    assert core.resolve("bilal").phone == "447700900003"


def test_resolve_ambiguous_name_lists_matches(data):
    with pytest.raises(core.WhatsAppError, match="matches 2 contacts"):
        core.resolve("asha")


def test_resolve_exact_name_beats_prefix(data):
    assert core.resolve("Asha Rao").phone == "919800000001"


def test_resolve_phone_formats(data):
    assert core.resolve("+44 7700 900003").name == "Bilal Khan"
    unknown = core.resolve("+1 (212) 555-0100")
    assert unknown.phone == "12125550100"
    assert unknown.name == "+12125550100"


def test_resolve_unknown_name(data):
    with pytest.raises(core.WhatsAppError, match="No WhatsApp contact"):
        core.resolve("nobody")


def test_send_url_encodes_text():
    url = core.send_url("447700900003", "hi & bye\nline 2 ✓")
    assert url.startswith("whatsapp://send?phone=447700900003&text=")
    assert "&text=hi%20%26%20bye%0Aline%202%20%E2%9C%93" in url


def test_send_confirms_via_database(mac):
    mac.text = "hello there"
    result = core.send("Bilal", "hello there", load_delay=0)
    assert result["status"] == "sent"
    assert result["chat"] == "447700900003@s.whatsapp.net"
    assert mac.returns == 1
    assert mac.opened == [core.send_url("447700900003", "hello there")]


def test_send_unconfirmed_when_nothing_recorded(data, monkeypatch):
    fake = FakeMac(data, deliver=False)
    monkeypatch.setattr(core.subprocess, "run", fake)
    result = core.send("Bilal", "hello", load_delay=0, confirm_timeout=0.3)
    assert result["status"] == "unconfirmed"


def test_old_identical_message_does_not_count_as_sent(data, monkeypatch):
    record_sent(data, "hello", when=time.time() - 3600)
    fake = FakeMac(data, deliver=False)
    monkeypatch.setattr(core.subprocess, "run", fake)
    assert core.send("Bilal", "hello", load_delay=0, confirm_timeout=0.3)["status"] == "unconfirmed"


def test_send_refuses_without_accessibility(data, monkeypatch):
    fake = FakeMac(data, accessibility=False)
    monkeypatch.setattr(core.subprocess, "run", fake)
    with pytest.raises(core.WhatsAppError, match="Accessibility"):
        core.send("Bilal", "hello", load_delay=0)
    assert fake.opened == [] and fake.returns == 0


def test_ambiguous_target_sends_nothing(mac):
    with pytest.raises(core.WhatsAppError):
        core.send("asha", "hello", load_delay=0)
    assert mac.opened == [] and mac.returns == 0


def test_dry_run_sends_nothing(mac):
    assert core.send("Bilal", "hello", dry_run=True)["status"] == "dry-run"
    assert mac.opened == [] and mac.returns == 0


def test_cli_send_json(mac):
    mac.text = "on my way"
    result = CliRunner().invoke(cli, ["--json", "send", "Bilal", "on", "my", "way"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "sent"


def test_cli_error_exit_code(data):
    result = CliRunner().invoke(cli, ["send", "asha", "hi"])
    assert result.exit_code == 1
    assert "matches 2 contacts" in result.output


def test_cli_find(data):
    result = CliRunner().invoke(cli, ["--json", "find", "asha"])
    assert [c["name"] for c in json.loads(result.output)] == ["Asha Menon", "Asha Rao"]
