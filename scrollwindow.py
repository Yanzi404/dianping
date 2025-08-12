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
        """设置Windows系统代理"""
        try:
            import winreg
            import ctypes
            
            print(f"🔧 设置Windows代理: {self.proxy_host}:{self.proxy_port}")
            
            # 检查管理员权限
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                if not is_admin:
                    print("⚠️  建议以管理员身份运行以确保代理设置生效")
            except:
                pass
            
            # 检查注册表访问权限
            registry_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    registry_path,
                    0, winreg.KEY_ALL_ACCESS
                )
                print("✅ 注册表访问权限正常")
            except PermissionError:
                print("❌ 注册表访问权限不足")
                print("💡 解决方案:")
                print("   1. 以管理员身份运行此程序")
                print("   2. 或手动设置代理: Windows设置 -> 网络和Internet -> 代理")
                return False
            except Exception as e:
                print(f"❌ 注册表访问失败: {e}")
                return False
            
            try:
                # 保存当前设置
                try:
                    self.original_settings['ProxyEnable'] = winreg.QueryValueEx(key, "ProxyEnable")[0]
                    print(f"📋 当前ProxyEnable: {self.original_settings['ProxyEnable']}")
                except FileNotFoundError:
                    self.original_settings['ProxyEnable'] = 0
                    print("📋 ProxyEnable不存在，默认为0")
                
                try:
                    self.original_settings['ProxyServer'] = winreg.QueryValueEx(key, "ProxyServer")[0]
                    print(f"📋 当前ProxyServer: {self.original_settings['ProxyServer']}")
                except FileNotFoundError:
                    self.original_settings['ProxyServer'] = ""
                    print("📋 ProxyServer不存在，默认为空")
                
                try:
                    self.original_settings['ProxyOverride'] = winreg.QueryValueEx(key, "ProxyOverride")[0]
                    print(f"📋 当前ProxyOverride: {self.original_settings['ProxyOverride']}")
                except FileNotFoundError:
                    self.original_settings['ProxyOverride'] = ""
                    print("📋 ProxyOverride不存在，默认为空")
                
                # 设置新的代理
                proxy_server = f"{self.proxy_host}:{self.proxy_port}"
                proxy_override = "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>"
                
                print(f"🔧 设置ProxyEnable = 1")
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                
                print(f"🔧 设置ProxyServer = {proxy_server}")
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
                
                print(f"🔧 设置ProxyOverride = {proxy_override}")
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, proxy_override)
                
                print("✅ 注册表设置完成")
                
            finally:
                winreg.CloseKey(key)
            
            # 刷新系统设置
            try:
                print("🔄 刷新系统代理设置...")
                
                # 通知系统代理设置已更改
                INTERNET_OPTION_REFRESH = 37
                INTERNET_OPTION_SETTINGS_CHANGED = 39
                
                wininet = ctypes.windll.wininet
                result1 = wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
                result2 = wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
                
                if result1 and result2:
                    print("✅ 系统代理设置已刷新")
                else:
                    print("⚠️  系统代理刷新可能不完整")
                
            except Exception as e:
                print(f"⚠️  刷新系统设置失败: {e}")
                print("💡 建议手动重启浏览器以使代理生效")
            
            # 验证设置是否成功
            try:
                verify_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    registry_path,
                    0, winreg.KEY_READ
                )
                
                verify_enable = winreg.QueryValueEx(verify_key, "ProxyEnable")[0]
                verify_server = winreg.QueryValueEx(verify_key, "ProxyServer")[0]
                
                winreg.CloseKey(verify_key)
                
                if verify_enable == 1 and verify_server == proxy_server:
                    print("✅ 代理设置验证成功")
                    print("💡 如果浏览器代理仍未生效，请重启浏览器")
                    return True
                else:
                    print(f"⚠️  代理设置验证失败 - Enable: {verify_enable}, Server: {verify_server}")
                    return False
                    
            except Exception as e:
                print(f"⚠️  代理设置验证失败: {e}")
                return True  # 设置可能成功，但验证失败
            
        except ImportError:
            print("❌ 无法导入Windows注册表模块")
            return False
        except Exception as e:
            print(f"❌ Windows代理设置失败: {e}")
            print("💡 请尝试:")
            print("   1. 以管理员身份运行")
            print("   2. 手动设置代理")
            print("   3. 运行 test_windows_proxy.py 进行诊断")
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
            
            print("🔄 恢复Windows代理设置...")
            
            # 检查是否有保存的原始设置
            if not hasattr(self, 'original_settings') or not self.original_settings:
                print("⚠️  没有找到原始代理设置，将禁用代理")
                # 如果没有原始设置，就简单地禁用代理
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                        0, winreg.KEY_ALL_ACCESS
                    )
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                    print("✅ 已禁用代理")
                    return True
                except Exception as e:
                    print(f"❌ 禁用代理失败: {e}")
                    return False
            
            # 检查注册表访问权限
            registry_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    registry_path,
                    0, winreg.KEY_ALL_ACCESS
                )
                print("✅ 注册表访问权限正常")
            except PermissionError:
                print("❌ 注册表访问权限不足")
                print("💡 解决方案:")
                print("   1. 以管理员身份运行此程序")
                print("   2. 或手动恢复代理设置")
                return False
            except Exception as e:
                print(f"❌ 注册表访问失败: {e}")
                return False
            
            try:
                # 恢复ProxyEnable设置
                if 'ProxyEnable' in self.original_settings:
                    original_enable = self.original_settings['ProxyEnable']
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, original_enable)
                    print(f"📋 恢复ProxyEnable: {original_enable}")
                else:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                    print("📋 设置ProxyEnable为默认值: 0")
                
                # 恢复ProxyServer设置
                if 'ProxyServer' in self.original_settings:
                    original_server = self.original_settings['ProxyServer']
                    if original_server:
                        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, original_server)
                        print(f"📋 恢复ProxyServer: {original_server}")
                    else:
                        try:
                            winreg.DeleteValue(key, "ProxyServer")
                            print("📋 删除ProxyServer（原为空）")
                        except FileNotFoundError:
                            print("📋 ProxyServer已不存在")
                else:
                    try:
                        winreg.DeleteValue(key, "ProxyServer")
                        print("📋 删除ProxyServer（无原始值）")
                    except FileNotFoundError:
                        print("📋 ProxyServer已不存在")
                
                # 恢复ProxyOverride设置
                if 'ProxyOverride' in self.original_settings:
                    original_override = self.original_settings['ProxyOverride']
                    if original_override:
                        winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, original_override)
                        print(f"📋 恢复ProxyOverride: {original_override}")
                    else:
                        try:
                            winreg.DeleteValue(key, "ProxyOverride")
                            print("📋 删除ProxyOverride（原为空）")
                        except FileNotFoundError:
                            print("📋 ProxyOverride已不存在")
                else:
                    try:
                        winreg.DeleteValue(key, "ProxyOverride")
                        print("📋 删除ProxyOverride（无原始值）")
                    except FileNotFoundError:
                        print("📋 ProxyOverride已不存在")
                
                print("✅ 注册表恢复完成")
                
            finally:
                winreg.CloseKey(key)
            
            # 刷新系统设置
            try:
                print("🔄 刷新系统代理设置...")
                
                # 通知系统代理设置已更改
                INTERNET_OPTION_REFRESH = 37
                INTERNET_OPTION_SETTINGS_CHANGED = 39
                
                wininet = ctypes.windll.wininet
                result1 = wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
                result2 = wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
                
                if result1 and result2:
                    print("✅ 系统代理设置已刷新")
                else:
                    print("⚠️  系统代理刷新可能不完整")
                
            except Exception as e:
                print(f"⚠️  刷新系统设置失败: {e}")
                print("💡 建议手动重启浏览器以使设置生效")
            
            # 验证恢复是否成功
            try:
                verify_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    registry_path,
                    0, winreg.KEY_READ
                )
                
                verify_enable = winreg.QueryValueEx(verify_key, "ProxyEnable")[0]
                expected_enable = self.original_settings.get('ProxyEnable', 0)
                
                winreg.CloseKey(verify_key)
                
                if verify_enable == expected_enable:
                    print("✅ 代理恢复验证成功")
                    print("💡 如果浏览器代理仍未恢复，请重启浏览器")
                    return True
                else:
                    print(f"⚠️  代理恢复验证失败 - 当前Enable: {verify_enable}, 期望: {expected_enable}")
                    return False
                    
            except Exception as e:
                print(f"⚠️  代理恢复验证失败: {e}")
                return True  # 恢复可能成功，但验证失败
            
        except ImportError:
            print("❌ 无法导入Windows注册表模块")
            return False
        except Exception as e:
            print(f"❌ Windows代理恢复失败: {e}")
            print("💡 请尝试:")
            print("   1. 以管理员身份运行")
            print("   2. 手动恢复代理设置")
            print("   3. 重启浏览器")
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
            print(f"🚀 准备启动mitmweb服务...")
            
            # 检查脚本文件是否存在
            if not os.path.exists(self.script_path):
                print(f"❌ 找不到脚本文件: {self.script_path}")
                return False
            
            print(f"✅ 脚本文件存在: {self.script_path}")
            
            # 检查mitmweb是否可用
            try:
                result = subprocess.run(["mitmweb", "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✅ mitmweb版本: {result.stdout.strip()}")
                else:
                    print(f"⚠️  mitmweb版本检查失败: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("⚠️  mitmweb版本检查超时")
            except FileNotFoundError:
                print("❌ 找不到mitmweb命令，请确保已安装mitmproxy")
                print("💡 安装命令: pip install mitmproxy")
                return False
            
            # 检查端口是否被占用
            if self._is_port_in_use(self.port):
                print(f"⚠️  端口 {self.port} 已被占用，尝试终止占用进程...")
                self._kill_port_process(self.port)
                time.sleep(2)
                
                if self._is_port_in_use(self.port):
                    print(f"❌ 端口 {self.port} 仍被占用，无法启动服务")
                    return False
            
            if self._is_port_in_use(self.port + 1):
                print(f"⚠️  Web端口 {self.port + 1} 已被占用，尝试终止占用进程...")
                self._kill_port_process(self.port + 1)
                time.sleep(2)
            
            # 构建启动命令
            cmd = [
                "mitmweb",
                "-s", self.script_path,
                "--listen-port", str(self.port),
                "--web-port", str(self.port + 1),
                "--no-web-open-browser"  # 不自动打开浏览器
            ]
            
            # Windows特定设置
            if platform.system() == "Windows":
                # 在Windows上使用CREATE_NEW_PROCESS_GROUP
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
                preexec_fn = None
            else:
                creation_flags = 0
                preexec_fn = os.setsid
            
            print(f"🔧 启动命令: {' '.join(cmd)}")
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags if platform.system() == "Windows" else 0,
                preexec_fn=preexec_fn
            )
            
            print(f"📋 进程ID: {self.process.pid}")
            
            # 等待服务启动并检查状态
            for i in range(10):  # 最多等待10秒
                time.sleep(1)
                
                # 检查进程是否还在运行
                if self.process.poll() is not None:
                    stdout, stderr = self.process.communicate()
                    print(f"❌ mitmweb进程已退出，返回码: {self.process.returncode}")
                    print(f"📄 标准输出: {stdout.decode('utf-8', errors='ignore')}")
                    print(f"📄 错误输出: {stderr.decode('utf-8', errors='ignore')}")
                    return False
                
                # 检查端口是否开始监听
                if self._is_port_listening(self.port):
                    print(f"✅ 代理端口 {self.port} 已开始监听")
                    break
                    
                print(f"⏳ 等待服务启动... ({i+1}/10)")
            else:
                print("❌ 服务启动超时")
                self.stop()
                return False
            
            # 检查Web界面端口
            for i in range(5):  # 最多等待5秒
                time.sleep(1)
                if self._is_port_listening(self.port + 1):
                    print(f"✅ Web界面端口 {self.port + 1} 已开始监听")
                    break
                print(f"⏳ 等待Web界面启动... ({i+1}/5)")
            
            # 验证服务是否正常工作
            try:
                import requests
                response = requests.get(f"http://127.0.0.1:{self.port + 1}", timeout=5)
                if response.status_code == 200:
                    print("✅ Web界面响应正常")
                else:
                    print(f"⚠️  Web界面响应异常，状态码: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Web界面验证失败: {e}")
            
            print(f"🎉 mitmweb服务启动成功!")
            print(f"📡 代理地址: 127.0.0.1:{self.port}")
            print(f"🌐 Web界面: http://127.0.0.1:{self.port + 1}")
            print("💡 提示: 请确保浏览器已设置代理")
            
            return True
                
        except Exception as e:
            print(f"❌ 启动mitmweb时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except Exception:
            return False
    
    def _is_port_listening(self, port: int) -> bool:
        """检查端口是否在监听"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except Exception:
            return False
    
    def _kill_port_process(self, port: int) -> None:
        """终止占用指定端口的进程"""
        try:
            if platform.system() == "Windows":
                # Windows下查找并终止占用端口的进程
                result = subprocess.run(
                    ["netstat", "-ano"], 
                    capture_output=True, text=True, timeout=10
                )
                
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                subprocess.run(["taskkill", "/F", "/PID", pid], 
                                             capture_output=True, timeout=5)
                                print(f"✅ 已终止进程 PID: {pid}")
                            except Exception as e:
                                print(f"⚠️  终止进程失败: {e}")
            else:
                # Linux/macOS下终止占用端口的进程
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"], 
                    capture_output=True, text=True, timeout=10
                )
                
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            subprocess.run(["kill", "-9", pid], timeout=5)
                            print(f"✅ 已终止进程 PID: {pid}")
                        except Exception as e:
                            print(f"⚠️  终止进程失败: {e}")
                            
        except Exception as e:
            print(f"⚠️  查找端口占用进程失败: {e}")
    
    def stop(self) -> bool:
        """停止mitmweb服务"""
        try:
            print("🛑 正在停止mitmweb服务...")
            
            if self.process and self.process.poll() is None:
                print(f"📋 终止进程 PID: {self.process.pid}")
                
                if platform.system() == "Windows":
                    # Windows下使用taskkill强制终止进程树
                    try:
                        subprocess.run([
                            "taskkill", "/F", "/T", "/PID", str(self.process.pid)
                        ], capture_output=True, timeout=10)
                        print("✅ 使用taskkill终止进程")
                    except Exception as e:
                        print(f"⚠️  taskkill失败: {e}")
                        # 备用方法
                        try:
                            self.process.terminate()
                            print("✅ 使用terminate终止进程")
                        except Exception as e2:
                            print(f"⚠️  terminate失败: {e2}")
                else:
                    # Linux/macOS下终止进程组
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                        print("✅ 发送SIGTERM信号")
                    except Exception as e:
                        print(f"⚠️  发送SIGTERM失败: {e}")
                        self.process.terminate()
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=5)
                    print("✅ 进程已正常退出")
                except subprocess.TimeoutExpired:
                    print("⚠️  进程未在5秒内退出，强制终止...")
                    
                    if platform.system() == "Windows":
                        try:
                            subprocess.run([
                                "taskkill", "/F", "/T", "/PID", str(self.process.pid)
                            ], capture_output=True, timeout=5)
                            print("✅ 强制终止成功")
                        except Exception as e:
                            print(f"⚠️  强制终止失败: {e}")
                            try:
                                self.process.kill()
                                print("✅ 使用kill终止进程")
                            except Exception as e2:
                                print(f"⚠️  kill失败: {e2}")
                    else:
                        try:
                            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                            print("✅ 发送SIGKILL信号")
                        except Exception as e:
                            print(f"⚠️  发送SIGKILL失败: {e}")
                            self.process.kill()
                
                # 额外清理：终止可能残留的mitmweb进程
                self._cleanup_mitmweb_processes()
                
                print("✅ mitmweb服务已停止")
                return True
            else:
                print("ℹ️  mitmweb服务未运行")
                # 仍然尝试清理可能的残留进程
                self._cleanup_mitmweb_processes()
                return True
                
        except Exception as e:
            print(f"❌ 停止mitmweb时发生错误: {e}")
            # 尝试清理残留进程
            self._cleanup_mitmweb_processes()
            return False
    
    def _cleanup_mitmweb_processes(self) -> None:
        """清理可能残留的mitmweb进程"""
        try:
            if platform.system() == "Windows":
                # Windows下查找并终止所有mitmweb进程
                result = subprocess.run([
                    "tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"
                ], capture_output=True, text=True, timeout=10)
                
                # 查找包含mitmweb的进程
                for line in result.stdout.split('\n'):
                    if 'mitmweb' in line.lower():
                        parts = line.split(',')
                        if len(parts) >= 2:
                            pid = parts[1].strip('"')
                            try:
                                subprocess.run([
                                    "taskkill", "/F", "/PID", pid
                                ], capture_output=True, timeout=5)
                                print(f"✅ 清理残留进程 PID: {pid}")
                            except Exception:
                                pass
            else:
                # Linux/macOS下查找并终止mitmweb进程
                result = subprocess.run([
                    "pgrep", "-f", "mitmweb"
                ], capture_output=True, text=True, timeout=10)
                
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            subprocess.run(["kill", "-9", pid], timeout=5)
                            print(f"✅ 清理残留进程 PID: {pid}")
                        except Exception:
                            pass
                            
        except Exception as e:
            print(f"⚠️  清理残留进程失败: {e}")


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
