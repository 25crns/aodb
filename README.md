# Airport AODB - Setup, Online Database & Vercel Deployment

**Stack:** MySQL 8 (Aiven cloud) · Flask (Python, raw SQL via PyMySQL) · HTML/CSS/JS frontend · hosted on Vercel.
**New:** login screen + two roles (Admin, User) enforced by the backend.

```
aodb-app/
├── app.py            Flask API + authentication + role checks
├── db.py             MySQL connection helper
├── seed_users.py     creates the first admin/user accounts
├── lab_queries.py    queries shown in "SQL Lab" (admin only)
├── requirements.txt, vercel.json, .env.example
├── public/           frontend (index.html, css/style.css, js/app.js)
├── database/         SQL scripts 01-09 + load_db.sh
└── docs/             VIVA_GUIDE.md, USER_GUIDE.md
```

## Roles

| Feature | Admin | User (operations staff) |
|---|:--:|:--:|
| Dashboard, Reports | ✔ | ✔ |
| View flights, staff, assignments, gates | ✔ | ✔ |
| Add / edit / delete flights | ✔ | ✖ (can only **update status**) |
| Add / edit passengers | ✔ | ✔ |
| Delete passengers | ✔ | ✖ |
| Issue boarding pass, Board, Cancel pass | ✔ | ✔ |
| Delete boarding pass | ✔ | ✖ |
| Add / delete staff, manage assignments | ✔ | ✖ |
| Change gate status | ✔ | ✖ |
| Audit log, SQL Lab | ✔ | ✖ |
| Manage user accounts | ✔ | ✖ |
| Change own password | ✔ | ✔ |

Security is enforced **on the server** (`before_request` in `app.py`); hiding buttons in the UI is only convenience. Passwords are stored as PBKDF2-SHA256 hashes; login uses a signed, HttpOnly, SameSite=Strict cookie that expires after 8 hours.

Default accounts after `seed_users.py`: **admin / Admin@12345** and **ops / User@12345** - change them (sidebar -> Password) or pass your own: `python seed_users.py MyAdminPw MyUserPw`.

---
## Part A - Create the Python environment (Linux / Ubuntu)

```
cd ~/aodb-app
sudo apt install -y python3-venv python3-pip     # skip if already installed / no sudo (see below)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
No sudo? `python3 -m venv --without-pip venv`, `source venv/bin/activate`, `curl -sS https://bootstrap.pypa.io/get-pip.py | python`, then `pip install -r requirements.txt`.
Windows: `python -m venv venv`, `venv\Scripts\activate`, `pip install -r requirements.txt`, `copy .env.example .env`.

Create a secret key and paste it as `SECRET_KEY` in `.env`:
```
python -c "import secrets; print(secrets.token_hex(32))"
```

## Part B - Test locally first (local MySQL)

```
./database/load_db.sh localhost 3306 root       # runs 01,02,03,05,07,06,09 in the correct order
```
(If your database already exists and has everything, you only need: `mysql -u root -p < database/09_auth.sql`.)
In `.env` set `DB_PASSWORD`, `DB_NAME=airport_aodb`, `SECRET_KEY`. Then:
```
python seed_users.py
python app.py
```
Open http://127.0.0.1:5000 and sign in as `admin` and as `ops` to compare the two sides.

---
## Part C - Put the database online (Aiven free MySQL)

Vercel runs only your code; MySQL must live on a cloud host. Use a **real MySQL** host (triggers + procedures are required, so avoid TiDB/PlanetScale-style services). Aiven's free MySQL plan (checked at time of writing: 1 vCPU, 1 GB RAM, 1 GB storage, no card; may power off if unused for long - switch it on again in the console; verify limits at aiven.io/free-tier).

1. aiven.io -> sign up -> **Create service -> MySQL -> Free plan** -> region -> Create. Wait for **Running**.
2. Service Overview: copy **Host, Port, User (avnadmin), Password**. Download the **CA certificate** and save it as `ca.pem` inside `aodb-app/`.
3. Load your database - choose **one**:

**Option 0 (simplest - no mysql client or Workbench needed, works in PowerShell too)**
Fill in `.env` with the Aiven details first (`DB_HOST`, `DB_PORT`, `DB_USER=avnadmin`, `DB_PASSWORD`, `DB_SSL_CA=ca.pem`), then, with the venv active:
```
python load_db.py
```
It runs `01,02,03,05,07,06,09` in order, stops at the first error, and prints a summary (expect 11 tables, 4 views, 6 triggers, 1 procedure). Then run `python seed_users.py`.

**Option 1: rerun your scripts against Aiven with the mysql client**
```
./database/load_db.sh YOUR_HOST YOUR_PORT avnadmin ca.pem
```
It asks for the password once, runs `01,02,03,05,07,06,09` in order and stops on the first error.
(Windows / no mysql client: in MySQL Workbench create a connection with those details, SSL = *Require and Verify CA* + `ca.pem`, then open and run each script in the same order.)

**Option 2: export your existing local database (keeps your own data)**
```
mysqldump -u root -p --routines --triggers --no-tablespaces --set-gtid-purged=OFF --databases airport_aodb > aodb_dump.sql
sed -E 's/DEFINER=`[^`]*`@`[^`]*`//g' aodb_dump.sql > aodb_clean.sql
mysql -h HOST -P PORT -u avnadmin -p --ssl-mode=VERIFY_CA --ssl-ca=ca.pem < aodb_clean.sql
mysql -h HOST -P PORT -u avnadmin -p --ssl-mode=VERIFY_CA --ssl-ca=ca.pem < database/09_auth.sql
```
The `sed` line removes `DEFINER=root@localhost`, which does not exist on Aiven and would break views/triggers/procedures. The last line adds the `AppUser` login table.

4. Verify:
```
mysql -h HOST -P PORT -u avnadmin -p --ssl-mode=VERIFY_CA --ssl-ca=ca.pem -e "USE airport_aodb; SHOW FULL TABLES; SHOW TRIGGERS;"
```
Expect 11 tables (10 + AppUser), 4 views, 6 triggers.
5. Point `.env` at the cloud DB and create the first logins **in the cloud DB**:
```
DB_HOST=...   DB_PORT=...   DB_USER=avnadmin   DB_PASSWORD=...   DB_NAME=airport_aodb   DB_SSL_CA=ca.pem
```
```
python seed_users.py
python app.py          # sign in locally against the cloud DB to confirm it works
```
If you hit error 1419 (needs SUPER / log_bin_trust_function_creators) when creating triggers, copy the exact message - it is a hosting permission setting. If `CREATE DATABASE` is refused, use the default `defaultdb`: replace `airport_aodb` with `defaultdb` in the scripts, skip 01, and set `DB_NAME=defaultdb`.

---
## Part D - Deploy the website on Vercel

1. Push `aodb-app/` to a GitHub repository (`.gitignore` keeps `.env` and `venv` out; **do commit `ca.pem`** - it is a public certificate).
2. vercel.com -> **Add New -> Project** -> import the repo. Vercel detects Flask automatically (`app.py`, `requirements.txt`).
3. Open **Environment Variables** and add:

| Name | Value |
|---|---|
| DB_HOST | Aiven host |
| DB_PORT | Aiven port (not 3306) |
| DB_USER | avnadmin |
| DB_PASSWORD | Aiven password |
| DB_NAME | airport_aodb |
| DB_SSL_CA | ca.pem |
| SECRET_KEY | the long random string from Part A |

4. **Deploy** -> open `https://<project>.vercel.app` -> sign in with `admin`.
5. Any later `git push` redeploys. After changing environment variables, redeploy.

**How the pieces connect:** Browser -> Vercel (serves `public/` and runs `app.py`) -> TLS -> Aiven MySQL. The login cookie is issued by the same Vercel domain, so no CORS setup is needed.

## Troubleshooting
| Problem | Fix |
|---|---|
| Login says "Invalid username or password" | Run `python seed_users.py` against the **same** database the site uses |
| "Cannot reach the database" | Wrong host/port/password, Aiven service powered off, or `DB_SSL_CA` missing / `ca.pem` not committed |
| Every API call returns "Please sign in" after login on Vercel | `SECRET_KEY` missing or changed between deployments; set it and redeploy |
| Table `AppUser` doesn't exist | Run `database/09_auth.sql` |
| Views/triggers fail with "definer does not exist" | You used Option 2 without the `sed` step |
| `./database/load_db.sh: Permission denied` | `chmod +x database/load_db.sh` or run `bash database/load_db.sh ...` |
| First page load slow | Serverless cold start + sleeping free database; normal |
| Port 5000 busy locally | `flask --app app run --port 5001` |

## Security notes (mention in the viva)
- Never commit `.env` or database passwords; use Vercel environment variables.
- Change the seeded passwords. Admin can add/deactivate users on the **Users** page.
- Login has no lockout/rate-limit (stateless serverless app): listed as future scope. The DB connection uses TLS; the free DB accepts connections from any IP because Vercel's IPs change, so the strong password matters.
