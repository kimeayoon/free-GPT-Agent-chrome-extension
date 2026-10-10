# -*- coding: utf-8 -*-
"""열매 — MCP 서버 창구 하나.

나물은 하나만 늘리고, 어느 서버의 어느 기능인지는 인자로 고른다.

  짓 없이            붙여 둔 서버 목록
  어디 blender       그 서버가 주는 기능 목록
  어디 … / 무엇 …     기능 부르기
  짓 심기            새 서버 붙이기 요청 (사용자 승인을 받는다)
  짓 뽑기            붙여 둔 서버 지우기
"""

import json

import installer
import mcp_client


def _인자풀기(값):
    """'값' 으로 온 것을 사전으로 만든다."""
    if 값 in (None, ""):
        return {}
    if isinstance(값, dict):
        return 값
    글 = str(값).strip()
    try:
        푼것 = json.loads(글)
    except ValueError:
        raise ValueError(
            "'값' 은 JSON 한 덩어리여야 합니다. 예) 값《 {\"size\": 2} 》"
        )
    if not isinstance(푼것, dict):
        raise ValueError("'값' 은 중괄호로 시작하는 사전이어야 합니다.")
    return 푼것


def _대답간추리기(결과: dict) -> dict:
    """MCP 대답에서 사람이 읽을 것만 뽑는다."""
    조각들 = 결과.get("content") or []
    글들 = []
    다른것 = []
    for 조각 in 조각들:
        갈래 = 조각.get("type")
        if 갈래 == "text":
            글들.append(조각.get("text", ""))
        elif 갈래 in ("image", "audio"):
            다른것.append(f"({갈래} — 글이 아니라 그대로 보여줄 수 없습니다)")
        else:
            다른것.append(json.dumps(조각, ensure_ascii=False)[:500])

    답 = {"나온것": "\n".join(글들 + 다른것)[:8000] or "(나온 것 없음)"}
    if 결과.get("isError"):
        답["좋음"] = False
        답["안내"] = "그쪽에서 실패했다고 합니다. 나온것을 읽고 인자를 고치세요."
    else:
        답["좋음"] = True
    return 답


def mcp_call(where: str = "", what: str = "", value=None,
             action: str = "", command: str = "", cwd: str = "", why: str = "", **_):
    """MCP 서버를 보거나 부르거나 새로 붙인다."""
    짓 = (action or "").strip()

    # ── 새 서버 붙이기 요청 (승인 받는다) ──────────────────────
    if 짓 == "심기":
        이름 = mcp_client.이름검사(where)
        조각 = mcp_client.명령쪼개기(command)
        return installer.바깥도구요청(이름, 조각, cwd, why)

    if 짓 == "뽑기":
        이름 = mcp_client.이름검사(where)
        mcp_client.지우기(이름)
        return {"이름": 이름, "한일": "뽑았습니다"}

    if 짓 and 짓 not in ("보기",):
        raise ValueError("짓 은 심기 · 뽑기 중 하나입니다. 그냥 볼 때는 비우세요.")

    # ── 목록 보기 ────────────────────────────────────────────
    if not (where or "").strip():
        것들 = mcp_client.상태들()
        return {
            "서버들": 것들,
            "개수": len(것들),
            "안내": (
                "어디 에 이름을 적으면 그 서버의 기능 목록이 나옵니다."
                if 것들 else
                "붙여 둔 것이 없습니다. 짓 심기 로 요청하세요. "
                "예) 나물 열매 / 짓 심기 / 어디 blender / "
                "불 python -m blender_mcp / 왜 짧은 이유"
            ),
        }

    이름 = mcp_client.이름검사(where)
    서버 = mcp_client.챙기기(이름)

    # ── 기능 목록 ────────────────────────────────────────────
    if not (what or "").strip():
        기능들 = []
        for 것 in 서버.도구들:
            기능들.append({
                "무엇": 것.get("name"),
                "설명": (것.get("description") or "")[:200],
                "넣을것": sorted((것.get("inputSchema") or {})
                               .get("properties", {}).keys()),
            })
        return {
            "이름": 이름, "상태": "붙음", "개수": len(기능들), "기능들": 기능들,
            "안내": "부를 때는 무엇 에 기능 이름, 값 에 JSON 한 덩어리를 넣으세요.",
        }

    # ── 실제로 부르기 ────────────────────────────────────────
    기능 = what.strip()
    있는것 = [t.get("name") for t in 서버.도구들]
    if 기능 not in 있는것:
        raise ValueError(
            f"'{이름}' 에 그런 기능이 없습니다: {기능}. "
            f"있는 것: {', '.join(있는것[:25]) or '(없음)'}"
        )

    결과 = 서버.부르기(기능, _인자풀기(value))
    return {"이름": 이름, "무엇": 기능, **_대답간추리기(결과)}


등록된도구 = {
    "mcp_call": mcp_call,
}
