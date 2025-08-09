import time
from typing import Optional, Tuple
import pyautogui
from pynput import keyboard

"""
通过pyautogui模拟前端滚动，配合mitmproxy拦截接口解析数据
添加了暂停/继续功能(按空格键控制)
"""


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


def scroll(scroll_count: int = 5, scroll_pause: float = 1, read_region: Optional[Tuple[int, int, int, int]] = None) -> None:
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
                pyautogui.scroll(-200)  # 负值表示向下滚动
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
    print("准备开始自动下滑并读取文本...")
    print("请在5秒内切换到目标应用窗口...")
    time.sleep(5)

    try:
        scroll(scroll_count=99999, scroll_pause=2)
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        print("操作结束")


if __name__ == "__main__":
    # mitmweb -s dianping_interceptor.py
    main()
