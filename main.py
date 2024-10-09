#!/usr/bin/env python3
import os
import subprocess
import sys

def run_command_realtime(command, cwd=None, output_file=None, show_output=True):
    MAX_OUTPUT_LINES = 100  # 设置最大输出行数
    output_lines = []

    # 检查并创建输出文件的目录
    if output_file:
        directory = os.path.dirname(output_file)
        if not os.path.exists(directory):
            os.makedirs(directory)

    try:
        process = subprocess.Popen(command, shell=True, cwd=cwd,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

        with open(output_file, 'w') as f_out:
            for line in process.stdout:
                line = line.rstrip()
                # 保存到文件
                f_out.write(line + '\n')
                f_out.flush()

                if show_output:
                    # 添加到输出列表
                    output_lines.append(line)
                    if len(output_lines) > MAX_OUTPUT_LINES:
                        output_lines.pop(0)  # 删除最早的行

                    # 清屏并打印最近的输出行
                    os.system('clear')
                    for out_line in output_lines:
                        print(out_line)

        return_code = process.wait()
        return return_code
    except Exception as e:
        print(f"执行命令时发生异常：{e}")
        return -1

def main():
    EXP_ID = "2024.10.2.1"
    PR_ID_FILE = "pr_ids.txt"  # 存放PR ID的文本文件
    APOLLO_REPO_PATH = "/home/mrb2/experiments/postgraduate_project/apollo/apollo"  # 本地Apollo仓库路径
    SHOW_OUTPUT = True  # 是否显示shell输出，设置为False则不显示

    # 获取当前脚本的绝对路径，确保路径正确
    script_dir = os.getcwd()

    # 检查PR ID文件是否存在
    if not os.path.isfile(PR_ID_FILE):
        print(f"错误：未找到PR ID文件：{PR_ID_FILE}")
        sys.exit(1)

    # 创建实验文件夹，使用绝对路径
    EXP_DIR = os.path.abspath(EXP_ID)
    if not os.path.exists(EXP_DIR):
        os.makedirs(EXP_DIR)
        print(f"已创建实验文件夹：{EXP_DIR}")
    else:
        print(f"实验文件夹已存在：{EXP_DIR}")

    # 读取PR ID列表
    with open(PR_ID_FILE, 'r') as f:
        pr_ids = [line.strip() for line in f if line.strip()]

    for pr_id in pr_ids:
        print(f"\n处理PR ID：{pr_id}")

        pr_folder = os.path.join(EXP_DIR, pr_id)
        # 检查是否已处理过该PR ID
        if os.path.exists(pr_folder):
            print(f"已存在PR ID文件夹，跳过：{pr_folder}")
            continue

        # 创建PR ID文件夹
        os.makedirs(pr_folder)
        print(f"已创建PR ID文件夹：{pr_folder}")

        # 创建output文件夹，使用绝对路径
        output_dir = os.path.join(pr_folder, 'output')
        os.makedirs(output_dir)
        print(f"已创建输出文件夹：{output_dir}")

        # 复制Apollo仓库
        apollo_src = APOLLO_REPO_PATH
        apollo_dst = os.path.join(pr_folder, 'apollo')
        cmd = f"cp -r {apollo_src} {apollo_dst}"
        ret, output = subprocess.getstatusoutput(cmd)
        if ret != 0:
            print(f"复制Apollo仓库失败：{output}")
            continue
        print("已复制Apollo仓库")

        # 设置apollo路径，使用绝对路径
        apollo_path = apollo_dst
        if not os.path.exists(apollo_path):
            print(f"Apollo目录未找到：{apollo_path}")
            continue

        # 获取提交ID
        cmd = f"git fetch origin pull/{pr_id}/head:pr-{pr_id}"
        output_file = os.path.join(output_dir, 'fetch_output.txt')
        ret = run_command_realtime(cmd, cwd=apollo_path,
                                   output_file=output_file,
                                   show_output=SHOW_OUTPUT)
        if ret != 0:
            print("获取PR提交失败，跳过")
            continue

        cmd = f"git checkout pr-{pr_id}"
        output_file = os.path.join(output_dir, 'checkout_output.txt')
        ret = run_command_realtime(cmd, cwd=apollo_path,
                                   output_file=output_file,
                                   show_output=SHOW_OUTPUT)
        if ret != 0:
            print("检出PR分支失败，跳过")
            continue

        # 获取当前的commit ID
        cmd = "git rev-parse HEAD"
        ret, commit_id = subprocess.getstatusoutput(cmd)
        commit_id = commit_id.strip()
        print(f"已检出到提交ID：{commit_id}")

        # 构建Docker容器
        cmd = "bash docker/scripts/dev_start.sh"
        output_file = os.path.join(output_dir, 'dev_start_output.txt')
        ret = run_command_realtime(cmd, cwd=apollo_path,
                                   output_file=output_file,
                                   show_output=SHOW_OUTPUT)
        if ret != 0:
            print("Docker容器构建失败，跳过该PR ID")
            continue
        print("Docker容器构建成功")

        # 在容器内执行命令
        container_name = "apollo_dev_" + os.getlogin()
        test_commands = [
            ("./apollo.sh test", 'test_output.txt'),
            ("./apollo.sh coverage", 'coverage_output.txt'),
            ("genhtml -o coverage_report $(bazel info output_path)/_coverage/_coverage_report.dat", 'genhtml_output.txt')
        ]
        for cmd, output_filename in test_commands:
            output_file = os.path.join(output_dir, output_filename)
            docker_cmd = f"docker exec {container_name} bash -c '{cmd}'"
            ret = run_command_realtime(docker_cmd, cwd=apollo_path,
                                       output_file=output_file,
                                       show_output=SHOW_OUTPUT)
            if ret != 0:
                print(f"命令执行失败：{cmd}，已保存输出")
            else:
                print(f"命令执行成功：{cmd}")

        print(f"PR ID {pr_id} 处理完成\n")

    print("\n所有PR ID处理完成")

if __name__ == "__main__":
    main()
