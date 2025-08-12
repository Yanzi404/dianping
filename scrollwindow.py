import time
import subprocess
import platform
import signal
import os
import atexit
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
            import ctypes
            from ctypes import wintypes
            
            print(f"正在设置Windows代理: {self.proxy_host}:{self.proxy_port}")
            
            # 打开注册表项
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0, winreg.KEY_ALL_ACCESS
                )
            except PermissionError:
                print("错误: 无法访问注册表，可能需要管理员权限")
                return False
            
            # 保存原始设置
            try:
                self.original_settings['ProxyEnable'] = winreg.QueryValueEx(key, "ProxyEnable")[0]
                print(f"保存原始ProxyEnable: {self.original_settings['ProxyEnable']}")
            except FileNotFoundError:
                self.original_settings['ProxyEnable'] = 0
                print("ProxyEnable不存在，设为默认值0")
                
            try:
                self.original_settings['ProxyServer'] = winreg.QueryValueEx(key, "ProxyServer")[0]
                print(f"保存原始ProxyServer: {self.original_settings['ProxyServer']}")
            except FileNotFoundError:
                self.original_settings['ProxyServer'] = ""
                print("ProxyServer不存在，设为默认值空字符串")
            
            # 保存ProxyOverride设置
            try:
                self.original_settings['ProxyOverride'] = winreg.QueryValueEx(key, "ProxyOverride")[0]
                print(f"保存原始ProxyOverride: {self.original_settings['ProxyOverride']}")
            except FileNotFoundError:
                self.original_settings['ProxyOverride'] = ""
                print("ProxyOverride不存在，设为默认值空字符串")
            
            # 设置代理
            proxy_server = f"{self.proxy_host}:{self.proxy_port}"
            
            # 启用代理
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            print("已启用代理")
            
            # 设置代理服务器
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
            print(f"已设置代理服务器: {proxy_server}")
            
            # 设置代理覆盖（绕过本地地址）
            proxy_override = "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>"
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, proxy_override)
            print("已设置代理覆盖规则")
            
            winreg.CloseKey(key)
            
            # 通知系统代理设置已更改
            try:
                # 定义Windows API函数
                internet_set_option = ctypes.windll.wininet.InternetSetOptionW
                internet_set_option.argtypes = [
                    wintypes.HANDLE,    # hInternet
                    wintypes.DWORD,     # dwOption
                    wintypes.LPVOID,    # lpBuffer
                    wintypes.DWORD      # dwBufferLength
                ]
                internet_set_option.restype = wintypes.BOOL
                
                # INTERNET_OPTION_SETTINGS_CHANGED = 39
                # INTERNET_OPTION_REFRESH = 37
                result1 = internet_set_option(None, 39, None, 0)
                result2 = internet_set_option(None, 37, None, 0)
                
                if result1 and result2:
                    print("已通知系统刷新代理设置")
                else:
                    print("警告: 无法通知系统刷新代理设置，可能需要重启浏览器")
                    
            except Exception as refresh_error:
                print(f"警告: 刷新代理设置时出错: {refresh_error}")
            
            # 额外的刷新方法
            try:
                subprocess.run([
                    "rundll32.exe", "url.dll,FileProtocolHandler", 
                    "about:blank"
                ], check=False, timeout=5)
            except Exception:
                pass
            
            print(f"✅ Windows代理设置完成: {self.proxy_host}:{self.proxy_port}")
            print("提示: 如果浏览器代理未生效，请重启浏览器")
            return True
            
        except ImportError:
            print("错误: 无法导入winreg模块，请确保在Windows系统上运行")
            return False
        except Exception as e:
            print(f"设置Windows代理失败: {e}")
            import traceback
            traceback.print_exc()
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
            import ctypes
            from ctypes import wintypes
            
            print("正在恢复Windows代理设置...")
            
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0, winreg.KEY_ALL_ACCESS
                )
            except PermissionError:
                print("错误: 无法访问注册表，可能需要管理员权限")
                return False
            
            # 恢复原始设置
            proxy_enable = self.original_settings.get('ProxyEnable', 0)
            proxy_server = self.original_settings.get('ProxyServer', "")
            proxy_override = self.original_settings.get('ProxyOverride', "")
            
            print(f"恢复ProxyEnable: {proxy_enable}")
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, proxy_enable)
            
            print(f"恢复ProxyServer: {proxy_server}")
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
            
            print(f"恢复ProxyOverride: {proxy_override}")
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, proxy_override)
            
            winreg.CloseKey(key)
            
            # 通知系统代理设置已更改
            try:
                # 定义Windows API函数
                internet_set_option = ctypes.windll.wininet.InternetSetOptionW
                internet_set_option.argtypes = [
                    wintypes.HANDLE,    # hInternet
                    wintypes.DWORD,     # dwOption
                    wintypes.LPVOID,    # lpBuffer
                    wintypes.DWORD      # dwBufferLength
                ]
                internet_set_option.restype = wintypes.BOOL
                
                # INTERNET_OPTION_SETTINGS_CHANGED = 39
                # INTERNET_OPTION_REFRESH = 37
                result1 = internet_set_option(None, 39, None, 0)
                result2 = internet_set_option(None, 37, None, 0)
                
                if result1 and result2:
                    print("已通知系统刷新代理设置")
                else:
                    print("警告: 无法通知系统刷新代理设置")
                    
            except Exception as refresh_error:
                print(f"警告: 刷新代理设置时出错: {refresh_error}")
            
            print("✅ Windows代理设置已恢复")
            return True
            
        except ImportError:
            print("错误: 无法导入winreg模块，请确保在Windows系统上运行")
            return False
        except Exception as e:
            print(f"恢复Windows代理失败: {e}")
            import traceback
            traceback.print_exc()
            return False


class MitmWebManager:
    """mitmweb服务管理器"""
    
    def __init__(self, script_path: str = "dianping_interceptor.py", port: int = 8080):
        self.script_path = script_path
        self.port = port
        self.process = None
        
    def start(self) -> bool:
        """启动mitmweb服务"""
        try:
            # 检查脚本文件是否存在
            if not os.path.exists(self.script_path):
                print(f"错误: 找不到脚本文件 {self.script_path}")
                return False
            
            # 启动mitmweb
            cmd = [
                "mitmweb",
                "-s", self.script_path,
                "--listen-port", str(self.port),
                "--web-port", str(self.port + 1)
            ]
            
            print(f"启动mitmweb服务: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if platform.system() != "Windows" else None
            )
            
            # 等待服务启动
            time.sleep(3)
            
            # 检查进程是否还在运行
            if self.process.poll() is None:
                print(f"mitmweb服务已启动，端口: {self.port}")
                print(f"Web界面地址: http://127.0.0.1:{self.port + 1}")
                return True
            else:
                stdout, stderr = self.process.communicate()
                print(f"mitmweb启动失败:")
                print(f"stdout: {stdout.decode()}")
                print(f"stderr: {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            print("错误: 找不到mitmweb命令，请确保已安装mitmproxy")
            return False
        except Exception as e:
            print(f"启动mitmweb时发生错误: {e}")
            return False
    
    def stop(self) -> bool:
        """停止mitmweb服务"""
        try:
            if self.process and self.process.poll() is None:
                if platform.system() == "Windows":
                    self.process.terminate()
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if platform.system() == "Windows":
                        self.process.kill()
                    else:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                
                print("mitmweb服务已停止")
                return True
            else:
                print("mitmweb服务未运行")
                return True
                
        except Exception as e:
            print(f"停止mitmweb时发生错误: {e}")
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


def scroll(scroll_count: int = 5, scroll_pause: float = 1, speed: int = -200, read_region: Optional[Tuple[int, int, int, int]] = None) -> None:
    """
    模拟下滑操作并读取屏幕文本

    参数:
    - scroll_count: 下滑次数
    - scroll_pause: 每次下滑后的暂停时间(秒)
    - read_region: 要读取文本的区域 (left, top, width, height)
    """
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
                time.sleep(scroll_pause)
                
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
        print("\n请在10秒内切换到目标应用窗口...")
        
        for i in range(3, 0, -1):
            print(f"倒计时: {i} 秒", end='\r')
            time.sleep(1)
        print("\n开始数据采集...")
        
        # 4. 开始滚动采集
        scroll(scroll_count=99999, scroll_pause=2,speed=-200)
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        cleanup_on_exit()
        print("程序结束")


if __name__ == "__main__":
    main()
