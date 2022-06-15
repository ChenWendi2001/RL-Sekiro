import ctypes
import logging
import pickle
from datetime import datetime
from typing import Tuple

import numpy as np
import numpy.typing as npt
from icecream import ic
from PIL import Image, ImageGrab
from utils import timeLog

from .env_config import (AGENT_EP_ANCHOR, AGENT_HP_ANCHOR, BOSS_EP_ANCHOR,
                         BOSS_HP_ANCHOR, SCREEN_ANCHOR, SCREEN_SIZE)


class Observer():
    """[summary]
    yield raw observation
    """

    def __init__(self, handle) -> None:
        self.handle: int = handle

        anchor = ctypes.wintypes.RECT()
        ctypes.windll.user32.SetProcessDPIAware(2)
        DMWA_EXTENDED_FRAME_BOUNDS = 9
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.wintypes.HWND(self.handle),
            ctypes.wintypes.DWORD(DMWA_EXTENDED_FRAME_BOUNDS),
            ctypes.byref(anchor), ctypes.sizeof(anchor))
        self.anchor = (anchor.left, anchor.top, anchor.right, anchor.bottom)
        logging.debug(anchor)

        self.timestamp: str = ""

        # HACK: load preset hp & ep
        self.agent_hp_full = pickle.load(
            open("./env/asset/agent-hp-full.pkl", "rb"))
        self.boss_hp_full = pickle.load(
            open("./env/asset/boss-hp-full.pkl", "rb"))
        self.agent_ep_full = pickle.load(
            open("./env/asset/agent-ep-full.pkl", "rb"))
        self.boss_ep_full = pickle.load(
            open("./env/asset/boss-ep-full.pkl", "rb"))

    def __select(self, arr: npt.NDArray, anchor: Tuple) -> npt.NDArray:
        # NOTE: C x H x W
        left, top, right, bottom = anchor
        return arr[:, top:bottom, left:right]

    # @timeLog
    def shotScreen(self) -> npt.NDArray[np.int16]:
        screen_shot = ImageGrab.grab(self.anchor)
        # NOTE: C x H x W, "RGB"
        screen_shot = np.array(screen_shot, dtype=np.int16).transpose(2, 0, 1)
        screen_shot = self.__select(screen_shot, SCREEN_ANCHOR)

        if ic.enabled:
            self.timestamp = datetime.now().strftime("%m-%d_%H-%M-%S")
            Image.fromarray(
                screen_shot.transpose(1, 2, 0).astype(np.uint8)).save(
                f"./debug/screen-shot-{self.timestamp}.png")

        if screen_shot.shape[1:] != SCREEN_SIZE:
            logging.critical("incorrect screenshot")
            raise RuntimeError()

        return screen_shot

    def __calcProperty(self, arr: npt.NDArray[np.int16],
                       target: npt.NDArray[np.int16], threshold, prefix="") -> float:
        """[summary]

        Args:
            arr (npt.NDArray[np.int16]): C x H x W
            target (npt.NDArray[np.int16]): C x H x W
        """
        if ic.enabled:
            Image.fromarray(
                arr.transpose(1, 2, 0).astype(np.uint8), mode="HSV").convert(
                    "RGB").save(f"./debug/{prefix}-{self.timestamp}.png")
        if arr.shape != target.shape:
            logging.critical("incorrect arr shape")
            raise RuntimeError()

        result = np.max(np.abs(target - arr), axis=0) < (threshold * 256)
        if ic.enabled:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(2, 1)
            ax[0].spy(result)
            ax[1].imshow(Image.fromarray(
                arr.transpose(1, 2, 0).astype(np.uint8), mode="HSV").convert("RGB"))
            fig.subplots_adjust(hspace=-0.8)
            plt.savefig(f"./debug/{prefix}-content-{self.timestamp}.png")
            plt.close()
        result = np.sum(result, axis=0) > result.shape[0] / 2

        return 100 * np.sum(result) / result.size

    @timeLog
    def state(self, screen_shot: npt.NDArray[np.int16]) -> \
            Tuple[npt.NDArray[np.uint8], float, float, float, float]:
        """[summary]

        State:
            image           npt.NDArray[np.uint8]
            agent_hp        float
            boss_hp         float
            agent_ep        float
            boss_ep         float
        """
        # NOTE: use HSV
        hsv_screen_shot = np.array(Image.fromarray(
            screen_shot.astype(np.uint8).transpose(1, 2, 0)).convert("HSV"),
            dtype=np.int16).transpose(2, 0, 1)
        agent_hp = self.__calcProperty(
            arr=self.__select(hsv_screen_shot, AGENT_HP_ANCHOR),
            target=self.agent_hp_full, threshold=0.25, prefix="agent-hp")
        boss_hp = self.__calcProperty(
            arr=self.__select(hsv_screen_shot, BOSS_HP_ANCHOR),
            target=self.boss_hp_full, threshold=0.25, prefix="boss-hp")
        logging.info(f"agent hp: {agent_hp:.1f}, boss hp: {boss_hp:.1f}")

        agent_ep = self.__calcProperty(
            self.__select(hsv_screen_shot, AGENT_EP_ANCHOR),
            target=self.agent_ep_full, threshold=0.45, prefix="agent-ep")
        boss_ep = self.__calcProperty(
            self.__select(hsv_screen_shot, BOSS_EP_ANCHOR),
            target=self.boss_ep_full, threshold=0.45, prefix="boss-ep")
        logging.info(f"agent ep: {agent_ep:.1f}, boss ep: {boss_ep:.1f}")

        # TODO: resize screen_shot

        return screen_shot, agent_hp, boss_hp, agent_ep, boss_ep
