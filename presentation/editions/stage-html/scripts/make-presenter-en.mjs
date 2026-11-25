import { readFileSync, writeFileSync } from 'node:fs';
const src = '/Users/lijinchuan/.agents/skills/guizang-ppt-skill/scripts/validate-presenter-mode.mjs';
let code = readFileSync(src, 'utf8');
code = code.replace(/if\(!\/id="ppt-timer-toggle"\[\^>\]\*>开始计时<\\\/button>\/\.test\(html\)\)errors\.push\('Presenter timer must use the explicit label "[^"]*"\.'\);/,
  'if(!/id="ppt-timer-toggle"[^>]*>Start timer<\\/button>/.test(html))errors.push(\'Presenter timer must use the explicit label "Start timer".\');');
code = code.replace(/if\(!\/id="ppt-timer-reset"\[\^>\]\*>重置计时<\\\/button>\/\.test\(html\)\)errors\.push\('Presenter timer reset must use the explicit label "[^"]*"\.'\);/,
  'if(!/id="ppt-timer-reset"[^>]*>Reset timer<\\/button>/.test(html))errors.push(\'Presenter timer reset must use the explicit label "Reset timer".\');');
code = code.replace(/if\(!html\.includes\('继续计时'\)\)errors\.push\('Presenter timer resume state must use the explicit label "[^"]*"\.'\);/,
  'if(!html.includes(\'Resume timer\'))errors.push(\'Presenter timer resume state must use the explicit label "Resume timer".\');');
code = code.replace('validate-presenter-mode.mjs', 'validate-presenter-en.mjs');
writeFileSync('scripts/validate-presenter-en.mjs', code);
console.log('local presenter validator written');
