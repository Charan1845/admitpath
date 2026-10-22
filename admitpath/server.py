"""AdmitPath MCP server: 13 tools over Streamable HTTP for Alexa+ (MCP spec 2025-11-25 or later).

Run:  python -m admitpath.server [--port 8000] [--public-host abc.trycloudflare.com]
MCP endpoint: http://localhost:8000/mcp
"""

from __future__ import annotations

import argparse
import os
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from . import __version__, tools
from .catalog import catalog

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)
Category = Literal["OPEN", "GENERAL", "EWS", "OBC-NCL", "OBC", "SC", "ST"]
InstType = Literal["IIT", "NIT", "IIIT", "GFTI"]

mcp = MCPServer(
    "admitpath",
    title="AdmitPath",
    description="Engineering admissions guide for families: realistic colleges from official JoSAA cutoffs, comparisons, "
                "the counselling process explained, and a choice list.",
    version=__version__,
    instructions=(
        "AdmitPath helps an Indian family through JoSAA engineering admissions (IITs, NITs, IIITs and other government "
        "institutes) after JEE. First save the student with set_student (name, JEE Main rank, category, category rank, "
        "gender, home state = state where they passed class 12; JEE Advanced rank for IITs). Then use predict_colleges "
        "for 'which colleges can she get', check_option for one college and branch, compare_options for two, "
        "cutoff_trend for past cutoffs, and the choice-list tools to build the ordered preference list. Use "
        "explain_term for words like float, slide, freeze, quota. Answers are spoken sentences: read them naturally. "
        "Predictions are estimates from past official data, not guarantees."
    ),
)


# ---------------- student ----------------

@mcp.tool(annotations=WRITE)
def set_student(
    name: Annotated[str | None, Field(description="Student's first name.")] = None,
    jee_main_rank: Annotated[int | None, Field(gt=0, description="JEE Main common rank list (CRL) rank.")] = None,
    category: Annotated[Category | None, Field(description="Reservation category. GENERAL means OPEN; OBC means OBC-NCL.")] = None,
    category_rank: Annotated[int | None, Field(gt=0, description="JEE Main category rank (for EWS, OBC-NCL, SC, ST).")] = None,
    gender: Annotated[Literal["Male", "Female"] | None, Field(description="Student's gender, for female-only seats.")] = None,
    home_state: Annotated[str | None, Field(description="State where the student passed class 12, e.g. Telangana.")] = None,
    jee_advanced_rank: Annotated[int | None, Field(gt=0, description="JEE Advanced CRL rank, needed for IITs.")] = None,
    advanced_category_rank: Annotated[int | None, Field(gt=0, description="JEE Advanced category rank.")] = None,
    pwd: Annotated[bool | None, Field(description="True if the student has a benchmark disability (PwD).")] = None,
    pwd_rank: Annotated[int | None, Field(gt=0, description="PwD rank, if PwD.")] = None,
) -> str:
    """Save or update the student's details. Only the fields given are changed.

    Use for 'Riya got rank 15,000 in JEE Main, she's OBC from Telangana', 'her OBC rank is 3,500', 'she also got
    2,800 in JEE Advanced'.
    """
    return tools.set_student(name, jee_main_rank, category, category_rank, gender, home_state,
                             jee_advanced_rank, advanced_category_rank, pwd, pwd_rank)


@mcp.tool(annotations=READ)
def get_student() -> str:
    """Read back the saved student's details and what's still missing. Use for 'what details do you have?'."""
    return tools.get_student()


# ---------------- colleges ----------------

@mcp.tool(annotations=READ)
def predict_colleges(
    branch: Annotated[str | None, Field(description="Branch, e.g. 'computer science', 'CSE', 'ECE', 'mechanical', 'AI'. Omit for all branches.")] = None,
    institute_type: Annotated[InstType | None, Field(description="Limit to IITs, NITs, IIITs or other government institutes (GFTI).")] = None,
    per_band: Annotated[int, Field(ge=1, le=10, description="How many options to read out per band.")] = 3,
) -> str:
    """List realistic colleges for the saved student as Safe, Target and Reach, from official JoSAA closing ranks.

    Use for 'which colleges can she get?', 'which NITs for CSE?', 'what are the safe options for ECE?'.
    """
    return tools.predict_colleges(branch, institute_type, per_band)


@mcp.tool(annotations=READ)
def check_option(
    institute: Annotated[str, Field(description="Institute as the user said it, e.g. 'NIT Warangal', 'IIT Bombay', 'IIIT Allahabad'.")],
    branch: Annotated[str, Field(description="Branch, e.g. 'CSE', 'electrical'.")],
) -> str:
    """The student's chance at one institute and branch, with past closing ranks and the trend.

    Use for 'can she get CSE at NIT Warangal?', 'what are her chances at IIT Madras electrical?'.
    """
    return tools.check_option(institute, branch)


@mcp.tool(annotations=READ)
def compare_options(
    institute_a: Annotated[str, Field(description="First institute.")],
    branch_a: Annotated[str, Field(description="First branch.")],
    institute_b: Annotated[str, Field(description="Second institute.")],
    branch_b: Annotated[str, Field(description="Second branch.")],
) -> str:
    """Compare two institute-and-branch options for the student: chances, cutoffs and trend, and which is safer.

    Use for 'CSE at NIT Warangal or ECE at NIT Trichy?'.
    """
    return tools.compare_options(institute_a, branch_a, institute_b, branch_b)


@mcp.tool(annotations=READ)
def cutoff_trend(
    institute: Annotated[str, Field(description="Institute, e.g. 'NIT Calicut'.")],
    branch: Annotated[str, Field(description="Branch, e.g. 'CSE'.")],
) -> str:
    """Past final-round closing ranks for one institute and branch, year by year, and whether it's getting harder.

    Use for 'how has NIT Calicut CSE's cutoff changed?', 'what was the cutoff last year?'.
    """
    return tools.cutoff_trend(institute, branch)


@mcp.tool(annotations=READ)
def find_programs(
    institute: Annotated[str, Field(description="Institute, e.g. 'IIT Hyderabad'.")],
) -> str:
    """List the branches and programs an institute offers through JoSAA. Use for 'what branches does NIT Goa have?'."""
    return tools.find_programs(institute)


# ---------------- choice list ----------------

@mcp.tool(annotations=WRITE)
def add_choice(
    institute: Annotated[str, Field(description="Institute.")],
    branch: Annotated[str, Field(description="Branch.")],
    position: Annotated[int | None, Field(ge=1, description="Where to put it, 1 = top. Omit to add at the end.")] = None,
) -> str:
    """Add an institute and branch to the student's ordered JoSAA choice list. Use for 'add NIT Warangal CSE at the top'."""
    return tools.add_choice(institute, branch, position)


@mcp.tool(annotations=WRITE)
def remove_choice(
    position: Annotated[int, Field(ge=1, description="Number of the choice to remove.")],
) -> str:
    """Remove one choice from the list by its number. Use for 'remove choice 3'."""
    return tools.remove_choice(position)


@mcp.tool(annotations=WRITE)
def move_choice(
    from_position: Annotated[int, Field(ge=1, description="Current number of the choice.")],
    to_position: Annotated[int, Field(ge=1, description="New number for it, 1 = top.")],
) -> str:
    """Move a choice up or down the list. Use for 'move choice 4 to number 1'."""
    return tools.move_choice(from_position, to_position)


@mcp.tool(annotations=READ)
def read_choices() -> str:
    """Read the student's choice list in order, with Safe, Target or Reach for each. Use for 'read her choices'."""
    return tools.read_choices()


# ---------------- process ----------------

@mcp.tool(annotations=READ)
def explain_term(
    term: Annotated[str, Field(description="The word to explain, e.g. 'float', 'slide', 'freeze', 'home state quota', 'CSAB'.")],
) -> str:
    """Explain a JoSAA counselling word in plain language. Use for 'what does float mean?', 'should we freeze?'."""
    return tools.explain_term(term)


@mcp.tool(annotations=READ)
def whats_next(
    step: Annotated[str | None, Field(description="Current step, e.g. 'round 1', 'seat acceptance'. Omit for the whole process.")] = None,
) -> str:
    """The usual order of JoSAA steps, or what comes after a given step. Use for 'what happens after round 1?'."""
    return tools.whats_next(step)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> Response:
    c = catalog()
    return JSONResponse({"ok": True, "version": __version__, "institutes": len(c.institutes), "years": c.years})


def build_app(public_host: str | None = None, bind_host: str = "127.0.0.1"):
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*", "127.0.0.1", "localhost"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    for h in filter(None, [public_host, *os.environ.get("ADMITPATH_ALLOWED_HOSTS", "").split(",")]):
        h = h.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        hosts += [h, f"{h}:*"]
        origins += [f"https://{h}", f"http://{h}"]
    security = TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins)
    return mcp.streamable_http_app(stateless_http=True, json_response=True, transport_security=security, host=bind_host)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the AdmitPath MCP server.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--public-host", default=os.environ.get("ADMITPATH_PUBLIC_HOST"),
                    help="Public hostname that reaches this server, e.g. abc.trycloudflare.com")
    args = ap.parse_args()
    catalog()                                  # load the cutoffs before the first request
    import uvicorn
    print(f"\n  AdmitPath MCP endpoint: http://localhost:{args.port}/mcp")
    if args.public_host:
        print(f"  Public MCP endpoint:    https://{args.public_host}/mcp")
    print(flush=True)
    uvicorn.run(build_app(args.public_host, args.host), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
