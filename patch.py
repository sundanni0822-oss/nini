# -*- coding: utf-8 -*-
import re

# Read file
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix CSS: add pending state style
old_css = '''.g-btn.correct.active { background: #eaf3de; border-color: #3b6d11; color: #3b6d11; }
.g-btn.wrong.active { background: #fcebeb; border-color: #a32d2d; color: #a32d2d; }
.g-btn:hover { border-color: #999; }'''
new_css = '''.g-btn.correct.active { background: #eaf3de; border-color: #3b6d11; color: #3b6d11; }
.g-btn.wrong.active { background: #fcebeb; border-color: #a32d2d; color: #a32d2d; }
.g-btn:not(.active) { background: #f5f5f5; border-color: #ddd; color: #bbb; }
.g-btn:hover { border-color: #999; }'''
content = content.replace(old_css, new_css)

# 2. Fix refreshGrading: remove default correct selection
old_rg = '''    $$('#gradeList .g-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const item = this.closest('.grade-item');
        item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
      });
    });
    $$('#gradeList .g-btn.correct').forEach(b => b.classList.add('active'));'''
new_rg = '''    $$('#gradeList .g-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const item = this.closest('.grade-item');
        item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
      });
    });
    // 默认全部未批改，用户必须逐词点选对/错'''
content = content.replace(old_rg, new_rg)

# 3. Fix renderReviewGrading: remove default correct selection
old_rrg = '''  $$('#reviewGradeList .g-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const item = this.closest('.grade-item');
      item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
    });
  });
  $$('#reviewGradeList .g-btn.correct').forEach(b => b.classList.add('active'));'''
new_rrg = '''  $$('#reviewGradeList .g-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const item = this.closest('.grade-item');
      item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
    });
  });
  // 默认全部未批改，用户必须逐词点选对/错'''
content = content.replace(old_rrg, new_rrg)

# 4. Fix submitGradingPage: add unchecked validation
old_sgp = '''function submitGradingPage() {
  const child = getActiveChild();
  if (!child) { toast('请先选择孩子'); return; }
  const date = $('#gradeDate').value || todayStr();
  const items = $$('#gradeList .grade-item');
  if (items.length === 0) { toast('没有可批改的词'); return; }
  const results = Array.from(items).map(item => {
    const wrong = item.querySelector('.g-btn.wrong.active');
    return { word: item.dataset.word, correct: !wrong };
  });'''
new_sgp = '''function submitGradingPage() {
  const child = getActiveChild();
  if (!child) { toast('请先选择孩子'); return; }
  const date = $('#gradeDate').value || todayStr();
  const items = $$('#gradeList .grade-item');
  if (items.length === 0) { toast('没有可批改的词'); return; }
  const unchecked = Array.from(items).filter(item => !item.querySelector('.g-btn.active'));
  if (unchecked.length > 0) {
    toast('还有 ' + unchecked.length + ' 个词未批改，请逐词点选对或错');
    unchecked[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  const results = Array.from(items).map(item => {
    const wrong = item.querySelector('.g-btn.wrong.active');
    return { word: item.dataset.word, correct: !wrong };
  });'''
content = content.replace(old_sgp, new_sgp)

# 5. Fix submitReviewPage: add unchecked validation
old_srp = '''function submitReviewPage() {
  const child = getActiveChild();
  if (!child) { toast('请先选择孩子'); return; }
  const date = $('#gradeDate').value || todayStr();
  const items = $$('#reviewGradeList .grade-item');
  if (items.length === 0) { toast('没有复习词'); return; }
  const results = Array.from(items).map(item => {
    const wrong = item.querySelector('.g-btn.wrong.active');
    return { word: item.dataset.word, correct: !wrong };
  });'''
new_srp = '''function submitReviewPage() {
  const child = getActiveChild();
  if (!child) { toast('请先选择孩子'); return; }
  const date = $('#gradeDate').value || todayStr();
  const items = $$('#reviewGradeList .grade-item');
  if (items.length === 0) { toast('没有复习词'); return; }
  const unchecked = Array.from(items).filter(item => !item.querySelector('.g-btn.active'));
  if (unchecked.length > 0) {
    toast('还有 ' + unchecked.length + ' 个复习词未批改，请逐词点选对或错');
    unchecked[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  const results = Array.from(items).map(item => {
    const wrong = item.querySelector('.g-btn.wrong.active');
    return { word: item.dataset.word, correct: !wrong };
  });'''
content = content.replace(old_srp, new_srp)

# 6. Add OCR status element after gradePhotoPreview
old_photo = '''        <div class="photo-preview" id="gradePhotoPreview"></div>
        <div style="margin-top:12px;font-size:12px;color:#888;">'''
new_photo = '''        <div class="photo-preview" id="gradePhotoPreview"></div>
        <div id="ocrStatus" style="display:none;margin-top:8px;font-size:12px;"></div>
        <div style="margin-top:12px;font-size:12px;color:#888;">'''
content = content.replace(old_photo, new_photo)

# 7. Update grading label hint
old_label = '正确答案对照表（逐词点对/错）</label>'
new_label = '正确答案对照表（逐词点对/错）<span style="font-size:11px;color:#888;margin-left:8px;">上传照片后自动识别</span></label>'
content = content.replace(old_label, new_label)

# 8. Add runAutoGrading trigger in handleFiles
old_hf = '''      const reader = new FileReader();
      reader.onload = e => {
        const img = document.createElement('img');
        img.src = e.target.result;
        img.style.cssText = 'max-width:200px;max-height:200px;border-radius:8px;border:1px solid #eee;';
        previewEl.appendChild(img);
        // 记录第一个用于 OCR
        if (window.__ocrImages.length < 6) {
          window.__ocrImages.push({ src: e.target.result, name: f.name });
        }
      };'''
new_hf = '''      const reader = new FileReader();
      reader.onload = e => {
        const img = document.createElement('img');
        img.src = e.target.result;
        img.style.cssText = 'max-width:200px;max-height:200px;border-radius:8px;border:1px solid #eee;';
        previewEl.appendChild(img);
        // 记录第一个用于 OCR
        if (window.__ocrImages.length < 6) {
          window.__ocrImages.push({ src: e.target.result, name: f.name });
        }
        // 批改页上传照片后自动触发 OCR 辅助批改
        if (previewEl.id === 'gradePhotoPreview') {
          runAutoGrading(e.target.result);
        }
      };'''
content = content.replace(old_hf, new_hf)

# 9. Add runAutoGrading function after runOcr
old_ocr_end = '''    $('#btnOcr').disabled = false;
  }
}
function clearOcrResult() {'''
new_ocr_end = '''    $('#btnOcr').disabled = false;
  }
}

// OCR 辅助批改：上传照片后自动识别手写答案和 √/× 标记
async function runAutoGrading(imageDataUrl) {
  const statusEl = document.getElementById('ocrStatus');
  if (statusEl) { statusEl.style.display = 'block'; statusEl.textContent = '正在识别照片...'; statusEl.style.color = '#888'; }
  try {
    const img = new Image();
    img.src = imageDataUrl;
    await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; });
    const ocrResult = await ocrRecognizeImage(img, true);
    const items = document.querySelectorAll('#gradeList .grade-item');
    const targetWords = Array.from(items).map(item => ({ word: item.dataset.word }));
    if (targetWords.length === 0) {
      if (statusEl) { statusEl.textContent = '没有可批改的词'; statusEl.style.color = '#a32d2d'; }
      return;
    }
    const analysis = analyzeGradingPhoto(ocrResult, targetWords);
    let autoChecked = 0;
    let uncertain = 0;
    analysis.forEach(result => {
      const item = document.querySelector('#gradeList .grade-item[data-word="' + result.word + '"]');
      if (!item) return;
      const wordDiv = item.querySelector('.g-word');
      if (wordDiv) {
        let ocrHint = '';
        if (result.hasCheck) ocrHint = ' [OCR: 对勾]';
        else if (result.hasCross) ocrHint = ' [OCR: 叉号]';
        else if (result.recognizedText) ocrHint = ' [识别: ' + result.recognizedText + ']';
        if (ocrHint) {
          const existingHint = wordDiv.querySelector('.ocr-hint');
          if (existingHint) existingHint.remove();
          const hintEl = document.createElement('span');
          hintEl.className = 'ocr-hint';
          hintEl.style.cssText = 'font-size:11px;color:#888;margin-left:8px;font-weight:normal;';
          hintEl.textContent = ocrHint;
          wordDiv.appendChild(hintEl);
        }
      }
      const correctBtn = item.querySelector('.g-btn.correct');
      const wrongBtn = item.querySelector('.g-btn.wrong');
      if (result.hasCheck) {
        correctBtn.classList.add('active');
        wrongBtn.classList.remove('active');
        autoChecked++;
      } else if (result.hasCross) {
        wrongBtn.classList.add('active');
        correctBtn.classList.remove('active');
        autoChecked++;
      } else if (result.suggestedCorrect && result.confidence === 'high') {
        correctBtn.classList.add('active');
        wrongBtn.classList.remove('active');
        autoChecked++;
      } else {
        uncertain++;
      }
    });
    if (statusEl) {
      statusEl.innerHTML = '自动识别完成：已标 ' + autoChecked + ' 词，待确认 ' + uncertain + ' 词。请检查并修正。';
      statusEl.style.color = '#3b6d11';
    }
  } catch (err) {
    console.error('OCR 批改失败:', err);
    if (statusEl) { statusEl.textContent = '识别失败，请手动批改'; statusEl.style.color = '#a32d2d'; }
  }
}

function clearOcrResult() {'''
content = content.replace(old_ocr_end, new_ocr_end)

# Write back
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('index.html patched OK')