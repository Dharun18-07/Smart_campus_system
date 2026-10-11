import datetime
from functools import wraps
import pg8000.dbapi as pg
from flask import Flask, request, session, redirect, flash, render_template_string

app = Flask(__name__)
app.secret_key = "campus-demo-key"
DB = dict(user="postgres", password="postgres", host="localhost", database="campus")

def q(sql, args=(), one=False):
    conn = pg.connect(**DB)
    try:
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = None
        if cur.description:
            cols = [c[0].decode() if isinstance(c[0], bytes) else c[0] for c in cur.description]
            data = [dict(zip(cols, r)) for r in cur.fetchall()]
            rows = (data[0] if data else None) if one else data
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def need(*roles):
    def deco(f):
        @wraps(f)
        def wrap(*a, **k):
            if "uid" not in session: return redirect("/login")
            if roles and session["role"] not in roles:
                flash("Unauthorized access.")
                return redirect("/")
            return f(*a, **k)
        return wrap
    return deco

BASE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Smart Campus Bookings</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
body { background: #f8fafc; color: #1e293b; min-height: 100vh; display: flex; flex-direction: column; }
.navbar { display: flex; justify-content: space-between; align-items: center; background: #fff; padding: 16px 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.logo { font-size: 20px; font-weight: 700; color: #0f172a; } .logo span { color: #2563eb; }
.nav-links { list-style: none; display: flex; gap: 24px; align-items: center; }
.nav-links a { text-decoration: none; color: #64748b; font-weight: 500; font-size: 14px; }
.nav-links a:hover { color: #2563eb; }
.btn-logout { background: #fee2e2; color: #991b1b !important; padding: 8px 16px; border-radius: 6px; font-weight: 600; }
.container { max-width: 1200px; margin: 30px auto; padding: 0 20px; width: 100%; flex: 1; }
.alert { background: #eff6ff; color: #1e40af; padding: 14px 20px; border-radius: 8px; margin-bottom: 24px; border-left: 4px solid #3b82f6; font-size: 14px; font-weight: 500; }
.hero { background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); color: white; padding: 60px 20px; text-align: center; border-radius: 12px; margin-bottom: 40px; }
.hero h1 { font-size: 32px; font-weight: 700; margin-bottom: 10px; } .hero p { color: #94a3b8; font-size: 16px; margin-bottom: 30px; }
.search-form { display: inline-flex; background: rgba(255,255,255,0.1); backdrop-filter: blur(12px); padding: 12px; border-radius: 12px; gap: 10px; flex-wrap: wrap; justify-content: center; align-items: center; border: 1px solid rgba(255,255,255,0.2); }
.search-form select, .search-form input { padding: 10px 14px; border-radius: 8px; border: none; outline: none; font-size: 14px; }
.search-form button { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; }
.search-form label { color: white; font-size: 13px; display: flex; align-items: center; gap: 6px; cursor: pointer; }
.section-title { font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 20px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; margin-bottom: 40px; }
.card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); border: 1px solid #e2e8f0; display: flex; flex-direction: column; justify-content: space-between; }
.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.card-header h3 { font-size: 18px; font-weight: 600; color: #0f172a; }
.badge { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
.badge-available { background: #dcfce7; color: #166534; } .badge-booked { background: #fee2e2; color: #991b1b; }
.card-body p { font-size: 14px; color: #64748b; line-height: 1.5; margin-bottom: 20px; }
.btn-primary { background: #2563eb; color: white; border: none; padding: 10px; border-radius: 8px; font-weight: 600; width: 100%; cursor: pointer; }
.btn-disabled { background: #f1f5f9; color: #94a3b8; border: none; padding: 10px; border-radius: 8px; font-weight: 600; width: 100%; cursor: not-allowed; }
.btn-danger { background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-weight: 600; cursor: pointer; }
.table-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); border: 1px solid #e2e8f0; overflow: hidden; margin-bottom: 30px; }
table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
th { background: #f8fafc; color: #475569; font-weight: 600; padding: 14px 20px; border-bottom: 1px solid #e2e8f0; }
td { padding: 14px 20px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.login-wrapper { display: flex; justify-content: center; align-items: center; min-height: 70vh; }
.login-card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; width: 100%; max-width: 400px; text-align: center; }
.login-card input { width: 100%; padding: 12px 16px; margin-bottom: 14px; border-radius: 8px; border: 1px solid #cbd5e1; outline: none; }
.login-card button { width: 100%; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
footer { text-align: center; padding: 24px; color: #94a3b8; font-size: 13px; border-top: 1px solid #e2e8f0; background: white; margin-top: auto; }
</style></head>
<body>
    <nav class="navbar">
        <div class="logo">SmartCampus <span>Bookings</span></div>
        <ul class="nav-links">
            {% if session.uid %}
                <li><a href="/">Dashboard</a></li>
                <li><a href="/my">My Reservations</a></li>
                {% if session.role in ('Admin','Maintenance') %}<li><a href="/admin">Admin Panel</a></li>{% endif %}
                <li><a href="/logout" class="btn-logout">Logout ({{ session.name }})</a></li>
            {% else %}
                <li><a href="/login">Login</a></li>
            {% endif %}
        </ul>
    </nav>
    <div class="container">
        {% for m in get_flashed_messages() %}<div class="alert">🔔 {{ m }}</div>{% endfor %}
        @@BODY@@
    </div>
    <footer>Group C5 - DBMS Project</footer>
</body></html>"""

def page(body, **ctx): return render_template_string(BASE.replace("@@BODY@@", body), **ctx)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = q("SELECT u.userid, u.name, r.rolename FROM users u JOIN role r USING(roleid) WHERE u.email=%s AND u.password = crypt(%s, u.password)", (request.form["email"], request.form["password"]), one=True)
        if u:
            session.update(uid=u["userid"], name=u["name"], role=u["rolename"])
            return redirect("/")
        flash("Invalid email or password.")
    return page("""<div class="login-wrapper"><div class="login-card"><h2 style="margin-bottom:8px">Welcome Back</h2><p style="color:#64748b; margin-bottom:24px; font-size:14px">Sign in to your campus account</p><form method=post><input name=email placeholder="Email Address" required><input name=password type=password placeholder="Password" required><button type=submit>Sign In</button></form><small style="display:block; margin-top:16px; color:#94a3b8">Demo Password (all roles): <b>pass123</b></small></div></div>""")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
@need()
def index():
    res = q("SELECT r.*, c.categoryname FROM resource r JOIN resource_category c USING(categoryid) ORDER BY r.resourceid")
    today = datetime.date.today().isoformat()
    return page("""
    <div class="hero">
        <h1>Find & Book Campus Resources</h1>
        <p>Real-time availability for classrooms, labs, equipment, and sports venues.</p>
        <form class="search-form" method=post action=/book>
            <select name=rid>{% for r in res %}<option value={{r.resourceid}}>{{r.resourcename}} ({{r.categoryname}})</option>{% endfor %}</select>
            <input type="datetime-local" name=s required value=\"""" + today + """T10:00">
            <input type="datetime-local" name=e required value=\"""" + today + """T12:00">
            <label><input type=checkbox name=wl> Waitlist if taken</label>
            <button type=submit>Request Booking</button>
        </form>
    </div>
    <div class="section-title">📦 Available Resources Catalog</div>
    <div class="grid">
        {% for r in res %}
        <div class="card">
            <div>
                <div class="card-header">
                    <h3>{{ r.resourcename }}</h3>
                    <span class="badge {% if r.status=='Available' %}badge-available{% else %}badge-booked{% endif %}">{{ r.status }}</span>
                </div>
                <div class="card-body"><p><b>Category:</b> {{ r.categoryname }}<br><b>Location:</b> {{ r.location }}<br><b>Capacity:</b> {{ r.capacity }} persons</p></div>
            </div>
            <div>
                {% if r.status == 'Available' %}
                    <form method=post action=/book style="margin:0;"><input type=hidden name=rid value={{ r.resourceid }}><input type=hidden name=s value=\"""" + today + """T10:00"><input type=hidden name=e value=\"""" + today + """T12:00"><button type=submit class="btn-primary">Book Now</button></form>
                {% else %}<button class="btn-disabled" disabled>Unavailable</button>{% endif %}
            </div>
        </div>
        {% endfor %}
    </div>""", res=res)

@app.route("/book", methods=["POST"])
@need()
def book():
    f = request.form
    try:
        q("SELECT book_resource(%s::int,%s::int,%s::timestamp,%s::timestamp)", (session["uid"], f["rid"], f["s"], f["e"]))
        flash("Reservation request submitted successfully. Waiting for admin approval.")
    except pg.Error as ex:
        if ex.args[0].get("C") == "23P01":
            if f.get("wl"):
                q("INSERT INTO waitlist(resourceid,userid,reqstarttime,reqendtime,position) SELECT %s::int,%s::int,%s::timestamp,%s::timestamp,COALESCE(MAX(position),0)+1 FROM waitlist WHERE resourceid=%s::int AND status='Waiting'", (f["rid"], session["uid"], f["s"], f["e"], f["rid"]))
                flash("Slot is taken. You have been added to the waitlist queue.")
            else: flash("That slot is already booked. Tick 'Waitlist if taken' to queue up.")
        else: flash(ex.args[0].get("M", str(ex)))
    return redirect("/my")

@app.route("/my")
@need()
def my():
    uid = session["uid"]
    bookings = q("SELECT rv.*, r.resourcename FROM reservation rv JOIN resource r USING(resourceid) WHERE rv.userid=%s ORDER BY rv.starttime DESC", (uid,))
    wl = q("SELECT w.*, r.resourcename FROM waitlist w JOIN resource r USING(resourceid) WHERE w.userid=%s ORDER BY w.waitlistid DESC", (uid,))
    notes = q("SELECT * FROM notification WHERE userid=%s ORDER BY createdat DESC LIMIT 15", (uid,))
    q("UPDATE notification SET isread=TRUE WHERE userid=%s", (uid,))
    return page("""
    <div class="section-title">📋 My Reservations</div>
    <div class="table-card"><table>
        <tr><th>#</th><th>Resource</th><th>Start Time</th><th>End Time</th><th>Status</th><th>Action</th></tr>
        {% for b in bookings %}
        <tr><td><b>#{{ b.reservationid }}</b></td><td>{{ b.resourcename }}</td><td>{{ b.starttime }}</td><td>{{ b.endtime }}</td><td><span class="badge badge-available">{{ b.status }}</span></td>
            <td>{% if b.status in ('Pending','Approved') %}<form method=post action=/cancel/{{b.reservationid}} style="margin:0;"><button type=submit class="btn-danger">Cancel</button></form>{% else %}-{% endif %}</td></tr>
        {% else %}<tr><td colspan="6" style="text-align:center; color:#94a3b8; padding:30px;">No reservations found.</td></tr>{% endfor %}
    </table></div>
    <div class="section-title">⏳ My Waitlist Entries</div>
    <div class="table-card"><table>
        <tr><th>Resource</th><th>From</th><th>To</th><th>Position</th><th>Status</th></tr>
        {% for w in wl %}
        <tr><td><b>{{ w.resourcename }}</b></td><td>{{ w.reqstarttime }}</td><td>{{ w.reqendtime }}</td><td>#{{ w.position }}</td><td>{{ w.status }}</td></tr>
        {% else %}<tr><td colspan="5" style="text-align:center; color:#94a3b8; padding:30px;">No active waitlist entries.</td></tr>{% endfor %}
    </table></div>
    <div class="section-title">🔔 Notifications</div>
    <div class="table-card" style="padding:20px">
        {% for n in notes %}<p style="padding:10px 0; border-bottom:1px solid #f1f5f9; font-size:14px; display:flex; justify-content:space-between"><span>{{ '' if n.isread else '🔴 ' }}{{ n.message }}</span><small style="color:#94a3b8">{{ n.createdat }}</small></p>
        {% else %}<p style="text-align:center; color:#94a3b8; padding:20px">No new notifications.</p>{% endfor %}
    </div>""", bookings=bookings, wl=wl, notes=notes)

@app.route("/cancel/<int:rid>", methods=["POST"])
@need()
def cancel(rid):
    q("UPDATE reservation SET status='Cancelled' WHERE reservationid=%s AND userid=%s AND status IN ('Pending','Approved')", (rid, session["uid"]))
    flash("Booking cancelled successfully.")
    return redirect("/my")

@app.route("/admin")
@need("Admin", "Maintenance")
def admin():
    pend = q("SELECT rv.*, u.name, r.resourcename FROM reservation rv JOIN users u USING(userid) JOIN resource r USING(resourceid) WHERE rv.status='Pending' ORDER BY rv.starttime")
    maint = q("SELECT m.*, r.resourcename FROM maintenance_record m JOIN resource r USING(resourceid) ORDER BY m.startdate DESC")
    util = q("SELECT * FROM v_utilisation ORDER BY hours_booked DESC")
    res = q("SELECT resourceid, resourcename FROM resource ORDER BY 1")
    return page("""
    {% if session.role=='Admin' %}
    <div class="section-title">⚡ Pending Approvals</div>
    <div class="table-card"><table>
        <tr><th>#</th><th>User</th><th>Resource</th><th>Start Time</th><th>End Time</th><th>Decision & Remarks</th></tr>
        {% for p in pend %}
        <tr><td><b>#{{ p.reservationid }}</b></td><td>{{ p.name }}</td><td>{{ p.resourcename }}</td><td>{{ p.starttime }}</td><td>{{ p.endtime }}</td>
            <td><form method=post action=/decide/{{p.reservationid}} style="display:flex; gap:8px; align-items:center; margin:0;"><input name=remarks placeholder="Remarks" style="padding:6px 10px; border:1px solid #cbd5e1; border-radius:6px; font-size:13px"><button name=d value=Approved style="background:#16a34a; color:white; border:none; padding:6px 12px; border-radius:6px; font-weight:600; cursor:pointer">Approve</button><button name=d value=Rejected class="btn-danger">Reject</button></form></td></tr>
        {% else %}<tr><td colspan="6" style="text-align:center; color:#94a3b8; padding:30px;">No pending approvals.</td></tr>{% endfor %}
    </table></div>
    {% endif %}
    <div class="section-title">🛠️ Schedule Resource Maintenance</div>
    <div class="table-card" style="padding:20px; margin-bottom:30px">
        <form method=post action=/maintenance style="display:flex; gap:12px; flex-wrap:wrap; align-items:center;">
            <select name=rid style="padding:10px; border-radius:6px; border:1px solid #cbd5e1">{% for r in res %}<option value={{r.resourceid}}>{{r.resourcename}}</option>{% endfor %}</select>
            From <input type=date name=s required style="padding:9px; border-radius:6px; border:1px solid #cbd5e1">
            To <input type=date name=e required style="padding:9px; border-radius:6px; border:1px solid #cbd5e1">
            <input name=d placeholder="Description" style="padding:9px; border-radius:6px; border:1px solid #cbd5e1; flex:1">
            <button type=submit style="background:#2563eb; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:600; cursor:pointer">Schedule</button>
        </form>
        <table style="margin-top:20px"><tr><th>Resource</th><th>From</th><th>To</th><th>Description</th><th>Status</th></tr>
            {% for m in maint %}<tr><td><b>{{m.resourcename}}</b></td><td>{{m.startdate}}</td><td>{{m.enddate}}</td><td>{{m.description}}</td><td>{{m.status}}</td></tr>{% endfor %}</table>
    </div>
    <div class="section-title">📊 Resource Utilisation Report</div>
    <div class="table-card"><table>
        <tr><th>Resource Name</th><th>Category</th><th>Approved Bookings</th><th>Hours Booked</th></tr>
        {% for u in util %}<tr><td><b>{{u.resourcename}}</b></td><td>{{u.categoryname}}</td><td>{{u.approved_bookings}}</td><td><b>{{u.hours_booked}} hrs</b></td></tr>{% endfor %}
    </table></div>""", pend=pend, maint=maint, util=util, res=res)

@app.route("/decide/<int:rid>", methods=["POST"])
@need("Admin")
def decide(rid):
    try:
        q("INSERT INTO approval(reservationid,approverid,approvalstatus,approvaldate,remarks) VALUES (%s,%s,%s,CURRENT_TIMESTAMP,%s)", (rid, session["uid"], request.form["d"], request.form.get("remarks")))
        flash(f"Reservation #{rid} {request.form['d'].lower()}.")
    except pg.Error as ex: flash(ex.args[0].get("M", str(ex)))
    return redirect("/admin")

@app.route("/maintenance", methods=["POST"])
@need("Admin", "Maintenance")
def maintenance():
    f = request.form
    try:
        q("INSERT INTO maintenance_record(resourceid,scheduledby,startdate,enddate,description) VALUES (%s::int,%s::int,%s::date,%s::date,%s)", (f["rid"], session["uid"], f["s"], f["e"], f["d"]))
        flash("Maintenance period scheduled successfully.")
    except pg.Error as ex: flash(ex.args[0].get("M", str(ex)))
    return redirect("/admin")

if __name__ == "__main__":
    app.run(debug=True)