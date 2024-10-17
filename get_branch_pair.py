import requests
import csv
import argparse

def get_pr_commits(repo, pr_id, headers):
    # 获取 PR 的详细信息
    pr_url = f'https://api.github.com/repos/{repo}/pulls/{pr_id}'
    response = requests.get(pr_url, headers=headers)
    if response.status_code != 200:
        print(f'获取 PR {pr_id} 的信息时出错：{response.status_code}')
        return None, None
    pr_data = response.json()
    merge_commit_sha = pr_data.get('merge_commit_sha')
    base_commit_id = pr_data.get('base', {}).get('sha')
    if not merge_commit_sha or not base_commit_id:
        print(f'无法获取 PR {pr_id} 的提交 ID')
        return None, None
    return base_commit_id, merge_commit_sha

def main():
    parser = argparse.ArgumentParser(description='根据给定的 PR ID 获取 base 和 fix commit ID。')
    parser.add_argument('repository', help='GitHub 仓库名，格式为 owner/repo')
    parser.add_argument('input_csv', help='包含 PR ID 的输入 CSV 文件')
    parser.add_argument('--token', help='GitHub 个人访问令牌，用于提高速率限制')
    args = parser.parse_args()
    
    repo = args.repository
    input_csv = args.input_csv
    token = args.token

    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'

    rows = []
    # 从输入 CSV 文件中读取数据
    with open(input_csv, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames
        # 检查是否已有目标列
        if 'Base Commit ID' not in fieldnames:
            fieldnames.append('Base Commit ID')
        if 'Fix Commit ID' not in fieldnames:
            fieldnames.append('Fix Commit ID')
        for row in reader:
            pr_id = row['pr_id']  # 使用列名 'pr_id' 来获取 PR ID
            base_commit_id, fix_commit_id = get_pr_commits(repo, pr_id, headers)
            if base_commit_id and fix_commit_id:
                row['Base Commit ID'] = base_commit_id
                row['Fix Commit ID'] = fix_commit_id
            else:
                row['Base Commit ID'] = ''
                row['Fix Commit ID'] = ''
                print(f'无法获取 PR {pr_id} 的提交 ID')
            rows.append(row)
    
    # 将更新后的数据写回同一个 CSV 文件
    with open(input_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        print(f'已将结果写入 {input_csv} 文件中。')

if __name__ == '__main__':
    main()
