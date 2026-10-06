import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
amounts = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]
figure, axis = plt.subplots(figsize=(4, 2.5))
axis.plot(range(1, len(amounts) + 1), amounts)
axis.set(xlabel='Sale', ylabel='Amount', title='2026 sales')
figure.tight_layout()
figure.savefig('outputs/sales_chart.png', dpi=90)
plt.close(figure)
print(json.dumps({'total': sum(amounts), 'rows': len(amounts)}))
