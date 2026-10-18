"""cli-anything-whatsapp: send WhatsApp messages from the terminal or over MCP."""

import json
import sys

import click

from cli_anything.whatsapp import core


def _emit(ctx, data, human):
    if ctx.obj["json"]:
        click.echo(json.dumps(data, ensure_ascii=False))
    else:
        click.echo(human)


def _fail(ctx, err):
    if ctx.obj["json"]:
        click.echo(json.dumps({"error": str(err)}, ensure_ascii=False))
    else:
        click.echo(f"Error: {err}", err=True)
    sys.exit(1)


@click.group()
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@click.version_option("1.0.0")
@click.pass_context
def cli(ctx, as_json):
    """Send WhatsApp messages through the WhatsApp Mac app."""
    ctx.obj = {"json": as_json}


@cli.command()
@click.argument("to")
@click.argument("message", nargs=-1, required=True)
@click.option("--dry-run", is_flag=True, help="Resolve the contact without sending.")
@click.pass_context
def send(ctx, to, message, dry_run):
    """Send MESSAGE to TO (a contact name or a phone number with country code)."""
    text = " ".join(message)
    try:
        result = core.send(to, text, dry_run=dry_run)
    except core.WhatsAppError as err:
        _fail(ctx, err)
    labels = {"sent": "Sent", "dry-run": "Would send", "unconfirmed": "Not confirmed"}
    human = f'{labels[result["status"]]} to {result["to"]} (+{result["phone"]})'
    if result.get("note"):
        human += f"\n{result['note']}"
    _emit(ctx, result, human)
    if result["status"] == "unconfirmed":
        sys.exit(2)


@cli.command()
@click.argument("query")
@click.pass_context
def find(ctx, query):
    """List WhatsApp contacts whose name matches QUERY."""
    try:
        hits = core.find_contacts(query)
    except core.WhatsAppError as err:
        _fail(ctx, err)
    _emit(ctx, [c.to_dict() for c in hits],
          "\n".join(f"{c.name}  +{c.phone}" for c in hits) or "No matches.")


@cli.command()
def mcp():
    """Run as an MCP server over stdio."""
    from cli_anything.whatsapp.mcp_server import run
    run()


def main():
    cli()


if __name__ == "__main__":
    main()
