"""Support Skills Console: a small web UI over the four support skills' scripts.

The app imports the skill scripts directly, so the web UI and the CLI run the same code.
The policy doc and changelog are read from disk on every request, so edits take
effect immediately (the policy doc changes often).

Run:  python webapp/app.py   ->  http://127.0.0.1:5000
"""
import importlib.util
import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, SKILLS / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


triage = _load("validate_triage", "ticket-triage/scripts/validate_triage.py")
reply = _load("check_reply", "support-reply/scripts/check_reply.py")
qa = _load("aggregate_grades", "qa-grading/scripts/aggregate_grades.py")
bugs = _load("search_changelog", "bug-intake/scripts/search_changelog.py")

DEFAULTS = {
    "POLICY_PATH": ROOT / "company-docs" / "refund-pricing-policy.md",
    "CHANGELOG_PATH": ROOT / "company-docs" / "CHANGELOG.md",
    "TONE_PATH": SKILLS / "support-reply" / "references" / "tone-of-voice.md",
    "ROUTING_PATH": SKILLS / "ticket-triage" / "references" / "routing.json",
    "RUBRIC_PATH": SKILLS / "qa-grading" / "references" / "rubric.md",
    "MAX_CONTENT_LENGTH": 1 * 1024 * 1024,
}
MAX_TEXT = 200_000


class BadRequest(Exception):
    pass


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.update(DEFAULTS)
    app.config.update(overrides or {})

    def read(key: str) -> str:
        return Path(app.config[key]).read_text(encoding="utf-8")

    def body() -> dict:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise BadRequest("request body must be a JSON object")
        return data

    def text_field(data: dict, key: str, required: bool = True) -> str:
        v = data.get(key, "")
        if not isinstance(v, str):
            raise BadRequest(f"'{key}' must be a string")
        if required and not v.strip():
            raise BadRequest(f"'{key}' is required")
        if len(v) > MAX_TEXT:
            raise BadRequest(f"'{key}' is too long (max {MAX_TEXT} characters)")
        return v

    @app.after_request
    def _security_headers(resp):
        # The app is public once hosted: block framing/sniffing and allow only our own scripts/styles.
        resp.headers.setdefault("Content-Security-Policy",
                                "default-src 'self'; img-src 'self' data: blob:; object-src 'none'; "
                                "base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        return resp

    @app.errorhandler(BadRequest)
    def _bad(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(413)
    def _too_big(_):
        return jsonify(error="request too large"), 413

    @app.errorhandler(404)
    def _nf(_):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def _method(_):
        return jsonify(error="method not allowed"), 405

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/routing")
    def routing():
        return jsonify(json.loads(read("ROUTING_PATH")))

    @app.get("/api/policy")
    def policy():
        return jsonify(text=read("POLICY_PATH"))

    @app.post("/api/triage/validate")
    def triage_validate():
        data = body()
        rec = data.get("record")
        if isinstance(rec, str):
            try:
                rec = json.loads(rec)
            except json.JSONDecodeError as e:
                return jsonify(valid=False, errors=[f"invalid JSON: {e.msg} (line {e.lineno})"])
        if not isinstance(rec, dict):
            raise BadRequest("'record' must be a JSON object (or a string containing one)")
        errors = triage.validate(rec, json.loads(read("ROUTING_PATH")))
        return jsonify(valid=not errors, errors=errors)

    @app.post("/api/reply/check")
    def reply_check():
        data = body()
        draft = text_field(data, "draft")
        allow = data.get("allow", [])
        if isinstance(allow, str):
            allow = [a.strip() for a in allow.split(",")]
        if not isinstance(allow, list) or not all(isinstance(a, str) for a in allow):
            raise BadRequest("'allow' must be a list of strings or a comma-separated string")
        return jsonify(reply.check(draft, read("POLICY_PATH"), read("TONE_PATH"), allow))

    @app.post("/api/qa/aggregate")
    def qa_aggregate():
        data = body()
        grades = data.get("grades")
        if isinstance(grades, str):
            if not grades.strip():
                raise BadRequest("'grades' is required")
            try:
                grades = qa.parse_grades(grades)
            except ValueError as e:
                return jsonify(errors=[str(e)])
        if not isinstance(grades, list):
            raise BadRequest("'grades' must be a JSON array (or a string containing JSON/JSONL)")
        return jsonify(qa.aggregate(grades, read("RUBRIC_PATH")))

    @app.post("/api/bugs/search")
    def bug_search():
        data = body()
        query = text_field(data, "query")
        top = data.get("top", 5)
        if not isinstance(top, int) or isinstance(top, bool) or not 1 <= top <= 50:
            raise BadRequest("'top' must be an integer between 1 and 50")
        return jsonify(bugs.search(read("CHANGELOG_PATH"), query, top))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
