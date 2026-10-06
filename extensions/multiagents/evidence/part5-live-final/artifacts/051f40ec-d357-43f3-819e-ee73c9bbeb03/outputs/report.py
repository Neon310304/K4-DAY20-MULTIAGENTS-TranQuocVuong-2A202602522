import csv
import json

input_csv = 'sales.csv'
output_json = 'outputs/answer.json'

quarter_filter = 3

revenue = 0
rows = 0

with open(input_csv, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if int(row['quarter']) == quarter_filter:
            revenue += int(row['amount'])
            rows += 1

result = {
    'revenue': revenue,
    'rows': rows
}

with open(output_json, 'w') as jsonfile:
    json.dump(result, jsonfile)

print(f"Report generated: {output_json}")
print(result)
