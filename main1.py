#!/usr/bin/env python3
import os
import subprocess
import sys
import getpass

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

def main():
    EXP_ID = "2024.10.2.1"
    PR_ID_FILE = "pr_ids.txt"
    APOLLO_REPO_PATH = "/home/mrb2/experiments/postgraduate_project/apollo/apollo"  # 请将此路径修改为您的实际 Apollo 仓库路径
    SHOW_OUTPUT = True

    # 获取当前脚本的绝对路径
    script_dir = os.getcwd()

    # 检查 PR ID 文件是否存在
    if not os.path.isfile(PR_ID_FILE):
        print(f"错误：未找到 PR ID 文件：{PR_ID_FILE}")
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

    # 读取 PR ID 列表和基准 PR ID
    pr_list = []
    with open(os.path.join(script_dir, PR_ID_FILE), 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                pr_id, base_pr = parts
            elif len(parts) == 1:
                pr_id = parts[0]
                base_pr = "master"
            else:
                continue
            pr_list.append((pr_id, base_pr))

    for pr_id, base_pr in pr_list:
        print(f"\n处理 PR ID：{pr_id}，基准 PR：{base_pr}")

        # Apollo 仓库副本路径（每个 PR 一个副本）
        pr_apollo_dir = os.path.join(EXP_DIR, f'apollo_{pr_id}')
        if os.path.exists(pr_apollo_dir):
            print(f"Apollo 仓库已存在，跳过复制：{pr_apollo_dir}")
        else:
            cmd = f"cp -r {APOLLO_REPO_PATH} {pr_apollo_dir}"
            ret, output = subprocess.getstatusoutput(cmd)
            if ret != 0:
                print(f"复制 Apollo 仓库失败：{output}")
                continue
            print(f"已复制 Apollo 仓库到：{pr_apollo_dir}")

        # 输出文件夹
        output_dir = os.path.join(OUTPUTS_DIR, pr_id)
        os.makedirs(output_dir, exist_ok=True)

        # 设置 Apollo 路径
        apollo_path = pr_apollo_dir
        if not os.path.exists(apollo_path):
            print(f"Apollo 目录未找到：{apollo_path}")
            continue

        # 切换到 Apollo 目录
        os.chdir(apollo_path)

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
                # 切换到基准 PR
                if base_pr == "master":
                    cmd = f"git checkout master"
                else:
                    # 获取并检出基准 PR
                    cmd = f"git fetch origin pull/{base_pr}/head:pr-{base_pr}"
                    output_file = os.path.join(state_output_dir, 'fetch_base_pr.txt')
                    ret = run_command_realtime(cmd, cwd=apollo_path,
                                               output_file=output_file,
                                               show_output=SHOW_OUTPUT)
                    if ret != 0:
                        print(f"获取基准 PR {base_pr} 失败，跳过")
                        break

                    cmd = f"git checkout pr-{base_pr}"
                output_file = os.path.join(state_output_dir, 'checkout_base_pr.txt')
                ret = run_command_realtime(cmd, cwd=apollo_path,
                                           output_file=output_file,
                                           show_output=SHOW_OUTPUT)
                if ret != 0:
                    print(f"切换到基准 PR {base_pr} 失败，跳过")
                    break
                print(f"已切换到基准 PR {base_pr}")
            else:
                # 应用当前 PR 到基准 PR 上
                cmd = f"git fetch origin pull/{pr_id}/head:pr-{pr_id}"
                output_file = os.path.join(state_output_dir, 'fetch_current_pr.txt')
                ret = run_command_realtime(cmd, cwd=apollo_path,
                                           output_file=output_file,
                                           show_output=SHOW_OUTPUT)
                if ret != 0:
                    print(f"获取 PR {pr_id} 失败，跳过")
                    break

                # 创建一个新的分支，基于基准 PR
                cmd = f"git checkout -b test-pr-{pr_id} pr-{base_pr}" if base_pr != "master" else f"git checkout -b test-pr-{pr_id} master"
                output_file = os.path.join(state_output_dir, 'checkout_new_branch.txt')
                ret = run_command_realtime(cmd, cwd=apollo_path,
                                           output_file=output_file,
                                           show_output=SHOW_OUTPUT)
                if ret != 0:
                    print(f"创建新分支失败，跳过")
                    break

                # 合并当前 PR
                cmd = f"git merge pr-{pr_id} --no-commit --no-ff"
                output_file = os.path.join(state_output_dir, 'merge_pr.txt')
                ret = run_command_realtime(cmd, cwd=apollo_path,
                                           output_file=output_file,
                                           show_output=SHOW_OUTPUT)
                if ret != 0:
                    print(f"合并 PR {pr_id} 失败，跳过")
                    break
                print(f"已合并 PR {pr_id}")

            # 获取当前的提交 ID
            cmd = "git rev-parse HEAD"
            ret, commit_id = subprocess.getstatusoutput(cmd)
            commit_id = commit_id.strip()
            print(f"当前提交 ID：{commit_id}")

            # 构建 Docker 容器
            cmd = "bash docker/scripts/dev_start.sh"
            output_file = os.path.join(state_output_dir, 'dev_start_output.txt')
            ret = run_command_realtime(cmd, cwd=apollo_path,
                                       output_file=output_file,
                                       show_output=SHOW_OUTPUT)
            if ret != 0:
                print("Docker 容器构建失败，跳过该状态")
            else:
                print("Docker 容器构建成功")

                # 获取当前用户
                DOCKER_USER = 'mrb2'
                DEV_CONTAINER_PREFIX = 'apollo_dev_'
                DEV_CONTAINER = f"{DEV_CONTAINER_PREFIX}{DOCKER_USER}"

                # 在容器内执行命令
                commands = [
                    ("./apollo.sh test", 'test_output.txt'),
                    ("./apollo.sh coverage", 'coverage_output.txt'),
                    ("genhtml -o coverage_report $(bazel info output_path)/_coverage/_coverage_report.dat", 'genhtml_output.txt')
                ]
                for idx, (cmd, output_filename) in enumerate(commands):
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
                        if idx < len(commands) -1:
                            print("继续执行后续命令")
                            continue
                        else:
                            print("最后一个命令执行失败，退出")
                    else:
                        print(f"命令执行成功：{cmd}")

                # # 停止并删除 Docker 容器，避免影响下一次构建
                # cmd = f"bash docker/scripts/dev_stop.sh"
                # output_file = os.path.join(state_output_dir, 'dev_stop_output.txt')
                # ret = run_command_realtime(cmd, cwd=apollo_path,
                #                            output_file=output_file,
                #                            show_output=SHOW_OUTPUT)
                # if ret != 0:
                #     print("Docker 容器停止失败")
                # else:
                #     print("Docker 容器已停止")

            # 执行 ./apollo.sh clean
            cmd = "./apollo.sh clean"
            output_file = os.path.join(state_output_dir, 'apollo_clean_output.txt')
            ret = run_command_realtime(cmd, cwd=apollo_path,
                                       output_file=output_file,
                                       show_output=SHOW_OUTPUT)
            if ret != 0:
                print("清理编译文件失败")
            else:
                print("已清理编译生成的文件")

            if state == "after":
                # 删除测试分支，返回到基准 PR
                cmd = "git checkout " + (f"pr-{base_pr}" if base_pr != "master" else "master")
                subprocess.getstatusoutput(cmd)
                cmd = "git branch -D test-pr-" + pr_id
                subprocess.getstatusoutput(cmd)

            print(f"状态 {state} 处理完成\n")

        print(f"PR ID {pr_id} 处理完成\n")

    print("\n所有 PR ID 处理完成")

if __name__ == "__main__":
    main()
