import pyautogui
import time
import os

print('Opening Edge...')
url = 'https://mail.google.com/mail/?view=cm&fs=1&to=test@example.com&su=Test&body=Hello'
os.system(f'start msedge "{url}"')
print('Waiting 6 seconds...')
time.sleep(6)
print('Pressing tab twice to ensure focus...')
pyautogui.press('tab', presses=2, interval=0.1)
print('Pressing Ctrl+Enter...')
pyautogui.hotkey('ctrl', 'enter')
print('Done!')
