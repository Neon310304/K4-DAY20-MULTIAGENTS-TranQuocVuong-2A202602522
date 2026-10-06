import csv
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Read sales.csv and filter for quarter 3
quarter_filter = 3
rows = []
revenue = 0
with open('sales.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if int(row['quarter']) == quarter_filter:
            rows.append(row)
            revenue += int(row['amount'])

# Write answer.json
answer = {'revenue': revenue, 'rows': len(rows)}
with open('outputs/answer.json', 'w') as f:
    json.dump(answer, f)

# Create a small chart for the filtered data
amounts = [int(row['amount']) for row in rows]
plt.figure(figsize=(4, 3))
plt.bar(range(len(amounts)), amounts)
plt.title('Q3 Sales Amounts')
plt.xlabel('Sale Index')
plt.ylabel('Amount')
plt.tight_layout()
plt.savefig('outputs/sales_chart.png')
