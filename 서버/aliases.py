# -*- coding: utf-8 -*-
"""바깥(대화창)에 노출되는 낱말을 전부 여기서 정한다.

원칙: 글자 단위 암호가 아니라 낱말 단위 1:1 교체.
      글자를 섞으면 '고치기'의 앞/뒤 문자열이 한 글자만 틀려도 전부 실패한다.

주제는 나물. 컴퓨터와 관련된 낱말을 쓰지 않는다.
이름 때문에 또 문제가 생기면 이 파일과 확장/protocol.js, 문서/프로토콜.md 만 고친다.
"""

# ── 1. 도구 이름 : 바깥이름 → 내부함수이름 ──────────────────────
공개이름 = {
    "열무":   "read_file",
    "가지":   "list_files",
    "미나리": "search_files",
    "부추":   "replace_text",
    "상추":   "write_file",
    "냉이":   "create_dir",
    "시금치": "delete_file",
    "도라지": "run_command",
    "감자":   "plan_set",
    "고구마": "plan_update",
    "토란":   "plan_get",

    "더덕":   "read_memory",
    "우엉":   "write_memory",
    "미역":   "restore_file",
    "숙주":   "resume",
    "도토리": "request_install",
    "이름표": "name_room",
    "씨앗":   "make_venv",
    "두릅":   "run_bg",
    "고사리": "watch_bg",
    "갓":     "move_file",
    "쑥":     "append_file",
    "버섯":   "file_info",
    "칡":     "git_do",
    "취":     "web_read",
    "열매":   "mcp_call",
    "배추":   "set_timer",
    "무":     "watch_timer",
    "콩":     "spawn_worker",
    "팥":     "watch_worker",
    "당근":   "board_set",
    # 눈과 손 — 그림 붙이기 · 화면 보기 · 키보드 마우스(화면 · 입력은 사용자 허락을 받아야 쓴다)
    "호박":   "attach_image",
    "오이":   "eye",
    "마늘":   "hand",
}

# ── 2. 들어오는 인자 : 바깥이름 → 파이썬 인자이름 ───────────────
인자키 = {
    "밭":   "path",
    "속":   "content",
    "앞":   "old",
    "뒤":   "new",
    "번":   "count",
    "불":   "command",
    "자리": "cwd",
    "참기": "timeout",
    "향":   "query",
    "갈래": "extensions",
    "깊이": "depth",
    "최대": "max_results",
    "첫줄": "start_line",
    "끝줄": "end_line",
    "일":   "task",
    "차례": "steps",
    "몇":   "step",
    "상태": "status",
    "쪽":   "note",
    "무엇": "what",
    "어디서": "source",
    "왜":   "why",
    "이름": "name",
    "덧":   "append",
    "때":   "when",
    "판":   "version",
    "번호": "job",
    "새밭": "dest",
    "짓":   "action",
    "창고": "index",
    "주소": "url",
    "어디": "where",
    "값":   "value",
    "간격": "interval",
    "말":   "message",
    "조건": "condition",
    "역할": "role",
    "먼저": "after",
    "항목": "items",
    "새몇": "to_step",
    # 눈과 손
    "창":     "window",
    "곳":     "point",
    "끝곳":   "end_point",
    "영역":   "region",
    "키":     "keys",
    "배율":   "scale",
    "장수":   "frames",
    "틈":     "gap_ms",
    "오래":   "hold_ms",
    "분":     "minutes",
    "버튼":   "button",
    "최대변": "max_side",
}

# ── 3. 나가는 결과 : 내부이름 → 바깥이름 ────────────────────────
응답키 = {
    "success":       "됨",
    "error":         "탈",
    "path":          "밭",
    "content":       "속",
    "total_lines":   "총줄",
    "start_line":    "첫줄",
    "end_line":      "끝줄",
    "truncated":     "잘림",
    "entries":       "개수",
    "tree":          "모양",
    "query":         "향",
    "count":         "건수",
    "matches":       "걸린것",
    "line":          "줄",
    "text":          "글",
    "action":        "한일",
    "bytes":         "크기",
    "lines":         "줄수",
    "backup":        "보관",
    "replaced":      "바꾼수",
    "changed_lines": "바뀐줄",
    "trash":         "치운곳",
    "command":       "불",
    "cwd":           "자리",
    "exit_code":     "끝번호",
    "ok":            "좋음",
    "timed_out":     "늦음",
    "output":        "나온것",
    "task":          "일",
    "progress":      "진도",
    "steps":         "차례",
    "board":         "판",
    "name":          "이름",
    "status":        "상태",
    "note":          "쪽",
    "version":       "판번호",
    "있음":          "있음",
    "안내":          "안내",
    "backups":       "보관목록",
    "때":            "때",
    "크기":          "크기",
    "줄수":          "줄수",
    "기준자리":      "기준자리",
    "등급":          "등급",
    "지금쓸수있는것": "지금쓸수있는것",
    "기억있음":      "기억있음",
    "최근손댐":      "최근손댐",
    "마지막손댐":    "마지막손댐",
    "상태":          "상태",
    "무엇":          "무엇",
    "어디서":        "어디서",
    "어디에":        "어디에",
    "파이썬":        "파이썬",
    "판목록":        "판목록",
    "일터인가":      "일터인가",
    "일터":          "일터",
    "번호":          "번호",
    "불":            "불",
    "시작":          "시작",
    "끝번호":        "끝번호",
    "총줄":          "총줄",
    "보인줄":        "보인줄",
    "나온것":        "나온것",
    "일들":          "일들",
    "개수":          "개수",
    "한일":          "한일",
    "간곳":          "간곳",
    "칸인가":        "칸인가",
    "더한줄":        "더한줄",
    "늘어난크기":    "늘어난크기",
    "앞머리":        "앞머리",
    "그림크기":      "그림크기",
    "속개수":        "속개수",
    "속목록":        "속목록",
    "짓":            "짓",
    "쪽":            "쪽",
    "확인":          "확인",
    "깔림":          "깔림",
    "판번호":        "판번호",
    "깔린자리":      "깔린자리",
    "창고":          "창고",
    "주소":          "주소",
    "종류":          "종류",
    "글자수":        "글자수",
    "글":            "글",
    "서버들":        "서버들",
    "서버정보":      "서버정보",
    "기능수":        "기능수",
    "기능들":        "기능들",
    "넣을것":        "넣을것",
    "설명":          "설명",
}

내부이름 = {v: k for k, v in 공개이름.items()}


def 등록표만들기(내부도구들: dict) -> dict:
    """{내부이름: 함수} 를 {바깥이름: 함수} 로 바꾼다."""
    표 = {}
    빠진것 = []
    for 바깥, 내부 in 공개이름.items():
        if 내부 in 내부도구들:
            표[바깥] = 내부도구들[내부]
        else:
            빠진것.append(내부)
    if 빠진것:
        raise RuntimeError(f"매핑에 적힌 내부 도구가 없습니다: {빠진것}")
    return 표


def 인자풀기(들어온인자: dict) -> dict:
    """바깥 이름으로 온 인자를 파이썬 인자 이름으로 바꾼다.

    모르는 이름은 그대로 둔다(서버가 '인자가 잘못됐습니다' 로 알려준다).
    """
    return {인자키.get(k, k): v for k, v in 들어온인자.items()}


def 결과포장(값):
    """결과 안의 키 이름을 바깥 이름으로 바꾼다. 중첩된 목록/사전까지 훑는다."""
    if isinstance(값, dict):
        return {응답키.get(k, k): 결과포장(v) for k, v in 값.items()}
    if isinstance(값, list):
        return [결과포장(v) for v in 값]
    return 값
