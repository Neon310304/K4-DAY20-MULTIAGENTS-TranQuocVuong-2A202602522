import csv, json
from pathlib import Path
with open('sales.csv') as source:
    amounts = [int(row['amount']) for row in csv.DictReader(source) if row['quarter'] == '3']
value = {'revenue': sum(amounts), 'rows': len(amounts)}
Path('outputs/answer.json').write_text(json.dumps(value))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
figure, axis = plt.subplots(figsize=(4, 2.5))
axis.bar(range(len(amounts)), amounts)
figure.tight_layout()
figure.savefig('outputs/sales_chart.png', dpi=90)
plt.close(figure)
print(json.dumps(value))
