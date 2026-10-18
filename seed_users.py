"""Create (or reset) the first login accounts in whichever database .env points to.
Usage:  python seed_users.py                     -> admin / Admin@12345 , ops / User@12345
        python seed_users.py MyAdminPw MyUserPw  -> choose your own passwords (min 8 chars)
Change the passwords after first login (sidebar -> Password)."""
import sys
from werkzeug.security import generate_password_hash
import db

admin_pw = sys.argv[1] if len(sys.argv) > 1 else "Admin@12345"
user_pw = sys.argv[2] if len(sys.argv) > 2 else "User@12345"

for username, name, role, pw in [("admin", "Airport Administrator", "admin", admin_pw),
                                 ("ops", "Operations Staff", "user", user_pw)]:
    db.execute(
        "INSERT INTO AppUser (username, password_hash, full_name, role) VALUES (%s,%s,%s,%s) AS new"
        " ON DUPLICATE KEY UPDATE password_hash=new.password_hash, full_name=new.full_name,"
        " role=new.role, is_active=1",
        (username, generate_password_hash(pw, method="pbkdf2:sha256"), name, role))
    print(f"ready: {username} ({role})")
