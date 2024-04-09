import subprocess
import time

import httpx


async def get_user_info():
    async with httpx.AsyncClient() as client:
        response = await client.request("get", "api/cx/student/info", timeout=3000)


def start_processes(num_processes, program_path):
    """启动指定数量的程序"""
    processes = []
    for _ in range(num_processes):
        process = subprocess.Popen(program_path)
        processes.append(process)
    return processes


def main():
    # 同时运行的进程数量
    num_processes = 20

    # 需要运行的程序路径
    program_path = "path/to/your/program.exe"

    # 启动初始进程
    processes = start_processes(num_processes, program_path)

    # 等待进程完成
    while True:
        for idx, p in enumerate(processes):
            if p.poll() is not None:  # 检查进程是否已经退出
                print(f"进程 {idx} 已退出，重新启动")
                processes[idx] = subprocess.Popen(program_path)
                break
        time.sleep(1)  # 每秒检查一次进程状态


if __name__ == "__main__":
    main()
