#!/usr/bin/env node
/* Assemble the stage deck from the installed guizang Swiss template.
 * Inputs are all local; output: index.html (no network at runtime).
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const read = (p) => readFileSync(join(root, p), 'utf8');

let html = read('vendor/template-swiss.html');
const slides = read('src/slides.html');
const notes = read('src/notes.js');
const deckCss = read('src/deck.css');
const brandCss = read('src/brand-theme.css');
const runtime = read('src/runtime.js');

/* 1. shell */
html = html.replace(
  '<html lang="zh-CN" data-family="swiss" data-medium="slide" data-theme="ikb">',
  '<html lang="en" data-family="swiss" data-medium="slide" data-theme="brand">'
);
html = html.replace(/<title>[\s\S]*?<\/title>/, '<title>Verifiable Tutor · CSIT6000V Final Presentation</title>');
html = html.replace(/<!-- GZ:FONTS:START[\s\S]*?<!-- GZ:FONTS:END -->\n?/, '<!-- fonts: local system stack (Georgia / Arial / Courier New); no network font loading -->\n');
html = html.replace(
  '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
  '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<meta name="deck-stage" content="1920x1080">'
);

/* 2. theme + overrides */
html = html.replace('</style>',
  '\n/* ===== brand theme (guizang gz-theme.mjs, family swiss) ===== */\n' + brandCss +
  '\n/* ===== stage deck overrides ===== */\n' + deckCss + '\n</style>');

/* 3. deck body */
const deckStart = html.indexOf('<div id="deck">');
const navStart = html.indexOf('<div id="nav">');
if (deckStart < 0 || navStart < 0 || navStart < deckStart) throw new Error('deck/nav anchors not found');
html = html.slice(0, deckStart) + '<div id="deck">\n' + slides + '\n</div>\n\n' + html.slice(navStart);

/* 4. speaker notes */
const notesIdx = html.indexOf('const SPEAKER_NOTES = [');
const scriptOpen = html.lastIndexOf('<script>', notesIdx);
const endMarker = 'window.__SPEAKER_NOTES__ = SPEAKER_NOTES;';
const endIdx = html.indexOf(endMarker, notesIdx);
if (notesIdx < 0 || scriptOpen < 0 || endIdx < 0) throw new Error('speaker notes anchors not found');
const scriptClose = html.indexOf('</script>', endIdx) + '</script>'.length;
html = html.slice(0, scriptOpen) + '<script>\n' + notes + '</script>' + html.slice(scriptClose);

/* 5. local-only scripts */
html = html.replace(
  '<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>\n<script>lucide.createIcons();</script>',
  '<!-- icons are inlined from the shared Lucide pack by build.mjs; no CDN runtime -->'
);
html = html.replace(
  /let motion;\s*try \{\s*motion = await import\('\.\/assets\/motion\.min\.js'\);\s*\} catch\(e1\) \{[\s\S]*?\n\}/,
  "let motion;\ntry {\n  motion = await import('./assets/motion.min.js');\n} catch(e1) {\n  console.warn('[motion] local copy failed, animations disabled', e1);\n  document.querySelectorAll('[data-anim]').forEach(el=>{el.style.opacity='1';el.style.transform='none'});\n}"
);

/* 6. stage scale bootstrap + runtime */
html = html.replace('<body class="canvas-mode">',
  '<body class="canvas-mode">\n<script>\n(function(){function f(){var s=Math.min(innerWidth/1920,innerHeight/1080);document.documentElement.style.setProperty("--stage-scale",String(s));}addEventListener("resize",f,{passive:true});f();})();\n</script>');
const bodyClose = html.lastIndexOf('</body>');
html = html.slice(0, bodyClose) + '<script>\n' + runtime + '\n</script>\n' + html.slice(bodyClose);

/* 7. inline shared Lucide icons */
const iconCache = new Map();
function iconSvg(name) {
  if (!iconCache.has(name)) {
    const raw = read('vendor/icons/' + name + '.svg');
    iconCache.set(name, raw.replace('<svg ', '<svg class="st-svg" ').replace(/\s+width="24"/, '').replace(/\s+height="24"/, ''));
  }
  return iconCache.get(name);
}
let iconCount = 0;
html = html.replace(/\[\[icon:([a-z-]+)\]\]/g, (_, name) => { iconCount += 1; return iconSvg(name); });

/* 8. presenter chrome in English */
const zh = {
  '表示观众页面的软件同步状态，不代表 HDMI 等物理线缆状态': 'Software sync state of the audience page; not an HDMI or projector check',
  '这里只能检查浏览器和观众页面的软件状态，不能确认 HDMI、转接器或投影仪线缆是否物理连接。': 'This checks browser and audience-page software state only. It cannot confirm HDMI, adapter or projector cables.',
  '单页 autoAdvanceSeconds 优先于全局间隔；minutes 只是讲述计划。': 'Per-slide autoAdvanceSeconds overrides the global interval; minutes is the speaking plan.',
  '根据屏幕宽度调整页面与备注的比例': 'Adjust the slide and notes ratio for this screen',
  '需要时手动开启，默认关闭': 'Off by default; enable it when needed',
  '已同步 · 第 ${idx+1} 页': 'Synced · page ${idx+1}',
  '建议 ${target?(target/60000).toFixed(1):\u0027\u2014\u0027} 分钟 · ${id}': 'Suggested ${target?(target/60000).toFixed(1):\u0027\u2014\u0027} min · ${id}',
  '计划 ${Number(totalPlan/60000).toFixed(1)} 分钟 · 预计 ${clockTime(Date.now()+Math.max(0,totalPlan-totalUsed))}': 'Plan ${Number(totalPlan/60000).toFixed(1)} min · ETA ${clockTime(Date.now()+Math.max(0,totalPlan-totalUsed))}',
  ' · 剩余 ${durationText(Math.max(0,section.planned-section.used))}': ' · ${durationText(Math.max(0,section.planned-section.used))} left',
  '观众屏 · ${labels[state]}': 'Audience · ${labels[state]}',
  '观众屏 · ${originalTitle}': 'Audience · ${originalTitle}',
  '演讲者视图 · ${originalTitle}': 'Presenter view · ${originalTitle}',
  '自动翻页 · ${durationText(autoRemainingMs||duration)}': 'Auto-advance · ${durationText(autoRemainingMs||duration)}',
  '自动翻页 · ${blocked}': 'Auto-advance · ${blocked}',
  '计划 ${durationText(target)}': 'Plan ${durationText(target)}',
  '第 ${idx+1} / ${total} 页': 'Page ${idx+1} / ${total}',
  '第 ${i+1} 页': 'Page ${i+1}',
  '第 ${idx+1} 页': 'Page ${idx+1}',
  '${escapeHTML(n.section||\u0027未分组\u0027)}': '${escapeHTML(n.section||\u0027Ungrouped\u0027)}',
  '演讲者视图': 'Presenter view',
  '观众屏 · 未连接': 'Audience · disconnected',
  '重新打开观众屏': 'Reopen audience',
  '观众屏连接': 'Audience connection',
  '观众屏黑屏 / 白屏': 'Audience black / white',
  '冻结 / 恢复观众屏': 'Freeze / resume audience',
  '临时遮挡或冻结观众屏': 'Temporarily blank or freeze the audience screen',
  '演讲者布局': 'Presenter layout',
  '演前检查': 'Preflight check',
  '进入全屏': 'Enter fullscreen',
  '全屏状态': 'Fullscreen',
  '已进入全屏': 'Fullscreen on',
  '尚未全屏，可在演讲前进入': 'Not fullscreen; enter it before presenting',
  '浏览器阻止了观众窗口': 'The browser blocked the audience window',
  '未检测到弹窗拦截': 'No popup block detected',
  '弹窗权限': 'Popup permission',
  '弹窗被拦截': 'Popup blocked',
  '字体加载': 'Fonts',
  '浏览器不提供字体状态': 'The browser does not expose font status',
  '图片资源': 'Images',
  '视频资源': 'Videos',
  '没有视频': 'No videos',
  '当前页 16:9': 'Current page 16:9',
  '尚未渲染': 'Not rendered yet',
  '重新检查': 'Check again',
  '快捷键说明': 'Keyboard shortcuts',
  '上一页 / 下一页': 'Prev / Next',
  '首页 / 尾页': 'First / Last',
  '宫格选页；标注工具激活时先退出工具': 'Page grid; exits an active annotation tool first',
  '开启 / 关闭自动翻页': 'Toggle auto-advance',
  '开始 / 结束排练': 'Start / end rehearsal',
  '激光笔（L）': 'Laser (L)',
  '圈选（C）': 'Circle (C)',
  '清除标记（X）': 'Clear marks (X)',
  '宫格选页（Esc）': 'Page grid (Esc)',
  '当前页预览': 'Current slide preview',
  '下一页预览': 'Next slide preview',
  '本页演讲备注': 'Speaker notes for this slide',
  '缩小备注字号': 'Smaller note text',
  '放大备注字号': 'Larger note text',
  '草稿（备注）': 'Draft (notes)',
  '本页目的': 'Purpose',
  '保存自动翻页': 'Save auto-advance',
  '全局间隔': 'Global interval',
  '减少一秒': 'Decrease one second',
  '增加一秒': 'Increase one second',
  '演示设置': 'Presentation settings',
  '演示已结束': 'Presentation ended',
  '查看快捷键': 'Show shortcuts',
  '排练记录': 'Rehearsal log',
  '本次总时长': 'Total rehearsal',
  '与计划相比': 'vs plan',
  '没有记录到页面时间': 'No per-slide time recorded',
  '最近排练': 'Recent rehearsals',
  '开始计时': 'Start timer',
  '重置计时': 'Reset timer',
  '继续计时': 'Resume timer',
  '结束排练': 'End rehearsal',
  '已超出本页计划': 'Over slide plan',
  '距本页计划': 'To slide plan',
  '等待观众屏同步': 'waiting for audience sync',
  '观众屏已暂停': 'audience paused',
  '自动翻页 · 等待时长': 'Auto-advance · waiting for duration',
  '自动翻页 · 已结束': 'Auto-advance · ended',
  '自动翻页 · 关闭': 'Auto-advance · off',
  '自动翻页': 'Auto-advance',
  '快捷控制': 'Quick controls',
  '← → 翻页': '← → Navigate',
  '演讲模式': 'Presenter',
  '舞台提示': 'Cue',
  '表达提示': 'Delivery',
  '翻页时机': 'Advance',
  '备用方案': 'Fallback',
  '读音提醒': 'Pronunciation',
  '【讲述要点】': '[Talk track]',
  '【转场】': '[Transition]',
  '页面优先': 'Slides first',
  '备注优先': 'Notes first',
  '已保存': 'Saved',
  '保存中…': 'Saving…',
  '未设置': 'Not set',
  '计划 —': 'Plan —',
  '已进行': 'Elapsed',
  '总时长': 'Total',
  '未分组': 'Ungrouped',
  '未连接': 'Disconnected',
  '连接中': 'Connecting',
  '未同步': 'Unsynced',
  '已冻结': 'Frozen',
  '已加载': 'loaded',
  '可播放': 'playable',
  '清除标记': 'Clear marks',
  '清除': 'Clear',
  '激光笔': 'Laser',
  '圈选': 'Circle',
  '激光': 'Laser',
  '当前页': 'Current',
  '下一页': 'Next',
  '上一页': 'Prev',
  '首页': 'First',
  '尾页': 'Last',
  '重新开始': 'Restart',
  '已到尾页': 'End of deck',
  '宫格选页中': 'page grid open',
  '宫格': 'Grid',
  '选择页面': 'Select a page',
  '返回预览': 'Back to preview',
  '标题': 'Title',
  '观众屏': 'Audience',
  '正常': 'Normal',
  '黑屏 B': 'Black B',
  '白屏 W': 'White W',
  '冻结 F': 'Freeze F',
  '排练': 'Rehearsal',
  '本页': 'Slide',
  '计划': 'Plan',
  '暂停': 'Pause',
  '超时': 'Over',
  '剩余': 'Remaining',
  '检查': 'Check',
  '设置中': 'settings open',
  '设置': 'Settings',
  '退出': 'Exit',
  '关闭': 'Close',
  '标注中': 'annotating',
  '窗口不可见': 'window hidden',
  '建议': 'Suggested',
  '异常': 'Error',
  '静态': 'Static',
  '动态': 'Live',
  '总览': 'Overview',
  '秒': 'sec',
  '互动': 'Interaction',
  '均衡': 'Balanced',
  '页面': 'Page',
  '实际': 'Actual'
};
const keys = Object.keys(zh).sort((a, b) => b.length - a.length);
const missed = [];
for (const key of keys) {
  const real = key.split('${').join('\${');
  const value = zh[key].split('${').join('\${');
  if (!html.includes(real)) { missed.push(real); continue; }
  html = html.split(real).join(value);
}

/* 9. report */
const leftoverPlaceholders = (html.match(/\[\[icon:/g) || []).length;
const leftoverFill = (html.match(/\[必填\]|\[选填\]/g) || []).length;
writeFileSync(join(root, 'index.html'), html);
console.log('built index.html');
console.log('  bytes:', Buffer.byteLength(html));
console.log('  slides:', (html.match(/<section\b[^>]*class="[^"]*\bslide\b/g) || []).length);
console.log('  icons inlined:', iconCount);
console.log('  leftover icon placeholders:', leftoverPlaceholders);
console.log('  leftover template placeholders:', leftoverFill);
if (missed.length) console.log('  translation keys not present:', missed.join(' | '));
