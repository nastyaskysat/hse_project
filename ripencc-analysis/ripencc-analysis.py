import requests
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime
import os

# Скачиваем файл статистики
lines = []
if not os.path.exists('delegated-ripencc-latest'):
    url = "https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest"
    response = requests.get(url)
    lines = response.text.splitlines()
else:
    with open('delegated-ripencc-latest', 'r') as file:
        lines = file.readlines()

# Словарь для подсчета ASN по годам
yearly_asns = defaultdict(int)
total_ru_asns = 0

for line in lines:
    if line.startswith('#'):
        continue  # Пропустить комментарии

    parts = line.strip().split('|')
    if len(parts) < 7:
        continue

    registry, country, resource_type, start, count, date_str, status = parts

    # Только ASN, страна RU, статус allocated или assigned
    if resource_type == 'asn' and country == 'RU' and status in ('allocated', 'assigned'):
        try:
            year = datetime.strptime(date_str, "%Y%m%d").year
            yearly_asns[year] += int(count)
            total_ru_asns += int(count)
        except Exception as e:
            print(f"Ошибка даты: {date_str} -> {e}")
            continue

print(f"Найдено всего ASN в RU: {total_ru_asns}")
print(f"Года: {sorted(yearly_asns.keys())}")

if not yearly_asns:
    print("Нет данных для построения графика!")
else:
    # Построение графика
    years = sorted(yearly_asns)
    counts = [yearly_asns[year] for year in years]

    plt.figure(figsize=(12, 6))
    plt.plot(years, counts, marker='o', linestyle='-', color='blue')
    plt.xticks(years, rotation=45)
    plt.title('Выделение номеров AS LIR-ам в РФ по годам (данные RIPE NCC)')
    plt.xlabel('Год')
    plt.ylabel('Количество AS номеров')
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    plt.savefig('asn_distribution.png', dpi=300)
