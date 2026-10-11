// 화면 글 번역 — 판(옆 창)에 보이는 글은 기본이 영어이고, ⋮ 메뉴의 Language 에서 한국어로 바꿀 수 있다.
//
// 코드 안의 글은 한국어 그대로 두고, 화면에 그려지는 순간(textContent · title · placeholder …)에 번역한다.
// 그래서 새 문구를 더하다가 번역표를 빼먹어도 한국어로 보일 뿐 깨지지 않는다.
//   1) 번역표   : 통째로 같은 글
//   2) 번역규칙 : 숫자 · 이름이 섞인 글(정규식 → 영어 틀, $1 $2 …)
//   3) 조각표   : 긴 문구 조각(위 둘에 안 걸린 문장 속 안내 문구)
// 사용자 자료(파일 이름 · 방 이름 · 목표)는 한국어여도 그대로 둔다 — 조각표에는 자주 쓰는 낱말을 넣지 않는다.

const 언어열쇠 = '언어';

function 지금언어() {
  try {
    const 값 = localStorage.getItem(언어열쇠);
    return 값 === 'ko' ? 'ko' : 'en';
  } catch (e) { return 'en'; }
}

function 언어바꾸기(언어) {
  try { localStorage.setItem(언어열쇠, 언어 === 'ko' ? 'ko' : 'en'); } catch (e) { /* 이번 판에서만 */ }
}

// ── 1) 통째로 같은 글 ────────────────────────────────────────────
const 번역표 = {
  // 칸 이름 · 단추
  '실행 현황': 'Activity', '일할 곳': 'Work folders', '추가한 것 (실행 기록)': 'Run log', '실행 기록': 'Run log', '파일': 'Files',
  '목표': 'Goal', '설정': 'Settings', '메뉴': 'Menu', '일하는 중': 'Working', '멈춰 있음': 'Paused', '대기 중': 'Idle',
  '⏸ 멈춤': '⏸ Pause', '▶ 이어서 하기': '▶ Resume', '자동': 'Auto', '수동': 'Manual', '전체권한': 'Full access',
  '추론 깊게': 'Deep thinking', '추론 ': 'Thinking ', '더 빠르게': 'Faster', '더 스마트하게': 'Smarter',
  '다시 보내기': 'Resend', '대답 다시 받기': 'Get answer again', '결과 다시 보내기': 'Resend result',
  '마지막 결과 다시 보내기': 'Resend last result', '대답 다시 시도': 'Retry answer', '새 대화로 넘기기': 'Move to a new chat',
  '다시 시작': 'Restart', '문제 살펴보기': 'Diagnose', '표시할 칸': 'Visible panes', '이름 바꾸기': 'Rename',
  '일할 폴더 바꾸기': 'Change work folder', '목록에서 빼기': 'Remove from list', '폴더 열기…': 'Open folder…',
  '폴더 고르기': 'Choose folder', '폴더 다시 고르기': 'Choose folder again', '윈도우 창에서 고르기': 'Pick in a Windows dialog',
  '이 폴더에서 새 대화': 'New chat in this folder', '일꾼 멈추기': 'Stop helper', '일꾼 합치기': 'Merge helper',
  '일꾼 다시': 'Rerun helper', '본 폴더에 합치기': 'Merge into the main folder', '새 탭에서': 'in a new tab',
  '이전 대화 ': 'Earlier chat ', '열기': 'Open', '더 불러오기': 'Load more', '읽는 중…': 'Reading…', '(빈 파일)': '(empty file)',
  '파일 되돌리기…': 'Restore file…', '이 파일 탭 닫기': 'Close this file tab', '눌러서 이 파일 보기': 'Click to view this file',
  '서버 확인 중…': 'Checking the server…', '알 수 없음': 'Unknown', '지켜보는 중': 'Watching',
  '이 일을 멈춥니다': 'Stop this job', '눌러서 자세히 보기': 'Click for details', '알림 닫기': 'Dismiss',
  '그만': 'Revoke', '허용': 'Allow', '거부': 'Deny', '이번만 허용': 'Allow once', '이 방에서 항상 허용': 'Always allow in this room',
  '읽기만 허용': 'Allow read-only', '전부 허용': 'Allow all', '새 목표 세우기': 'Set a new goal', '목표 포기': 'Drop goal',
  '되돌리기': 'Undo', '되살리기': 'Restore', '접기': 'Collapse', '닫기': 'Close', '취소': 'Cancel', '확인': 'OK',
  '(이름 짓는 중…)': '(naming…)', '일할 곳을 고르세요': 'Choose a work folder', '(이름 없음)': '(no name)', '(빈 칸)': '(empty)',
  '시킬 일을 적으세요': 'Type a task', '파일 거르기…': 'Filter files…', '보내기': 'Send', '지우기': 'Clear',
  '이 대화에는 아직 일할 방이 없습니다': 'This chat has no work room yet',
  '일할 곳이 없습니다': 'No work folder yet', '걸린 파일이 없습니다': 'No matching files', '방 자료': 'Room data',
  '아직 비어 있습니다.': 'Nothing here yet.', '아직 실행 기록이 없습니다.': 'No run log yet.',
  '할 일': 'To do', '지난 목표': 'Past goals', '단계를 한 줄에 하나씩': 'One step per line',
  '목표 이름 (나중에 보고 알아볼 만큼)': 'Goal name (clear enough to recognize later)',
  '앞 목표를 바꾸는 까닭 (선택)': 'Why you are replacing the current goal (optional)', '접는 까닭 (선택)': 'Why you are dropping it (optional)',
  '＋ 단계 더하기 (Enter)': '＋ Add a step (Enter)',
  // panel.html 의 title · placeholder
  '일할 곳 접기 · 펴기': 'Collapse / expand work folders', '오른쪽 칸 접기 · 펴기': 'Collapse / expand the right column',
  '파일 보기 도구': 'File view tools', '파일 나무 접기 · 펴기': 'Collapse / expand the file tree', '다시 읽기': 'Reload',
  '크게 보기 · 되돌리기': 'Enlarge / restore', '연 파일 모두 닫기': 'Close all open files', '이번 일을 얼마나 했는지': 'How much has been done this time',
  '창을 덮어도 계속 동작하는지 보는 표시': 'Shows whether it keeps working when the window is covered',
  '끌어서 너비 바꾸기': 'Drag to resize', '끌어서 실행 현황 크기 바꾸기': 'Drag to resize Activity',
  '끌어서 일할 곳 크기 바꾸기': 'Drag to resize Work folders', '끌어서 실행 기록 크기 바꾸기': 'Drag to resize Run log',
  '끌어서 나무 너비 바꾸기': 'Drag to resize the tree', '일할 폴더 고르기': 'Choose a work folder',
  '그린 것 · 원본 바꾸기': 'Switch between rendered and raw', '일시정지 · 재개': 'Pause / resume',
  'ChatGPT 모델과 추론 수준 — 더 빠르게 ↔ 더 스마트하게': 'ChatGPT model and thinking level — faster ↔ smarter',
  '모델': 'Model', '추론': 'Thinking', '빠름': 'Fast', '보통': 'Medium', '깊게': 'Deep', 'ChatGPT 에서 모델 목록을 읽는 중…': 'Reading the model list from ChatGPT…',
  '⚠ ChatGPT 모델 목록을 열지 못했습니다': '⚠ Could not open the ChatGPT model list',
  '⚠ ChatGPT 모델을 못 바꿨습니다(쓰는 중이면 끝난 뒤 다시).': '⚠ Could not change the model (if ChatGPT is writing, try again after it finishes).',
  '권한 모드 — 누가 결정할지 정합니다': 'Permission mode — who decides', '준비됨': 'Ready', '도구 실행 중': 'Running a tool',
  // 도구 이름 뜻풀이(protocol.js)
  '내용 보기': 'Read file', '구조 보기': 'List folder', '글자 찾기': 'Search text', '일부 고치기': 'Edit file', '통째로 쓰기': 'Write file',
  '칸 만들기': 'Create folder', '치우기': 'Delete', '돌려보기': 'Run command', '차례 세우기': 'Set plan', '차례 갱신': 'Update plan',
  '차례 보기': 'View plan', '기억 보기': 'Read memory', '기억 적기': 'Write memory', '이어하기': 'Resume', '받아오기 요청': 'Install request',
  '방 이름 짓기': 'Name room', '일터 만들기': 'Create environment', '뒤뜰에 풀어놓기': 'Start long job', '뒤뜰 들여다보기': 'Check long job',
  '옮기기': 'Move', '이어 붙이기': 'Append', '파일 속내 보기': 'Inspect file', '깃': 'Git', '바깥 글 읽기': 'Read web page',
  '바깥 도구 쓰기': 'Use outside tool', '현황판 걸기': 'Pin status board', '그림 붙이기': 'Attach image', '화면 보기': 'View screen',
  '키보드·마우스': 'Keyboard & mouse',
  // 작업 묶음 줄 이름
  '읽음': 'Read', '살핌': 'Looked', '찾음': 'Searched', '생성됨': 'Created', '수정됨': 'Edited', '실행': 'Ran', '기록': 'Log', '도구': 'Tool',
  // content.js 가 판에 보내는 상태 글
  '답을 기다리는 중…': 'Waiting for the answer…', '보내지 못했습니다. ChatGPT 입력칸을 확인해 주세요.': 'Could not send. Please check the ChatGPT input box.',
  '다시 보낼 결과가 없습니다.': 'There is no result to resend.', '보내지 못했습니다. ChatGPT 입력칸에 글이 남아 있는지 보세요.': 'Could not send. Check whether text is left in the ChatGPT input box.',
  '결과를 받지 못했습니다. 다시 요청하세요.': 'No result was received. Please ask again.', '결과를 입력칸에 넣지 못했습니다.': 'Could not put the result into the input box.',
  '설치 결과를 GPT에 전달했습니다.': 'The install result was passed to GPT.', '설치 결과를 입력칸에 넣지 못했습니다.': 'Could not put the install result into the input box.',
  '다시 시작했습니다. 보류된 결과는 [다시 보내기]로 보냅니다.': 'Restarted. Held results are sent with [Resend].', '판이 열려 시작했습니다': 'Started because the panel opened',
  '다시 시도를 눌렀습니다': 'Pressed Retry', '다시 시도 단추를 찾지 못했습니다. ChatGPT 화면에서 직접 눌러 주세요.': 'Could not find the Retry button. Please press it on the ChatGPT page.',
  '⚠ 추론 수준 메뉴를 열지 못했습니다': '⚠ Could not open the thinking-level menu',
  '🔧 일꾼 일을 마쳤습니다. 결과를 대장에게 넘깁니다': '🔧 The helper finished. Passing the result to the main chat.', '🔧 대장이 이 일꾼을 멈췄습니다': '🔧 The main chat stopped this helper',
  '⚠ 일꾼 일감을 보내지 못했습니다': '⚠ Could not send the task to the helper', '이 대화에는 방이 없습니다.': 'This chat has no room.',
  '넘김 파일을 만들지 못했습니다.': 'Could not create the hand-off file.', '넘김 파일을 새 대화에 보냅니다…': 'Sending the hand-off file to a new chat…',
  '⚠ 새 대화 번호가 안 생겼습니다. 판에서 방을 확인하세요.': '⚠ The new chat did not get an ID. Check the room in the panel.',
  '새 대화로 넘겼습니다. 같은 방에서 이어서 합니다.': 'Moved to a new chat. Continuing in the same room.', '앞 시점으로 되돌렸습니다.': 'Rolled back to an earlier point.',
  '⚠ ChatGPT가 대답하지 않습니다 — [대답 다시 받기] 를 눌러 보세요.': '⚠ ChatGPT is not answering — try [Get answer again].',
  'ChatGPT가 대답하지 않아 같은 말을 다시 보냅니다(메시지 편집 → 보내기)…': 'ChatGPT did not answer; resending the same message (edit → send)…',
  '같은 말을 다시 보냈습니다. 답을 기다립니다': 'Resent the same message. Waiting for the answer.',
  '편집으로 다시 보내지 못해 이어서 해 달라고 보냅니다…': 'Could not resend by editing; asking ChatGPT to continue…',
  '정지를 눌러 멈췄습니다. 이어서 하려면 ▶ 또는 [대답 다시 받기] 를 누르세요.': 'Stopped because you pressed stop. Press ▶ or [Get answer again] to continue.',
  '⚠ ChatGPT 답이 비었는데 재촉을 못 보냈습니다 — 입력칸을 보고 [대답 다시 받기] 를 눌러 보세요.': '⚠ ChatGPT’s answer was empty and the nudge could not be sent — check the input box and try [Get answer again].',
  'GPT가 다음 일을 말만 하고 멈췄습니다 — 지금 하라고 보냅니다…': 'GPT only described the next step and stopped — telling it to do it now…',
  'GPT가 결과를 기다리고 있습니다 — 직접 도구로 확인하라고 보냅니다…': 'GPT is waiting for a result — telling it to check with the tools itself…',
  '지금 하라고 보냈습니다. 답을 기다립니다': 'Told it to do it now. Waiting for the answer.', '직접 도구로 확인하라고 보냈습니다. 답을 기다립니다': 'Told it to check with the tools. Waiting for the answer.',
  '⏰ 예약을 못 보냈습니다(입력칸에 글이 있음). 조금 뒤 다시 봅니다': '⏰ Could not send the reminder (the input box has text). Will try again shortly.',
  '⏰ 예약 알림을 보냈습니다. 답을 기다립니다': '⏰ Reminder sent. Waiting for the answer.',
  'ChatGPT가 아직 작성 중이라 마지막 결과를 다시 보내지 않습니다': 'ChatGPT is still writing, so the last result is not resent',
  '지난번 결과가 이미 보내져 있었습니다. 이어서 답을 기다립니다': 'The previous result had already been sent. Waiting for the answer.',
  '결과를 들고 ChatGPT 화면이 준비되기를 기다리는 중': 'Holding the result until the ChatGPT page is ready',
  '결과를 너무 빠르게 보내지 않도록 잠시 기다리는 중': 'Waiting a moment so results are not sent too fast',
  '결과를 보낼 때를 기다리는 중 — ChatGPT가 아직 쓰는 중으로 보입니다': 'Waiting to send the result — ChatGPT still seems to be writing',
  '결과 보내는 중…': 'Sending the result…', '보냈습니다. 답을 기다립니다': 'Sent. Waiting for the answer.',
  '사용자 허용을 기다리는 중… 판에서 허용하면 이어서 결과를 GPT에 보냅니다': 'Waiting for your approval… allow it in the panel and the result goes to GPT.',
  '⚠ 글자가 깨질 위험이 있어 처리하지 않았습니다': '⚠ Skipped because the text could be corrupted', '답변 생성 중…': 'ChatGPT is answering…',
  '작업 요청 준비 중': 'Preparing a tool request', 'GPT 작성 중': 'GPT is writing', '도구 요청을 정리하는 중입니다…': 'Preparing the tool request…',
  '답변을 작성하는 중입니다…': 'Writing the answer…', '다 끝났습니다. 대기 중': 'All done. Idle.', '알 수 없는 문제': 'Unknown problem',
  '서버가 꺼져 있고, 자동 켜기가 등록돼 있지 않습니다. ': 'The server is off and auto-start is not registered. ',
  '로컬 에이전트': 'Local Agent',
  // 판 상태 · 안내
  '자동 진행을 멈춥니다. 하던 도구는 끝까지 합니다.': 'Pause automatic work. A tool that is running will finish.',
  '멈춘 자동 진행을 다시 시작합니다.': 'Resume automatic work.',
  '⚠ ChatGPT 화면이 없습니다. chatgpt.com 을 먼저 열어 주세요.': '⚠ No ChatGPT page found. Open chatgpt.com first.',
  '⚠ ChatGPT 화면과 연결되지 않았습니다. 그 화면을 새로고침해 보세요.': '⚠ Cannot reach the ChatGPT page. Try reloading it.',
  '서버를 자동으로 켜지 못했습니다. 잠시 뒤 다시 시도합니다.': 'Could not start the server automatically. Retrying shortly.',
  '⚠ 서버 꺼짐': '⚠ Server is off', '서버가 다시 연결되었습니다': 'The server is connected again',
  '앞 결과를 보고 이어서 하도록 ChatGPT에 짧게 알립니다.': 'Tells ChatGPT briefly to continue from the last result.',
  '결과를 입력칸에 다시 넣어 보냅니다. 도구는 다시 실행하지 않습니다.': 'Puts the result into the input box again. The tool is not run again.',
  '새 대화로 넘길 파일을 만드는 중…': 'Preparing a hand-off file for a new chat…',
  '새 대화를 열어 지금까지의 내용을 넘기고, 같은 방에서 이어 갑니다.': 'Opens a new chat, hands over what was done so far, and continues in the same room.',
  '이어서 해 달라고 보내는 중…': 'Asking ChatGPT to continue…', '이어서 하라고 보냈습니다. 답을 기다립니다': 'Asked ChatGPT to continue. Waiting for the answer.',
  '마지막 결과를 다시 보내는 중…': 'Resending the last result…', '마지막 결과를 다시 보냈습니다. 답을 기다립니다': 'Resent the last result. Waiting for the answer.',
  '결과를 다시 보내는 중…': 'Resending the result…', '다시 보냈습니다. 답을 기다립니다': 'Resent. Waiting for the answer.',
  '넘기지 못했습니다': 'Could not move to a new chat', '보내지 못했습니다': 'Could not send', '하지 못했습니다': 'Failed',
  '실패했습니다': 'Failed', '멈추지 못했습니다': 'Could not stop it',
  '횟수 제한은 없습니다. 너무 오래 걸린다 싶으면 [⏸ 멈춤] 으로 멈추세요.': 'There is no run limit. If it takes too long, press [⏸ Pause].',
  '아직 동작이 확인되지 않았습니다. ChatGPT 화면을 새로고침해 보세요.': 'No activity seen yet. Try reloading the ChatGPT page.',
  '다른 창으로 덮었다가 다시 열어도 1초 안쪽이면 정상입니다.': 'If covering and reopening the window stays under 1 s, it is working fine.',
  '(⋮ → 다시 시작 을 누르면 다시 잽니다)': '(⋮ → Restart measures again)',
  'GPT가 묻지 않고 모두 처리합니다. 위험한 명령·화면·입력은 그래도 막거나 묻습니다.': 'GPT handles everything without asking. Dangerous commands, screen and input control are still blocked or asked.',
  '결정을 GPT가 처리합니다. 위험한 일만 사용자에게 묻습니다.': 'GPT makes the decisions. It asks you only about risky things.',
  '고치거나 실행하기 전에 늘 사용자에게 묻습니다.': 'It always asks you before editing or running anything.',
  'GPT가 일하는 중…': 'GPT is working…',
  '⏰ 예약': '⏰ Reminders', '이 예약을 멈춥니다': 'Stop this reminder', '⏰ 예약을 멈췄습니다': '⏰ Reminder stopped',
  '허가를 거두었습니다.': 'Permission revoked.', '⚠ 허가를 거두지 못했습니다. 서버가 켜져 있는지 보세요.': '⚠ Could not revoke it. Check that the server is on.',
  '👁 화면 보기 허가 · ': '👁 Screen view allowed · ', '🖱 키보드·마우스 허가 · ': '🖱 Keyboard & mouse allowed · ', '화면 전체': 'Whole screen',
  '요청을 읽지 못함': 'Could not read the request', '… 더 있습니다': '… more', '… 바뀐 줄이 더 있습니다': '… more changed lines',
  '눌러서 접기': 'Click to collapse', '눌러서 결과 보기': 'Click to see the result', '눌러서 다 보기': 'Click to see all',
  '목표 고치기 · 접기 · 새로 세우기': 'Edit · drop · set a new goal',
  '이 대화에는 아직 일할 방이 없습니다. 프로젝트 안의 대화는 열면 바로, 그 밖의 대화는 도구를 처음 쓸 때 만들어집니다.':
    'This chat has no work room yet. Chats inside a project get one right away; other chats get one the first time a tool is used.',
  '오른쪽 [일할 곳] 의 ＋ 로 일할 폴더를 고르세요.': 'Choose a work folder with ＋ in [Work folders] on the right.',
  '아직 한 일이 없습니다. ChatGPT 창에서 시키면 여기에 쌓입니다.': 'Nothing done yet. Give ChatGPT a task and it shows up here.',
  '눌러서 상태 바꾸기 (☐ → ▶ → ☑)': 'Click to change status (☐ → ▶ → ☑)', '눌러서 이름 고치기': 'Click to rename',
  '이 단계 빼기 (되돌리기로 살릴 수 있습니다)': 'Remove this step (you can undo it)',
  '⚠ 목표 이름과 단계를 적어 주세요': '⚠ Enter a goal name and steps',
  '지금 목표는 지난 목표로 보관되고, 이 목표가 지금 목표가 됩니다': 'The current goal is archived and this one becomes the current goal',
  '이 목표를 지금 목표로 되살립니다': 'Make this the current goal again', '눌러서 목표 이름 고치기': 'Click to rename the goal',
  '세운 목표가 없습니다. 아래에서 새로 세우거나 지난 목표를 되살릴 수 있습니다.': 'No goal set. Set a new one below, or restore a past goal.',
  '마지막 수정을 되돌립니다': 'Undo the last edit', '바꾸기 전 모양으로 돌립니다': 'Restore the previous state',
  '볼 수 없습니다.': 'Cannot be shown.', '위 [일할 곳] 의 ＋ 로 폴더를 고르면 그 안이 여기 보입니다.': 'Choose a folder with ＋ in [Work folders] above and its files show up here.',
  '위의 ＋ 로 일할 폴더를 고르세요.': 'Choose a work folder with the ＋ above.',
  '이 ChatGPT 프로젝트의 대화들이 쓸 폴더를 고릅니다': 'Choose the folder the chats of this ChatGPT project will use',
  '⚠ 이 창에 ChatGPT 화면이 없습니다.': '⚠ This window has no ChatGPT page.', '다시 부름': 'Called again',
  '새 대화를 엽니다. 첫 말을 보내면 이 방에 붙습니다.': 'Opening a new chat. It joins this room when you send the first message.',
  '새 대화를 엽니다. 첫 말을 보내면 이 폴더에서 일합니다.': 'Opening a new chat. It will work in this folder when you send the first message.',
  '새 일할 곳을 만들었습니다. ChatGPT에서 일을 시키세요.': 'Created a new work folder. Give ChatGPT a task.',
  '폴더 선택창을 띄웠습니다. 이 프로젝트가 쓸 폴더를 고르세요…': 'A folder dialog opened. Choose the folder this project will use…',
  '폴더 창을 열지 못했습니다. 이 프로젝트 폴더의 전체 경로를 적어 주세요.': 'Could not open the folder dialog. Please type the full path of the project folder.',
  '폴더 선택창을 띄웠습니다. 화면에서 고르세요…': 'A folder dialog opened. Choose a folder…',
  '폴더 창을 열지 못했습니다. 프로젝트 폴더의 전체 경로를 적어 주세요.': 'Could not open the folder dialog. Please type the full path of the project folder.',
  '고르지 않았습니다': 'Nothing was chosen', '폴더를 등록하지 못했습니다': 'Could not register the folder',
  // 승인 · 허가 카드
  '이 일을 해도 될까요?': 'May I do this?', '👁 화면을 보려 합니다': '👁 It wants to look at your screen',
  '🖱 키보드와 마우스를 움직이려 합니다': '🖱 It wants to use the keyboard and mouse',
  '찍은 그림은 ChatGPT에 올라갑니다. 다른 창이나 개인 정보가 겹쳐 보이지 않는지 확인하세요.': 'The captured image is uploaded to ChatGPT. Make sure no other window or personal information is visible.',
  ' 화면 전체라 열린 모든 창이 찍힙니다.': ' It is the whole screen, so every open window is captured.',
  '허용하면 그동안 이 창에 키·마우스 입력이 갑니다. 위의 [그만] 으로 언제든 거둘 수 있습니다.': 'While allowed, keys and mouse input are sent to this window. You can revoke it any time with [Revoke] above.',
  ' 화면 전체라 어느 창에든 입력이 갈 수 있습니다.': ' It is the whole screen, so input can go to any window.',
  '⬇ 인터넷에서 받아 설치하려 합니다': '⬇ It wants to download and install from the internet', '⚠ 이 폴더를 고쳐도 될까요?': '⚠ May it edit this folder?',
  '🧩 낯선 확장이 에이전트를 쓰려 합니다': '🧩 An unknown extension wants to use the agent', '🌐 웹사이트가 에이전트를 쓰려 합니다': '🌐 A website wants to use the agent',
  '허용하면 이 곳이 일할 폴더의 파일을 읽을 수 있습니다. [전부 허용] 은 파일 고치기도 허락합니다. 단, 사용자 승인이 필요한 일은':
    'If allowed, this site can read files in your work folder. [Allow all] also lets it edit files; however, anything that needs your approval',
  '웹사이트에서 할 수 없습니다. 내가 연 곳이 아니면 거부하세요.': 'cannot be done from a website. Deny it if you did not open it.',
  '🌐 웹사이트가 에이전트를 쓰려 합니다 — 위 카드에서 허용할지 정하세요': '🌐 A website wants to use the agent — decide on the card above',
  '아직 없습니다. 모르는 웹사이트가 들어오려 하면 위쪽에 허용 카드가 뜹니다.': 'None yet. If an unknown website tries to connect, an allow card appears at the top.',
  '목록에서 뺍니다(다시 오면 처음처럼 물어봅니다)': 'Removes it from the list (it will be asked again next time)',
  '거부를 풉니다(다시 오면 처음처럼 물어봅니다)': 'Lifts the denial (it will be asked again next time)',
  '확장은 처음 연결된 것을 믿습니다. 웹사이트는 도구 호출과 서버 확인만 할 수 있고, 방·폴더·권한 모드·허락은 바꿀 수 없습니다.':
    'The first extension that connects is trusted. A website can only call tools and ping the server; it cannot change rooms, folders, permission mode or approvals.',
  '허락했습니다. 실행하는 중…': 'Allowed. Running…', '허락하지 않기로 했습니다': 'Denied', '승인 결과를 받지 못했습니다.': 'No approval result was received.',
  '⚠ 결과를 GPT에 전달하지 못했습니다. ChatGPT 화면을 새로고침해 주세요.': '⚠ Could not pass the result to GPT. Please reload the ChatGPT page.',
  '실행했습니다 — 결과를 GPT에게 보냈습니다': 'Done — the result was sent to GPT', '거부했다고 GPT에게 알렸습니다': 'GPT was told you denied it',
  '허락하는 중…': 'Allowing…', '받아오는 중… (오래 걸릴 수 있습니다)': 'Downloading… (this may take a while)', '받지 않기로 했습니다': 'Not downloading',
  '허락하지 않았습니다 — GPT에게 알렸습니다': 'Not allowed — GPT was told',
  '⚠ 설치 결과를 GPT에 전달하지 못했습니다. ChatGPT 화면을 새로고침해 주세요.': '⚠ Could not pass the install result to GPT. Please reload the ChatGPT page.',
  '⚠ 설치 요청 처리 결과를 받지 못했습니다.': '⚠ No result was received for the install request.',
  '⚠ 다시 시작 요청에 응답이 없습니다. ChatGPT 화면을 새로고침해 보세요.': '⚠ No response to the restart request. Try reloading the ChatGPT page.',
  '⚠ ChatGPT 추론 수준을 못 바꿨습니다(쓰는 중이면 끝난 뒤 다시).': '⚠ Could not change the thinking level (if ChatGPT is writing, try again after it finishes).',
  '다시 시도 중…': 'Retrying…', '다시 시작했습니다': 'Restarted', '개발자 도구(F12)의 콘솔에 기록했습니다': 'Written to the developer console (F12)',
  '보냈습니다. 답을 기다립니다…': 'Sent. Waiting for the answer…', '⚠ 보내지 못했습니다. ChatGPT 화면을 확인하세요.': '⚠ Could not send. Check the ChatGPT page.',
  '되돌릴 것이 없습니다: ': 'Nothing to restore: ', '보관된 것이 없습니다.': 'No saved copies.', '되돌렸습니다: ': 'Restored: ',
  '곳 허용': ' sites allowed',
  // 현황판
  '평균 보상': 'Mean reward', '보상 합계': 'Total reward', '한 판 보상': 'Reward per episode', '학습 성공률': 'Success rate',
  '찾아낸 비율': 'Detection rate', '종합 점수': 'Overall score', '학습 손실': 'Training loss', '검증 손실': 'Validation loss',
  '정책 손실': 'Policy loss', '가치 손실': 'Value loss', '정책 변화량': 'Policy change', '갱신 횟수': 'Updates',
  '학습 속도': 'Learning rate', '초당 처리량': 'Throughput', '판 수': 'Episodes',
  '올라가는 중': 'rising', '내려가는 중': 'falling', '좋아지는 중': 'improving', '나빠지는 중': 'getting worse',
  '읽지 못함': 'unreadable', '달리는 중': 'running', '끝남 ✓': 'finished ✓', '끊김 (프로세스가 사라짐)': 'interrupted (process gone)',
  '진행률 표시를 로그에서 못 찾았습니다': 'No progress indicator found in the log', '아직 값이 없습니다': 'No value yet',
  '(비어 있음)': '(empty)', 'GPU 사용률': 'GPU usage', 'GPU 메모리': 'GPU memory', 'GPU 온도': 'GPU temperature',
  '메모리 사용률': 'Memory usage', '디스크 여유': 'Disk free', '이 현황판 치우기': 'Remove this board',
  '이 카드 치우기 (일은 그대로 둡니다)': 'Remove this card (the job keeps running)', '숫자는 GPT가 아니라 서버가 직접 읽은 값입니다': 'These numbers were read by the server, not by GPT',
  // 물음 카드
  '하면 어떻게 되나': 'What happens', '바뀌는 것': 'What changes', '하는 일': 'What it does', '좋은 점': 'Pros', '걱정되는 점': 'Concerns',
  '걸리는 시간': 'Time it takes', '지금 상황': 'Current situation', '왜 묻나': 'Why it asks', '왜 묻는지': 'Why it asks', '묻는 까닭': 'Why it asks',
  '★ ChatGPT 추천: ': '★ ChatGPT recommends: ', '★ 추천: ': '★ Recommended: ', ' ★추천': ' ★ recommended',
  'ChatGPT가 묻습니다 · 몇 개든 고를 수 있습니다': 'ChatGPT is asking · you can pick any number', '닫기 (ChatGPT 창에서 직접 답할 때)': 'Close (when answering in ChatGPT yourself)',
  '직접 적기 (다른 답이나 덧붙일 말)': 'Write your own (another answer or an addition)', '더 자세히 설명해 줘': 'Explain in more detail',
  '이 카드는 설명이 짧습니다. ChatGPT가 배경 · 선택지별 상세 · 추천을 넣어 다시 씁니다.': 'This card is short on detail. ChatGPT will rewrite it with background, per-option details and a recommendation.',
  ' 사용자가 판에서 직접 고른 답입니다': ' This answer was chosen by the user in the panel', '(목록에서는 고르지 않음)': '(nothing picked from the list)',
  '(답하지 않음)': '(no answer)', '줄 세우기 (일 끝나면 보냄)': 'Queue (sent when the job ends)',
  // 설정창
  '허용한 웹사이트 (': 'Allowed websites (', '거부한 곳 (': 'Denied sites (', '믿는 확장 (': 'Trusted extensions (',
  // 서버 · 연결 문구 (background)
  '자동 켜기가 답을 안 했습니다.': 'Auto-start did not respond.',
  '교체': 'replaced', '포기': 'dropped', '끝': 'done', '되살림': 'restored',
  // 승인 카드(서버가 만든 글)
  '일할 폴더 밖을 읽으려 합니다': 'It wants to read outside the work folder', '웹 글을 읽으려 합니다': 'It wants to read a web page',
  '파일 일부를 고치려 합니다': 'It wants to edit part of a file', '파일을 쓰려 합니다': 'It wants to write a file',
  '파일 끝에 글을 덧붙이려 합니다': 'It wants to append to a file', '폴더를 만들려 합니다': 'It wants to create a folder',
  '지우려 합니다': 'It wants to delete', '옮기거나 베끼려 합니다': 'It wants to move or copy',
  '보관해 둔 것으로 되돌리려 합니다': 'It wants to restore from a saved copy', '일터(.venv)를 만들려 합니다': 'It wants to create a virtual environment (.venv)',
  '오래 걸리는 일이 이미 많이 돌고 있습니다': 'Many long jobs are already running', '명령을 실행하려 합니다': 'It wants to run a command',
  '오래 걸리는 일을 시작하려 합니다': 'It wants to start a long job', '깃에 기록하려 합니다': 'It wants to record in git',
  '일꾼을 부르려 합니다': 'It wants to start a helper agent', '비밀 파일 — 내용은 표시하지 않습니다': 'Secret file — content is not shown',
  '이미 있는 파일을 덮어씁니다(원본은 백업됩니다)': 'It overwrites an existing file (the original is backed up)', '새 파일을 만듭니다': 'It creates a new file',
  '실제로 지우지 않고 휴지통 폴더로 옮깁니다': 'Nothing is really deleted; it is moved to the trash folder',
  '오래 걸리는 일로 풀어 둡니다(서버를 껐다 켜도 계속 돕니다)': 'It runs as a long job (it keeps running even if the server restarts)',
  '(정하지 않음)': '(not set)', '(가장 최근)': '(most recent)', '(기본)': '(default)',
};

// ── 2) 숫자 · 이름이 섞인 글 ──────────────────────────────────────
// 시간 조각: '3분 12초' · '45초' · '1시간 3분' → '3m 12s' · '45s' · '1h 3m'
function 시간영어(글) {
  return String(글)
    .replace(/(\d+)\s*시간/g, '$1h').replace(/(\d+)\s*분/g, '$1m').replace(/(\d+)\s*초/g, '$1s')
    .replace(/(\d+m)\s+(\d+s)/g, '$1 $2').replace(/(\d+h)\s+(\d+m)/g, '$1 $2');
}

const 번역규칙 = [
  [/^⚠ 서버에 연결하지 못했습니다: (.*)$/s, '⚠ Could not connect to the server: $1'],
  [/^서버 v(.*) · 도구 (\d+)개$/, 'Server v$1 · $2 tools'],
  [/^서버 꺼짐 — (.*)$/s, 'Server is off — $1'],
  [/^⚠ 서버가 꺼져 있습니다\. (.*)$/s, '⚠ The server is off. $1'],
  [/^서버가 꺼져 있습니다\. (.*)$/s, 'The server is off. $1'],
  [/^○ 멈춤 · (.*)$/s, '○ Paused · $1'],
  [/^경과 (.+) · 도구 (\d+)번 실행$/, (m, a, b) => `Elapsed ${시간영어(a)} · ${b} tool runs`],
  [/^이번 일을 시작한 지 (.+), 도구를 (\d+)번 실행했습니다\.$/, (m, a, b) => `Started ${시간영어(a)} ago; ${b} tool runs so far.`],
  [/^같은 실패가 (\d+)번 이어졌습니다\.$/, 'The same failure repeated $1 times.'],
  [/^화면 최대 멈춤 ([\d.]+)초(.*)$/s, (m, a, b) => `Max page stall ${a}s${b.replace(' · GPT 쓰기 속도 ', ' · GPT writing speed ').replace('자/초', ' chars/s').replace(' (평소 ', ' (usual ')}`],
  [/^ChatGPT 화면에서 가장 오래 멈췄던 시간: ([\d.]+)초$/, 'Longest stall on the ChatGPT page: $1s'],
  [/^돈 횟수 (\d+) · 박동 (\d+)$/, 'Loops $1 · heartbeats $2'],
  [/^(\d+)개$/, '$1'],
  [/^조건 (.*) · (\d+)\/(\d+) · 다음 (.*) — (.*)$/s, 'When $1 · $2/$3 · next $4 — $5'],
  [/^(.+)마다 · (\d+)\/(\d+) · 다음 (.*) — (.*)$/s, (m, a, b, c, d, e) => `Every ${시간영어(a)} · ${b}/${c} · next ${d} — ${e}`],
  [/^(.*)(👁 화면 보기 허가|🖱 키보드·마우스 허가) · (화면 전체|창 .+) · 남은 (.+) · (\d+)번 사용$/s,
    (m, p, 뜻, 곳, 남, 수) => `${뜻 === '👁 화면 보기 허가' ? '👁 Screen view allowed' : '🖱 Keyboard & mouse allowed'} · ${곳 === '화면 전체' ? 'whole screen' : 'window ' + 곳.slice(2)} · ${시간영어(남)} left · used ${수}×`],
  [/^읽은 파일 (\d+)개(.*)$/s, (m, n, 나머지) => 조합요약(m)],
  [/^(찾은 글자|살펴본 것|만든 파일|고친 파일|실행한 명령|차례·기억|깃|그 밖의 도구) (\d+)(개|번)(.*)$/s, (m) => 조합요약(m)],
  [/^실패 (\d+)$/, '$1 failed'],
  [/^… 더 있습니다 \(앞 (\d+)줄만\)$/, '… more (first $1 lines only)'],
  [/^파일 (\d+)개 고쳤습니다$/, 'Edited $1 files'],
  [/^지난 목표 \((\d+)\)$/, 'Past goals ($1)'],
  [/^마지막 수정: (.*)$/s, 'Last edit: $1'],
  [/^되돌리기 \((\d+)\)$/, 'Undo ($1)'],
  [/^✎ GPT가 목표를 바꿨습니다 — (.*)$/s, '✎ GPT changed the goal — $1'],
  [/^지금 목표 '(.*)' \((.*)\) 는 지난 목표로 보관됩니다\.$/s, "The current goal '$1' ($2) will be archived."],
  [/^'(.*)' \((.*)\) 를 접습니다\. 지난 목표로 보관되어 나중에 되살릴 수 있습니다\.$/s, "Dropping '$1' ($2). It is archived and can be restored later."],
  [/^(.*)  —  눌러서 보기$/s, '$1  —  click to view'],
  [/^(.*) · (GPT|사용자)가$/s, (m, a, 누구) => `${a} · by ${누구 === 'GPT' ? 'GPT' : 'user'}`],
  [/^'(.*)' 되살리기로 바뀜$/s, "replaced by restoring '$1'"],
  [/^"(.*)" 가 든 이름이 없습니다\.$/s, 'No file name contains "$1".'],
  [/^(.*) · (\d+)번$/s, '$1 · #$2'],
  [/^이전 대화 (\d+)$/, 'Earlier chat $1'],
  [/^⚠ ChatGPT 화면을 옮기지 못했습니다: (.*)$/s, '⚠ Could not move the ChatGPT page: $1'],
  [/^대화를 엽니다: (.*)$/s, 'Opening chat: $1'],
  [/^⚠ 합치는 중 충돌이 나서 되돌렸습니다: (.*)$/s, '⚠ The merge hit a conflict and was undone: $1'],
  [/^프로젝트 폴더를 정했습니다: (.*)$/s, 'Project folder set: $1'],
  [/^폴더 더함: (.*)$/s, 'Folder added: $1'],
  [/^일할 곳: (.*)$/s, 'Work folder: $1'],
  [/^허용했습니다: (.*)$/s, 'Allowed: $1'],
  [/^거부했습니다: (.*)$/s, 'Denied: $1'],
  [/^(.*) 을\(를\) 허용했습니다$/s, '$1 allowed'],
  [/^(.*) 을\(를\) 거부했습니다$/s, '$1 denied'],
  [/^(.*) 을\(를\) 목록에서 뺐습니다$/s, '$1 removed from the list'],
  [/^허락했습니다: (.*) — GPT에게 알렸습니다$/s, 'Allowed: $1 — GPT was told'],
  [/^받았습니다\. 설치 결과를 GPT에 전달했습니다: (.*)$/s, 'Downloaded. The install result was passed to GPT: $1'],
  [/^⚠ 설치는 끝났지만 실패 결과를 GPT에 전달했습니다: (.*)$/s, '⚠ The install ended with a failure; the result was passed to GPT: $1'],
  [/^추론 수준: (.*)$/s, 'Thinking level: $1'],
  [/^모델을 (.+) 으로 바꾸는 중…$/s, 'Changing the model to $1…'],
  [/^모델: (.*)$/s, 'Model: $1'],
  [/^⚠ 모델을 (.+) 으로 바꾸지 못했습니다$/s, '⚠ Could not change the model to $1'],
  [/^⚠ ChatGPT 에 (.+) 모델이 없습니다$/s, '⚠ ChatGPT has no model named $1'],
  [/^(.+) · (빠름|보통|깊게)$/, (m, 모델, 수준) => `${모델} · ${{ 빠름: 'Fast', 보통: 'Medium', 깊게: 'Deep' }[수준]}`],
  [/^추론 수준을 (.*) 으로 바꾸는 중…$/s, 'Changing the thinking level to $1…'],
  [/^권한 모드를 (.*)\(으\)로 바꿨습니다$/s, 'Permission mode changed to $1'],
  [/^(\d+)개 선택$/, '$1 selected'],
  [/^(.*) 개 선택 · (.*)$/s, '$1 selected · $2'],
  [/^고름 (.*)$/s, 'Picked $1'], [/^덧붙임 (.*)$/s, 'Added $1'], [/^상세 (.*)$/s, 'Details $1'],
  [/^(\d+)줄 세웠습니다 \((\d+)개\)\. 일이 끝나면 보냅니다\.$/, 'Queued $1 ($2). It will be sent when the job ends.'],
  [/^줄 세웠습니다 \((\d+)개\)\. 일이 끝나면 보냅니다\.$/, 'Queued ($1). It will be sent when the job ends.'],
  [/^읽지 못했습니다: (.*)$/s, 'Could not read: $1'],
  [/^⚠ 되돌리지 못했습니다: (.*)$/s, '⚠ Could not restore: $1'],
  [/^(.+) 이\(가\) 중간에 끊겼습니다$/s, '$1 was interrupted'],
  [/^(.+) 끝났습니다 \((.*)\)$/s, (m, a, b) => `${a} finished (${시간영어(b)})`],
  [/^(.+) 이\(가\) 실패했습니다 \(끝번호 (.*)\)$/s, '$1 failed (exit code $2)'],
  [/^실패 \(끝번호 (.*)\)$/s, 'failed (exit code $1)'],
  [/^걸린 시간 (.+)$/s, (m, a) => `took ${시간영어(a)}`],
  [/^남은 시간 (.+)$/s, (m, a) => `time left ${시간영어(a)}`],
  [/^남은 약 (.+) \(추정\)$/s, (m, a) => `about ${시간영어(a)} left (estimate)`],
  [/^약 (.+) \(추정\)$/s, (m, a) => `about ${시간영어(a)} (estimate)`],
  [/^(.+) 동안 출력이 없습니다$/s, (m, a) => `no output for ${시간영어(a)}`],
  [/^명령: (.*)$/s, 'Command: $1'],
  [/^(.*): 진행 표시를 못 찾았습니다$/s, '$1: no progress indicator found'],
  [/^(\d+)개 · (.*)$/s, '$1 · $2'],
  [/^… 오래된 일 (\d+)개는 접어 두었습니다$/, '… $1 older jobs are collapsed'],
  [/^도는 일 (.*)$/s, 'Running jobs $1'], [/^끊기거나 실패한 일 (.*)$/s, 'Interrupted or failed jobs $1'],
  [/^현황판 (.*)$/s, 'Board $1'], [/^원래 이름: (.*)$/s, 'Original name: $1'],
  [/^멈췄습니다: (.*)$/s, 'Stopped: $1'], [/^"(.*)" 을\(를\) 멈춥니다\. 하던 학습은 여기서 끊깁니다\. 멈출까요\?$/s, 'Stop "$1"? The training in progress will be cut off here.'],
  [/^시도 (\d+)번 · (.*)$/s, (m, a, b) => `${a} attempts · ${시간영어(b)}`],
  [/^(.+) 전$/, (m, a) => `${시간영어(a)} ago`],
  [/^(.*) · (.*) 전\)$/s, '$1 · $2 ago)'],
  [/^(\d+)분 동안$/, 'for $1 min'],
  [/^⚠ 추론 수준을 (.+) 으로 바꾸지 못했습니다$/s, '⚠ Could not change the thinking level to $1'],
  [/^🔧 일꾼 "(.*)" 을 새 탭에서 부릅니다\((.*)\)$/s, '🔧 Starting helper "$1" in a new tab ($2)'],
  [/^🔧 일꾼 "(.*)" 결과를 받았습니다$/s, '🔧 Got the result from helper "$1"'],
  [/^🔧 일꾼 "(.*)" 일을 시작했습니다$/s, '🔧 Helper "$1" started working'],
  [/^⚠ 일꾼 탭을 열지 못했습니다: (.*)$/s, '⚠ Could not open the helper tab: $1'],
  [/^(느려져서 )?새 대화로 넘깁니다… 넘김 파일 (.*)$/s, (m, 느림, 나머지) => `${느림 ? 'Slow, so m' : 'M'}oving to a new chat… hand-off file ${나머지.replace('천 자', 'k chars')}`],
  [/^⚠ 대화가 꽉 찼는데 넘기지 못했습니다: (.*)$/s, '⚠ The chat is full but could not be moved: $1'],
  [/^✎ 답 쓰는 속도가 (\d+)번 연속 평소\(([\d.]+)자\/초\)의 3분의 1 밑입니다\(([\d.]+)자\/초\)\. 다음 도구 결과는 새 대화로 넘겨 보냅니다\.$/s,
    '✎ The answer speed was under a third of normal ($2 chars/s) $1 times in a row ($3 chars/s). The next tool result goes to a new chat.'],
  [/^압축 요약을 적었습니다\((\d+)자\)\. 다음 넘김은 이 요약부터 이어 갑니다\.$/, 'Saved a compressed summary ($1 chars). The next hand-off continues from it.'],
  [/^⚠ 넘김 파일을 보내지 못했습니다\((.*)\)\. 판 ⋮ → 새 대화로 넘기기 로 다시 해 보세요\.$/s, '⚠ Could not send the hand-off file ($1). Try ⋮ → Move to a new chat.'],
  [/^⚠ 새 대화를 방에 잇지 못했습니다: (.*)$/s, '⚠ Could not attach the new chat to the room: $1'],
  [/^앞 시점으로 되돌렸습니다\. 기록 (\d+)건을 지웠습니다\.$/, 'Rolled back to an earlier point. Removed $1 log entries.'],
  [/^답이 비어 보입니다 — (\d+)초 더 봅니다$/, 'The answer looks empty — watching $1 s more'],
  [/^⚠ 같은 것이 (\d+)번 같은 이유로 실패했습니다\. 같은 일을 되풀이하는 것 같아 멈췄습니다 — ▶ 로 다시 시작하세요\.$/s,
    '⚠ The same thing failed $1 times for the same reason. It looks like it is going in circles, so it stopped — press ▶ to restart.'],
  [/^⚠ (\d+)판 내리 하나도 성공하지 못했습니다\. 멈췄습니다 — ▶ 로 다시 시작하세요\.$/s, '⚠ Nothing succeeded for $1 rounds in a row. Stopped — press ▶ to restart.'],
  [/^⚠ 문제가 생겨 자동 진행을 멈췄습니다: (.*)$/s, '⚠ A problem occurred and automatic work was paused: $1'],
  [/^⚠ 결과를 보내는 중 문제가 생겨 자동 진행을 멈췄습니다: (.*)$/s, '⚠ A problem occurred while sending the result and automatic work was paused: $1'],
  [/^ChatGPT가 아직 대답하지 않습니다 — (.+) 뒤 다시 보냅니다 \((.*)\)$/s, (m, a, b) => `ChatGPT has not answered yet — resending in ${시간영어(a)} (${b})`],
  [/^⚠ ChatGPT가 (\d+)번 재촉해도 빈 답만 냅니다 — \[대답 다시 받기\] 를 눌러 보세요\.$/s, '⚠ ChatGPT only gives empty answers even after $1 nudges — try [Get answer again].'],
  [/^ChatGPT 답이 비었습니다\(생각 중단됨\)\. 이어서 해 달라고 보냅니다… \((.*)\)$/s, 'ChatGPT’s answer was empty (thinking stopped). Asking it to continue… ($1)'],
  [/^⏰ 예약 시간이 됐습니다\. GPT에게 보냅니다… \((.*)마다\)$/s, (m, a) => `⏰ Reminder is due. Sending it to GPT… (every ${시간영어(a)})`],
  [/^결과를 다시 보낼 때를 기다리는 중 \((.*), (\d+)초\)$/s, 'Waiting to resend the result ($1, $2 s)'],
  [/^결과를 아직 보내지 못했습니다 — (\d+)초 뒤 저절로 다시 보냅니다 \((.*)\)$/s, 'Could not send the result yet — retrying automatically in $1 s ($2)'],
  [/^⚠ 결과를 (\d+)번 다시 보내도 보내지 못했습니다 — \[다시 보내기\] 를 누르면 도구는 다시 실행하지 않고 결과만 보냅니다\.$/s,
    '⚠ Still could not send the result after $1 retries — [Resend] sends only the result without running the tool again.'],
  [/^바구니 오류: (.*)$/s, 'Request error: $1'],
  [/^(.+) 처리 중…$/s, 'Processing $1…'],
  [/^🔧 일꾼 (.*)$/s, '🔧 Helper $1'],
  [/^(\d+|\?)줄$/, '$1 lines'],
  [/^(\d+) \/ (\d+|\?)줄$/, '$1 / $2 lines'],
  [/^마지막 (\d.*)$/s, 'Last $1'],
];

// '읽은 파일 3개, 찾은 글자 2번, ...' 같은 작업 묶음 요약을 영어로
function 조합요약(글) {
  const 틀 = [
    [/읽은 파일 (\d+)개/g, (m, n) => `${n} file${n === '1' ? '' : 's'} read`],
    [/찾은 글자 (\d+)번/g, (m, n) => `${n} search${n === '1' ? '' : 'es'}`],
    [/살펴본 것 (\d+)번/g, (m, n) => `${n} look${n === '1' ? '' : 's'}`],
    [/만든 파일 (\d+)개/g, (m, n) => `${n} file${n === '1' ? '' : 's'} created`],
    [/고친 파일 (\d+)개/g, (m, n) => `${n} file${n === '1' ? '' : 's'} edited`],
    [/실행한 명령 (\d+)개/g, (m, n) => `${n} command${n === '1' ? '' : 's'} run`],
    [/차례·기억 (\d+)번/g, (m, n) => `${n} plan/memory update${n === '1' ? '' : 's'}`],
    [/깃 (\d+)번/g, (m, n) => `${n} git action${n === '1' ? '' : 's'}`],
    [/그 밖의 도구 (\d+)개/g, (m, n) => `${n} other tool${n === '1' ? '' : 's'}`],
  ];
  let 값 = 글;
  for (const [정규, 바꿈] of 틀) 값 = 값.replace(정규, 바꿈);
  return 값;
}

// ── 3) 긴 문구 조각 ──────────────────────────────────────────────
// 문장 안에 이름 · 경로가 붙은 안내(카드 줄 등). 긴 것부터 바꾼다. 흔한 낱말은 넣지 않는다.
const 조각표 = [
  ['바꿀 글  ', 'Replace  '], ['새 글  ', 'With  '], ['덧붙일 글  ', 'Append  '], ['파일  ', 'File  '], ['폴더  ', 'Folder  '],
  ['내용  ', 'Content  '], ['지울 것  ', 'Delete  '], ['대상  ', 'Target  '], ['새 자리  ', 'To  '], ['하는 일  ', 'Action  '],
  ['읽을 곳  ', 'Read  '], ['일할 폴더  ', 'Work folder  '], ['주소  ', 'URL  '], ['명령  ', 'Command  '], ['자리  ', 'In  '],
  ['메모  ', 'Note  '], ['역할  ', 'Role  '], ['이름  ', 'Name  '], ['맡길 일  ', 'Task  '], ['버전  ', 'Version  '], ['때  ', 'Time  '],
  ['어디   ', 'Where   '], ['시간   ', 'Time   '], ['왜     ', 'Why     '], ['무엇   ', 'What   '], ['어디서 ', 'From '], ['어디에 ', 'To '],
  ['파일이 10개를 넘습니다', 'More than 10 files'],
];

const 번역캐시 = new Map();
let 번역중단수 = 0;

// 사람 말 · GPT 말 · 파일 내용처럼 사용자 자료를 그리는 동안은 번역하지 않는다.
function 번역멈춤(일) {
  번역중단수 += 1;
  try { return 일(); } finally { 번역중단수 -= 1; }
}

function 번역(글) {
  if (typeof 글 !== 'string' || !/[가-힣]/.test(글)) return 글;
  if (번역중단수 > 0 || 지금언어() !== 'en') return 글;
  if (번역캐시.has(글)) return 번역캐시.get(글);
  const 앞공백 = (글.match(/^\s*/) || [''])[0];
  const 뒤공백 = (글.match(/\s*$/) || [''])[0];
  const 속 = 글.slice(앞공백.length, 글.length - 뒤공백.length);
  let 결과 = null;
  if (Object.prototype.hasOwnProperty.call(번역표, 글)) 결과 = 번역표[글];
  else if (Object.prototype.hasOwnProperty.call(번역표, 속)) 결과 = 앞공백 + 번역표[속] + 뒤공백;
  if (결과 === null) {
    for (const [정규, 틀] of 번역규칙) {
      const m = 속.match(정규);
      if (m) {
        const 바뀐 = typeof 틀 === 'function' ? 틀(...m) : 속.replace(정규, 틀);
        결과 = 앞공백 + 바뀐 + 뒤공백;
        break;
      }
    }
  }
  if (결과 === null) {
    // 조각 바꾸기 — 문장 안의 알려진 안내 문구만 바꾸고 나머지(이름 · 경로)는 둔다
    let 값 = 글;
    for (const [한, 영] of 조각표) 값 = 값.split(한).join(영);
    // 번역표의 긴 문장이 문장 속에 들어 있는 경우도 바꾼다(8자 이상인 것만)
    for (const 한 of Object.keys(번역표)) {
      if (한.length >= 8 && 값.indexOf(한) !== -1) 값 = 값.split(한).join(번역표[한]);
    }
    결과 = 값;
  }
  if (번역캐시.size > 3000) 번역캐시.clear();
  번역캐시.set(글, 결과);
  return 결과;
}

// ── 화면에 그려지는 순간 번역 ────────────────────────────────────
// 진짜 브라우저에서만 끼워 넣는다(시험의 가짜 문서에는 Node 가 없다).
function 번역끼우기() {
  if (typeof Node === 'undefined' || typeof Element === 'undefined' || !Node.prototype) return;
  if (Node.prototype.__번역끼움) return;
  Node.prototype.__번역끼움 = true;

  const 속성 = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
  if (속성 && 속성.set) {
    Object.defineProperty(Node.prototype, 'textContent', {
      configurable: true, enumerable: 속성.enumerable,
      get: 속성.get,
      set(값) { 속성.set.call(this, typeof 값 === 'string' ? 번역(값) : 값); },
    });
  }
  const 만들기 = Document.prototype.createTextNode;
  Document.prototype.createTextNode = function (글) { return 만들기.call(this, 번역(String(글))); };

  for (const [클래스, 이름] of [[HTMLElement, 'title'], [HTMLInputElement, 'placeholder'], [HTMLTextAreaElement, 'placeholder']]) {
    if (!클래스 || !클래스.prototype) continue;
    const d = Object.getOwnPropertyDescriptor(클래스.prototype, 이름);
    if (d && d.set) {
      Object.defineProperty(클래스.prototype, 이름, {
        configurable: true, enumerable: d.enumerable, get: d.get,
        set(값) { d.set.call(this, typeof 값 === 'string' ? 번역(값) : 값); },
      });
    }
  }
  const 속성설정 = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function (이름, 값) {
    return 속성설정.call(this, 이름, (이름 === 'title' || 이름 === 'placeholder' || 이름 === 'aria-label') && typeof 값 === 'string' ? 번역(값) : 값);
  };
}

// 처음에 이미 그려진 정적 글(panel.html)을 한 번 훑어 번역한다.
function 처음글번역() {
  if (typeof document === 'undefined' || !document.body || 지금언어() !== 'en') return;
  const 걷개 = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const 글들 = [];
  while (걷개.nextNode()) 글들.push(걷개.currentNode);
  for (const 노드 of 글들) {
    const 새 = 번역(노드.nodeValue);
    if (새 !== 노드.nodeValue) 노드.nodeValue = 새;
  }
  if (document.title && /[가-힣]/.test(document.title)) document.title = 번역(document.title);
  for (const 요소 of document.querySelectorAll('[title],[placeholder]')) {
    for (const 이름 of ['title', 'placeholder']) {
      const 값 = 요소.getAttribute(이름);
      if (값 && /[가-힣]/.test(값)) 요소.setAttribute(이름, 번역(값));
    }
  }
}

try { 번역끼우기(); } catch (e) { /* 번역이 안 돼도 판은 그대로 돈다 */ }
