/* Airport AODB - single-page frontend (plain JavaScript, no build step).
   Every screen calls the Flask JSON API under /api and renders the result. */
(() => {
'use strict';

/* ---------- small helpers ---------- */
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = v => v ? String(v).replace('T', ' ').slice(0, 16) : '—';
const slug = s => String(s || '').toLowerCase().replace(/\s+/g, '-');
const badge = s => s ? `<span class="badge ${slug(s)}">${esc(s)}</span>` : '—';
const FLIGHT_STATUS = ['Scheduled', 'Boarding', 'Departed', 'Arrived', 'Delayed', 'Cancelled'];
const GATE_STATUS = ['Available', 'Occupied', 'Maintenance', 'Closed'];
const PALETTE = ['#7f9bb3', '#9bbcab', '#d8bf8f', '#c99a96', '#aaa0bd', '#a3aab3', '#8aa8a1'];

let L = {};              // lookup lists (airlines, gates, ...)
let actions = {};        // click handlers of the current page
let ME = null;           // signed-in user: {user_id, username, full_name, role}
const isAdmin = () => !!ME && ME.role === 'admin';
const charts = {};

async function api(path, method = 'GET', body) {
  const res = await fetch('/api' + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (e) { /* empty body */ }
  if (res.status === 401 && path !== '/login') { showLogin(); throw new Error('Please sign in.'); }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}
const loadLookups = async () => { L = await api('/lookups'); };

function toast(msg, kind = '') {
  const t = document.createElement('div');
  t.className = 'toast-item ' + kind;
  t.textContent = msg;
  $('#toast').appendChild(t);
  setTimeout(() => t.remove(), kind === 'err' ? 6000 : 2800);
}
const setActions = html => { $('#pageActions').innerHTML = html; };

/* ---------- tables ---------- */
function table(cols, rows, empty = 'Nothing to show yet.') {
  if (!rows.length) return `<p class="empty">${empty}</p>`;
  const head = cols.map(c => `<th>${c.label}</th>`).join('');
  const body = rows.map(r => `<tr>${cols.map(c => `<td${c.cls ? ` class="${c.cls}"` : ''}>${c.render(r)}</td>`).join('')}</tr>`).join('');
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
const col = (label, key, fn) => ({ label, render: r => fn ? fn(r[key], r) : esc(r[key] ?? '—') });
const btn = (act, id, label, cls = '') => `<button class="btn small ${cls}" data-act="${act}" data-id="${id}">${label}</button>`;
const actionCol = fn => ({ label: '', cls: 'actions', render: fn });

/* ---------- modal + forms ---------- */
const modal = $('#modal');
const closeModal = () => { modal.hidden = true; };
$('#modalClose').onclick = closeModal;
modal.addEventListener('mousedown', e => { if (e.target === modal) closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

function fieldHtml(f, v) {
  const val = v[f.name] ?? f.value ?? '';
  const req = f.required ? 'required' : '';
  let input;
  if (f.type === 'select') {
    const blank = f.required ? '' : '<option value="">— none —</option>';
    input = `<select name="${f.name}" ${req}>${blank}${f.options.map(([k, l]) =>
      `<option value="${esc(k)}" ${String(k) === String(val) ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select>`;
  } else {
    input = `<input name="${f.name}" type="${f.type || 'text'}" value="${esc(val)}" ${req} ${f.placeholder ? `placeholder="${esc(f.placeholder)}"` : ''}>`;
  }
  return `<label class="field"><span>${f.label}${f.required ? ' *' : ''}</span>${input}</label>`;
}

function openForm({ title, fields, values = {}, submit = 'Save', onSubmit }) {
  $('#modalTitle').textContent = title;
  $('#modalBody').innerHTML = `<form id="mf"><div class="grid2">${fields.map(f => fieldHtml(f, values)).join('')}</div>
    <p class="form-error" id="mferr"></p>
    <div class="modal-actions"><button type="button" class="btn ghost" id="mfcancel">Cancel</button><button class="btn primary">${submit}</button></div></form>`;
  modal.hidden = false;
  $('#mfcancel').onclick = closeModal;
  $('#mf').onsubmit = async e => {
    e.preventDefault();
    try { await onSubmit(Object.fromEntries(new FormData(e.target))); closeModal(); }
    catch (err) { $('#mferr').textContent = err.message; }
  };
  const first = $('#mf input, #mf select'); if (first) first.focus();
}

function confirmBox(message, onYes, label = 'Delete') {
  $('#modalTitle').textContent = 'Please confirm';
  $('#modalBody').innerHTML = `<p>${message}</p><div class="modal-actions"><button class="btn ghost" id="cno">Cancel</button><button class="btn primary" id="cyes">${label}</button></div>`;
  modal.hidden = false;
  $('#cno').onclick = closeModal;
  $('#cyes').onclick = async () => {
    try { await onYes(); } catch (err) { toast(err.message, 'err'); }
    closeModal();
  };
}

/* ---------- charts ---------- */
function drawChart(id, type, rows, label = 'Count') {
  const ctx = document.getElementById(id);
  if (!ctx) return;
  if (typeof Chart === 'undefined') { ctx.parentElement.innerHTML = '<p class="empty">Chart library could not be loaded (check internet connection).</p>'; return; }
  const pie = type === 'doughnut';
  charts[id] = new Chart(ctx, {
    type,
    data: { labels: rows.map(r => r.label), datasets: [{ label, data: rows.map(r => r.total),
      backgroundColor: pie ? PALETTE : PALETTE[0], borderWidth: 0, borderRadius: pie ? 0 : 4 }] },
    options: { maintainAspectRatio: false, cutout: pie ? '62%' : undefined,
      plugins: { legend: { display: pie, position: 'bottom' } },
      scales: pie ? {} : { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#eeece7' } }, x: { grid: { display: false } } } },
  });
}

/* ================= PAGES ================= */
const pages = {};

/* ----- Dashboard ----- */
pages.dashboard = { title: 'Dashboard', async render() {
  setActions('');
  const d = await api('/dashboard');
  const s = d.by_status;
  const card = (label, num, cls = '') => `<div class="card ${cls}"><div class="label">${label}</div><div class="num">${num}</div></div>`;
  $('#view').innerHTML = `
    <div class="cards">
      ${card('Total flights', d.totals.flights)}
      ${card('Boarding', s.Boarding || 0)}
      ${card('Delayed', s.Delayed || 0, 'warn')}
      ${card('Cancelled', s.Cancelled || 0, 'bad')}
      ${card('Passengers', d.totals.passengers)}
      ${card('Gates available', d.totals.gates_available)}
    </div>
    <div class="split">
      <div class="panel"><h3>Flight status board</h3>${table([
        col('Flight', 'flight_number', v => `<strong>${esc(v)}</strong>`),
        col('Airline', 'airline_name'), col('Aircraft', 'aircraft_type'), col('Gate', 'gate_number'),
        col('Route', 'departure_airport', (v, r) => `${esc(v)} → ${esc(r.arrival_airport)}`),
        col('Departure', 'scheduled_departure', fmt), col('Status', 'status', badge),
      ], d.flights, 'No flights yet.')}</div>
      <div class="panel"><h3>Flights by status</h3><div class="chart-box"><canvas id="c1"></canvas></div></div>
    </div>`;
  drawChart('c1', 'doughnut', Object.entries(s).map(([label, total]) => ({ label, total })));
}};

/* ----- Flights ----- */
pages.flights = { title: 'Flights', async render() {
  await loadLookups();
  let rows = [];
  const flightFields = () => [
    { name: 'flight_number', label: 'Flight number', required: true, placeholder: 'e.g. AI101' },
    { name: 'status', label: 'Status', type: 'select', required: true, options: FLIGHT_STATUS.map(x => [x, x]) },
    { name: 'airline_id', label: 'Airline', type: 'select', required: true, options: L.airlines.map(a => [a.airline_id, `${a.airline_name} (${a.iata_code})`]) },
    { name: 'aircraft_type_id', label: 'Aircraft', type: 'select', required: true, options: L.aircraft.map(a => [a.aircraft_type_id, a.name]) },
    { name: 'departure_airport', label: 'From (airport code)', required: true, placeholder: 'BOM' },
    { name: 'arrival_airport', label: 'To (airport code)', required: true, placeholder: 'DEL' },
    { name: 'scheduled_departure', label: 'Scheduled departure', type: 'datetime-local', required: true },
    { name: 'scheduled_arrival', label: 'Scheduled arrival', type: 'datetime-local', required: true },
    { name: 'gate_id', label: 'Gate', type: 'select', options: L.gates.map(g => [g.gate_id, `${g.gate_number} · ${g.terminal} (${g.status})`]) },
  ];
  setActions(isAdmin() ? '<button class="btn primary" data-act="add">+ Add flight</button>' : '');
  $('#view').innerHTML = `<div class="toolbar"><input id="q" placeholder="Search flight, airline or destination…">
    <select id="st"><option value="">All statuses</option>${FLIGHT_STATUS.map(x => `<option>${x}</option>`).join('')}</select></div>
    <div class="panel" id="list"></div>`;
  const load = async () => {
    rows = await api('/flights?' + new URLSearchParams({ q: $('#q').value, status: $('#st').value }));
    $('#list').innerHTML = table([
      col('Flight', 'flight_number', v => `<strong>${esc(v)}</strong>`), col('Airline', 'airline_name'), col('Aircraft', 'aircraft'),
      col('Gate', 'gate_number'), col('Route', 'departure_airport', (v, r) => `${esc(v)} → ${esc(r.arrival_airport)}`),
      col('Departure', 'scheduled_departure', fmt), col('Arrival', 'scheduled_arrival', fmt), col('Status', 'status', badge),
      actionCol(r => isAdmin() ? btn('edit', r.flight_id, 'Edit') + ' ' + btn('del', r.flight_id, 'Delete', 'danger') : btn('status', r.flight_id, 'Update status')),
    ], rows, 'No flights match your search.');
  };
  let timer; $('#q').oninput = () => { clearTimeout(timer); timer = setTimeout(load, 250); };
  $('#st').onchange = load;
  actions = {
    status: id => { const r = rows.find(x => String(x.flight_id) === id);
      openForm({ title: `Update status - ${r.flight_number}`, submit: 'Update', values: { status: r.status },
        fields: [{ name: 'status', label: 'Flight status', type: 'select', required: true, options: FLIGHT_STATUS.map(x => [x, x]) }],
        onSubmit: async d => { await api(`/flights/${id}/status`, 'PATCH', d); toast('Status updated'); await load(); } }); },
    add: () => openForm({ title: 'Add flight', fields: flightFields(), submit: 'Add flight',
      onSubmit: async d => { await api('/flights', 'POST', d); toast('Flight added'); await load(); } }),
    edit: id => {
      const r = rows.find(x => String(x.flight_id) === id);
      openForm({ title: `Edit ${r.flight_number}`, fields: flightFields(), submit: 'Save changes',
        values: { ...r, scheduled_departure: String(r.scheduled_departure).slice(0, 16), scheduled_arrival: String(r.scheduled_arrival).slice(0, 16) },
        onSubmit: async d => { await api('/flights/' + id, 'PUT', d); toast('Flight updated'); await load(); } });
    },
    del: id => {
      const r = rows.find(x => String(x.flight_id) === id);
      confirmBox(`Delete flight <strong>${esc(r.flight_number)}</strong>? Its boarding passes, staff assignments and status history are removed too (in one transaction).`,
        async () => { await api('/flights/' + id, 'DELETE'); toast('Flight deleted'); await load(); });
    },
  };
  await load();
}};

/* ----- Boarding ----- */
pages.boarding = { title: 'Boarding', async render() {
  await loadLookups();
  let rows = [];
  setActions('<button class="btn primary" data-act="issue">+ Issue boarding pass</button>');
  $('#view').innerHTML = `<div class="toolbar"><select id="fl"><option value="">All flights</option>${
    L.flights.map(f => `<option value="${f.flight_id}">${esc(f.flight_number)} (${esc(f.status)})</option>`).join('')}</select></div>
    <div class="panel"><div id="prog"></div><div id="list"></div></div>`;
  const load = async () => {
    rows = await api('/boarding' + ($('#fl').value ? '?flight_id=' + $('#fl').value : ''));
    const active = rows.filter(r => r.boarding_status !== 'Cancelled');
    const done = active.filter(r => r.boarding_status === 'Boarded').length;
    $('#prog').innerHTML = `<span class="muted">${done} of ${active.length} passengers boarded</span><div class="progress"><span style="width:${active.length ? done / active.length * 100 : 0}%"></span></div>`;
    $('#list').innerHTML = table([
      col('Passenger', 'passenger'), col('Flight', 'flight_number', v => `<strong>${esc(v)}</strong>`),
      col('Seat', 'seat_number'), col('Group', 'boarding_group'),
      col('Boarding time', 'boarding_time', fmt), col('Status', 'boarding_status', badge),
      actionCol(r => (r.boarding_status === 'Not Boarded' ? btn('board', r.boarding_pass_id, 'Board', 'primary') + ' ' + btn('cancel', r.boarding_pass_id, 'Cancel') + ' ' : '') + (isAdmin() ? btn('del', r.boarding_pass_id, 'Delete', 'danger') : '')),
    ], rows, 'No boarding passes for this selection.');
  };
  $('#fl').onchange = load;
  actions = {
    issue: () => openForm({ title: 'Issue boarding pass', submit: 'Issue pass', fields: [
      { name: 'passenger_id', label: 'Passenger', type: 'select', required: true, options: L.passengers.map(p => [p.passenger_id, `${p.name} (${p.passport_number})`]) },
      { name: 'flight_id', label: 'Flight', type: 'select', required: true, value: $('#fl').value, options: L.flights.map(f => [f.flight_id, f.flight_number]) },
      { name: 'seat_number', label: 'Seat', required: true, placeholder: '12A' },
      { name: 'boarding_group', label: 'Boarding group', placeholder: 'A' }],
      onSubmit: async d => { await api('/boarding', 'POST', d); toast('Boarding pass issued'); await load(); } }),
    board: async id => { try { await api(`/boarding/${id}/board`, 'POST'); toast('Passenger boarded - time recorded by trigger'); } catch (e) { toast(e.message, 'err'); } await load(); },
    cancel: id => confirmBox('Cancel this boarding pass?', async () => { await api(`/boarding/${id}/cancel`, 'PUT'); toast('Boarding pass cancelled'); await load(); }, 'Cancel pass'),
    del: id => confirmBox('Delete this boarding pass?', async () => { await api('/boarding/' + id, 'DELETE'); toast('Boarding pass deleted'); await load(); }),
  };
  await load();
}};

/* ----- Passengers ----- */
pages.passengers = { title: 'Passengers', async render() {
  let rows = [];
  const fields = () => [
    { name: 'first_name', label: 'First name', required: true }, { name: 'last_name', label: 'Last name', required: true },
    { name: 'passport_number', label: 'Passport number', required: true }, { name: 'date_of_birth', label: 'Date of birth', type: 'date' },
    { name: 'nationality', label: 'Nationality' }, { name: 'email', label: 'Email', type: 'email' }, { name: 'phone', label: 'Phone' }];
  setActions('<button class="btn primary" data-act="add">+ Add passenger</button>');
  $('#view').innerHTML = `<div class="toolbar"><input id="q" placeholder="Search name or passport…"></div><div class="panel" id="list"></div>`;
  const load = async () => {
    rows = await api('/passengers?' + new URLSearchParams({ q: $('#q').value }));
    $('#list').innerHTML = table([
      col('ID', 'passenger_id'), col('Name', 'first_name', (v, r) => `<strong>${esc(v)} ${esc(r.last_name)}</strong>`),
      col('Passport', 'passport_number'), col('Nationality', 'nationality'), col('Email', 'email'), col('Phone', 'phone'),
      actionCol(r => btn('edit', r.passenger_id, 'Edit') + (isAdmin() ? ' ' + btn('del', r.passenger_id, 'Delete', 'danger') : '')),
    ], rows, 'No passengers found.');
  };
  let timer; $('#q').oninput = () => { clearTimeout(timer); timer = setTimeout(load, 250); };
  actions = {
    add: () => openForm({ title: 'Add passenger', fields: fields(), submit: 'Add passenger',
      onSubmit: async d => { await api('/passengers', 'POST', d); toast('Passenger added'); await load(); } }),
    edit: id => { const r = rows.find(x => String(x.passenger_id) === id);
      openForm({ title: 'Edit passenger', fields: fields(), values: r, submit: 'Save changes',
        onSubmit: async d => { await api('/passengers/' + id, 'PUT', d); toast('Passenger updated (audit row created by trigger)'); await load(); } }); },
    del: id => { const r = rows.find(x => String(x.passenger_id) === id);
      confirmBox(`Delete <strong>${esc(r.first_name)} ${esc(r.last_name)}</strong>? Passengers who hold a boarding pass cannot be deleted (foreign key).`,
        async () => { await api('/passengers/' + id, 'DELETE'); toast('Passenger deleted'); await load(); }); },
  };
  await load();
}};

/* ----- Staff ----- */
pages.staff = { title: 'Staff & assignments', async render() {
  await loadLookups();
  setActions(isAdmin() ? '<button class="btn" data-act="addStaff">+ Add staff</button> <button class="btn primary" data-act="assign">+ Assign to flight</button>' : '');
  $('#view').innerHTML = `<div class="panel"><h3>Assignments</h3><div id="alist"></div></div><div class="panel"><h3>Staff directory</h3><div id="slist"></div></div>`;
  const load = async () => {
    const [a, s] = await Promise.all([api('/assignments'), api('/staff')]);
    $('#alist').innerHTML = table([
      col('Staff member', 'staff_member'), col('Flight', 'flight_number', v => `<strong>${esc(v)}</strong>`),
      col('Role', 'assignment_role'), col('From', 'start_time', fmt), col('Until', 'end_time', fmt),
      actionCol(r => isAdmin() ? btn('delA', r.assignment_id, 'Remove', 'danger') : ''),
    ], a, 'No assignments yet.');
    $('#slist').innerHTML = table([
      col('Name', 'first_name', (v, r) => `<strong>${esc(v)} ${esc(r.last_name)}</strong>`), col('Role', 'role'), col('Department', 'department'),
      col('Email', 'email'), col('Status', 'employment_status', badge),
      actionCol(r => isAdmin() ? btn('delS', r.staff_id, 'Delete', 'danger') : ''),
    ], s);
  };
  actions = {
    addStaff: () => openForm({ title: 'Add staff member', submit: 'Add staff', fields: [
      { name: 'first_name', label: 'First name', required: true }, { name: 'last_name', label: 'Last name', required: true },
      { name: 'role', label: 'Role', type: 'select', required: true, options: ['Gate Agent', 'Ground Staff', 'Security Officer', 'Airport Manager', 'Baggage Handler', 'Operations Officer'].map(x => [x, x]) },
      { name: 'department', label: 'Department' }, { name: 'email', label: 'Email', type: 'email' }, { name: 'phone', label: 'Phone' }],
      onSubmit: async d => { await api('/staff', 'POST', d); toast('Staff member added'); await loadLookups(); await load(); } }),
    assign: () => openForm({ title: 'Assign staff to flight', submit: 'Assign', fields: [
      { name: 'staff_id', label: 'Staff member', type: 'select', required: true, options: L.staff.map(x => [x.staff_id, `${x.name} · ${x.role}`]) },
      { name: 'flight_id', label: 'Flight', type: 'select', required: true, options: L.flights.map(f => [f.flight_id, f.flight_number]) },
      { name: 'assignment_role', label: 'Duty on this flight', required: true, placeholder: 'Gate Agent' },
      { name: 'start_time', label: 'Start', type: 'datetime-local', required: true }, { name: 'end_time', label: 'End', type: 'datetime-local' }],
      onSubmit: async d => { await api('/assignments', 'POST', d); toast('Assignment saved'); await load(); } }),
    delA: id => confirmBox('Remove this assignment?', async () => { await api('/assignments/' + id, 'DELETE'); toast('Assignment removed'); await load(); }, 'Remove'),
    delS: id => confirmBox('Delete this staff member? (Not possible while they have assignments.)', async () => { await api('/staff/' + id, 'DELETE'); toast('Staff member deleted'); await loadLookups(); await load(); }),
  };
  await load();
}};

/* ----- Gates ----- */
pages.gates = { title: 'Gates', async render() {
  setActions('');
  $('#view').innerHTML = '<div class="panel" id="list"></div>';
  const load = async () => {
    const rows = await api('/gates');
    $('#list').innerHTML = table([
      col('Gate', 'gate_number', v => `<strong>${esc(v)}</strong>`), col('Terminal', 'terminal'), col('Type', 'gate_type'),
      col('Active flights', 'active_flights'), col('Status', 'status', badge),
      { label: isAdmin() ? 'Change status' : '', render: r => !isAdmin() ? '' : `<select class="inline" data-gate="${r.gate_id}">${GATE_STATUS.map(x => `<option ${x === r.status ? 'selected' : ''}>${x}</option>`).join('')}</select>` },
    ], rows);
    document.querySelectorAll('[data-gate]').forEach(sel => sel.onchange = async () => {
      try { await api('/gates/' + sel.dataset.gate, 'PUT', { status: sel.value }); toast('Gate status updated'); } catch (e) { toast(e.message, 'err'); }
      await load();
    });
  };
  actions = {};
  await load();
}};

/* ----- Reports ----- */
pages.reports = { title: 'Reports', async render() {
  setActions('');
  const r = await api('/reports');
  const box = (id, title) => `<div class="panel"><h3>${title}</h3><div class="chart-box"><canvas id="${id}"></canvas></div></div>`;
  $('#view').innerHTML = `<div class="grid-charts">
      ${box('r1', 'Flights by status')}${box('r2', 'Flights per airline')}${box('r3', 'Passengers per flight')}
      ${box('r4', 'Boarding status')}${box('r5', 'Staff by department')}${box('r6', 'Staff assignments by role')}${box('r7', 'Gates by status')}</div>
    <div class="panel"><h3>Flight statistics <span class="muted">(FlightStatisticsView)</span></h3>${table([
      col('Flight', 'flight_number', v => `<strong>${esc(v)}</strong>`), col('Status', 'status', badge),
      col('Passengers', 'passenger_count'), col('Staff', 'staff_count')], r.flight_stats)}</div>`;
  drawChart('r1', 'doughnut', r.flights_by_status); drawChart('r2', 'bar', r.flights_per_airline, 'Flights');
  drawChart('r3', 'bar', r.passengers_per_flight, 'Passengers'); drawChart('r4', 'doughnut', r.boarding_status);
  drawChart('r5', 'bar', r.staff_by_department, 'Staff'); drawChart('r6', 'bar', r.staff_by_role, 'Assignments');
  drawChart('r7', 'doughnut', r.gates_by_status);
}};

/* ----- Audit log (shows trigger output) ----- */
pages.audit = { title: 'Audit log', admin: true, async render() {
  setActions('');
  const a = await api('/audit');
  $('#view').innerHTML = `
    <p class="muted">These two tables are filled <strong>automatically by database triggers</strong> - the application never inserts into them.</p>
    <div class="panel"><h3>Flight status history <span class="muted">(trigger: trg_flight_status_history)</span></h3>${table([
      col('When', 'changed_at', fmt), col('Flight', 'flight_number', v => `<strong>${esc(v)}</strong>`),
      col('From', 'old_status', badge), col('To', 'new_status', badge)], a.flight_history, 'No status changes yet - change a flight status on the Flights page.')}</div>
    <div class="panel"><h3>Passenger audit <span class="muted">(triggers: update / delete)</span></h3>${table([
      col('When', 'changed_at', fmt), col('Passenger ID', 'passenger_id'), col('Operation', 'operation', badge)],
      a.passenger_audit, 'No passenger changes yet - edit a passenger on the Passengers page.')}</div>`;
}};

/* ----- SQL Lab ----- */
pages.lab = { title: 'SQL Lab', admin: true, async render() {
  setActions('');
  const list = await api('/lab');
  const cats = [...new Set(list.map(q => q.category))];
  $('#view').innerHTML = `<div class="panel"><div class="toolbar">
      <select id="qsel" style="max-width:520px">${cats.map(c => `<optgroup label="${esc(c)}">${list.filter(q => q.category === c).map(q => `<option value="${q.key}">${esc(q.title)}</option>`).join('')}</optgroup>`).join('')}</select>
      <button class="btn primary" id="run">Run query</button></div><pre class="sql" id="sqlbox"></pre></div>
    <div class="panel"><div id="result"><p class="empty">Choose a query and press “Run query”.</p></div></div>`;
  const cur = () => list.find(q => q.key === $('#qsel').value);
  const showSql = () => { $('#sqlbox').textContent = cur().sql; };
  $('#qsel').onchange = () => { showSql(); $('#result').innerHTML = '<p class="empty">Press “Run query”.</p>'; };
  showSql();
  $('#run').onclick = async () => {
    try {
      const rows = await api('/lab/' + cur().key);
      if (!rows.length) { $('#result').innerHTML = '<p class="empty">Query ran successfully but returned 0 rows.</p>'; return; }
      const keys = Object.keys(rows[0]);
      const cell = v => v === null ? '<span class="muted">NULL</span>' : esc(/^\d{4}-\d\d-\d\dT/.test(v) ? fmt(v) : v);
      $('#result').innerHTML = `<p class="muted" style="margin-top:0">${rows.length} row(s)</p>` +
        table(keys.map(k => ({ label: esc(k), render: r => cell(r[k]) })), rows);
    } catch (e) { toast(e.message, 'err'); }
  };
}};

/* ----- Users (admin only) ----- */
pages.users = { title: 'User accounts', admin: true, async render() {
  let rows = [];
  setActions('<button class="btn primary" data-act="add">+ Add user</button>');
  $('#view').innerHTML = `<p class="muted"><strong>Admin</strong>: full access. <strong>User</strong> (operations staff): view everything except the audit log, SQL Lab and user accounts; add/edit passengers, issue boarding passes, board passengers and update flight status.</p><div class="panel" id="list"></div>`;
  const roleOpts = [['user', 'User (operations staff)'], ['admin', 'Admin']];
  const load = async () => {
    rows = await api('/users');
    $('#list').innerHTML = table([
      col('Username', 'username', v => `<strong>${esc(v)}</strong>`), col('Name', 'full_name'), col('Role', 'role', badge),
      col('Status', 'is_active', v => badge(v ? 'Active' : 'Inactive')), col('Last sign-in', 'last_login', fmt),
      actionCol(r => btn('edit', r.user_id, 'Edit')),
    ], rows);
  };
  actions = {
    add: () => openForm({ title: 'Add user', submit: 'Create user', fields: [
      { name: 'username', label: 'Username', required: true }, { name: 'full_name', label: 'Full name' },
      { name: 'role', label: 'Role', type: 'select', required: true, options: roleOpts },
      { name: 'password', label: 'Password (min 8 characters)', type: 'password', required: true }],
      onSubmit: async d => { await api('/users', 'POST', d); toast('User created'); await load(); } }),
    edit: id => { const r = rows.find(x => String(x.user_id) === id);
      openForm({ title: `Edit ${r.username}`, submit: 'Save changes', values: { ...r, is_active: r.is_active ? 1 : 0 }, fields: [
        { name: 'full_name', label: 'Full name' },
        { name: 'role', label: 'Role', type: 'select', required: true, options: roleOpts },
        { name: 'is_active', label: 'Account', type: 'select', required: true, options: [[1, 'Active'], [0, 'Inactive (cannot sign in)']] },
        { name: 'password', label: 'New password (leave empty to keep)', type: 'password' }],
        onSubmit: async d => { await api('/users/' + id, 'PUT', d); toast('User updated'); await load(); } }); },
  };
  await load();
}};

function changePassword() {
  openForm({ title: 'Change my password', submit: 'Change password', fields: [
    { name: 'old_password', label: 'Current password', type: 'password', required: true },
    { name: 'new_password', label: 'New password (min 8 characters)', type: 'password', required: true },
    { name: 'confirm', label: 'Repeat new password', type: 'password', required: true }],
    onSubmit: async d => {
      if (d.new_password !== d.confirm) throw new Error('The new passwords do not match.');
      await api('/me/password', 'POST', { old_password: d.old_password, new_password: d.new_password });
      toast('Password changed');
    } });
}

/* ================= router ================= */
async function route() {
  if (!ME) return;
  const key = (location.hash || '#dashboard').slice(1);
  const page = pages[key] || pages.dashboard;
  if (page.admin && !isAdmin()) { location.hash = '#dashboard'; return; }
  document.querySelectorAll('#nav a').forEach(a => a.classList.toggle('active', a.dataset.page === (pages[key] ? key : 'dashboard')));
  $('#pageTitle').textContent = page.title;
  Object.values(charts).forEach(c => c.destroy());
  Object.keys(charts).forEach(k => delete charts[k]);
  actions = {};
  $('#view').innerHTML = '<p class="muted">Loading…</p>';
  try { await page.render(); }
  catch (e) { $('#view').innerHTML = `<div class="panel error-panel"><strong>Could not load this page.</strong><br>${esc(e.message)}</div>`; }
}

document.addEventListener('click', e => {
  const b = e.target.closest('[data-act]');
  if (b && actions[b.dataset.act]) actions[b.dataset.act](b.dataset.id, b);
});
window.addEventListener('hashchange', route);

function showLogin() {
  ME = null;
  $('#app').hidden = true; $('#login').hidden = false;
  closeModal(); $('#lp').value = ''; $('#lu').focus();
}

function startApp(user) {
  ME = user;
  $('#login').hidden = true; $('#app').hidden = false; $('#loginErr').textContent = '';
  $('#uName').textContent = user.full_name || user.username;
  $('#uRole').innerHTML = badge(user.role);
  document.querySelectorAll('[data-role="admin"]').forEach(el => { el.hidden = !isAdmin(); });
  api('/health').then(() => { $('#dbDot').className = 'dot on'; $('#dbText').textContent = 'Database connected'; })
                .catch(() => { $('#dbDot').className = 'dot off'; $('#dbText').textContent = 'Database offline'; });
  route();
}

$('#loginForm').onsubmit = async e => {
  e.preventDefault();
  $('#loginErr').textContent = '';
  try { startApp(await api('/login', 'POST', { username: $('#lu').value, password: $('#lp').value })); }
  catch (err) { $('#loginErr').textContent = err.message; }
};
$('#logoutBtn').onclick = async () => { try { await api('/logout', 'POST'); } catch (e) { /* already signed out */ } showLogin(); location.hash = ''; };
$('#pwBtn').onclick = changePassword;

api('/me').then(startApp).catch(() => showLogin());
})();
