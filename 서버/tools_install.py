# -*- coding: utf-8 -*-
"""받아오기 요청 나물 — 도토리.

무엇을 어디서 받아 어디에 놓을지 사람에게 보여주고 허락을 받는다.
허락 전에는 아무것도 내려받지 않는다.
"""

import installer


def request_install(what: str = "", source: str = "pip", why: str = "",
                    index: str = "", action: str = "깔기", **_):
    """받아오기를 요청하거나, 허락 뒤 결과를 확인한다."""
    return installer.요청하기(what, source, why, index, action)


등록된도구 = {
    "request_install": request_install,
}
