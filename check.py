import csv

# 打开 CSV 文件并打印表头
filename = 'branch_pairs.csv'
with open(filename, mode='r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    headers = reader.fieldnames  # 获取表头
    print(f"CSV Headers: {headers}")  # 打印表头
    

    for row in reader:
        print(f"Row keys: {list(row.keys())}")  # 打印当前行的所有键，检查是否有多余空格

        print(row)  # 检查每一行是否被正确读取
