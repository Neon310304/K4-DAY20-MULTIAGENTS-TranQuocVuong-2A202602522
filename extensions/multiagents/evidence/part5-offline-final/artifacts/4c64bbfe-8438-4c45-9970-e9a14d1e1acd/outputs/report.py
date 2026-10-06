import csv, json
from pathlib import Path
with open('sales.csv') as source:
    amounts = [int(row['amount']) for row in csv.DictReader(source) if row['quarter'] == '3']
value = {'revenue': sum(amounts), 'rows': len(amounts)}
Path('outputs/answer.json').write_text(json.dumps(value))
print(json.dumps(value))
