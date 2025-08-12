import time
import subprocess
import platform
import signal
import os
import atexit
import threading
from typing import Optional, Tuple
import pyautogui
from pynput import keyboard

"""
通过pyautogui模拟前端滚动，配合mitmproxy拦截接口解析数据
添加了暂停/继续功能(按空格键控制)
自动启动mitmweb服务并设置系统代理
"""

# 全局变量存储进程和原始代理设置
mitm_process = None
original_proxy_settings = {}


class ProxyManager:
    """代理管理器，负责设置和恢复系统代理"""

    def __init__(self, proxy_host: str = "127.0.0.1", proxy_port: int = 8080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.system = platform.system().lower()
        self.original_settings = {}

    def set_proxy(self) -> bool:
        """设置系统代理"""
        try:
            if self.system == "darwin":  # macOS
                return self._set_macos_proxy()
            elif self.system == "windows":  # Windows
                return self._set_windows_proxy()
            else:
                print(f"不支持的操作系统: {self.system}")
                return False
        except Exception as e:
            print(f"设置代理时发生错误: {e}")
            return False

    def restore_proxy(self) -> bool:
        """恢复原始代理设置"""
        try:
            if self.system == "darwin":  # macOS
                return self._restore_macos_proxy()
            elif self.system == "windows":  # Windows
                return self._restore_windows_proxy()
            else:
                return False
        except Exception as e:
            print(f"恢复代理时发生错误: {e}")
            return False

    def _set_macos_proxy(self) -> bool:
        """设置macOS代理"""
        try:
            # 获取当前网络服务
            result = subprocess.run(
                ["networksetup", "-listallnetworkservices"],
                capture_output=True, text=True, check=True
            )
            services = [line.strip() for line in result.stdout.split('\n')
                        if line.strip() and not line.startswith('*')]

            for service in services:
                if not service:
                    continue

                # 保存原始设置
                try:
                    # 获取HTTP代理设置
                    http_result = subprocess.run(
                        ["networksetup", "-getwebproxy", service],
                        capture_output=True, text=True, check=True
                    )
                    # 获取HTTPS代理设置
                    https_result = subprocess.run(
                        ["networksetup", "-getsecurewebproxy", service],
                        capture_output=True, text=True, check=True
                    )

                    self.original_settings[service] = {
                        'http': http_result.stdout,
                        'https': https_result.stdout
                    }

                    # 设置HTTP代理
                    subprocess.run([
                        "networksetup", "-setwebproxy", service,
                        self.proxy_host, str(self.proxy_port)
                    ], check=True)

                    # 设置HTTPS代理
                    subprocess.run([
                        "networksetup", "-setsecurewebproxy", service,
                        self.proxy_host, str(self.proxy_port)
                    ], check=True)

                except subprocess.CalledProcessError:
                    continue

            print(f"已设置macOS代理: {self.proxy_host}:{self.proxy_port}")
            return True

        except Exception as e:
            print(f"设置macOS代理失败: {e}")
            return False

    def _set_windows_proxy(self) -> bool:
        """设置Windows代理"""
        try:
            import winreg

            # 打开注册表项
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_ALL_ACCESS
            )

            # 保存原始设置
            try:
                self.original_settings['ProxyEnable'] = winreg.QueryValueEx(key, "ProxyEnable")[0]
            except FileNotFoundError:
                self.original_settings['ProxyEnable'] = 0

            try:
                self.original_settings['ProxyServer'] = winreg.QueryValueEx(key, "ProxyServer")[0]
            except FileNotFoundError:
                self.original_settings['ProxyServer'] = ""

            # 设置代理
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"{self.proxy_host}:{self.proxy_port}")

            winreg.CloseKey(key)

            # 刷新IE设置
            subprocess.run(["rundll32.exe", "inetcpl.cpl,ClearMyTracksByProcess", "8"], check=False)

            print(f"已设置Windows代理: {self.proxy_host}:{self.proxy_port}")
            return True

        except Exception as e:
            print(f"设置Windows代理失败: {e}")
            return False

    def _restore_macos_proxy(self) -> bool:
        """恢复macOS代理设置"""
        try:
            for service in self.original_settings:
                try:
                    # 关闭HTTP代理
                    subprocess.run([
                        "networksetup", "-setwebproxystate", service, "off"
                    ], check=True)

                    # 关闭HTTPS代理
                    subprocess.run([
                        "networksetup", "-setsecurewebproxystate", service, "off"
                    ], check=True)

                except subprocess.CalledProcessError:
                    continue

            print("已恢复macOS代理设置")
            return True

        except Exception as e:
            print(f"恢复macOS代理失败: {e}")
            return False

    def _restore_windows_proxy(self) -> bool:
        """恢复Windows代理设置"""
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_ALL_ACCESS
            )

            # 恢复原始设置
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD,
                              self.original_settings.get('ProxyEnable', 0))
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ,
                              self.original_settings.get('ProxyServer', ""))

            winreg.CloseKey(key)

            print("已恢复Windows代理设置")
            return True

        except Exception as e:
            print(f"恢复Windows代理失败: {e}")
            return False


class MitmWebManager:
    """mitmweb服务管理器"""

    def __init__(self, script_path: str = "dianping_interceptor.py", port: int = 8080):
        self.script_path = script_path
        self.port = port
        self.process = None
        self.log_file = None
        self.monitor_thread = None
        self.should_monitor = False
        self.restart_count = 0
        self.max_restarts = 3

    def start(self) -> bool:
        """启动mitmweb服务"""
        try:
            # 检查脚本文件是否存在
            if not os.path.exists(self.script_path):
                print(f"错误: 找不到脚本文件 {self.script_path}")
                return False

            # 创建日志文件
            log_filename = f"log/mitm_log/mitmweb_{int(time.time())}.log"
            self.log_file = open(log_filename, 'w', encoding='utf-8')

            # 启动mitmweb
            cmd = [
                "mitmweb",
                "-s", self.script_path,
                "--listen-port", str(self.port),
                "--web-port", str(self.port + 1),
                "--set", "confdir=~/.mitmproxy"  # 指定配置目录
            ]

            print(f"启动mitmweb服务: {' '.join(cmd)}")
            print(f"日志文件: {log_filename}")
            
            # 使用DEVNULL避免输出缓冲区问题，同时将输出重定向到日志文件
            self.process = subprocess.Popen(
                cmd,
                stdout=self.log_file,
                stderr=subprocess.STDOUT,  # 将stderr重定向到stdout
                preexec_fn=os.setsid if platform.system() != "Windows" else None,
                bufsize=0  # 无缓冲
            )

            # 等待服务启动
            print("等待mitmweb服务启动...")
            for i in range(10):  # 最多等待10秒
                time.sleep(1)
                if self.process.poll() is None:
                    # 进程还在运行，检查端口是否可用
                    if self._check_service_ready():
                        print(f"mitmweb服务已启动，端口: {self.port}")
                        print(f"Web界面地址: http://127.0.0.1:{self.port + 1}")
                        
                        # 启动监控线程
                        self._start_monitor()
                        return True
                else:
                    # 进程已退出
                    break
                print(f"等待中... ({i+1}/10)")

            # 如果到这里说明启动失败
            if self.process.poll() is not None:
                print(f"mitmweb进程已退出，退出码: {self.process.poll()}")
                self._print_log_tail()
            else:
                print("mitmweb服务启动超时")
                self.stop()
            
            return False

        except FileNotFoundError:
            print("错误: 找不到mitmweb命令，请确保已安装mitmproxy")
            print("安装命令: pip install mitmproxy")
            return False
        except Exception as e:
            print(f"启动mitmweb时发生错误: {e}")
            return False

    def _check_service_ready(self) -> bool:
        """检查服务是否准备就绪"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self.port))
            sock.close()
            return result == 0
        except:
            return False

    def _print_log_tail(self):
        """打印日志文件的最后几行"""
        try:
            if self.log_file:
                self.log_file.flush()
                self.log_file.close()
                
            # 重新打开文件读取内容
            if hasattr(self, 'log_file') and self.log_file:
                with open(self.log_file.name, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print("mitmweb日志输出:")
                        for line in lines[-10:]:  # 显示最后10行
                            print(f"  {line.strip()}")
        except Exception as e:
            print(f"读取日志文件失败: {e}")

    def is_running(self) -> bool:
        """检查服务是否正在运行"""
        if self.process is None:
            return False
        return self.process.poll() is None

    def check_status(self) -> None:
        """检查并报告服务状态"""
        if not self.is_running():
            print("警告: mitmweb服务已停止运行")
            if self.process:
                print(f"进程退出码: {self.process.poll()}")
                self._print_log_tail()

    def _start_monitor(self) -> None:
        """启动监控线程"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
            
        self.should_monitor = True
        self.monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
        self.monitor_thread.start()
        print("已启动mitmweb服务监控")

    def _stop_monitor(self) -> None:
        """停止监控线程"""
        self.should_monitor = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

    def _monitor_process(self) -> None:
        """监控进程状态的线程函数"""
        while self.should_monitor:
            try:
                if self.process and self.process.poll() is not None:
                    # 进程已退出
                    exit_code = self.process.poll()
                    print(f"\n⚠️  mitmweb进程意外退出，退出码: {exit_code}")
                    self._print_log_tail()
                    
                    # 尝试自动重启
                    if self.restart_count < self.max_restarts:
                        self.restart_count += 1
                        print(f"尝试自动重启mitmweb服务 ({self.restart_count}/{self.max_restarts})...")
                        
                        # 清理当前进程状态
                        self.process = None
                        if self.log_file:
                            try:
                                self.log_file.close()
                            except:
                                pass
                            self.log_file = None
                        
                        # 重启服务
                        if self._restart_service():
                            print("✅ mitmweb服务自动重启成功")
                            continue
                        else:
                            print("❌ mitmweb服务自动重启失败")
                    else:
                        print(f"❌ 已达到最大重启次数 ({self.max_restarts})，停止自动重启")
                    
                    break
                    
                # 检查服务端口是否可用
                elif not self._check_service_ready():
                    print("⚠️  mitmweb服务端口不可用，可能存在问题")
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                print(f"监控线程发生错误: {e}")
                time.sleep(5)

    def _restart_service(self) -> bool:
        """重启服务的内部方法"""
        try:
            # 创建新的日志文件
            log_filename = f"mitmweb_{int(time.time())}.log"
            self.log_file = open(log_filename, 'w', encoding='utf-8')

            # 启动mitmweb
            cmd = [
                "mitmweb",
                "-s", self.script_path,
                "--listen-port", str(self.port),
                "--web-port", str(self.port + 1),
                "--set", "confdir=~/.mitmproxy"
            ]

            self.process = subprocess.Popen(
                cmd,
                stdout=self.log_file,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if platform.system() != "Windows" else None,
                bufsize=0
            )

            # 等待服务启动
            for i in range(10):
                time.sleep(1)
                if self.process.poll() is None and self._check_service_ready():
                    return True
                elif self.process.poll() is not None:
                    break

            return False

        except Exception as e:
            print(f"重启服务时发生错误: {e}")
            return False

    def stop(self) -> bool:
        """停止mitmweb服务"""
        try:
            # 停止监控线程
            self._stop_monitor()
            
            if self.process and self.process.poll() is None:
                print("正在停止mitmweb服务...")
                if platform.system() == "Windows":
                    self.process.terminate()
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

                # 等待进程结束
                try:
                    self.process.wait(timeout=5)
                    print("mitmweb服务已正常停止")
                except subprocess.TimeoutExpired:
                    print("强制终止mitmweb服务...")
                    if platform.system() == "Windows":
                        self.process.kill()
                    else:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    print("mitmweb服务已强制停止")

            # 关闭日志文件
            if self.log_file:
                try:
                    self.log_file.close()
                    self.log_file = None
                except:
                    pass

            self.process = None
            return True

        except Exception as e:
            print(f"停止mitmweb时发生错误: {e}")
            # 确保清理资源
            self._stop_monitor()
            if self.log_file:
                try:
                    self.log_file.close()
                    self.log_file = None
                except:
                    pass
            self.process = None
            return False


def cleanup_on_exit():
    """程序退出时的清理函数"""
    global mitm_process, original_proxy_settings

    print("\n正在清理资源...")

    # 停止mitmweb服务
    if mitm_process:
        mitm_process.stop()

    # 恢复代理设置
    proxy_manager = ProxyManager()
    proxy_manager.original_settings = original_proxy_settings
    proxy_manager.restore_proxy()

    print("资源清理完成")


class ScrollController:
    """滚动控制器，管理暂停和退出状态"""

    def __init__(self) -> None:
        self.paused: bool = False
        self.should_exit: bool = False

    def toggle_pause(self) -> None:
        """切换暂停状态"""
        self.paused = not self.paused
        status = "暂停" if self.paused else "继续"
        print(f"\n程序已{status}")

    def request_exit(self) -> None:
        """请求退出程序"""
        self.should_exit = True
        print("\n请求退出程序...")


def on_press(key: keyboard.Key, controller: ScrollController) -> Optional[bool]:
    """键盘按键处理函数"""
    try:
        if key == keyboard.Key.space:
            controller.toggle_pause()
        elif key == keyboard.Key.esc:
            controller.request_exit()
            return False  # 停止监听
    except AttributeError:
        pass
    return None


def scroll(scroll_count: int = 5, scroll_pause: float = 1, speed: int = -200,
           read_region: Optional[Tuple[int, int, int, int]] = None) -> None:
    """
    模拟下滑操作并读取屏幕文本

    参数:
    - scroll_count: 下滑次数
    - scroll_pause: 每次下滑后的暂停时间(秒)
    - read_region: 要读取文本的区域 (left, top, width, height)
    """
    global mitm_process
    
    # 创建控制器实例
    controller = ScrollController()

    # 启动键盘监听
    listener = keyboard.Listener(
        on_press=lambda key: on_press(key, controller)
    )
    listener.start()

    try:
        # 确保有足够时间将鼠标移动到安全位置
        time.sleep(2)

        # 获取屏幕尺寸并设置默认读取区域
        screen_width, screen_height = pyautogui.size()
        if read_region is None:
            read_region = (0, 0, int(screen_width / 3), screen_height)

        print("操作提示:")
        print("- 按空格键暂停/继续")
        print("- 按ESC键退出程序")

        for i in range(scroll_count):
            if controller.should_exit:
                break

            # 等待暂停状态结束
            while controller.paused and not controller.should_exit:
                time.sleep(0.1)

            if controller.should_exit:
                break

            print(f"\n--- 第 {i + 1} 次下滑 ---")
            try:
                # 模拟下滑操作 (向下滚动鼠标滚轮)
                pyautogui.scroll(speed)  # 负值表示向下滚动
                time.sleep(scroll_pause)  # 等待页面稳定

                pyautogui.scroll(100)  # 向上滚动100

            except Exception as e:
                print(f"第 {i + 1} 次操作出错: {e}")
                break
    finally:
        listener.stop()


def main() -> None:
    """主程序入口"""
    global mitm_process, original_proxy_settings

    # 注册退出清理函数
    atexit.register(cleanup_on_exit)

    # 设置信号处理器
    def signal_handler(signum, frame):
        print(f"\n接收到信号 {signum}，正在退出...")
        cleanup_on_exit()
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=== 大众点评数据采集工具 ===")
    print("正在初始化服务...")

    try:
        # 1. 启动mitmweb服务
        print("\n1. 启动mitmweb服务...")
        mitm_process = MitmWebManager()
        if not mitm_process.start():
            print("启动mitmweb服务失败，程序退出")
            return

        # 2. 设置系统代理
        print("\n2. 设置系统代理...")
        proxy_manager = ProxyManager()
        if proxy_manager.set_proxy():
            original_proxy_settings = proxy_manager.original_settings.copy()
            print("代理设置成功")
        else:
            print("代理设置失败，但程序将继续运行")

        # 3. 等待用户准备
        print("\n3. 服务初始化完成！")
        print("请确保:")
        print("- 浏览器已配置使用系统代理")
        print("- 已打开目标网页")
        print("- 准备开始数据采集")
        print("\n请在3秒内切换到目标应用窗口...")

        for i in range(3, 0, -1):
            print(f"倒计时: {i} 秒", end='\r')
            time.sleep(1)
        print("\n开始数据采集...")


        # 4. 开始滚动采集
        scroll(scroll_count=99999, scroll_pause=2, speed=-1000)

    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        cleanup_on_exit()
        print("程序结束")


if __name__ == "__main__":
    main()
