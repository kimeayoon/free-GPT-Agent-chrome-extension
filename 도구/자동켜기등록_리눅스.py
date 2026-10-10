# -*- coding: utf-8 -*-
"""Linux 데스크톱 Chrome/Chromium/Firefox용 Native Messaging 등록."""

import argparse
import json
import shlex
import sys
from pathlib import Path


이름 = "com.local_agent.server"
확장칸 = Path(__file__).resolve().parent.parent / "확장"
파이어폭스아이디 = "local-agent@example.org"
브라우저폴더 = {
    "chrome": Path.home() / ".config/google-chrome",
    "chromium": Path.home() / ".config/chromium",
    "firefox": Path.home() / ".mozilla/native-messaging-hosts",
}


def 확장아이디찾기(브라우저):
    """브라우저에 이미 불러온 이 프로젝트 확장만 찾는다."""
    찾음 = set()
    기본 = 브라우저폴더[브라우저]
    for 파일 in (*기본.glob("*/Preferences"), *기본.glob("*/Secure Preferences")):
        try:
            내용 = json.loads(파일.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for 번호, 값 in 내용.get("extensions", {}).get("settings", {}).items():
            자리 = 값.get("path") if isinstance(값, dict) else None
            if 자리 and Path(자리).expanduser().resolve() == 확장칸.resolve():
                찾음.add(번호)
    return sorted(찾음)


def 등록(브라우저, 수동아이디="", 작업폴더=""):
    if sys.platform != "linux":
        raise SystemExit("Linux에서 실행하세요.")
    실행파일 = 확장칸.parent / "서버" / "자동켜기" / f"agent_host_{브라우저}.sh"
    if 브라우저 == "firefox":
        아이디들 = [파이어폭스아이디]
        목적지 = 브라우저폴더[브라우저] / (이름 + ".json")
        허용 = {"allowed_extensions": 아이디들}
    else:
        아이디들 = [수동아이디] if 수동아이디 else 확장아이디찾기(브라우저)
        if not 아이디들 or any(len(i) != 32 or not all("a" <= c <= "p" for c in i) for i in 아이디들):
            raise SystemExit("확장 ID를 못 찾았습니다. 확장을 불러온 뒤 --id <32자리 ID>로 다시 등록하세요.")
        목적지 = 브라우저폴더[브라우저] / "NativeMessagingHosts" / (이름 + ".json")
        허용 = {"allowed_origins": [f"chrome-extension://{i}/" for i in 아이디들]}

    설명 = {"name": 이름, "description": "로컬 에이전트 서버 자동 켜기",
            "path": str(실행파일), "type": "stdio", **허용}
    작업폴더 = Path(작업폴더).expanduser().resolve() if 작업폴더 else 확장칸.parent.resolve()
    if not 작업폴더.is_dir() or 작업폴더 in (Path("/"), Path.home().resolve()):
        raise SystemExit("--workspace는 존재하는 프로젝트 폴더 하나여야 합니다(홈 전체·/ 불가).")
    if 목적지.exists():
        옛것 = json.loads(목적지.read_text(encoding="utf-8"))
        if 옛것.get("name") != 이름 or Path(옛것.get("path", "")).resolve() != 실행파일.resolve():
            raise SystemExit(f"다른 프로그램의 등록을 덮지 않습니다: {목적지}")

    실행파일.write_text("#!/bin/sh\nexport LOCAL_AGENT_WORKSPACE=" + shlex.quote(str(작업폴더))
                       + "\nexec " + shlex.quote(sys.executable)
                       + " -X utf8 " + shlex.quote(str(실행파일.with_name("agent_host.py")))
                       + ' "$@"\n', encoding="utf-8")
    실행파일.chmod(0o700)
    목적지.parent.mkdir(parents=True, exist_ok=True)
    목적지.write_text(json.dumps(설명, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"등록됨: {브라우저} / {목적지}")


if __name__ == "__main__":
    인자 = argparse.ArgumentParser()
    인자.add_argument("--browser", choices=브라우저폴더, required=True)
    인자.add_argument("--id", default="", help="Chrome/Chromium의 확장 ID를 직접 지정")
    인자.add_argument("--workspace", default="", help="에이전트가 작업할 프로젝트 폴더 하나")
    값 = 인자.parse_args()
    등록(값.browser, 값.id, 값.workspace)
