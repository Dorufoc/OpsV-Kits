import json

d = json.load(open('test-results.json', 'r', encoding='utf-8'))

test_files = [
    'tests/views/DockerPages.test.ts',
    'tests/views/MonitorPages.test.ts',
    'tests/views/ServerPages.test.ts',
    'tests/views/DevOpsPages.test.ts',
    'tests/views/ToolPages.test.ts',
    'tests/views/OtherPages.test.ts',
    'tests/components/DockerComponents.test.ts',
    'tests/components/FileAndProcessComponents.test.ts',
    'tests/components/DbComponents.test.ts',
    'tests/components/MonitorComponents.test.ts',
    'tests/components/GitComponents.test.ts',
    'tests/components/OtherComponents.test.ts',
]

total_new = 0
for r in d['testResults']:
    name = r['name'].replace('\\', '/').split('frontend/')[-1]
    if name in test_files:
        count = len(r.get('assertionResults', []))
        total_new += count
        print(f'{name}: {count} 个测试用例')

print(f'\n新增测试文件总计: {total_new} 个测试用例')
print(f'全项目测试总计: {d["numPassedTests"]} passed, {d["numFailedTests"]} failed')
