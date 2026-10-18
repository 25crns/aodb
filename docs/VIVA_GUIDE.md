# AODB - Complete Viva Guide

## 0. 60-second pitch
"Our project is an **Airport Operational Database**. It stores airlines, aircraft types, gates, flights, passengers, staff, staff assignments and boarding passes in **10 normalized MySQL tables** (8 core + 2 audit). It demonstrates keys and constraints, CRUD, joins, aggregates, GROUP BY/HAVING, subqueries, **4 views**, **transactions**, **triggers** and normalization to **3NF**. A Flask REST backend and a minimalist web dashboard connect to the database; the database is hosted on cloud MySQL (Aiven), the site on Vercel, and access is controlled by login with admin/user roles."

---
## 1. DBMS fundamentals
- **Data**: raw facts. **Database**: organized, persistent collection of related data. **DBMS**: software to define, store, query, secure and share a database (MySQL). **RDBMS**: stores data as tables (relations) linked by keys.
- **File system vs DBMS**: files have redundancy, inconsistency, no concurrency control, no integrity rules, weak security, no standard query language. A DBMS solves these.
- **Advantages**: reduced redundancy, integrity, concurrent access, security, backup/recovery, data independence, standard SQL.
- **Schema** = structure (design); **instance** = data at a moment in time.
- **Three-schema architecture**: external (views) / conceptual (tables) / internal (storage). **Data independence**: logical (change tables without breaking apps - views help) and physical (change storage without changing tables).
- **Relational terms**: relation = table, tuple = row, attribute = column, domain = allowed values, degree = number of columns, cardinality of a relation = number of rows.
- **Why MySQL / InnoDB**: open source, supports FK, CHECK (8.0.16+), views, triggers, procedures, ACID transactions (InnoDB engine).

## 2. Keys
- **Super key**: any attribute set that uniquely identifies a row. **Candidate key**: minimal super key. **Primary key**: chosen candidate key (unique, NOT NULL). **Alternate key**: candidate not chosen. **Composite key**: more than one column. **Foreign key**: column referring to a primary key of another (or same) table. **Surrogate key**: system-generated id (our AUTO_INCREMENT ids).
- Our examples: `Passenger.passport_number` is a candidate (alternate) key - UNIQUE; `passenger_id` is the primary key. `Airline.iata_code` and `icao_code` are alternate keys. `BoardingPass (flight_id, seat_number)` and `(passenger_id, flight_id)` are unique composites.

## 3. ER model
- **Entity** (thing: Airline), **attribute** (property), **relationship** (association). Attribute types: simple/composite, single/multi-valued, derived, key. **Weak entity**: no key of its own (we have none; our audit tables are separate logs).
- **Cardinality**: 1:1, 1:N, M:N. **Participation**: total/partial.
- **Our relationships**
  - Airline 1:N FlightSchedule; AircraftType 1:N FlightSchedule; Gate 1:N FlightSchedule.
  - **Passenger M:N FlightSchedule** resolved by associative entity **BoardingPass** (a passenger can fly many flights; a flight carries many passengers).
  - **Staff M:N FlightSchedule** resolved by **StaffAssignment**.
  - FlightSchedule 1:N FlightStatusHistory.
- **Why resolve M:N?** A relational table cannot hold a multi-valued foreign key; a junction table holds two foreign keys plus the relationship's own attributes (seat, role, times).
- **ER -> tables rules**: entity -> table; 1:N -> FK on the "many" side; M:N -> junction table.
- **Why FlightSchedule is central**: every operational fact (who flies, where, with what, who works it) hangs off a flight.

## 4. Table-by-table justification
| Table | Why | Key points |
|---|---|---|
| Airline | Airline data stored once | PK airline_id; UNIQUE iata/icao codes |
| AircraftType | Aircraft specs stored once per model | CHECK seat_capacity > 0, cargo >= 0 |
| Gate | Physical gates | UNIQUE gate_number; CHECK status |
| FlightSchedule | Central operational table | 3 FKs; CHECK status; CHECK arrival >= departure |
| Passenger | Traveller identity | UNIQUE passport |
| Staff | Employees | CHECK employment_status |
| StaffAssignment | Junction Staff-Flight | 2 FKs; CHECK end >= start |
| BoardingPass | Junction Passenger-Flight | 2 FKs; UNIQUE seat per flight |
| FlightStatusHistory | Audit (trigger output) | FK to flight |
| PassengerAudit | Audit (trigger output) | **No FK on purpose** so delete-audit rows survive the deleted passenger |

## 5. Constraints (integrity)
- **Domain integrity**: data type, NOT NULL, DEFAULT, CHECK (status lists, capacity > 0).
- **Entity integrity**: PK unique and not NULL.
- **Referential integrity**: FK values must exist in the parent (or be NULL). Default action here is **RESTRICT** (cannot delete a parent that has children - we demo this by deleting a passenger with a boarding pass, error 1451). Other options: CASCADE, SET NULL, NO ACTION.
- **User-defined integrity**: business rules (gate conflict) via triggers.
- **Error codes to remember**: 1062 duplicate, 1451 cannot delete parent, 1452 cannot add child (parent missing), 3819 CHECK violated, 1644 custom SIGNAL.

## 6. SQL
- **DDL**: CREATE, ALTER, DROP, TRUNCATE (auto-commit). **DML**: INSERT, UPDATE, DELETE. **DQL**: SELECT. **DCL**: GRANT, REVOKE. **TCL**: START TRANSACTION, COMMIT, ROLLBACK, SAVEPOINT.
- **DELETE vs TRUNCATE vs DROP**: DELETE removes chosen rows (can rollback, fires triggers); TRUNCATE empties the table quickly (DDL); DROP removes the table itself.
- **WHERE vs HAVING**: WHERE filters rows *before* grouping; HAVING filters groups *after* aggregation.
- **Order of execution**: FROM/JOIN -> WHERE -> GROUP BY -> HAVING -> SELECT -> DISTINCT -> ORDER BY -> LIMIT.
- **Joins**: INNER (matching rows only); LEFT (all left rows + matches, NULL if none); RIGHT; FULL (not native in MySQL); CROSS; SELF. We use LEFT JOIN for "passengers with no boarding pass" and "staff with no assignment" (`WHERE x IS NULL` pattern = anti-join).
- **Aggregates**: COUNT, SUM, AVG, MIN, MAX (ignore NULLs, except COUNT(*)). `COUNT(*)` counts rows, `COUNT(col)` counts non-NULL values.
- **Subqueries**: scalar (returns one value: `> (SELECT AVG(...))`), row/table subquery, **derived table** (subquery in FROM - needed for "average of counts"), correlated (references outer query), `IN`/`EXISTS`. Our gate trigger uses `EXISTS`.
- **LIKE**: `%` any string, `_` one character. **BETWEEN** is inclusive. **IN** = list of OR.
- **Indexes**: PK/UNIQUE create indexes automatically; indexes speed lookups but slow writes.
- **Views**: stored SELECT, a virtual table. Benefits: simplicity (hides joins), security (expose only some columns), logical data independence. Ours: FlightOperationsView, PassengerBoardingView, StaffOperationsView, FlightStatisticsView. Views containing joins/aggregates are generally **not updatable**. A view stores no data - it re-runs its query.
- **Stored procedure**: saved SQL program (`sp_board_passenger`). Benefits: reuse, less network traffic, central business logic.

## 7. Normalization
- **Why**: remove redundancy and anomalies. **Insertion anomaly** (cannot add an airline without a flight), **update anomaly** (change an airline name in many rows), **deletion anomaly** (deleting last flight deletes airline info).
- **Functional dependency** X -> Y: X determines Y. **Full** vs **partial** vs **transitive** dependency.
- **1NF**: atomic values, no repeating groups. **2NF**: 1NF + no *partial* dependency on part of a composite key. **3NF**: 2NF + no *transitive* dependency (non-key -> non-key). **BCNF**: every determinant is a candidate key (stricter 3NF).
- **Worked example** (use this in the viva):
  - **UNF**: `Flight(flight_id, flight_number, airline_name, airline_country, aircraft_model, aircraft_capacity, gate_number, passenger_1, passenger_2, passenger_3 ...)` - repeating passenger columns, duplicated airline/aircraft data.
  - **1NF**: remove repeating group -> one row per (flight, passenger): `(flight_id, passenger_id, passenger_name, seat, flight_number, airline_name, ...)`; key = (flight_id, passenger_id).
  - **2NF**: `passenger_name` depends only on passenger_id; `flight_number, airline_name...` depend only on flight_id (partial dependencies). Split into **Flight**, **Passenger**, **BoardingPass(flight_id, passenger_id, seat)**.
  - **3NF**: in Flight, `flight_id -> airline_id -> airline_name, country` and `flight_id -> aircraft_type_id -> model, capacity` are transitive. Split into **Airline** and **AircraftType**; Flight keeps only FKs.
  - Result = our schema. Every non-key attribute depends on "the key, the whole key, and nothing but the key".
- **Denormalization**: deliberately adding redundancy for speed (not needed here). Our dashboard counts come from views/queries, not stored duplicates.

## 8. Transactions & ACID
- **Transaction**: a logical unit of work - all or nothing.
- **ACID**: **Atomicity** (all steps or none - ROLLBACK undoes), **Consistency** (DB moves from one valid state to another; constraints enforced), **Isolation** (concurrent transactions do not see each other's partial work), **Durability** (committed data survives crashes - InnoDB redo log).
- **States**: active -> partially committed -> committed; or failed -> aborted.
- **Commands**: `START TRANSACTION; ... COMMIT;` / `ROLLBACK;`. MySQL defaults to **autocommit** (each statement commits itself) until you START TRANSACTION. DDL statements cause implicit commit. `SAVEPOINT` allows partial rollback.
- **Concurrency problems**: dirty read, non-repeatable read, phantom read, lost update. **Isolation levels**: READ UNCOMMITTED, READ COMMITTED, **REPEATABLE READ (InnoDB default)**, SERIALIZABLE. **Locks**: shared/exclusive, row-level in InnoDB. `SELECT ... FOR UPDATE` locks the row - used in `sp_board_passenger` so two operators cannot board the same pass twice. **Deadlock**: two transactions wait on each other; InnoDB detects and rolls one back.
- **In our project**: (1) script 06 shows COMMIT vs ROLLBACK; (2) `sp_board_passenger` locks, validates, updates, commits, and has an EXIT HANDLER that rolls back on error; (3) the Flask "delete flight" route deletes children and parent inside one transaction (`with db.cursor()`).

## 9. Triggers
- **Definition**: stored code that runs **automatically** on INSERT/UPDATE/DELETE of a table. Row-level (`FOR EACH ROW`). `NEW` = new row values, `OLD` = old values (UPDATE has both, INSERT only NEW, DELETE only OLD).
- **BEFORE** triggers: validate or modify NEW values, or block the operation (can `SET NEW.col`). **AFTER** triggers: audit/history and related actions (cannot modify NEW).
- **SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT=...** raises a custom error (shows as 1644) and cancels the statement.
- **Our triggers**
| Trigger | Table / timing | What it does |
|---|---|---|
| trg_boarding_time | BoardingPass, BEFORE UPDATE | When status becomes Boarded and time is empty, `SET NEW.boarding_time = CURRENT_TIMESTAMP` (BEFORE because it modifies the row being saved) |
| trg_flight_status_history | FlightSchedule, AFTER UPDATE | If `OLD.status <> NEW.status` insert old/new into FlightStatusHistory (AFTER because it should log only successful changes) |
| trg_gate_conflict_insert / _update | FlightSchedule, BEFORE INSERT / UPDATE | `EXISTS` another non-cancelled flight at the same gate whose time overlaps -> SIGNAL error |
| trg_passenger_update_audit / _delete_audit | Passenger, AFTER UPDATE / DELETE | Insert operation + passenger_id into PassengerAudit |
- **Overlap logic**: two intervals overlap when `new.start < other.end AND new.end > other.start`. Touching end/start does not conflict. The update trigger excludes the flight itself (`flight_id <> NEW.flight_id`). Cancelled flights are ignored. Simplification: we treat the gate as occupied from scheduled departure to scheduled arrival (a real system would use a turnaround window).
- **Why two gate triggers?** MySQL allows one trigger per timing/event combination here, so INSERT and UPDATE need separate triggers.
- **Constraint vs trigger**: use constraints for simple declarative rules (UNIQUE, NOT NULL, CHECK, FK) - they are faster and visible in the schema; use triggers for automatic actions or rules that need other rows.
- **Advantages**: automatic, centralized (applies to every client app), auditing, enforces complex rules. **Limitations**: hidden logic, harder to debug, performance cost on every write, cannot call COMMIT/ROLLBACK inside, can cascade, DBMS-specific syntax.
- **Trigger vs stored procedure**: a trigger fires automatically on an event; a procedure runs only when called.

## 10. Application architecture
```
Browser (HTML/CSS/JS)  --HTTP/JSON-->  Flask API (Python)  --SQL-->  MySQL (cloud)
```
- **3-tier**: presentation, application, data. **REST API**: URLs + HTTP verbs (GET read, POST create, PUT update, DELETE delete = CRUD).
- **PyMySQL with raw SQL** (no ORM) so the SQL is visible. **Parameterized queries** (`%s` placeholders) prevent **SQL injection** - user input is sent as data, never concatenated into SQL. SQL Lab only runs a **whitelist** of stored queries.
- Errors from MySQL (duplicate, FK, CHECK, trigger SIGNAL) are caught by Flask and shown as friendly messages.
- **Deployment**: Vercel runs the Flask code as a serverless function and serves `public/`; the database is on **Aiven managed MySQL** (a database server cannot run on Vercel because functions are stateless and short-lived). Credentials and the signing key live in **environment variables**. A short connection per request suits serverless and limited connection pools; TLS protects data in transit.

## 10A. Authentication, authorization & security
- **Authentication** = who are you (username + password). **Authorization** = what may you do (role). Our roles: **admin** (everything) and **user** (operations staff: limited rights). This is **RBAC - role-based access control**; the role is stored in the `AppUser` table (CHECK role IN ('admin','user')).
- **Password storage**: never plain text. We store a salted **PBKDF2-SHA256 hash** (`generate_password_hash`); login compares with `check_password_hash`. Hashes are one-way, so even the admin cannot read a password.
- **Session**: after login the server issues a **signed token** (itsdangerous) inside a cookie that is **HttpOnly** (JavaScript cannot read it - limits XSS theft), **SameSite=Strict** (not sent from other sites - limits CSRF), **Secure** on HTTPS, and expires after 8 hours. Stateless tokens suit Vercel because serverless functions keep no memory between requests. Tampering breaks the signature -> 401.
- **Enforcement on the server**: a Flask `before_request` hook checks login and role for **every** `/api` call (401 not signed in, 403 not allowed). Hiding buttons in the UI is only convenience - a user cannot bypass it by calling the API directly.
- **Least privilege**: users cannot delete data, edit flights, see the audit log, or run SQL Lab. SQL Lab accepts no free text, only whitelisted queries.
- **Other protections**: parameterized queries (SQL injection), generic login error + hash check for unknown users (no username enumeration), 0.5 s delay on failed login, admins cannot lock themselves out, secrets in environment variables, TLS to the cloud database.
- **DBMS-level link**: the `AppUser` table itself uses PK, UNIQUE (username), NOT NULL and CHECK constraints - authentication data is just another relational table. In a larger system you would also use SQL `GRANT`/`REVOKE` and DB roles.

## 11. Security & limitations (say these honestly)
- Login has no lockout/rate limiting or multi-factor authentication; the app connects to MySQL with one account (a real system would use least-privilege DB users, e.g., a read-only reporting user); audit tables do not record *which web user* made a change (future scope: add a `changed_by` column).
- Passenger data is fictional; real data needs encryption and privacy compliance (GDPR-style).
- Gate rule is simplified; no time zones; no baggage, crew-duty-hour or airline-slot modules.
- Future scope: authentication, real-time updates (WebSockets), indexes/partitioning for scale, baggage and fuel tables, flight-data API integration.

## 12. Likely viva questions (short answers)
1. **Why separate Airline from FlightSchedule?** To avoid repeating airline data on every flight (3NF, no update anomaly).
2. **Primary vs unique key?** One PK per table, never NULL; many UNIQUE keys allowed. Both are candidate keys.
3. **Why BoardingPass?** It resolves the Passenger-Flight M:N relationship and holds seat/group/status.
4. **What happens if I delete a flight with passengers?** In SQL, RESTRICT blocks it (1451). In the app, a transaction deletes children first, then the flight - or rolls everything back.
5. **Difference between DELETE and ROLLBACK?** DELETE removes rows; ROLLBACK undoes uncommitted changes.
6. **Is a view stored data?** No, a stored query; it runs each time.
7. **Why BEFORE UPDATE for boarding time?** We modify the row being saved (`SET NEW...`), only possible before the write.
8. **Why AFTER UPDATE for status history?** We log only after the update succeeded.
9. **Can a trigger fire another trigger?** Yes (cascading), e.g., an update that causes an insert into another table with its own trigger.
10. **Why does PassengerAudit have no foreign key?** The audit row for a DELETE must outlive the deleted passenger.
11. **What is a cross join?** Cartesian product of two tables (every row with every row).
12. **INNER vs LEFT JOIN?** Inner returns only matches; left keeps all left rows with NULLs where no match.
13. **What is a correlated subquery?** A subquery that uses columns of the outer query and runs per outer row.
14. **COUNT(*) vs COUNT(col)?** All rows vs non-NULL values.
15. **Why can't I use WHERE with COUNT()?** WHERE runs before grouping; use HAVING.
16. **What is 3NF in one line?** Every non-key attribute depends on the key, the whole key, and nothing but the key.
17. **Difference between 3NF and BCNF?** BCNF requires every determinant to be a candidate key; 3NF allows a determinant that is a prime attribute.
18. **What is a deadlock?** Two transactions each hold a lock the other needs; the DBMS aborts one.
19. **What is autocommit?** Each statement is its own committed transaction unless START TRANSACTION is used.
20. **How is SQL injection prevented here?** Parameterized queries and a whitelisted query list.
21. **Why does the app open a new DB connection per request?** It keeps the code simple and avoids stale or leaked connections; a connection pool would be the next step for heavier use.
22. **What is an index?** A data structure (B-tree) speeding up lookups; UNIQUE/PK create one automatically.
23. **What is referential integrity?** FK values must match an existing parent key (or be NULL).
24. **What is data redundancy and why bad?** Duplicate storage causing wasted space and inconsistency.
25. **Entity vs entity set?** Entity = one object (AI101); entity set = all of that type (FlightSchedule).
26. **What does `ON DELETE CASCADE` do?** Deleting a parent automatically deletes its children (we use RESTRICT instead, deliberately).
27. **Stored procedure vs function?** A procedure is called with CALL and can return result sets/out params; a function returns a single value usable inside SQL.
28. **Why CHECK instead of a trigger for status values?** Declarative, faster, visible in the schema.
29. **What isolation level does MySQL use by default?** REPEATABLE READ (InnoDB).
30. **What does ACID's "C" mean here?** Constraints always hold after a transaction (e.g., no boarding pass for a missing flight).
31. **What is RBAC?** Permissions are attached to roles, and users get roles, instead of permissions per person.
32. **Why hash passwords instead of encrypting them?** Hashing is one-way; a stolen database does not reveal passwords. Salting stops rainbow-table attacks.
33. **Why is the role check done on the server?** The browser is untrusted; anyone can call the API manually.
34. **401 vs 403?** 401 = not authenticated (sign in); 403 = authenticated but not permitted.
35. **What is an HttpOnly cookie?** A cookie JavaScript cannot access, so XSS cannot steal the session.
36. **Why a signed token instead of a server session?** Serverless functions are stateless; the signed cookie carries the proof of login.

## 13. 10-minute demo script
1. ER diagram + 8 core tables (1 min). 2. Dashboard (30 s). 3. Constraints: duplicate passport, bad status, arrival before departure (1 min). 4. CRUD from Flights/Passengers pages, show FK-blocked delete (1 min). 5. **SQL Lab**: join, group by, having, subquery, views (2 min). 6. Transactions: Workbench COMMIT/ROLLBACK from script 06, then double-board in the app (1.5 min). 7. Triggers: Board a passenger -> time appears; change status -> Audit log; gate conflict error; passenger edit -> audit (2 min). 8. Normalization UNF->3NF on the whiteboard (1 min). 9. Sign in as `ops` (user) and show restricted menu + 403 message, then as `admin`; mention hosting (Vercel + Aiven) and limitations (1 min).

## 14. Last-minute checklist
- Run scripts 01-03, 05, 07, 06 fresh before the demo so sample data is clean.
- Open Workbench with `04_queries.sql` and `08_test_cases.sql` ready.
- Know each trigger's BEFORE/AFTER reason and the overlap formula.
- Have one slide of the ER diagram with cardinalities.
- Open the deployed site once on the morning (cold start; the free database may need switching on) and sign in with both accounts.
