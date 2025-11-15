import csv
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, render_template, request, send_file

app = Flask(__name__)

DATA_PATH = Path(__file__).with_name("rsvps.csv")
FIELDNAMES = ["timestamp", "name", "email", "attending", "guests", "note"]
EVENT_DETAILS = {
    "title": "AI Community Launch Party",
    "date": "Friday, July 26",
    "time": "6:00 – 9:00 PM",
    "location": "Launchpad Loft, San Francisco",
    "description": "Join fellow builders for an evening of demos, networking, and hands-on AI mini-workshops.",
}


def ensure_csv():
    if not DATA_PATH.exists():
        with DATA_PATH.open("w", newline="") as f:
            csv.DictWriter(f, FIELDNAMES).writeheader()


def read_rsvps():
    ensure_csv()
    with DATA_PATH.open() as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_rsvp(row):
    ensure_csv()
    with DATA_PATH.open("a", newline="") as f:
        writer = csv.DictWriter(f, FIELDNAMES)
        writer.writerow(row)


def validate_form(form):
    errors = {}
    name = form.get("name", "").strip()
    email = form.get("email", "").strip()
    attending = form.get("attending")
    guests = form.get("guests", "0")

    if len(name) < 2:
        errors["name"] = "Please enter your full name."
    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_pattern, email):
        errors["email"] = "Enter a valid email address."
    if attending not in {"yes", "no"}:
        errors["attending"] = "Let us know if you can attend."
    try:
        guests_val = int(guests)
        if guests_val < 0 or guests_val > 5:
            raise ValueError
    except ValueError:
        errors["guests"] = "The guest count must be between 0 and 5."
        guests_val = 0

    note = form.get("note", "").strip()
    return errors, {
        "name": name,
        "email": email,
        "attending": attending or "no",
        "guests": str(guests_val),
        "note": note,
    }


@app.get("/")
def index():
    return render_template("index.html", event=EVENT_DETAILS)


@app.post("/submit")
def submit():
    errors, cleaned = validate_form(request.form)
    if errors:
        return (
            render_template(
                "index.html",
                event=EVENT_DETAILS,
                errors=errors,
                form_data=request.form,
            ),
            400,
        )
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        **cleaned,
    }
    write_rsvp(row)
    return render_template("thanks.html", event=EVENT_DETAILS, rsvp=row)


@app.get("/rsvps")
def list_rsvps():
    rows = read_rsvps()
    if not rows:
        abort(404, description="No RSVPs recorded yet.")
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    totals = {
        "yes": sum(1 for r in rows if r["attending"] == "yes"),
        "no": sum(1 for r in rows if r["attending"] == "no"),
        "guests": sum(int(r["guests"]) for r in rows if r["attending"] == "yes"),
    }
    return render_template("rsvps.html", rows=rows, totals=totals, event=EVENT_DETAILS)


@app.get("/rsvps.csv")
def download_rsvps():
    rows = read_rsvps()
    if not rows:
        abort(404, description="No RSVPs recorded yet.")
    filename = f"rsvps_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    return send_file(
        DATA_PATH,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(debug=True)
