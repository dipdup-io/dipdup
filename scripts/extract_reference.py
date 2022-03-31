import importlib

config_module = importlib.import_module('dipdup.config')
for name, member in config_module.__dict__.items():
    if not name.endswith('Config'):
        continue
    if isinstance(member, type):
        doc = member.__doc__
        if not doc:
            continue

        print()
        print(f'=> {name}')
        print()
        print('| field | description |')
        print('| - | - |')
        for line in doc.split('\n'):
            line = line.strip()
            if line.startswith(':param'):
                parts = line.split(':')
                param, desc = parts[1], ':'.join(parts[2:]).strip()
                print(f'| `{param[6:]}` | {desc} |')