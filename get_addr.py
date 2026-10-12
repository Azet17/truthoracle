#!/usr/bin/env python3
"""Get TruthOracle FULL deployed contract address from Studio store."""
import json, sys
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
    r = eval_js(sock, '''
    (() => {
      const el = document.querySelector('#app, [data-v-app]');
      const store = el.__vue_app__.config.globalProperties.$pinia._s.get('contractsStore');
      const c = store.contracts.find(c => c.name === 'truth_oracle.py');
      // deployed address might live on the contract entry or in allDeployedContracts
      const dep = (store.allDeployedContracts || []).filter(d =>
        JSON.stringify(d).includes('truth') || true);
      return JSON.stringify({entry: c ? {id: c.id, deployed: c.deployedAddress || c.address || '(not on entry)'} : null,
                             deployedCount: dep.length,
                             last3: dep.slice(-3).map(d => JSON.stringify(d).slice(0, 200))});
    })()
    ''')
    print(r)

if __name__ == '__main__':
    main()
