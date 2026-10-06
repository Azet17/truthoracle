#!/usr/bin/env python3
"""Get TruthOracle's OWN contract address (newest tx, not TrustLeaf's old one)."""
import json, time, base64, sys
sys.path.insert(0, '/home/ubuntu/trustleaf')
from cdp_driver import ws_connect, cdp, eval_js
import urllib.request

def get_sock():
    tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read())
    page = [t for t in tabs if t['type'] == 'page'][0]
    sock = ws_connect('/devtools/page/' + page['id'])
    cdp(sock, 'Runtime.enable')
    return sock

def main():
    sock = get_sock()
    state = eval_js(sock, '''
    (() => {
      const el = document.querySelector('#app, [data-v-app]');
      const ts = el.__vue_app__.config.globalProperties.$pinia._s.get('transactionsStore');
      const txs = ts ? (ts.$state.allTransactions || []) : [];
      // find the LAST deploy tx (TruthOracle — newest)
      const deploys = txs.filter(t => t.type === 'deploy');
      const last = deploys.length ? deploys[deploys.length-1] : null;
      if (!last) return 'no deploy tx';
      const d = last.data || {};
      return JSON.stringify({status: last.statusName, hash: (last.hash||'').slice(0,20),
                             from: d.from_address, to: d.to_address,
                             contractAddress: last.contractAddress || '(none)'});
    })()
    ''')
    print(state)

    r = cdp(sock, 'Page.captureScreenshot', {'format': 'png'})
    if 'data' in r.get('result', {}):
        open('/tmp/studio_oracle_status.png', 'wb').write(base64.b64decode(r['result']['data']))
        print('shot :: /tmp/studio_oracle_status.png')

if __name__ == '__main__':
    main()
