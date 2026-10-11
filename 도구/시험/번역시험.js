// 판 번역기(i18n.js) 시험 — 영어 기본일 때 한글이 남지 않는지, 한국어일 때 그대로인지, 사용자 글은 안 건드리는지
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const 확장 = path.join(__dirname, '..', '..', '확장', 'i18n.js');

function 만들기(언어) {
  const 칸 = { 언어 };
  const ctx = {
    localStorage: { getItem: () => 칸.언어, setItem(k, v) { 칸.언어 = v; } },
    console,
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(확장, 'utf8'), ctx);
  return {
    번역: (s) => vm.runInContext('번역(' + JSON.stringify(s) + ')', ctx),
    멈춤: (s) => vm.runInContext('번역멈춤(() => 번역(' + JSON.stringify(s) + '))', ctx),
  };
}

// [한글 문장, 기대하는 영어(통째로 같아야 함)]
const 표본 = [
  ['답을 기다리는 중…', 'Waiting for the answer…'],
  ['✎ 답 쓰는 속도가 3번 연속 평소(42자/초)의 3분의 1 밑입니다(11.5자/초). 다음 도구 결과는 새 대화로 넘겨 보냅니다.',
    '✎ The answer speed was under a third of normal (42 chars/s) 3 times in a row (11.5 chars/s). The next tool result goes to a new chat.'],
  ['느려져서 새 대화로 넘깁니다… 넘김 파일 12천 자', 'Slow, so moving to a new chat… hand-off file 12k chars'],
  ['새 대화로 넘깁니다… 넘김 파일 3천 자', 'Moving to a new chat… hand-off file 3k chars'],
  ['압축 요약을 적었습니다(1200자). 다음 넘김은 이 요약부터 이어 갑니다.', 'Saved a compressed summary (1200 chars). The next hand-off continues from it.'],
  ['앞 시점으로 되돌렸습니다. 기록 5건을 지웠습니다.', 'Rolled back to an earlier point. Removed 5 log entries.'],
  ['⚠ 같은 것이 4번 같은 이유로 실패했습니다. 같은 일을 되풀이하는 것 같아 멈췄습니다 — ▶ 로 다시 시작하세요.',
    '⚠ The same thing failed 4 times for the same reason. It looks like it is going in circles, so it stopped — press ▶ to restart.'],
  ['⚠ 6판 내리 하나도 성공하지 못했습니다. 멈췄습니다 — ▶ 로 다시 시작하세요.', '⚠ Nothing succeeded for 6 rounds in a row. Stopped — press ▶ to restart.'],
  ['ChatGPT가 아직 대답하지 않습니다 — 2분 30초 뒤 다시 보냅니다 (1/3)', 'ChatGPT has not answered yet — resending in 2m 30s (1/3)'],
  ['⚠ ChatGPT가 3번 재촉해도 빈 답만 냅니다 — [대답 다시 받기] 를 눌러 보세요.', '⚠ ChatGPT only gives empty answers even after 3 nudges — try [Get answer again].'],
  ['ChatGPT 답이 비었습니다(생각 중단됨). 이어서 해 달라고 보냅니다… (1/3)', 'ChatGPT’s answer was empty (thinking stopped). Asking it to continue… (1/3)'],
  ['⏰ 예약 시간이 됐습니다. GPT에게 보냅니다… (5분마다)', '⏰ Reminder is due. Sending it to GPT… (every 5m)'],
  ['결과를 다시 보낼 때를 기다리는 중 (0/3, 12초)', 'Waiting to resend the result (0/3, 12 s)'],
  ['결과를 아직 보내지 못했습니다 — 8초 뒤 저절로 다시 보냅니다 (1/3)', 'Could not send the result yet — retrying automatically in 8 s (1/3)'],
  ['⚠ 결과를 3번 다시 보내도 보내지 못했습니다 — [다시 보내기] 를 누르면 도구는 다시 실행하지 않고 결과만 보냅니다.',
    '⚠ Still could not send the result after 3 retries — [Resend] sends only the result without running the tool again.'],
  ['바구니 오류: 도구 이름이 없습니다', 'Request error: 도구 이름이 없습니다'], // 서버가 준 사유는 그대로 둔다
  ['열무 처리 중…', 'Processing 열무…'],
  ['🔧 일꾼 "검토" 을 새 탭에서 부릅니다(리뷰어)', '🔧 Starting helper "검토" in a new tab (리뷰어)'],
  ['🔧 일꾼 "검토" 결과를 받았습니다', '🔧 Got the result from helper "검토"'],
  ['빌드 끝났습니다 (1분 5초)', '빌드 finished (1m 5s)'],
  ['모델을 GPT-5.6 Sol 으로 바꾸는 중…', 'Changing the model to GPT-5.6 Sol…'],
  ['모델: GPT-6', 'Model: GPT-6'],
  ['GPT-6 · 깊게', 'GPT-6 · Deep'],
  ['GPT-5.6 Sol · 보통', 'GPT-5.6 Sol · Medium'],
  ['⚠ ChatGPT 모델을 못 바꿨습니다(쓰는 중이면 끝난 뒤 다시).', '⚠ Could not change the model (if ChatGPT is writing, try again after it finishes).'],
  ['ChatGPT 에서 모델 목록을 읽는 중…', 'Reading the model list from ChatGPT…'],
];

// 한글이 남아도 되는 문장(사용자 · 서버가 준 이름이 섞인 것)
const 이름섞임 = new Set(표본.filter(([, 영]) => /[가-힣]/.test(영)).map(([한]) => 한));

let 실패 = 0;
function 확인(참, 설명, 덧) {
  if (!참) {
    실패 += 1;
    console.log('  ✗ ' + 설명 + (덧 ? '\n      ' + 덧 : ''));
  }
}

const 영 = 만들기('en');
for (const [한, 기대] of 표본) {
  const 얻음 = 영.번역(한);
  확인(얻음 === 기대, '영어 변환: ' + 한.slice(0, 40), '기대 ' + 기대 + '\n      실제 ' + 얻음);
  if (!이름섞임.has(한)) 확인(!/[가-힣]/.test(얻음), '한글이 남음: ' + 한.slice(0, 40), 얻음);
}

// 한국어 모드 — 아무것도 바꾸지 않는다
const 한 = 만들기('ko');
for (const [원문] of 표본) 확인(한.번역(원문) === 원문, '한국어 모드는 그대로: ' + 원문.slice(0, 40));

// 사용자 글은 번역하지 않는다(번역멈춤 안)
const 사람말 = '파일을 읽고 요약해 줘';
확인(영.멈춤(사람말) === 사람말, '번역멈춤 안에서는 그대로');
확인(영.번역('사용자 글 아님') !== undefined, '번역은 문자열을 돌려준다');

// 한글이 없는 글은 손대지 않는다
확인(영.번역('Hello 123') === 'Hello 123', '영어 글은 그대로');

console.log(실패 === 0 ? '번역시험 통과 (' + 표본.length + '개 표본)' : '번역시험 실패 ' + 실패 + '건');
process.exit(실패 === 0 ? 0 : 1);
