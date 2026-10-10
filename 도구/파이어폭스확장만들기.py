# -*- coding: utf-8 -*-
"""공유 소스로 Firefox 임시 확장 XPI를 만든다(외부 다운로드 없음)."""

import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


확장칸 = Path(__file__).resolve().parent.parent / "확장"
결과 = Path(__file__).resolve().parent / "파이어폭스확장.xpi"
설명 = json.loads((확장칸 / "manifest.json").read_text(encoding="utf-8"))
설명["permissions"] = [p for p in 설명["permissions"] if p != "sidePanel"]
설명["background"] = {"scripts": ["background.js"]}
설명.pop("side_panel", None)
설명.pop("commands", None)
설명["sidebar_action"] = {"default_panel": "panel.html", "default_title": "로컬 에이전트"}
설명["browser_specific_settings"] = {"gecko": {"id": "local-agent@example.org"}}

with ZipFile(결과, "w", ZIP_DEFLATED) as 묶음:
    묶음.writestr("manifest.json", json.dumps(설명, ensure_ascii=False, indent=2))
    for 파일 in 확장칸.iterdir():
        if 파일.suffix in {".js", ".html", ".css", ".png", ".svg"}:
            묶음.write(파일, 파일.name)
print(결과)
