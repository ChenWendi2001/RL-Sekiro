import logging
import time

import win32con
import win32gui
from icecream import ic

from env.actions import Actor
from env.env_config import GAME_NAME

if __name__ == "__main__":
    # ic.disable()
    logging.basicConfig(level=logging.DEBUG)

    handle = win32gui.FindWindow(0, GAME_NAME)
    if handle == 0:
        logging.critical(f"can't find {GAME_NAME}")
        raise RuntimeError()

    # restore window
    win32gui.SendMessage(handle, win32con.WM_SYSCOMMAND,
                         win32con.SC_RESTORE, 0)
    # focus on window
    win32gui.SetForegroundWindow(handle)
    time.sleep(0.5)

    actor = Actor(handle)

    actor.envAction("resume", action_delay=True)
    actor.envAction("focus", action_delay=True)

    actor.agentAction("attack", action_delay=True)
    actor.agentAction("defense", action_delay=True)
    actor.agentAction("dodge", action_delay=True)
    actor.agentAction("jump", action_delay=True)

    actor.envAction("revive", action_delay=True)
    actor.envAction("pause")
