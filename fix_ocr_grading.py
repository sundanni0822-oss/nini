import re
import sys

# ======== 修改 app.js ========
with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# 1. 修改 ocrRecognizeImage 返回详细结果
old_ocr = '''// ---------- OCR 识别（Tesseract.js，免费本地方案）----------
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
}'''

new_ocr = '''// ---------- OCR 识别（Tesseract.js，免费本地方案）----------
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
  // 返回详细结果：文本 + 每个词的边界框
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
// 返回: [{word, recognizedText, hasCheck, hasCross, confidence}]
function analyzeGradingPhoto(ocrResult, targetWords) {
  const words = ocrResult.words || [];
  const results = [];

  // √/× 检测的正则
  const checkPattern = /^[✓√✔vV\\/\\\\]$/;
  const crossPattern = /^[✗×xX*#]$/;

  targetWords.forEach(target => {
    const tw = target.word.toLowerCase();
    let recognizedText = '';
    let hasCheck = false;
    let hasCross = false;
    let confidence = 'low';

    // 1. 查找与目标词接近的 OCR 结果（文本匹配或位置邻近）
    const nearbyWords = words.filter(w => {
      const wt = w.text.toLowerCase().trim();
      // 匹配目标词本身（避免把题目词当答案）
      if (wt === tw || wt === tw.replace(/[-']/g, '')) return false;
      // 匹配答案：与目标词有一定编辑距离的英文词
      if (/^[a-zA-Z]+$/.test(wt) && wt.length >= 2 && wt.length <= 24) {
        recognizedText = wt;
        return true;
      }
      return false;
    });

    if (nearbyWords.length > 0) {
      // 取最长的一个作为识别结果
      recognizedText = nearbyWords.sort((a, b) => b.text.length - a.text.length)[0].text;
      // 简单比对：完全匹配或近似匹配
      const rt = recognizedText.toLowerCase().replace(/[^a-z]/g, '');
      const tt = tw.replace(/[^a-z]/g, '');
      if (rt === tt) confidence = 'high';
      else if (rt.length > 2 && (rt.includes(tt) || tt.includes(rt))) confidence = 'medium';
    }

    // 2. 扫描所有词，检测 √/× 符号
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
      // 自动判断建议：有√ → 对；有× → 错；识别文本匹配 → 对；否则 → 不确定
      suggestedCorrect: hasCheck || (confidence === 'high' && !hasCross),
      suggestedWrong: hasCross
    });
  });

  return results;
}'''

app_js = app_js.replace(old_ocr, new_ocr)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)

print('app.js OK')

# ======== 修改 index.html ========
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 2. 修改批改页面的 upload 区域，添加 OCR 状态提示
old_upload_label = '<label class="lbl">上传默写纸照片（可不上传，对照屏幕批改）</label>'
new_upload_label = '<label class="lbl">上传默写纸照片（可不上传，对照屏幕批改）</label>\n        <div id="ocrStatus" style="display:none;font-size:12px;color:#3b6d11;margin-bottom:8px;">🔄 正在识别照片...</div>'
html = html.replace(old_upload_label, new_upload_label)

# 3. 修改 grade-item 的 HTML 结构，添加识别结果显示区域
old_grade_item = '''<div class="grade-item" data-word="${w.word}">
        <div>
          <div class="g-word">${w.word}</div>
          <div class="g-mean">${w.meaning || \'\'}</div>
        </div>
        <div class="grade-btns">
          <button class="g-btn correct" title="对">✓</button>
          <button class="g-btn wrong" title="错">✗</button>
        </div>
      </div>'''

new_grade_item = '''<div class="grade-item" data-word="${w.word}">
        <div style="flex:1;min-width:0;">
          <div class="g-word">${w.word}</div>
          <div class="g-mean">${w.meaning || \'\'}</div>
          <div class="g-ocr" id="ocr-${w.word}" style="display:none;font-size:11px;color:#888;margin-top:2px;"></div>
        </div>
        <div class="grade-btns">
          <button class="g-btn correct" title="对">✓</button>
          <button class="g-btn wrong" title="错">✗</button>
        </div>
      </div>'''

html = html.replace(old_grade_item, new_grade_item)

# 4. 修改复习区的 grade-item 结构
old_review_item = '''<div class="grade-item" data-word="${w.word}">
      <div>
        <div class="g-word">${w.word} <span class="stage-badge">复习第${w.reviewRound}天</span></div>
        <div class="g-mean">${w.meaning}</div>
      </div>
      <div class="grade-btns">
        <button class="g-btn correct" title="对">✓</button>
        <button class="g-btn wrong" title="错">✗</button>
      </div>
    </div>'''

new_review_item = '''<div class="grade-item" data-word="${w.word}">
      <div style="flex:1;min-width:0;">
        <div class="g-word">${w.word} <span class="stage-badge">复习第${w.reviewRound}天</span></div>
        <div class="g-mean">${w.meaning}</div>
        <div class="g-ocr" id="ocr-review-${w.word}" style="display:none;font-size:11px;color:#888;margin-top:2px;"></div>
      </div>
      <div class="grade-btns">
        <button class="g-btn correct" title="对">✓</button>
        <button class="g-btn wrong" title="错">✗</button>
      </div>
    </div>'''

html = html.replace(old_review_item, new_review_item)

# 5. 修改照片上传事件处理，添加 OCR 辅助批改
# 找到 gradeUploadInput 的事件监听器
old_upload_event = '''$('#gradeUploadInput').addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    $('#gradePhotoPreview').innerHTML = `<img src="${ev.target.result}" style="max-width:100%;border-radius:10px;">`;
  };
  reader.readAsDataURL(file);
});'''

new_upload_event = '''$('#gradeUploadInput').addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    $('#gradePhotoPreview').innerHTML = `<img src="${ev.target.result}" style="max-width:100%;border-radius:10px;" id="gradePhotoImg">`;
    // 触发 OCR 辅助批改
    runAutoGrading(ev.target.result);
  };
  reader.readAsDataURL(file);
});

// OCR 辅助批改：上传照片后自动识别
async function runAutoGrading(imageDataUrl) {
  const statusEl = $('#ocrStatus');
  if (statusEl) statusEl.style.display = 'block';

  try {
    // 创建临时图片元素用于 OCR
    const img = new Image();
    img.src = imageDataUrl;
    await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; });

    // 获取详细 OCR 结果
    const ocrResult = await ocrRecognizeImage(img, true);

    // 获取当前需要批改的单词列表
    const items = $$('#gradeList .grade-item');
    const targetWords = Array.from(items).map(item => ({ word: item.dataset.word }));

    if (targetWords.length === 0) {
      if (statusEl) { statusEl.textContent = '⚠️ 没有可批改的词'; statusEl.style.color = '#a32d2d'; }
      return;
    }

    // 分析照片
    const analysis = analyzeGradingPhoto(ocrResult, targetWords);

    // 应用识别结果
    let autoChecked = 0;
    let uncertain = 0;
    analysis.forEach(result => {
      const item = $(`#gradeList .grade-item[data-word="${result.word}"]`);
      if (!item) return;

      const ocrEl = item.querySelector('.g-ocr');
      if (ocrEl) {
        ocrEl.style.display = 'block';
        let statusText = '';
        if (result.hasCheck) statusText = '✓ 检测到对勾';
        else if (result.hasCross) statusText = '✗ 检测到叉号';
        else if (result.recognizedText) statusText = `识别: "${result.recognizedText}"`;
        else statusText = '未识别到答案';
        ocrEl.textContent = statusText;
      }

      const correctBtn = item.querySelector('.g-btn.correct');
      const wrongBtn = item.querySelector('.g-btn.wrong');

      if (result.hasCheck) {
        // 检测到 √ → 标对
        correctBtn.classList.add('active');
        wrongBtn.classList.remove('active');
        autoChecked++;
      } else if (result.hasCross) {
        // 检测到 × → 标错
        wrongBtn.classList.add('active');
        correctBtn.classList.remove('active');
        autoChecked++;
      } else if (result.suggestedCorrect && result.confidence === 'high') {
        // 高置信度文本匹配 → 标对（浅绿色提示是自动的）
        correctBtn.classList.add('active');
        wrongBtn.classList.remove('active');
        correctBtn.style.borderColor = '#a0d080';
        autoChecked++;
      } else {
        uncertain++;
      }
    });

    if (statusEl) {
      statusEl.innerHTML = `✅ 自动识别完成：已标 ${autoChecked} 词，待确认 ${uncertain} 词。请检查并手动修正。`;
      statusEl.style.color = '#3b6d11';
    }
  } catch (err) {
    console.error('OCR 批改失败:', err);
    if (statusEl) { statusEl.textContent = '⚠️ 识别失败，请手动批改'; statusEl.style.color = '#a32d2d'; }
  }
}'''

# 需要找到 gradeUploadInput 的事件监听器位置
# 由于可能有多个匹配，我们用更精确的方式
pattern = r"(\$\('#gradeUploadInput'\)\.addEventListener\('change', e => \{\n  const file = e\.target\.files\[0\];\n  if \(!file\) return;\n  const reader = new FileReader\(\);\n  reader\.onload = ev => \{\n    \$\('#gradePhotoPreview'\)\.innerHTML = `<img src="\$\{ev\.target\.result\}" style="max-width:100%;border-radius:10px;">`;\n  \};\n  reader\.readAsDataURL\(file\);\n\}\);)"

match = re.search(pattern, html)
if match:
    html = html[:match.start()] + new_upload_event + html[match.end():]
    print('Upload event OK')
else:
    print('Upload event NOT FOUND - trying fallback')
    # Fallback: 尝试更简单的替换
    html = html.replace(old_upload_event, new_upload_event)
    print('Upload event fallback OK')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('index.html OK')
