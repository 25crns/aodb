"""Airport AODB - Flask backend.
Plain SQL through PyMySQL (no ORM) so every database operation stays visible for the viva.
Run locally:  python app.py   ->  http://127.0.0.1:5000
On Vercel this file is detected automatically (it exposes `app`)."""
import os
import time
from datetime import datetime, date, timedelta
from decimal import Decimal

import pymysql
from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature

import db
from lab_queries import LAB_QUERIES

BASE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(BASE, "public")

app = Flask(__name__, static_folder=None)
app.json.sort_keys = False


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, timedelta):
        return str(o)
    raise TypeError(f"Cannot serialise {type(o)}")


app.json.default = _json_default


# ---------------------------------------------------------------- authentication & roles
# Login = signed token in an HttpOnly cookie (stateless, so it works on Vercel serverless).
# Roles: 'admin' = everything; 'user' = operations staff (see ADMIN_ONLY below).
SECRET_KEY = os.getenv("SECRET_KEY") or "dev-only-secret-change-me"
SESSION_HOURS = 8
COOKIE = "aodb_session"
_signer = URLSafeTimedSerializer(SECRET_KEY, salt="aodb-session")
DUMMY_HASH = generate_password_hash("not-a-real-password", method="pbkdf2:sha256")
FLIGHT_STATUSES = ("Scheduled", "Boarding", "Departed", "Arrived", "Delayed", "Cancelled")

PUBLIC_ENDPOINTS = {"login", "health"}
ADMIN_ONLY = {
    "flights_add", "flights_update", "flights_delete",      # full flight management
    "passengers_delete", "boarding_delete",                 # destructive actions
    "staff_add", "staff_delete", "assignments_add", "assignments_delete",
    "gates_update", "audit", "lab_list", "lab_run",         # gates, audit log, SQL Lab
}                                                           # (+ every users_* endpoint)


def hash_pw(pw):
    return generate_password_hash(pw, method="pbkdf2:sha256")


def _is_https():
    return request.is_secure or request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip() == "https"


@app.before_request
def authenticate():
    """Runs before EVERY /api request: who is calling, and are they allowed?"""
    if not request.path.startswith("/api/") or request.endpoint in PUBLIC_ENDPOINTS:
        return None
    user = None
    token = request.cookies.get(COOKIE)
    if token:
        try:
            uid = _signer.loads(token, max_age=SESSION_HOURS * 3600)["uid"]
            user = db.fetch_one(
                "SELECT user_id, username, full_name, role FROM AppUser WHERE user_id=%s AND is_active=1", (uid,))
        except (BadSignature, KeyError):
            user = None
    if not user:
        return jsonify(error="Please sign in."), 401
    ep = request.endpoint or ""
    if (ep in ADMIN_ONLY or ep.startswith("users_")) and user["role"] != "admin":
        return jsonify(error="Not allowed: this action is for administrators only."), 403
    g.user = user
    return None


# ---------------------------------------------------------------- helpers
def body():
    return request.get_json(force=True, silent=True) or {}


def nz(v):
    """Empty string -> NULL"""
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def to_int(v):
    return None if v in (None, "") else int(v)


def dt(v):
    """'2026-09-28T12:30' (browser) -> '2026-09-28 12:30:00' (MySQL)"""
    v = nz(v)
    if v is None:
        return None
    v = v.replace("T", " ")
    return v + ":00" if len(v) == 16 else v


# ---------------------------------------------------------------- errors
FRIENDLY = {
    1062: "Duplicate value - that record already exists.",
    1451: "Cannot delete - other records still depend on this row.",
    1452: "Invalid reference - the related record does not exist.",
    3819: "A data rule (CHECK constraint) was violated.",
    1048: "A required field is empty.",
    1364: "A required field is missing.",
}


@app.errorhandler(pymysql.MySQLError)
def on_db_error(e):
    code = e.args[0] if e.args and isinstance(e.args[0], int) else 0
    detail = e.args[1] if len(e.args) > 1 else str(e)
    if code in (1044, 1045, 1049, 2002, 2003, 2006, 2013):
        return jsonify(error=f"Cannot reach the database - check your DB settings. ({detail})", code=code), 503
    if code == 1644:  # SIGNAL raised by one of our triggers / procedures
        return jsonify(error=detail, code=code), 409
    msg = f"{FRIENDLY.get(code, 'Database error.')} ({detail})"
    return jsonify(error=msg, code=code), (409 if code in (1062, 1451) else 400)


@app.errorhandler(Exception)
def on_error(e):
    if isinstance(e, HTTPException):
        return e
    if isinstance(e, KeyError):
        return jsonify(error=f"Missing field: {e.args[0]}"), 400
    if isinstance(e, (ValueError, TypeError)):
        return jsonify(error=f"Invalid input: {e}"), 400
    app.logger.exception(e)
    return jsonify(error="Unexpected server error"), 500


# ---------------------------------------------------------------- health / lookups / dashboard
@app.get("/api/health")
def health():
    db.fetch_one("SELECT 1 AS ok")
    return {"ok": True}


@app.get("/api/lookups")
def lookups():
    return {
        "airlines": db.fetch_all("SELECT airline_id, airline_name, iata_code FROM Airline ORDER BY airline_name"),
        "aircraft": db.fetch_all("SELECT aircraft_type_id, CONCAT(manufacturer,' ',model) AS name, seat_capacity FROM AircraftType ORDER BY name"),
        "gates": db.fetch_all("SELECT gate_id, gate_number, terminal, status FROM Gate ORDER BY gate_number"),
        "flights": db.fetch_all("SELECT flight_id, flight_number, status FROM FlightSchedule ORDER BY scheduled_departure"),
        "passengers": db.fetch_all("SELECT passenger_id, CONCAT(first_name,' ',last_name) AS name, passport_number FROM Passenger ORDER BY first_name"),
        "staff": db.fetch_all("SELECT staff_id, CONCAT(first_name,' ',last_name) AS name, role FROM Staff ORDER BY first_name"),
    }


@app.get("/api/dashboard")
def dashboard():
    by_status = {r["status"]: r["total"] for r in db.fetch_all(
        "SELECT status, COUNT(*) AS total FROM FlightSchedule GROUP BY status")}
    totals = db.fetch_one(
        "SELECT (SELECT COUNT(*) FROM FlightSchedule) AS flights,"
        " (SELECT COUNT(*) FROM Passenger) AS passengers,"
        " (SELECT COUNT(*) FROM Staff) AS staff,"
        " (SELECT COUNT(*) FROM Gate WHERE status = 'Available') AS gates_available")
    flights = db.fetch_all("SELECT * FROM FlightOperationsView ORDER BY scheduled_departure")  # uses the VIEW
    return {"totals": totals, "by_status": by_status, "flights": flights}


# ---------------------------------------------------------------- flights (CRUD)
FLIGHT_SELECT = """
SELECT f.flight_id, f.flight_number, f.airline_id, a.airline_name,
       f.aircraft_type_id, CONCAT(ac.manufacturer,' ',ac.model) AS aircraft,
       f.gate_id, g.gate_number, f.departure_airport, f.arrival_airport,
       f.scheduled_departure, f.scheduled_arrival, f.status
FROM FlightSchedule f
JOIN Airline a       ON f.airline_id = a.airline_id
JOIN AircraftType ac ON f.aircraft_type_id = ac.aircraft_type_id
LEFT JOIN Gate g     ON f.gate_id = g.gate_id"""


def flight_params(d):
    return (d["flight_number"].strip().upper(), int(d["airline_id"]), int(d["aircraft_type_id"]),
            to_int(d.get("gate_id")), d["departure_airport"].strip().upper(),
            d["arrival_airport"].strip().upper(), dt(d["scheduled_departure"]),
            dt(d["scheduled_arrival"]), d.get("status") or "Scheduled")


@app.get("/api/flights")
def flights_list():
    sql, args, where = FLIGHT_SELECT, [], []
    st, q = request.args.get("status"), request.args.get("q")
    if st:
        where.append("f.status = %s"); args.append(st)
    if q:
        where.append("(f.flight_number LIKE %s OR a.airline_name LIKE %s OR f.arrival_airport LIKE %s)")
        args += [f"%{q}%"] * 3
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY f.scheduled_departure"
    return jsonify(db.fetch_all(sql, args or None))


@app.post("/api/flights")
def flights_add():
    new_id = db.execute(
        "INSERT INTO FlightSchedule (flight_number, airline_id, aircraft_type_id, gate_id,"
        " departure_airport, arrival_airport, scheduled_departure, scheduled_arrival, status)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", flight_params(body()))
    return {"flight_id": new_id}, 201


@app.put("/api/flights/<int:fid>")
def flights_update(fid):
    db.execute(
        "UPDATE FlightSchedule SET flight_number=%s, airline_id=%s, aircraft_type_id=%s, gate_id=%s,"
        " departure_airport=%s, arrival_airport=%s, scheduled_departure=%s, scheduled_arrival=%s,"
        " status=%s WHERE flight_id=%s", flight_params(body()) + (fid,))
    return {"ok": True}


@app.delete("/api/flights/<int:fid>")
def flights_delete(fid):
    # One TRANSACTION: remove dependants first, then the flight. Any error -> full ROLLBACK.
    with db.cursor() as cur:
        cur.execute("DELETE FROM BoardingPass WHERE flight_id=%s", (fid,))
        cur.execute("DELETE FROM StaffAssignment WHERE flight_id=%s", (fid,))
        cur.execute("DELETE FROM FlightStatusHistory WHERE flight_id=%s", (fid,))
        cur.execute("DELETE FROM FlightSchedule WHERE flight_id=%s", (fid,))
    return {"ok": True}


# ---------------------------------------------------------------- passengers (CRUD)
def passenger_params(d):
    return (d["first_name"].strip(), d["last_name"].strip(), nz(d.get("date_of_birth")),
            d["passport_number"].strip(), nz(d.get("nationality")), nz(d.get("email")), nz(d.get("phone")))


@app.get("/api/passengers")
def passengers_list():
    q = request.args.get("q")
    sql = "SELECT * FROM Passenger"
    args = None
    if q:
        sql += " WHERE first_name LIKE %s OR last_name LIKE %s OR passport_number LIKE %s"
        args = [f"%{q}%"] * 3
    return jsonify(db.fetch_all(sql + " ORDER BY passenger_id", args))


@app.post("/api/passengers")
def passengers_add():
    new_id = db.execute(
        "INSERT INTO Passenger (first_name,last_name,date_of_birth,passport_number,nationality,email,phone)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s)", passenger_params(body()))
    return {"passenger_id": new_id}, 201


@app.put("/api/passengers/<int:pid>")
def passengers_update(pid):
    db.execute(
        "UPDATE Passenger SET first_name=%s,last_name=%s,date_of_birth=%s,passport_number=%s,"
        "nationality=%s,email=%s,phone=%s WHERE passenger_id=%s", passenger_params(body()) + (pid,))
    return {"ok": True}


@app.delete("/api/passengers/<int:pid>")
def passengers_delete(pid):
    db.execute("DELETE FROM Passenger WHERE passenger_id=%s", (pid,))  # blocked by FK if a boarding pass exists
    return {"ok": True}


# ---------------------------------------------------------------- boarding
@app.get("/api/boarding")
def boarding_list():
    sql = """SELECT bp.boarding_pass_id, bp.passenger_id,
                    CONCAT(p.first_name,' ',p.last_name) AS passenger,
                    bp.flight_id, f.flight_number, f.status AS flight_status,
                    bp.seat_number, bp.boarding_group, bp.boarding_time, bp.boarding_status
             FROM BoardingPass bp
             JOIN Passenger p      ON bp.passenger_id = p.passenger_id
             JOIN FlightSchedule f ON bp.flight_id = f.flight_id"""
    fid = request.args.get("flight_id")
    args = None
    if fid:
        sql += " WHERE bp.flight_id = %s"; args = [fid]
    return jsonify(db.fetch_all(sql + " ORDER BY f.flight_number, bp.seat_number", args))


@app.post("/api/boarding")
def boarding_add():
    d = body()
    new_id = db.execute(
        "INSERT INTO BoardingPass (passenger_id, flight_id, seat_number, boarding_group) VALUES (%s,%s,%s,%s)",
        (int(d["passenger_id"]), int(d["flight_id"]), d["seat_number"].strip().upper(), nz(d.get("boarding_group"))))
    return {"boarding_pass_id": new_id}, 201


@app.post("/api/boarding/<int:bid>/board")
def boarding_board(bid):
    # Stored procedure = transaction (lock row, validate, update, COMMIT / ROLLBACK).
    # The BEFORE UPDATE trigger then stamps boarding_time automatically.
    with db.cursor() as cur:
        cur.execute("CALL sp_board_passenger(%s)", (bid,))
    return {"ok": True}


@app.put("/api/boarding/<int:bid>/cancel")
def boarding_cancel(bid):
    db.execute("UPDATE BoardingPass SET boarding_status='Cancelled' WHERE boarding_pass_id=%s", (bid,))
    return {"ok": True}


@app.delete("/api/boarding/<int:bid>")
def boarding_delete(bid):
    db.execute("DELETE FROM BoardingPass WHERE boarding_pass_id=%s", (bid,))
    return {"ok": True}


# ---------------------------------------------------------------- staff & assignments
@app.get("/api/staff")
def staff_list():
    return jsonify(db.fetch_all("SELECT * FROM Staff ORDER BY staff_id"))


@app.post("/api/staff")
def staff_add():
    d = body()
    new_id = db.execute(
        "INSERT INTO Staff (first_name,last_name,role,department,email,phone,employment_status)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (d["first_name"].strip(), d["last_name"].strip(), d["role"].strip(), nz(d.get("department")),
         nz(d.get("email")), nz(d.get("phone")), d.get("employment_status") or "Active"))
    return {"staff_id": new_id}, 201


@app.delete("/api/staff/<int:sid>")
def staff_delete(sid):
    db.execute("DELETE FROM Staff WHERE staff_id=%s", (sid,))
    return {"ok": True}


@app.get("/api/assignments")
def assignments_list():
    return jsonify(db.fetch_all(
        """SELECT sa.assignment_id, CONCAT(s.first_name,' ',s.last_name) AS staff_member,
                  f.flight_number, sa.assignment_role, sa.start_time, sa.end_time
           FROM StaffAssignment sa
           JOIN Staff s          ON sa.staff_id = s.staff_id
           JOIN FlightSchedule f ON sa.flight_id = f.flight_id
           ORDER BY f.flight_number, sa.start_time"""))


@app.post("/api/assignments")
def assignments_add():
    d = body()
    new_id = db.execute(
        "INSERT INTO StaffAssignment (staff_id, flight_id, assignment_role, start_time, end_time)"
        " VALUES (%s,%s,%s,%s,%s)",
        (int(d["staff_id"]), int(d["flight_id"]), d["assignment_role"].strip(),
         dt(d["start_time"]), dt(d.get("end_time"))))
    return {"assignment_id": new_id}, 201


@app.delete("/api/assignments/<int:aid>")
def assignments_delete(aid):
    db.execute("DELETE FROM StaffAssignment WHERE assignment_id=%s", (aid,))
    return {"ok": True}


# ---------------------------------------------------------------- gates
@app.get("/api/gates")
def gates_list():
    return jsonify(db.fetch_all(
        """SELECT g.gate_id, g.gate_number, g.terminal, g.gate_type, g.status,
                  COUNT(f.flight_id) AS active_flights
           FROM Gate g
           LEFT JOIN FlightSchedule f ON f.gate_id = g.gate_id AND f.status <> 'Cancelled'
           GROUP BY g.gate_id, g.gate_number, g.terminal, g.gate_type, g.status
           ORDER BY g.gate_number"""))


@app.put("/api/gates/<int:gid>")
def gates_update(gid):
    db.execute("UPDATE Gate SET status=%s WHERE gate_id=%s", (body()["status"], gid))
    return {"ok": True}


# ---------------------------------------------------------------- reports, audit, SQL lab
@app.get("/api/reports")
def reports():
    q = db.fetch_all
    return {
        "flights_by_status": q("SELECT status AS label, COUNT(*) AS total FROM FlightSchedule GROUP BY status ORDER BY total DESC"),
        "flights_per_airline": q("SELECT a.airline_name AS label, COUNT(f.flight_id) AS total FROM Airline a LEFT JOIN FlightSchedule f ON a.airline_id = f.airline_id GROUP BY a.airline_id, a.airline_name ORDER BY total DESC"),
        "passengers_per_flight": q("SELECT flight_number AS label, passenger_count AS total FROM FlightStatisticsView ORDER BY flight_number"),
        "boarding_status": q("SELECT boarding_status AS label, COUNT(*) AS total FROM BoardingPass GROUP BY boarding_status"),
        "staff_by_department": q("SELECT COALESCE(department,'Unassigned') AS label, COUNT(*) AS total FROM Staff GROUP BY department"),
        "staff_by_role": q("SELECT assignment_role AS label, COUNT(*) AS total FROM StaffAssignment GROUP BY assignment_role"),
        "gates_by_status": q("SELECT status AS label, COUNT(*) AS total FROM Gate GROUP BY status"),
        "flight_stats": q("SELECT flight_number, status, passenger_count, staff_count FROM FlightStatisticsView ORDER BY flight_number"),
    }


@app.get("/api/audit")
def audit():
    return {
        "flight_history": db.fetch_all(
            """SELECT h.history_id, f.flight_number, h.old_status, h.new_status, h.changed_at
               FROM FlightStatusHistory h JOIN FlightSchedule f ON h.flight_id = f.flight_id
               ORDER BY h.changed_at DESC, h.history_id DESC LIMIT 50"""),
        "passenger_audit": db.fetch_all(
            "SELECT audit_id, passenger_id, operation, changed_at FROM PassengerAudit"
            " ORDER BY changed_at DESC, audit_id DESC LIMIT 50"),
    }


@app.get("/api/lab")
def lab_list():
    return jsonify([{"key": k, "category": c, "title": t, "sql": s} for k, c, t, s in LAB_QUERIES])


@app.get("/api/lab/<key>")
def lab_run(key):
    for k, _c, _t, sql in LAB_QUERIES:
        if k == key:
            return jsonify(db.fetch_all(sql))
    return jsonify(error="Unknown query"), 404


# ---------------------------------------------------------------- login / logout / account
@app.post("/api/login")
def login():
    d = body()
    u = db.fetch_one(
        "SELECT user_id, username, full_name, role, password_hash, is_active FROM AppUser WHERE username=%s",
        ((d.get("username") or "").strip().lower(),))
    # always run a hash check (even for unknown users) so response time does not reveal valid usernames
    ok = check_password_hash(u["password_hash"] if u else DUMMY_HASH, d.get("password") or "")
    if not (u and u["is_active"] and ok):
        time.sleep(0.5)
        return jsonify(error="Invalid username or password."), 401
    db.execute("UPDATE AppUser SET last_login = NOW() WHERE user_id=%s", (u["user_id"],))
    resp = jsonify({k: u[k] for k in ("user_id", "username", "full_name", "role")})
    resp.set_cookie(COOKIE, _signer.dumps({"uid": u["user_id"]}), max_age=SESSION_HOURS * 3600,
                    httponly=True, samesite="Strict", secure=_is_https())
    return resp


@app.post("/api/logout")
def logout():
    resp = jsonify(ok=True)
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/api/me")
def me():
    return jsonify(g.user)


@app.post("/api/me/password")
def change_password():
    d = body()
    new = d.get("new_password") or ""
    if len(new) < 8:
        return jsonify(error="New password must be at least 8 characters."), 400
    row = db.fetch_one("SELECT password_hash FROM AppUser WHERE user_id=%s", (g.user["user_id"],))
    if not check_password_hash(row["password_hash"], d.get("old_password") or ""):
        return jsonify(error="Current password is incorrect."), 403
    db.execute("UPDATE AppUser SET password_hash=%s WHERE user_id=%s", (hash_pw(new), g.user["user_id"]))
    return {"ok": True}


# ---------------------------------------------------------------- flight status (allowed for 'user' too)
@app.patch("/api/flights/<int:fid>/status")
def flights_status(fid):
    st = body().get("status")
    if st not in FLIGHT_STATUSES:
        return jsonify(error="Invalid status."), 400
    db.execute("UPDATE FlightSchedule SET status=%s WHERE flight_id=%s", (st, fid))  # trigger logs the change
    return {"ok": True}


# ---------------------------------------------------------------- user management (admin only: users_*)
@app.get("/api/users")
def users_list():
    return jsonify(db.fetch_all(
        "SELECT user_id, username, full_name, role, is_active, last_login, created_at FROM AppUser ORDER BY user_id"))


@app.post("/api/users")
def users_add():
    d = body()
    pw = d.get("password") or ""
    if d.get("role") not in ("admin", "user"):
        return jsonify(error="Role must be admin or user."), 400
    if len(pw) < 8:
        return jsonify(error="Password must be at least 8 characters."), 400
    new_id = db.execute(
        "INSERT INTO AppUser (username, password_hash, full_name, role) VALUES (%s,%s,%s,%s)",
        (d["username"].strip().lower(), hash_pw(pw), nz(d.get("full_name")), d["role"]))
    return {"user_id": new_id}, 201


@app.put("/api/users/<int:uid>")
def users_update(uid):
    d = body()
    role, active = d.get("role"), int(d.get("is_active", 1))
    if role not in ("admin", "user"):
        return jsonify(error="Role must be admin or user."), 400
    if uid == g.user["user_id"] and (role != "admin" or not active):
        return jsonify(error="You cannot demote or deactivate your own account."), 400
    pw = d.get("password")
    if pw and len(pw) < 8:
        return jsonify(error="Password must be at least 8 characters."), 400
    db.execute("UPDATE AppUser SET full_name=%s, role=%s, is_active=%s WHERE user_id=%s",
               (nz(d.get("full_name")), role, active, uid))
    if pw:
        db.execute("UPDATE AppUser SET password_hash=%s WHERE user_id=%s", (hash_pw(pw), uid))
    return {"ok": True}


# ---------------------------------------------------------------- frontend (local dev; on Vercel public/ is served by the CDN)
@app.get("/")
def index():
    return send_from_directory(PUBLIC, "index.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(PUBLIC, path)


if __name__ == "__main__":
    app.run(debug=True)
