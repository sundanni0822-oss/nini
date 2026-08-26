/* =========================================================
   单词学习管理系统 · 数据层与逻辑层
   ========================================================= */

// ---------- 工具 ----------
const $ = sel => document.querySelector(sel);
const $$ = sel => document.querySelectorAll(sel);
const todayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
};
// 在指定基准日期上加 N 天（默认从今天起）
const addDays = (n, from) => {
  const base = from ? new Date(from + 'T00:00:00') : new Date();
  base.setDate(base.getDate() + n);
  return `${base.getFullYear()}-${String(base.getMonth()+1).padStart(2,'0')}-${String(base.getDate()).padStart(2,'0')}`;
};
const uid = () => 'id' + Date.now().toString(36) + Math.random().toString(36).slice(2,7);

// ---------- 存储 ----------
const STORE_KEY = 'vocabSystem_v1';
let store = null;

function loadStore() {
  try {
    store = JSON.parse(localStorage.getItem(STORE_KEY)) || null;
  } catch(e) { store = null; }
  if (!store) {
    store = {
      groupName: '我的班级',     // 班级/机构名
      children: [],            // 孩子档案
      activeChildId: null,     // 当前选中的孩子
      assignments: {},         // 作业存档：childId|date -> {date, bookId, dir, words:[{word,meaning,isReview}]}
      parentWords: [],         // 家长上传的词（localStorage 部分）
      childData: {},           // childId -> {wrong:{wordId:obj}, calendar:{date:obj}, checkin:{date:bool}}
      ocrDays: {},             // OCR 识别入库的 DAY：title -> [words]
      settings: {              // 全局设置
        startDate: todayStr(), // 学习起点：第一天对应的日期
      }
    };
    saveStore();
  }
  // 兼容旧数据：补字段
  if (!store.groupName) store.groupName = '我的班级';
  if (!store.ocrDays) store.ocrDays = {};
  if (!store.childData) store.childData = {};
  if (!store.settings) store.settings = { startDate: todayStr() };
  if (!store.assignments) store.assignments = {};
  Object.values(store.childData).forEach(cd => {
    if (!cd.calendar) cd.calendar = {};
    if (!cd.wrong) cd.wrong = {};
    if (!cd.checkin) cd.checkin = {};
  });
  store.children.forEach(c => { if (!c.bookId) c.bookId = 'tj'; }); // 旧数据兼容
  saveStore();
}
function saveStore() {
  localStorage.setItem(STORE_KEY, JSON.stringify(store));
}

// ---------- 全局词库（统一）----------
// 内置词库 = 教材(42) + 小托福(8500)；加上家长上传词 = 全量统一词库
function getGlobalWords() {
  const all = [];
  const push = (w, src) => {
    all.push({
      id: w.id || (src + '-' + w.word),
      word: w.word,
      phonetic: w.phonetic || '',
      pos: w.pos || '',
      meaning: w.meaning || w.m || '',
      source: src
    });
  };
  // 教材
  if (typeof VOCAB !== 'undefined') {
    VOCAB.days.forEach(d => d.words.forEach(w => {
      push({...w, id: 'book-' + w.word}, '教材');
    }));
  }
  // 小托福
  if (typeof TJ_VOCAB !== 'undefined') {
    TJ_VOCAB.levels.forEach(lv => {
      lv.units.forEach(u => u.words.forEach(w => {
        push({...w, id: lv.id + '-' + w.w}, '小托福·' + lv.name.split('·')[0]);
      }));
    });
  }
  // 家长上传
  (store.parentWords || []).forEach(w => push({...w, id: w.id}, '家长上传'));
  return all;
}

// 按词查全局词库
function findWord(word) {
  return getGlobalWords().find(w => w.word.toLowerCase() === String(word).toLowerCase());
}

// ================= 版本（教材）注册表 =================
// 两套完全独立的词库，绝不混池：小托福(按 DAY 推进) / 沪教四上(按 Unit 推进)
// 各自持有自己的词表与节点，跨库不调词、不混算
const BOOKS = {
  tj: {
    id: 'tj',
    name: '小托福',
    paceDays: 1,            // 1 天 / 节点（DAY）
    nodeType: 'day',
    getNodes: () => getAllDays(),                       // 教材 DAY + 照片识别 DAY
    getWords: () => {
      const all = [];
      if (typeof VOCAB !== 'undefined') VOCAB.days.forEach(d => d.words.forEach(w => all.push({ ...w, source: '教材' })));
      if (typeof TJ_VOCAB !== 'undefined') TJ_VOCAB.levels.forEach(lv => lv.units.forEach(u => u.words.forEach(w => all.push({ word: w.w, phonetic: '', pos: '', meaning: w.m, source: '小托福' }))));
      (store.parentWords || []).forEach(w => all.push({ ...w, source: '家长上传' }));
      return all;
    }
  },
  sishang: {
    id: 'sishang',
    name: '沪教四上',
    paceDays: 7,            // 1 单元 / 周
    nodeType: 'unit',
    getNodes: () => {
      if (typeof SISHANG_VOCAB === 'undefined') return [];
      return SISHANG_VOCAB.units.map(u => ({ num: u.unit, title: u.title, words: u.words, source: '四上' }));
    },
    getWords: () => {
      if (typeof SISHANG_VOCAB === 'undefined') return [];
      const all = [];
      SISHANG_VOCAB.units.forEach(u => u.words.forEach(w => all.push({ ...w, source: '四上·' + u.title })));
      return all;
    }
  }
};
function getBook(id) { return BOOKS[id] || BOOKS.tj; }
function getActiveBook(child) { return child ? getBook(child.bookId) : BOOKS.tj; }

// 自学习起点起经过的天数（非负）
function daysSinceStart(date) {
  const start = (store.settings && store.settings.startDate) ? store.settings.startDate : todayStr();
  const a = new Date(start + 'T00:00:00');
  const b = new Date((date || todayStr()) + 'T00:00:00');
  return Math.max(0, Math.floor((b - a) / 86400000));
}

// 版本感知的今日节点（自动循环 + 轮次）
function getTodayNode(child, date) {
  const book = getActiveBook(child);
  const nodes = book.getNodes();
  if (!nodes.length) return null;
  const dss = daysSinceStart(date);
  const stageIndex = Math.floor(dss / book.paceDays);
  const nodeIndex = ((stageIndex % nodes.length) + nodes.length) % nodes.length;
  const round = Math.floor(stageIndex / nodes.length) + 1;
  const node = nodes[nodeIndex];
  return { ...node, round, stageNumber: stageIndex + 1, bookId: book.id, bookName: book.name };
}
// 按词库 id 直接算今日节点（生成默写纸显式选词库时用，不依赖孩子）
function getTodayNodeForBook(bookId, date) {
  const book = getBook(bookId);
  const nodes = book.getNodes();
  if (!nodes.length) return null;
  const dss = daysSinceStart(date);
  const stageIndex = Math.floor(dss / book.paceDays);
  const nodeIndex = ((stageIndex % nodes.length) + nodes.length) % nodes.length;
  const round = Math.floor(stageIndex / nodes.length) + 1;
  const node = nodes[nodeIndex];
  return { ...node, round, stageNumber: stageIndex + 1, bookId: book.id, bookName: book.name };
}

// 在某本书词库内查词（错词快照用，不跨库）
function lookupWordInBook(bookId, word) {
  const book = getBook(bookId);
  return book.getWords().find(w => w.word.toLowerCase() === String(word).toLowerCase()) || null;
}

// ---------- 孩子管理 ----------
function getChildren() { return store.children; }
function getActiveChild() {
  return store.children.find(c => c.id === store.activeChildId) || null;
}
function addChild(name, grade, bookId) {
  const c = { id: uid(), name, grade: grade || '', bookId: bookId || 'tj', createdAt: todayStr() };
  store.children.push(c);
  store.childData[c.id] = { wrong: {}, calendar: {} };
  if (!store.activeChildId) store.activeChildId = c.id;
  saveStore();
  return c;
}
function deleteChild(id) {
  store.children = store.children.filter(c => c.id !== id);
  delete store.childData[id];
  if (store.activeChildId === id) {
    store.activeChildId = store.children.length ? store.children[0].id : null;
  }
  saveStore();
}
function setActiveChild(id) {
  store.activeChildId = id;
  saveStore();
}
function getChildData(childId) {
  if (!store.childData[childId]) {
    store.childData[childId] = { wrong: {}, calendar: {} };
    saveStore();
  }
  return store.childData[childId];
}

// ---------- 作业存档（生成默写纸时写入，供批改页读取）----------
// 结构：store.assignments[childId + '|' + date] = { date, bookId, dir, words:[{word,meaning,isReview}] }

// ---------- 错题本 + 艾宾浩斯 ----------
const EBB_STAGES = [1, 3, 7, 15, 30]; // 复习间隔（天）

// 记录一次默写批改结果
// 参数：childId, results = [{word, correct:bool}], date
function submitGrading(childId, results, date, bookId) {
  const bid = bookId || (getActiveChild() && getActiveChild().bookId) || 'tj';
  const cd = getChildData(childId);
  if (!cd.wrong) cd.wrong = {};
  if (!cd.calendar) cd.calendar = {};

  const newWords = results.length;
  let correctCount = 0;
  const wrongWords = [];

  results.forEach(r => {
    if (r.correct) {
      correctCount++;
      // 之前错的词这次对了 → 进入下一阶段
      if (cd.wrong[r.word]) {
        const w = cd.wrong[r.word];
        w.stage = Math.min(w.stage + 1, EBB_STAGES.length - 1);
        w.nextReview = addDays(EBB_STAGES[w.stage], date);
        w.lastResult = 'correct';
        w.correctCount = (w.correctCount || 0) + 1;
      }
    } else {
      wrongWords.push(r.word);
      if (cd.wrong[r.word]) {
        const w = cd.wrong[r.word];
        w.stage = 0;               // 又错 → 回到第一阶段
        w.nextReview = addDays(EBB_STAGES[0], date);
        w.wrongCount = (w.wrongCount || 0) + 1;
        w.lastResult = 'wrong';
      } else {
        const gw = lookupWordInBook(bid, r.word);
        cd.wrong[r.word] = {
          word: r.word,
          bookId: bid,
          meaning: gw ? gw.meaning : '',
          phonetic: gw ? gw.phonetic : '',
          pos: gw ? gw.pos : '',
          stage: 0,
          nextReview: addDays(EBB_STAGES[0], date),
          wrongCount: 1,
          correctCount: 0,
          lastResult: 'wrong',
          firstWrong: date
        };
      }
    }
  });

  // 日历记录 + 打卡标记（提交批改 = 当天打卡）
  cd.calendar[date] = {
    newWords, correctCount, wrongCount: wrongWords.length,
    reviewCount: 0, reviewCorrect: 0,
    status: wrongWords.length === 0 ? 'perfect' : (correctCount > 0 ? 'partial' : 'failed')
  };
  if (!cd.checkin) cd.checkin = {};
  cd.checkin[date] = { uploaded: true, time: new Date().toISOString() };
  saveStore();
  return { correctCount, wrongWords, total: newWords };
}

// 某孩子当天到期的复习词（艾宾浩斯）—— 严格按当前孩子所属词库隔离
function getDueReviewWords(childId, date, bookId) {
  const cd = getChildData(childId);
  const bid = bookId || (getActiveChild() && getActiveChild().bookId) || 'tj';
  const due = [];
  Object.values(cd.wrong || {}).forEach(w => {
    const wb = w.bookId || 'tj';            // 旧数据无 bookId 默认归小托福，不会泄漏到四上
    if (wb !== bid) return;                 // 跨库错词不混入
    if (w.nextReview && w.nextReview <= date) {
      due.push({
        id: w.word, word: w.word,
        phonetic: w.phonetic || '', pos: w.pos || '',
        meaning: w.meaning || '', source: w.bookId || '错题本',
        stage: w.stage, reviewRound: w.stage + 1
      });
    }
  });
  return due;
}

// 记录复习结果（孩子模式复习区）
function submitReview(childId, results, date) {
  const cd = getChildData(childId);
  const cal = cd.calendar[date] || { newWords: 0, correctCount: 0, wrongCount: 0, reviewCount: 0, reviewCorrect: 0, status: 'partial' };

  let correct = 0;
  results.forEach(r => {
    if (cd.wrong[r.word]) {
      const w = cd.wrong[r.word];
      if (r.correct) {
        w.stage = Math.min(w.stage + 1, EBB_STAGES.length - 1);
        w.nextReview = addDays(EBB_STAGES[w.stage], date);
        w.correctCount = (w.correctCount || 0) + 1;
        w.lastResult = 'correct';
        correct++;
      } else {
        w.stage = 0;
        w.nextReview = addDays(EBB_STAGES[0], date);
        w.wrongCount = (w.wrongCount || 0) + 1;
        w.lastResult = 'wrong';
      }
    }
  });
  cal.reviewCount = (cal.reviewCount || 0) + results.length;
  cal.reviewCorrect = (cal.reviewCorrect || 0) + correct;
  if (cal.reviewCount > 0 && cal.reviewCorrect === cal.reviewCount) cal.status = 'perfect';
  cd.calendar[date] = cal;
  saveStore();
  return { correct, total: results.length };
}

// ---------- 家长上传词库 ----------
function addParentWords(words) {
  // words: [{word, phonetic, pos, meaning}]
  words.forEach(w => {
    if (!w.word) return;
    const existing = store.parentWords.find(p => p.word.toLowerCase() === w.word.toLowerCase());
    if (existing) {
      existing.meaning = w.meaning || existing.meaning;
      existing.phonetic = w.phonetic || existing.phonetic;
      existing.pos = w.pos || existing.pos;
    } else {
      store.parentWords.push({ id: uid(), word: w.word, phonetic: w.phonetic || '', pos: w.pos || '', meaning: w.meaning || '' });
    }
  });
  saveStore();
}
function removeParentWord(id) {
  store.parentWords = store.parentWords.filter(w => w.id !== id);
  saveStore();
}

// ---------- 简单解析粘贴的单词表 ----------
// 支持格式：word [音标] 词性. 释义  或  word|释义  或  word 释义
function parseWordText(text) {
  const lines = text.split(/\n+/).map(l => l.trim()).filter(Boolean);
  const words = [];
  lines.forEach(line => {
    // word [音标] pos. meaning
    let m = line.match(/^([A-Za-z][A-Za-z\-' ]*)\s*(\[[^\]]*\])?\s*([a-zA-Z]+\s*[.．]?\s*)?(.*)$/);
    if (m && m[1]) {
      words.push({
        word: m[1].trim(),
        phonetic: m[2] ? m[2] : '',
        pos: m[3] ? m[3].trim() : '',
        meaning: m[4] ? m[4].trim() : ''
      });
    }
  });
  return words;
}

// ---------- 看板 / 统计 ----------

// 计算某孩子某天是否打卡（提交过批改）
function hasCheckin(childId, date) {
  const cd = getChildData(childId);
  return !!(cd.checkin && cd.checkin[date]);
}

// 获取某孩子最近 N 天的打卡情况
function getCheckinStreak(childId) {
  const cd = getChildData(childId);
  if (!cd.checkin) return 0;
  let streak = 0;
  let d = new Date();
  // 从今天开始往前数（今天没打就从昨天算）
  if (!cd.checkin[todayStr()]) d.setDate(d.getDate() - 1);
  while (true) {
    const ds = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    if (cd.checkin[ds]) { streak++; d.setDate(d.getDate() - 1); }
    else break;
  }
  return streak;
}

// 计算某孩子历史累计正确率
function getChildAccuracy(childId) {
  const cd = getChildData(childId);
  let total = 0, correct = 0;
  Object.values(cd.calendar || {}).forEach(rec => {
    total += (rec.newWords || 0);
    correct += (rec.correctCount || 0);
  });
  return total === 0 ? null : { correct, total, rate: Math.round(correct / total * 100) };
}

// 某孩子的错词排行（按错次倒序）—— 仅统计当前版本（bookId 隔离）
function getChildWrongTop(childId, limit = 10, bookId) {
  const cd = getChildData(childId);
  const bid = bookId || (getChildren().find(c => c.id === childId) || {}).bookId || 'tj';
  return Object.values(cd.wrong || {})
    .filter(w => (w.bookId || 'tj') === bid)
    .sort((a, b) => (b.wrongCount || 0) - (a.wrongCount || 0))
    .slice(0, limit)
    .map(w => {
      return { word: w.word, meaning: w.meaning || '', wrongCount: w.wrongCount || 0, stage: w.stage, bookId: w.bookId || 'tj' };
    });
}

// 班级共性错词：多个孩子都错过的词（按当前版本隔离）
function getClassSharedWrong(limit = 10, bookId) {
  const bid = bookId || (getActiveChild() && getActiveChild().bookId) || 'tj';
  const countMap = {};
  const detailMap = {};
  store.children.forEach(c => {
    const cd = getChildData(c.id);
    Object.values(cd.wrong || {}).forEach(w => {
      const wb = w.bookId || 'tj';
      if (wb !== bid) return;
      countMap[w.word] = (countMap[w.word] || 0) + 1;
      if (!detailMap[w.word]) {
        detailMap[w.word] = { word: w.word, meaning: w.meaning || '', bookId: w.bookId || 'tj' };
      }
      detailMap[w.word][c.name] = w.wrongCount || 0;
    });
  });
  return Object.values(detailMap)
    .map(d => ({ ...d, childrenCount: countMap[d.word] }))
    .sort((a, b) => b.childrenCount - a.childrenCount)
    .slice(0, limit);
}

// 班级打卡总览（某天每个孩子的打卡状态）
function getClassCheckin(date) {
  return store.children.map(c => ({
    child: c,
    checked: hasCheckin(c.id, date),
    streak: getCheckinStreak(c.id)
  }));
}

// OCR 文本 → 单词列表（解析词书页面的 DAY 结构）
function parseOcrTextToWords(text) {
  const lines = text.split(/\n+/).map(l => l.trim()).filter(Boolean);
  const words = [];
  lines.forEach(line => {
    let m = line.match(/^(?:\d+\s*[.、．]?\s*)?([A-Za-z][A-Za-z\-' ]*)\s*(\[[^\]]*\])?\s*([a-zA-Z]+\s*[.．]?\s*)?(.*)$/);
    if (m && m[1]) {
      const word = m[1].trim().toLowerCase();
      if (word.length >= 2 && word.length <= 24 && !/^(the|and|for|are|was|were|with|that|this)$/i.test(word)) {
        words.push({
          word,
          phonetic: m[2] ? m[2] : '',
          pos: m[3] ? m[3].trim() : '',
          meaning: m[4] ? m[4].trim() : ''
        });
      }
    }
  });
  const seen = new Set();
  return words.filter(w => {
    if (seen.has(w.word)) return false;
    seen.add(w.word);
    return true;
  });
}

// ---------- OCR 识别（Tesseract.js，免费本地方案）----------
let tesseractWorker = null;
async function ocrRecognizeImage(imageEl, detailed = false) {
  if (typeof Tesseract === 'undefined') {
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';
      s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
  }
  if (!tesseractWorker) {
    tesseractWorker = await Tesseract.createWorker('eng');
  }
  const { data } = await tesseractWorker.recognize(imageEl);
  if (!detailed) return data.text;
  return {
    text: data.text,
    words: (data.words || []).map(w => ({
      text: w.text,
      x0: w.bbox.x0, y0: w.bbox.y0,
      x1: w.bbox.x1, y1: w.bbox.y1
    }))
  };
}

// 分析批改照片：识别手写答案和 √/× 标记
// 返回: [{word, recognizedText, hasCheck, hasCross, confidence, suggestedCorrect, suggestedWrong}]
function analyzeGradingPhoto(ocrResult, targetWords) {
  const words = ocrResult.words || [];
  const results = [];
  const checkPattern = /^[\u2713\u2714\u221A\u2717\u2718vV\\/\\\\]$/;
  const crossPattern = /^[\u00D7\u2717\u2718xX*#\u2716]$/;

  targetWords.forEach(target => {
    const tw = target.word.toLowerCase();
    let recognizedText = '';
    let hasCheck = false;
    let hasCross = false;
    let confidence = 'low';

    // 1. 查找手写答案（排除题目词本身）
    const nearbyWords = words.filter(w => {
      const wt = w.text.toLowerCase().trim();
      if (wt === tw || wt === tw.replace(/[-']/g, '')) return false;
      if (/^[a-zA-Z]+$/.test(wt) && wt.length >= 2 && wt.length <= 24) {
        if (!recognizedText || wt.length > recognizedText.length) recognizedText = wt;
        return true;
      }
      return false;
    });

    if (recognizedText) {
      const rt = recognizedText.toLowerCase().replace(/[^a-z]/g, '');
      const tt = tw.replace(/[^a-z]/g, '');
      if (rt === tt) confidence = 'high';
      else if (rt.length > 2 && (rt.includes(tt) || tt.includes(rt))) confidence = 'medium';
    }

    // 2. 扫描 √/× 符号
    words.forEach(w => {
      const t = w.text.trim();
      if (checkPattern.test(t)) hasCheck = true;
      if (crossPattern.test(t)) hasCross = true;
    });

    results.push({
      word: target.word,
      recognizedText,
      hasCheck,
      hasCross,
      confidence,
      suggestedCorrect: hasCheck || (confidence === 'high' && !hasCross),
      suggestedWrong: hasCross
    });
  });

  return results;
}
let tesseractWorker = null;
async function ocrRecognizeImage(imageEl) {
  if (typeof Tesseract === 'undefined') {
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';
      s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
  }
  if (!tesseractWorker) {
    tesseractWorker = await Tesseract.createWorker('eng');
  }
  const { data } = await tesseractWorker.recognize(imageEl);
  return data.text;
}

// OCR 文本 → 单词列表（解析词书页面的 DAY 结构）
function parseOcrTextToWords(text) {
  const lines = text.split(/\n+/).map(l => l.trim()).filter(Boolean);
  const words = [];
  lines.forEach(line => {
    // 尝试多种格式
    // 1) [序号.] word [音标] 词性. 释义
    // 2) word [音标] 词性. 释义
    // 3) word|释义
    let m = line.match(/^(?:\d+\s*[.、．]?\s*)?([A-Za-z][A-Za-z\-' ]*)\s*(\[[^\]]*\])?\s*([a-zA-Z]+\s*[.．]?\s*)?(.*)$/);
    if (m && m[1]) {
      const word = m[1].trim().toLowerCase();
      // 过滤明显非单词的
      if (word.length >= 2 && word.length <= 24 && !/^(the|and|for|are|was|were|with|that|this)$/i.test(word)) {
        words.push({
          word,
          phonetic: m[2] ? m[2] : '',
          pos: m[3] ? m[3].trim() : '',
          meaning: m[4] ? m[4].trim() : ''
        });
      }
    }
  });
  // 去重
  const seen = new Set();
  return words.filter(w => {
    if (seen.has(w.word)) return false;
    seen.add(w.word);
    return true;
  });
}

// ---------- 学习计划 / 今日 DAY ----------

// 合并所有 DAYS（教材 + OCR），按 DAY 数字排序
function getAllDays() {
  const list = [];
  if (typeof VOCAB !== 'undefined') {
    VOCAB.days.forEach(d => {
      const m = d.title.match(/DAY\s*(\d+)/i);
      list.push({ title: d.title, num: m ? parseInt(m[1]) : 9999, words: d.words, source: '教材' });
    });
  }
  Object.keys(store.ocrDays || {}).forEach(k => {
    const m = k.match(/DAY\s*(\d+)/i);
    list.push({ title: k, num: m ? parseInt(m[1]) : 9999, words: store.ocrDays[k], source: '照片识别' });
  });
  list.sort((a, b) => (a.num - b.num) || a.title.localeCompare(b.title));
  return list;
}

// 给定日期，输出对应的 DAY 编号（1 = startDate, 2 = startDate+1, ...）
function todayDayNumber(date) {
  const start = store.settings && store.settings.startDate ? store.settings.startDate : todayStr();
  const a = new Date(start + 'T00:00:00');
  const b = new Date((date || todayStr()) + 'T00:00:00');
  const days = Math.floor((b - a) / 86400000) + 1;
  return Math.max(1, days);
}

// 找今天对应的 DAY（按学习起点日 +1）
function todayDay() {
  const n = todayDayNumber(todayStr());
  return getAllDays().find(d => d.num === n) || null;
}

// 设置学习起点
function setStartDate(date) {
  store.settings.startDate = date;
  saveStore();
}
