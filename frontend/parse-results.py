import json

d = json.load(open('test-results.json', 'r', encoding='utf-8'))
for r in d['testResults']:
    if r['status'] == 'failed':
        name = r['name'].replace('\\', '/').split('frontend/')[-1]
        print(f'=== {name} ===')
        for assertion in r.get('assertionResults', []):
            if assertion['status'] == 'failed':
                full = assertion.get('fullName', '')
                print(f'  FAIL: {full}')
                msgs = assertion.get('failureMessages', [])
                if msgs:
                    for m in msgs[:1]:
                        print(f'    {m[:300]}')
        print()
