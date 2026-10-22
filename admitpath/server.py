"""AdmitPath MCP server: 13 tools over Streamable HTTP for Alexa+ (MCP spec 2025-11-25 or later).

Run:  python -m admitpath.server [--port 8000] [--public-host abc.trycloudflare.com]
MCP endpoint: http://localhost:8000/mcp
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response

from . import __version__, tools
from .catalog import catalog

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)
Category = Literal["OPEN", "GENERAL", "EWS", "OBC-NCL", "OBC", "SC", "ST"]
InstType = Literal["IIT", "NIT", "IIIT", "GFTI"]

mcp = MCPServer(
    "admitpath",
    title="AdmitPath",
    description="Engineering admissions guide for families: realistic colleges from official JoSAA and TG EAPCET cutoffs, "
                "comparisons, the counselling process explained, and a choice list.",
    version=__version__,
    instructions=(
        "AdmitPath helps an Indian family with engineering admissions. It covers JoSAA (IITs, NITs, IIITs and other "
        "government institutes, by JEE rank) and Telangana state colleges such as CBIT, VNR VJIET, BVRIT, Vasavi, MGIT "
        "and JNTUH (TG EAPCET counselling, by EAPCET rank). Save the student with set_student (name, ranks, category, "
        "gender, home state; eapcet_rank and telangana_category for Telangana colleges). Use predict_colleges for JoSAA "
        "options and predict_telangana_colleges for state colleges; check_option and compare_options work for both kinds "
        "(branch is optional; it defaults to CSE); college_info describes a college; cutoff_trend gives past cutoffs; the "
        "choice-list tools build the JoSAA preference list; explain_term explains words like float, slide, freeze. "
        "Pass college names exactly as the user said them, including places like 'in Hyderabad'. Answers are spoken "
        "sentences: read them naturally. Predictions are estimates from past official data, not guarantees."
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
    eapcet_rank: Annotated[int | None, Field(gt=0, description="TG EAPCET (TS EAMCET) rank, for Telangana state colleges.")] = None,
    telangana_category: Annotated[str | None, Field(description="Telangana category: OC, BC-A, BC-B, BC-C, BC-D, BC-E, SC-I, SC-II, SC-III, ST or EWS.")] = None,
) -> str:
    """Save or update the student's details. Only the fields given are changed.

    Use for 'Riya got rank 15,000 in JEE Main, she's OBC from Telangana', 'her OBC rank is 3,500', 'she also got
    2,800 in JEE Advanced', 'her EAPCET rank is 6,000, BC-B'.
    """
    return tools.set_student(name, jee_main_rank, category, category_rank, gender, home_state,
                             jee_advanced_rank, advanced_category_rank, pwd, pwd_rank, eapcet_rank, telangana_category)


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
def predict_telangana_colleges(
    branch: Annotated[str | None, Field(description="Branch, e.g. 'CSE', 'ECE', 'AI and ML'. Defaults to CSE.")] = None,
    hyderabad_only: Annotated[bool, Field(description="True to list only colleges in and around Hyderabad.")] = False,
    per_band: Annotated[int, Field(ge=1, le=10, description="How many options to read out per band.")] = 3,
) -> str:
    """List Telangana state colleges (TG EAPCET counselling) as Safe, Target and Reach for the student's EAPCET rank.

    Use for 'which Telangana colleges can she get with EAPCET?', 'which Hyderabad colleges for CSE?'.
    """
    return tools.predict_telangana_colleges(branch, hyderabad_only, per_band)


@mcp.tool(annotations=READ)
def check_option(
    institute: Annotated[str, Field(description="College as the user said it, e.g. 'NIT Warangal', 'IIT Bombay', 'CBIT', 'BVRIT Hyderabad'.")],
    branch: Annotated[str | None, Field(description="Branch, e.g. 'CSE', 'electrical'. Defaults to CSE.")] = None,
) -> str:
    """The student's chance at one college and branch, with cutoffs (JoSAA colleges or Telangana state colleges).

    Use for 'can she get CSE at NIT Warangal?', 'what are her chances at CBIT?'.
    """
    return tools.check_option(institute, branch)


@mcp.tool(annotations=READ)
def compare_options(
    institute_a: Annotated[str, Field(description="First college as the user said it, e.g. 'BVRIT in Hyderabad'.")],
    institute_b: Annotated[str, Field(description="Second college as the user said it, e.g. 'CBIT'.")],
    branch_a: Annotated[str | None, Field(description="First branch. Defaults to CSE.")] = None,
    branch_b: Annotated[str | None, Field(description="Second branch. Defaults to the first branch.")] = None,
) -> str:
    """Compare two colleges or college-and-branch options: location, type, cutoffs, and the student's chances.

    Works for JoSAA colleges and Telangana state colleges. Use for 'compare BVRIT and CBIT', 'CSE at NIT Warangal
    or ECE at NIT Trichy?', 'which is better, VNR or Vasavi?'.
    """
    return tools.compare_options(institute_a, branch_a, institute_b, branch_b)


@mcp.tool(annotations=READ)
def college_info(
    college: Annotated[str, Field(description="College as the user said it, e.g. 'CBIT', 'NIT Warangal'.")],
) -> str:
    """Describe a college: where it is, what kind it is, how it admits, its branches and its CSE cutoff.

    Use for 'tell me about CBIT', 'is BVRIT autonomous?', 'what is MGIT like?'.
    """
    return tools.college_info(college)


@mcp.tool(annotations=READ)
def cutoff_trend(
    institute: Annotated[str, Field(description="College, e.g. 'NIT Calicut', 'CBIT'.")],
    branch: Annotated[str | None, Field(description="Branch, e.g. 'CSE'. Defaults to CSE.")] = None,
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


# ---------------- simulated Alexa+ page (demo) ----------------

WEB = Path(__file__).resolve().parent / "web"
_TYPES = {".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png"}


@mcp.custom_route("/", methods=["GET"])
async def home(request: Request) -> Response:
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})


@mcp.custom_route("/static/{path:path}", methods=["GET"])
async def static_file(request: Request) -> Response:
    target = (WEB / request.path_params["path"]).resolve()
    if WEB not in target.parents or not target.is_file() or target.suffix not in _TYPES:
        return PlainTextResponse("Not found", status_code=404)
    return FileResponse(target, media_type=_TYPES[target.suffix], headers={"Cache-Control": "no-cache"})


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
