#!/usr/bin/env python3
import os
import subprocess
import sys
import getpass
import shutil  # 导入 shutil 模块
import csv     # 导入 csv 模块
from datetime import datetime

def run_command_realtime(command, cwd=None, output_file=None, show_output=True):
    MAX_OUTPUT_LINES = 100
    output_lines = []

    # 检查并创建输出文件的目录
    if output_file:
        directory = os.path.dirname(output_file)
        if not os.path.exists(directory):
            os.makedirs(directory)

    try:
        process = subprocess.Popen(command, shell=True, cwd=cwd,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        with open(output_file, 'w') as f_out:
            for line in process.stdout:
                line = line.rstrip()
                f_out.write(line + '\n')
                f_out.flush()

                if show_output:
                    output_lines.append(line)
                    if len(output_lines) > MAX_OUTPUT_LINES:
                        output_lines.pop(0)
                    os.system('clear')
                    for out_line in output_lines:
                        print(out_line)

        return_code = process.wait()
        return return_code
    except Exception as e:
        print(f"执行命令时发生异常：{e}")
        return -1

def container_exists(container_name):
    cmd = f"docker ps -a --format '{{{{.Names}}}}'"
    output = subprocess.getoutput(cmd)
    containers = output.strip().split('\n')
    return container_name in containers

def start_docker_container(apollo_path, state_output_dir, SHOW_OUTPUT):
    # 构建 Docker 容器
    cmd = "bash docker/scripts/dev_start.sh"
    output_file = os.path.join(state_output_dir, 'dev_start_output.txt')
    ret = run_command_realtime(cmd, cwd=apollo_path,
                               output_file=output_file,
                               show_output=SHOW_OUTPUT)
    return ret

def workspace_check(repo_path):
    file_path = os.path.join(repo_path, 'WORKSPACE')

    if os.path.isfile(file_path):
        print(f"WORKSPACE file is under {repo_path}")
        return True
    else:
        print(f"Can not fine WORKSPACE file under {repo_path}, run configurator next")
        return False


def experiment_log(log_file, base_branch, fix_branch, start_time, end_time):
    duration = end_time - start_time
    current_time = datetime.now()
    with open(log_file, 'w') as f:
        f.write(f"Date: {current_time.strftime('%Y-%m-%d')}, Time: {current_time.strftime('%H:%M:%S')},\n ")
        f.write(f"Base Branch: {base_branch}, Fix Branch: {fix_branch},\n ")
        f.write(f"Duration: {duration}\n")

def main():
    EXP_ID = "2024.10.2.1"
    INPUT_CSV_FILE = "/home/user/experiments/EXP_2024.10.2.1/branch_pairs.csv"  # 修改为 CSV 文件名
    APOLLO_REPO_PATH = "/home/user/experiments/apollo"  # 请将此路径修改为您的实际 Apollo 仓库路径
    SHOW_OUTPUT = True
    LOG_FILE_NAME = 'experiment_log.txt'

    # 新增配置：是否在测试完成后删除 Apollo 仓库
    DELETE_REPO_AFTER_TEST = True  # 设置为 True 或 False

    # 新增配置：压缩间隔
    COMPRESSION_INTERVAL = 10  # 每处理多少个分支对后进行一次压缩

    # 用于保存待压缩的仓库目录
    repos_to_compress = []

    # 获取当前脚本的绝对路径
    script_dir = os.getcwd()

    # 检查 CSV 文件是否存在
    if not os.path.isfile(INPUT_CSV_FILE):
        print(f"错误：未找到输入文件：{INPUT_CSV_FILE}")
        sys.exit(1)

    # 创建实验文件夹
    EXP_DIR = os.path.abspath(EXP_ID)
    if not os.path.exists(EXP_DIR):
        os.makedirs(EXP_DIR)
        print(f"已创建实验文件夹：{EXP_DIR}")
    else:
        print(f"实验文件夹已存在：{EXP_DIR}")

    # 创建 outputs 文件夹
    OUTPUTS_DIR = os.path.join(EXP_DIR, 'outputs')
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    # 读取分支对列表
    branch_pairs = []
    with open(os.path.join(script_dir, INPUT_CSV_FILE), 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for row in reader:
            pr = row['pr_id'].strip()
            base_commit_id = row['base_commit_id'].strip()
            fix_commit_id = row['fix_commit_id'].strip()
            component = row['component'].strip()
            branch_pairs.append((base_commit_id, fix_commit_id, component))

    error_component = {
        'PL': 'planning',
        'Map': 'map',
        'OD': 'perception',
        'SF': 'localization',
        'AC': 'canbus',
        'TP': 'prediction',
        'Cont': 'control',
        'LL': 'common'
    }

    for idx, (base_branch, fix_branch, component) in enumerate(branch_pairs):
        start_time = datetime.now()
        print(f"\n处理分支对：基准提交 {base_branch}，修复提交 {fix_branch}，组件 {component}")
        # 输出文件夹名称修改，仅展示前七位
        base_branch_short = base_branch[:7]
        fix_branch_short = fix_branch[:7]
        output_folder_name = f"{idx+1}_{base_branch_short}_{fix_branch_short}"

        # 输出文件夹
        output_dir = os.path.join(OUTPUTS_DIR, output_folder_name)
        log_path = os.path.join(output_dir, LOG_FILE_NAME)
        if os.path.isfile(log_path):
            print("Experiment on this pair was conducted already, skip.")
            continue

        component_to_test = error_component[component]
        print(f'\nComponent to test is \033[32m{component_to_test}\033[0m')
        # Apollo 仓库副本路径（每个分支对一个副本）
        repo_dir = os.path.join(EXP_DIR, f'apollo_pair_{idx}')
        if os.path.exists(repo_dir):
            print(f"Apollo 仓库已存在，跳过复制：{repo_dir}")
        else:
            cmd = f"cp -r {APOLLO_REPO_PATH} {repo_dir}"
            ret, output = subprocess.getstatusoutput(cmd)
            if ret != 0:
                print(f"复制 Apollo 仓库失败：{output}")
                continue
            print(f"已复制 Apollo 仓库到：{repo_dir}")

        os.makedirs(output_dir, exist_ok=True)

        # 设置 Apollo 路径
        apollo_path = repo_dir
        if not os.path.exists(apollo_path):
            print(f"Apollo 目录未找到：{apollo_path}")
            continue

        # 切换到 Apollo 目录
        os.chdir(apollo_path)

        # 获取当前用户
        DOCKER_USER = 'user'  # 请将此处的用户名修改为您的实际用户名
        DEV_CONTAINER_PREFIX = 'apollo_dev_'
        DEV_CONTAINER = f"{DEV_CONTAINER_PREFIX}{DOCKER_USER}"

        # 定义两种状态的输出目录：before 和 after
        output_states = {
            "before": os.path.join(output_dir, 'before'),
            "after": os.path.join(output_dir, 'after')
        }

        for state in ["before", "after"]:
            state_output_dir = output_states[state]
            os.makedirs(state_output_dir, exist_ok=True)

            # 清理工作区，确保没有未提交的更改
            cmd = "git reset --hard && git clean -fd"
            ret, output = subprocess.getstatusoutput(cmd)
            if ret != 0:
                print(f"清理工作区失败：{output}")
                # 即使清理失败，也尝试继续

            if state == "before":
                branch = base_branch
            else:
                branch = fix_branch

            # 检查本地是否已有该提交
            cmd = f"git cat-file -t {branch}"
            ret, output = subprocess.getstatusoutput(cmd)
            if ret != 0:
                # 尝试从远程获取提交
                cmd = f"git fetch origin {branch}"
                output_file = os.path.join(state_output_dir, f'fetch_{branch}.txt')
                ret = run_command_realtime(cmd, cwd=apollo_path,
                                           output_file=output_file,
                                           show_output=SHOW_OUTPUT)
                if ret != 0:
                    print(f"获取提交 {branch} 失败，跳过")
                    break

            # 检出到指定提交
            cmd = f"git checkout {branch}"
            output_file = os.path.join(state_output_dir, f'checkout_{branch}.txt')
            ret = run_command_realtime(cmd, cwd=apollo_path,
                                       output_file=output_file,
                                       show_output=SHOW_OUTPUT)
            if ret != 0:
                print(f"检出到提交 {branch} 失败，跳过")
                break
            print(f"已检出到提交 {branch}")

            # 检查当前提交
            cmd = "git rev-parse HEAD"
            ret, current_commit = subprocess.getstatusoutput(cmd)
            current_commit = current_commit.strip()
            if current_commit != branch:
                print(f"错误：当前提交为 {current_commit}，期望提交为 {branch}")
                break
            else:
                print(f"已确认检出到了期望的提交：{current_commit}")

            # 获取当前的提交 ID
            commit_id = current_commit
            print(f"当前提交 ID：{commit_id}")

            # 检查 Docker 容器是否存在
            if not container_exists(DEV_CONTAINER):
                print(f"Docker 容器 {DEV_CONTAINER} 不存在，尝试构建容器")
                ret = start_docker_container(apollo_path, state_output_dir, SHOW_OUTPUT)
                if ret != 0:
                    print("Docker 容器构建失败，跳过该状态")
                    continue
                else:
                    print("Docker 容器构建成功")
            else:
                print(f"使用已有的 Docker 容器 {DEV_CONTAINER}")

            if workspace_check(repo_dir):
                # 在容器内执行命令
                commands = [
                    (f'bazel test //modules/{component_to_test}/...', 'test_output.txt'),
                    #("./apollo.sh test", 'test_output.txt'),
                    #("./apollo.sh coverage", 'coverage_output.txt'),
                    #("genhtml -o coverage_report $(bazel info output_path)/_coverage/_coverage_report.dat", 'genhtml_output.txt'),
                    ("./apollo.sh clean", 'apollo_clean_output.txt')
                ]
            else:
                commands = [
                    ('./apollo.sh config', 'config_output.txt'),
                    (f'bazel test //modules/{component_to_test}/...', 'test_output.txt'),
                    #("./apollo.sh test", 'test_output.txt'),
                    #("./apollo.sh coverage", 'coverage_output.txt'),
                    #("genhtml -o coverage_report $(bazel info output_path)/_coverage/_coverage_report.dat", 'genhtml_output.txt'),
                    ("./apollo.sh clean", 'apollo_clean_output.txt')
                ]
            for idx_cmd, (cmd, output_filename) in enumerate(commands):
                output_file = os.path.join(state_output_dir, output_filename)
                # 修改 docker exec 命令，单独执行每个命令
                docker_cmd = (
                    f"docker exec "
                    f"-u {DOCKER_USER} "
                    f"-e HISTFILE=/apollo/.dev_bash_hist "
                    f"-i {DEV_CONTAINER} "
                    f"/bin/bash -c 'cd /apollo && {cmd}'"
                )
                ret = run_command_realtime(docker_cmd, output_file=output_file, show_output=SHOW_OUTPUT)
                if ret != 0:
                    print(f"命令执行失败：{cmd}，已保存输出")

                    # 如果不是最后一个命令，继续执行后续命令
                    if idx_cmd < len(commands) -1:
                        print("继续执行后续命令")
                        continue
                    else:
                        print("最后一个命令执行失败，将重新尝试执行")
                else:
                    print(f"命令执行成功：{cmd}")

            print(f"状态 {state} 处理完成\n")

        # 在完成一个分支对的测试之后，删除 Docker 容器
        print(f"删除 Docker 容器 {DEV_CONTAINER}")
        cmd = f"docker rm -f {DEV_CONTAINER}"
        ret, output = subprocess.getstatusoutput(cmd)
        if ret != 0:
            print(f"删除 Docker 容器失败：{output}")
        else:
            print(f"Docker 容器 {DEV_CONTAINER} 已删除")

        # 新增功能：删除 Apollo 仓库目录或压缩
        if DELETE_REPO_AFTER_TEST:
            print(f"删除 Apollo 仓库目录 {repo_dir}")
            try:
                # 修改目录的所有权，以防止权限问题
                cmd = f"sudo chown -R {os.getuid()}:{os.getgid()} {repo_dir}"
                ret, output = subprocess.getstatusoutput(cmd)
                if ret != 0:
                    print(f"修改目录所有权失败：{output}")
                shutil.rmtree(repo_dir)
                print(f"Apollo 仓库目录 {repo_dir} 已删除")
            except Exception as e:
                print(f"删除 Apollo 仓库目录失败：{e}")
        else:
            # 将仓库目录添加到待压缩列表
            repos_to_compress.append(repo_dir)

            # 每处理 COMPRESSION_INTERVAL 个分支对，执行一次压缩
            if (idx + 1) % COMPRESSION_INTERVAL == 0 or (idx + 1) == len(branch_pairs):
                print(f"开始压缩已完成的 Apollo 仓库，共计 {len(repos_to_compress)} 个")
                for repo_to_compress in repos_to_compress:
                    # 压缩仓库目录
                    archive_name = f"{repo_to_compress}.tar.gz"
                    print(f"压缩 {repo_to_compress} 到 {archive_name}")
                    try:
                        shutil.make_archive(repo_to_compress, 'gztar', root_dir=repo_to_compress)
                        print(f"压缩完成：{archive_name}")
                        # 删除原始目录
                        shutil.rmtree(repo_to_compress)
                        print(f"已删除原始目录：{repo_to_compress}")
                    except Exception as e:
                        print(f"压缩或删除目录时发生错误：{e}")
                # 清空待压缩列表
                repos_to_compress = []
        
        end_time = datetime.now()
        # # 调用 experiment_log 函数，记录日志
        experiment_log(log_path, base_branch, fix_branch, start_time, end_time)
        print(f"分支对 {base_branch} 和 {fix_branch} 处理完成\n")

    print("\n所有分支对处理完成")

if __name__ == "__main__":
    main()
