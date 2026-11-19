const assert = require('node:assert/strict');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');

const html = JSON.parse(execFileSync('python', ['-B', '-c',
  "import ast,json,pathlib; t=ast.parse(pathlib.Path('app/web_display_server.py').read_text(encoding='utf-8')); print(json.dumps(next(n.value.value for n in t.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='DISPLAY_HTML' for v in n.targets))))"
], { encoding: 'utf8' }));
const script = html.split('<script>')[1].split('</script>')[0];
let now = Date.UTC(2026, 10, 19, 14, 30);
let reachable = true, plays = 0, wakeRequests = 0;
let payload = { role: 'server', server_address: '192.168.1.10', candidates: [],
  server_epoch_ms: now, utc_offset_minutes: 60,
  state: { doctor1: { doctor_id: 'doctor1', doctor_name: 'Medico', queue_active: true,
    queue_mode: 'number', number: 1 } } };
const elements = {};
for (const name of ['content','technical','clock','audioButton','turnSound','wakePulse']) {
  let inner = '';
  elements[name] = { id: name, className: '', writes: 0, style: {}, volume: 1,
    get innerHTML() { return inner; },
    set innerHTML(value) { inner = value; this.writes++; },
    play() { plays++; return { catch() {} }; }, pause() {}, load() {} };
}
const intervals = [];
const storage = new Map();
class FakeDate extends Date {
  constructor(...args) { super(...(args.length ? args : [now])); }
  static now() { return now; }
}
class XHR {
  open() {}
  send() {
    this.status = reachable ? 200 : 503;
    this.readyState = 4;
    this.responseText = JSON.stringify(payload);
    this.onreadystatechange();
  }
  abort() {}
}
const context = {
  navigator: { userAgent: 'Android GestioneTurniTV/1.0',
    wakeLock: { request() { wakeRequests++; throw new Error('native app should not ask web wake lock'); } } },
  document: { getElementById: id => elements[id], visibilityState: 'visible', addEventListener() {} },
  window: { location: { protocol: 'http:', host: '192.168.1.10:8080' },
    setInterval(fn, ms) { intervals.push({ fn, ms }); return intervals.length; },
    setTimeout() { return 1; }, clearTimeout() {}, clearInterval() {} },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  XMLHttpRequest: XHR, Date: FakeDate, console,
};
vm.runInNewContext(script, context);
const poll = intervals.find(item => item.fn.name === 'poll').fn;
assert.equal(wakeRequests, 0);
assert.equal(elements.clock.innerHTML, '15:30');
assert.match(elements.content.innerHTML, />1<\/div>/);
assert.equal(plays, 0);
const firstWrites = elements.content.writes;
for (let i = 0; i < 3; i++) { now += 1000; payload.server_epoch_ms = now; poll(); }
assert.equal(elements.content.writes, firstWrites, 'unchanged queue must not rebuild DOM');
payload.state.doctor1.number = 2;
poll();
assert.equal(plays, 1, 'new turn should sound once');
poll();
assert.equal(plays, 1);
payload.state.doctor1.queue_mode = 'surname';
payload.state.doctor1.current_surname = '<script>alert(1)</script>';
poll();
assert.match(elements.content.innerHTML, /&lt;SCRIPT&gt;/);
assert.doesNotMatch(elements.content.innerHTML, /<script>/);
reachable = false;
now += 6000;
poll();
assert.match(elements.content.innerHTML, /Connessione in corso/);
reachable = true;
payload.server_epoch_ms = now;
poll();
assert.match(elements.content.innerHTML, /&lt;SCRIPT&gt;/);
payload.state = {};
poll();
assert.match(elements.content.innerHTML, /In attesa/);
const emptyWrites = elements.content.writes;
poll();
assert.equal(elements.content.writes, emptyWrites);
console.log('Display JS: 9 scenari verificati (render, audio, escaping, orologio, disconnessione e ripristino).');
