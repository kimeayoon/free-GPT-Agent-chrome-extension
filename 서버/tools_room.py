# -*- coding: utf-8 -*-
"""방 이름 짓기 — 이름표.

새 방은 이름이 비어 있다. 에이전트가 무슨 일인지 알아낸 뒤 이름을 붙인다.
사람이 나중에 창에서 두 번 눌러 고칠 수 있다.
"""

import rooms


def name_room(name: str = "", **_):
    """지금 방에 이름을 붙인다."""
    이름 = (name or "").strip()
    if not 이름:
        raise ValueError('"이름" 이 비었습니다. 무슨 일인지 짧게 적으세요.')
    if len(이름) > 40:
        raise ValueError("너무 깁니다. 40자 안쪽으로 줄이세요.")

    방 = rooms.지금방()
    if 방 is None:
        raise ValueError("고른 방이 없습니다. 사용자에게 방을 만들라고 말하세요.")

    바뀐것 = rooms.방이름바꾸기(방["쪽번호"], 이름)
    return {"이름": 바뀐것["이름"], "action": "이름 붙임"}


등록된도구 = {
    "name_room": name_room,
}
