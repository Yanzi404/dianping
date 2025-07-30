import time

import pyautogui


def get_active_window_region():
    """
    获取当前活动窗口的区域坐标
    注意: 这个功能需要额外库支持，如 pygetwindow
    """
    screen_width, screen_height = pyautogui.size()
    return 0, 0,int(screen_width/3), screen_height

def scroll(scroll_count=5, scroll_pause=1, read_region=None):
    """
    模拟下滑操作并读取屏幕文本

    参数:
    - scroll_count: 下滑次数
    - scroll_pause: 每次下滑后的暂停时间(秒)
    - read_region: 要读取文本的区域 (left, top, width, height)
    """
    # 确保有足够时间将鼠标移动到安全位置
    time.sleep(2)

    # 如果没有指定读取区域，尝试获取活动窗口区域

    screen_width, screen_height = pyautogui.size()
    read_region = (0, 0,int(screen_width/3), screen_height)

    for i in range(scroll_count):
        print(f"\n--- 第 {i + 1} 次下滑 ---")
        try:
            # 截取指定区域的屏幕
            # screenshot = pyautogui.screenshot(region=read_region)
            # 可以保存截图用于调试
            # screenshot.save(f'screenshot_{i}.png')
            # 模拟下滑操作 (向下滚动鼠标滚轮)
            pyautogui.scroll(-50)  # 负值表示向下滚动
            # 等待页面稳定
            time.sleep(scroll_pause)
        except Exception as e:
            print(f"第 {i + 1} 次操作出错: {e}")
            break


if __name__ == "__main__":
    print("准备开始自动下滑并读取文本...")
    print("请在5秒内切换到目标应用窗口...")
    time.sleep(5)

    try:
        scroll(scroll_count=99999, scroll_pause=1)
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        print("操作结束")
