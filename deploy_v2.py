#!/usr/bin/env python3
"""Deploy TruthOracle v2 to GenLayer Studio via CDP (correct helper API)."""
import json, time, sys, urllib.request
sys.path.insert(0, '/home/ubuntu/trustleaf_internal')
from cdp_driver import ws_connect, cdp, eval_js

NAME = 'truth_oracle_v2'
SRC_PATH = '/home/ubuntu/truthoracle/truth_oracle.py'
SRC = open(SRC_PATH).read()

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read())
page = [t for t in tabs if t['type'] == 'page' and 'genlayer' in t.get('url', '')]
if not page:
    page = [t for t in tabs if t['type'] == 'page']
page = page[0]
print('page ::', page['url'][:80])
sock = ws_connect('/devtools/page/' + page['id'])
cdp(sock, 'Runtime.enable')

# make sure we're on studio
url = eval_js(sock, 'location.href')
if 'studio.genlayer.com' not in (url or ''):
    cdp(sock, 'Page.enable')
    cdp(sock, 'Page.navigate', {'url': 'https://studio.genlayer.com'})
    time.sleep(8)
    print('navigated to studio')

def js(expr, aw=False):
    return eval_js(sock, expr, await_promise=aw)

# 1. add contract file via Pinia store
res = js("""
(async () => {
  const app = document.querySelector('#app').__vue_app__;
  const pinia = app.config.globalProperties.$pinia;
  const cs = pinia._s.get('contractsStore');
  if (!cs) return 'NO_STORE';
  const r = await cs.addContractFile({name: '%s', content: %s});
  const id = (r && r.id) ? r.id : (typeof r === 'string' ? r : null);
  const listIds = (cs.contracts || []).map(c=>c.id);
  cs.$patch({currentContractId: id || listIds[listIds.length-1], openedFiles: listIds});
  return 'ADDED:' + (id || listIds[listIds.length-1]);
})()
""" % (NAME, json.dumps(SRC)), aw=True)
print('add contract ::', res)
if not str(res).startswith('ADDED'):
    sys.exit(1)
time.sleep(3)

# 2. open the contract editor tab (skip welcome) + Run&Debug panel
r2 = js("""
(() => {
  const btns = [...document.querySelectorAll('button,[role=button],.side-icon,[class*=icon]')];
  const rdb = btns.find(b => /run\\s*&?\\s*debug|debug/i.test((b.textContent||'') + (b.getAttribute('aria-label')||'') + (b.title||'')));
  if (rdb) { rdb.click(); return 'PANEL'; }
  return 'NO_PANEL';
})()
""")
print('panel ::', r2)
time.sleep(3)

# 3. schema check — Deploy button present?
chk = js("""
(() => {
  const t = document.body.innerText || '';
  const err = /Could not load contract schema|execution failed/i.test(t);
  const btn = [...document.querySelectorAll('button')].find(b => /^Deploy/.test((b.textContent||'').trim()));
  return JSON.stringify({schemaErr: err, hasDeploy: !!btn});
})()
""")
print('schema ::', chk)
try:
    cj = json.loads(chk)
except Exception:
    cj = {}
if not cj.get('hasDeploy'):
    print('NO DEPLOY BUTTON — stopping. Screenshot: /tmp/to_deploy_fail.png')
    r = cdp(sock, 'Page.captureScreenshot', {'format': 'png'})
    open('/tmp/to_deploy_fail.png', 'wb').write(__import__('base64').b64decode(r['data']))
    sys.exit(1)

# 4. click Deploy
click = js("""
(() => {
  const btn = [...document.querySelectorAll('button')].find(b => /^Deploy/.test((b.textContent||'').trim()));
  btn.click(); return 'CLICKED';
})()
""")
print('deploy ::', click, '— waiting for consensus...')

# 5. poll status
final = None
for i in range(80):
    time.sleep(5)
    st = js("""
    (() => {
      const t = document.body.innerText || '';
      const m = t.match(/(PROPOSING|ACCEPTED|FINALIZED|REJECTED)/g);
      return m ? m[m.length-1] : '';
    })()
    """)
    print(f'[{(i+1)*5}s] status :: {st}')
    if st in ('FINALIZED', 'ACCEPTED'):
        final = st
        break
    if st == 'REJECTED':
        r = cdp(sock, 'Page.captureScreenshot', {'format': 'png'})
        open('/tmp/to_rejected.png', 'wb').write(__import__('base64').b64decode(r['data']))
        print('REJECTED — screenshot /tmp/to_rejected.png')
        sys.exit(1)

if not final:
    print('TIMEOUT — no final status in 400s')
    sys.exit(1)

# 6. get full address from store
addr = js("""
(() => {
  const app = document.querySelector('#app').__vue_app__;
  const pinia = app.config.globalProperties.$pinia;
  const cs = pinia._s.get('contractsStore');
  const all = cs.allDeployedContracts || [];
  const mine = all.filter(c => (c.name||'').includes('%s'));
  return mine.length ? mine[mine.length-1].address : 'NO_ADDR';
})()
""" % NAME)
print('DEPLOYED ::', final)
print('CONTRACT_ADDRESS ::', addr)
