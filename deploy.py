#!/usr/bin/env python3
"""Deploy TruthOracle to GenLayer Studio via CDP (same proven flow)."""
import json, time, base64, sys
sys.path.insert(0, '/home/ubuntu/trustleaf')
from cdp_driver import ws_connect, cdp, eval_js
import urllib.request

CONTRACT = open('/home/ubuntu/truthoracle/truth_oracle.py').read()

def get_sock():
    tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read())
    page = [t for t in tabs if t['type'] == 'page'][0]
    sock = ws_connect('/devtools/page/' + page['id'])
    cdp(sock, 'Runtime.enable')
    return sock

def click_xy(sock, x, y):
    cdp(sock, 'Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': x, 'y': y})
    cdp(sock, 'Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': x, 'y': y,
        'button': 'left', 'clickCount': 1})
    time.sleep(0.12)
    cdp(sock, 'Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': x, 'y': y,
        'button': 'left', 'clickCount': 1})

def main():
    sock = get_sock()

    # 1. add contract + open it
    r = eval_js(sock, f'''
    (() => {{
      const el = document.querySelector('#app, [data-v-app]');
      const store = el.__vue_app__.config.globalProperties.$pinia._s.get('contractsStore');
      const exists = store.contracts.find(c => c.name === 'truth_oracle.py');
      if (!exists) store.addContractFile({{ name: 'truth_oracle.py', content: {json.dumps(CONTRACT)} }});
      const c = store.contracts.find(c => c.name === 'truth_oracle.py');
      if (!c.id) c.id = crypto.randomUUID();
      store.$patch({{currentContractId: c.id,
        openedFiles: [c.id, ...store.openedFiles.filter(x => x && x !== c.id)]}});
      return 'id=' + c.id + ' total=' + store.contracts.length;
    }})()
    ''')
    print('add ::', r)
    time.sleep(3)

    # 2. click file in sidebar
    item = eval_js(sock, '''
    (() => {
      const els = document.querySelectorAll('*');
      for (const e of els) {
        if (e.children.length === 0 && (e.innerText || '').trim() === 'truth_oracle.py') {
          const r = e.getBoundingClientRect();
          return {x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
        }
      }
      return null;
    })()
    ''')
    print('sidebar ::', item)
    if item:
        click_xy(sock, item['x'], item['y'])
        time.sleep(3)

    # 3. open Run and Debug panel
    click_xy(sock, 126, 71)
    time.sleep(4)

    # 4. check schema + find Deploy button
    panel = eval_js(sock, '''
    (() => {
      const body = document.body.innerText;
      const els = document.querySelectorAll('button');
      let dep = null;
      for (const e of els) {
        const r = e.getBoundingClientRect();
        if (r.width > 0 && (e.innerText||'').trim().toLowerCase().startsWith('deploy')) {
          dep = {x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2),
                 text: (e.innerText||'').trim()};
        }
      }
      return {schemaErr: body.includes('Could not load contract schema'),
              deploy: dep};
    })()
    ''')
    print('panel ::', json.dumps(panel, indent=1))

    if panel.get('deploy'):
        p = panel['deploy']
        click_xy(sock, p['x'], p['y'])
        print('>>> DEPLOY CLICKED')
        time.sleep(15)

    # 5. result
    state = eval_js(sock, '''
    (() => {
      const el = document.querySelector('#app, [data-v-app]');
      const ts = el.__vue_app__.config.globalProperties.$pinia._s.get('transactionsStore');
      const txs = ts ? (ts.$state.allTransactions || []) : [];
      const last = txs.length ? txs[txs.length-1] : null;
      const body = document.body.innerText;
      const addrs = body.match(/0x[a-fA-F0-9]{40}/g) || [];
      return last ? {status: last.statusName, hash: (last.hash||'').slice(0,18),
                     to: last.data ? JSON.stringify(last.data).slice(0,0) : '',
                     allAddrs: addrs.slice(0,3)} : {status: 'no tx', addrs: addrs.slice(0,3)};
    })()
    ''')
    print('RESULT ::', json.dumps(state, indent=1))

    r = cdp(sock, 'Page.captureScreenshot', {'format': 'png'})
    if 'data' in r.get('result', {}):
        open('/tmp/studio_oracle.png', 'wb').write(base64.b64decode(r['result']['data']))
        print('shot :: /tmp/studio_oracle.png')

if __name__ == '__main__':
    main()
