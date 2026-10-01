#!/usr/bin/env python3
"""
The one way Keymaker Sales reads and writes its pipeline.

Backend is chosen from the environment:
  * FIBERY_HOST + FIBERY_API_TOKEN set  -> Fibery CRM (CRM/Opportunities), HTTP command API
  * otherwise                           -> pipeline/deals.yaml in this repo

Commands (identical on both backends):
  python3 scripts/crm.py list [--owner NAME] [--all]
  python3 scripts/crm.py show <slug>
  python3 scripts/crm.py create <slug> --company NAME --owner NAME [--value N] [--champion TEXT] [--confirm]
  python3 scripts/crm.py move <slug> --stage "2. Qualified" [--confirm]
  python3 scripts/crm.py note <slug> --text "..." [--confirm]
  python3 scripts/crm.py edit <slug> [--value N] [--champion TEXT] [--owner NAME] [--confirm]
  python3 scripts/crm.py backend

Every write prints the change it is about to make and refuses without --confirm.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEALS_FILE = os.path.join(ROOT, "pipeline", "deals.yaml")

STAGES = [
    "0. Discovery Call Booked",
    "1. Discovery Call Held",
    "2. Qualified",
    "3. Workflows Reviewed",
    "4. Proposal Sent",
    "5. Contract Under Review",
    "6. Won",
    "Nurturing",
    "Lost",
    "Disqualified",
]
OPEN_STAGES = STAGES[:7]


# --------------------------------------------------------------------------- yaml (no dependency)
def _load_yaml(path):
    try:
        import yaml  # type: ignore
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        sys.exit("PyYAML is not installed: pip install pyyaml")


def _dump_yaml(data, path):
    import yaml  # type: ignore
    with open(path, "w") as f:
        f.write("# File-backed pipeline (the default backend of scripts/crm.py).\n")
        f.write("# Sample deals for a fictional agency - edit freely. Stage names must match CLAUDE.md.\n")
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


# --------------------------------------------------------------------------- backends
class FileBackend:
    name = "file (pipeline/deals.yaml)"

    def _read(self):
        return _load_yaml(DEALS_FILE).get("deals", [])

    def _write(self, deals):
        _dump_yaml({"deals": deals}, DEALS_FILE)

    def list(self, owner=None, include_closed=False):
        deals = self._read()
        if owner:
            deals = [d for d in deals if d.get("owner") == owner]
        if not include_closed:
            deals = [d for d in deals if d.get("stage") in OPEN_STAGES]
        return deals

    def show(self, slug):
        for d in self._read():
            if d.get("slug") == slug:
                return d
        return None

    def create(self, slug, company, owner, value=None, champion=None):
        deals = self._read()
        if any(d.get("slug") == slug for d in deals):
            sys.exit(f"deal {slug} already exists")
        deals.append({
            "slug": slug, "company": company, "owner": owner, "stage": STAGES[0],
            "value_usd": value, "champion": champion, "updated": _today(),
            "notes": [f"{_today()} Deal opened."],
        })
        self._write(deals)

    def move(self, slug, stage):
        deals = self._read()
        for d in deals:
            if d.get("slug") == slug:
                d["stage"] = stage
                d["updated"] = _today()
                d.setdefault("notes", []).append(f"{_today()} Moved to {stage}.")
                self._write(deals)
                return
        sys.exit(f"no deal {slug}")

    def note(self, slug, text):
        deals = self._read()
        for d in deals:
            if d.get("slug") == slug:
                d.setdefault("notes", []).append(f"{_today()} {text}")
                d["updated"] = _today()
                self._write(deals)
                return
        sys.exit(f"no deal {slug}")

    def edit(self, slug, **fields):
        deals = self._read()
        for d in deals:
            if d.get("slug") == slug:
                for k, v in fields.items():
                    if v is not None:
                        d[k] = v
                d["updated"] = _today()
                d.setdefault("notes", []).append(f"{_today()} Edited: " + ", ".join(f"{k}={v}" for k, v in fields.items() if v is not None))
                self._write(deals)
                return
        sys.exit(f"no deal {slug}")


class FiberyBackend:
    """Fibery CRM/Opportunities. Stage names in Fibery must match STAGES."""
    name = "fibery"
    TYPE = "CRM/Opportunities"

    def __init__(self):
        self.host = os.environ["FIBERY_HOST"]
        self.token = os.environ["FIBERY_API_TOKEN"]

    def _call(self, commands):
        req = urllib.request.Request(
            f"https://{self.host}/api/commands",
            data=json.dumps(commands).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Token {self.token}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.load(resp)
        for r in out:
            if not r.get("success"):
                sys.exit(f"Fibery error: {json.dumps(r.get('result'))[:500]}")
        return [r["result"] for r in out]

    def _query(self, where=None, params=None, limit=200):
        q = {
            "q/from": self.TYPE,
            "q/select": ["fibery/id", "fibery/public-id", "CRM/Name",
                         {"CRM/Owner": ["user/name"]}, {"CRM/Stages": ["enum/name"]},
                         "fibery/modification-date"],
            "q/limit": limit,
        }
        if where:
            q["q/where"] = where
        cmd = {"command": "fibery.entity/query", "args": {"query": q}}
        if params:
            cmd["args"]["params"] = params
        rows = self._call([cmd])[0]
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(r):
        return {
            "slug": r.get("fibery/public-id"),
            "company": r.get("CRM/Name"),
            "owner": (r.get("CRM/Owner") or {}).get("user/name"),
            "stage": (r.get("CRM/Stages") or {}).get("enum/name"),
            "updated": (r.get("fibery/modification-date") or "")[:10],
            "_id": r.get("fibery/id"),
        }

    def list(self, owner=None, include_closed=False):
        rows = self._query()
        if owner:
            rows = [r for r in rows if r["owner"] == owner]
        if not include_closed:
            rows = [r for r in rows if r["stage"] in OPEN_STAGES]
        return rows

    def show(self, slug):
        rows = self._query(where=["=", ["fibery/public-id"], "$id"], params={"$id": str(slug)})
        return rows[0] if rows else None

    def create(self, slug, company, owner, value=None, champion=None):
        self._call([{"command": "fibery.entity/create", "args": {
            "type": self.TYPE, "entity": {"CRM/Name": company, "CRM/Stages": {"enum/name": STAGES[0]}}}}])

    def move(self, slug, stage):
        d = self.show(slug) or sys.exit(f"no deal {slug}")
        self._call([{"command": "fibery.entity/update", "args": {
            "type": self.TYPE, "entity": {"fibery/id": d["_id"], "CRM/Stages": {"enum/name": stage}}}}])

    def note(self, slug, text):
        sys.exit("notes on the Fibery backend are not implemented in this starter - add a comment in Fibery")

    def edit(self, slug, **fields):
        d = self.show(slug) or sys.exit(f"no deal {slug}")
        entity = {"fibery/id": d["_id"]}
        if fields.get("value_usd") is not None:
            entity["CRM/TCV"] = fields["value_usd"]
        if fields.get("company"):
            entity["CRM/Name"] = fields["company"]
        if len(entity) == 1:
            sys.exit("on the Fibery backend only --value and --company can be edited in this starter")
        self._call([{"command": "fibery.entity/update", "args": {"type": self.TYPE, "entity": entity}}])


def backend():
    if os.environ.get("FIBERY_HOST") and os.environ.get("FIBERY_API_TOKEN"):
        return FiberyBackend()
    return FileBackend()


def _today():
    return dt.date.today().isoformat()


def _days_since(s):
    try:
        return (dt.date.today() - dt.date.fromisoformat(str(s)[:10])).days
    except Exception:
        return None


def _gate(description, confirm):
    print(f"ABOUT TO WRITE: {description}")
    if not confirm:
        print("Not written. Re-run with --confirm after the operator has seen this.")
        sys.exit(2)


# --------------------------------------------------------------------------- cli
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backend")
    s = sub.add_parser("list"); s.add_argument("--owner"); s.add_argument("--all", action="store_true")
    s = sub.add_parser("show"); s.add_argument("slug")
    s = sub.add_parser("create"); s.add_argument("slug"); s.add_argument("--company", required=True)
    s.add_argument("--owner", required=True); s.add_argument("--value", type=int); s.add_argument("--champion")
    s.add_argument("--confirm", action="store_true")
    s = sub.add_parser("move"); s.add_argument("slug"); s.add_argument("--stage", required=True)
    s.add_argument("--confirm", action="store_true")
    s = sub.add_parser("note"); s.add_argument("slug"); s.add_argument("--text", required=True)
    s.add_argument("--confirm", action="store_true")
    s = sub.add_parser("edit"); s.add_argument("slug"); s.add_argument("--value", type=int)
    s.add_argument("--champion"); s.add_argument("--owner"); s.add_argument("--company")
    s.add_argument("--confirm", action="store_true")
    a = p.parse_args()
    b = backend()

    if a.cmd == "backend":
        print(b.name)
    elif a.cmd == "list":
        rows = b.list(owner=a.owner, include_closed=a.all)
        if not rows:
            print("No deals." + (f" (owner: {a.owner})" if a.owner else ""))
            return
        print(f"{'STAGE':<26} {'COMPANY':<28} {'OWNER':<16} {'VALUE':>8}  {'DAYS':>4}  SLUG")
        for d in sorted(rows, key=lambda d: d.get("stage") or ""):
            days = _days_since(d.get("updated"))
            flag = " STALLED" if days is not None and days >= 14 and d.get("stage") in OPEN_STAGES else ""
            print(f"{str(d.get('stage')):<26} {str(d.get('company'))[:28]:<28} {str(d.get('owner'))[:16]:<16} "
                  f"{(d.get('value_usd') or ''):>8}  {('' if days is None else days):>4}  {d.get('slug')}{flag}")
    elif a.cmd == "show":
        d = b.show(a.slug) or sys.exit(f"no deal {a.slug}")
        print(json.dumps({k: v for k, v in d.items() if not k.startswith('_')}, indent=2, ensure_ascii=False))
    elif a.cmd == "create":
        _gate(f"create deal {a.slug} ({a.company}) owner={a.owner} stage={STAGES[0]} on {b.name}", a.confirm)
        b.create(a.slug, a.company, a.owner, a.value, a.champion); print("created")
    elif a.cmd == "move":
        if a.stage not in STAGES:
            sys.exit(f"unknown stage {a.stage!r}; one of: " + " | ".join(STAGES))
        _gate(f"move {a.slug} -> {a.stage} on {b.name}", a.confirm)
        b.move(a.slug, a.stage); print("moved")
    elif a.cmd == "note":
        _gate(f"append note to {a.slug} on {b.name}: {a.text}", a.confirm)
        b.note(a.slug, a.text); print("noted")
    elif a.cmd == "edit":
        fields = {"value_usd": a.value, "champion": a.champion, "owner": a.owner, "company": a.company}
        changes = ", ".join(f"{k}={v}" for k, v in fields.items() if v is not None) or sys.exit("nothing to edit")
        _gate(f"edit {a.slug} on {b.name}: {changes}", a.confirm)
        b.edit(a.slug, **fields); print("edited")


if __name__ == "__main__":
    main()
