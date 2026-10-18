"""MCP server exposing WhatsApp send and contact lookup."""

from mcp.server.fastmcp import FastMCP

from cli_anything.whatsapp import core

server = FastMCP("whatsapp")


@server.tool()
def send_message(to: str, message: str, dry_run: bool = False) -> dict:
    """Send a WhatsApp message through the WhatsApp Mac app.

    `to` is a contact name or a phone number with country code. If the name
    matches several contacts, nothing is sent and the matches are returned.
    Use dry_run=True to check who would receive it.
    """
    try:
        return core.send(to, message, dry_run=dry_run)
    except core.WhatsAppError as err:
        return {"status": "error", "error": str(err)}


@server.tool()
def find_contact(query: str) -> list[dict]:
    """List WhatsApp contacts whose name matches `query`."""
    return [c.to_dict() for c in core.find_contacts(query)]


def run():
    server.run()
