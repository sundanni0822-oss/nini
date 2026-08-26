import re
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改CSS：添加未批改状态样式，并修改默认非active样式
old_css = '''.g-btn.correct.active { background: #eaf3de; border-color: #3b6d11; color: #3b6d11; }
.g-btn.wrong.active { background: #fcebeb; border-color: #a32d2d; color: #a32d2d; }
.g-btn:hover { border-color: #999; }'''

new_css = '''.g-btn.correct.active { background: #eaf3de; border-color: #3b6d11; color: #3b6d11; }
.g-btn.wrong.active { background: #fcebeb; border-color: #a32d2d; color: #a32d2d; }
.g-btn:not(.active) { background: #f5f5f5; border-color: #ddd; color: #bbb; }
.g-btn:hover { border-color: #999; }'''

content = content.replace(old_css, new_css)

# 2. 修改 refreshGrading：删除默认全选correct，改为不给任何按钮加active
# 原来的代码：
# $$('#gradeList .g-btn').forEach(btn => {
#   btn.addEventListener('click', function() {
#     const item = this.closest('.grade-item');
#     item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
#     this.classList.add('active');
#   });
# });
# $$('#gradeList .g-btn.correct').forEach(b => b.classList.add('active'));

old_refresh = '''    $$('#gradeList .g-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const item = this.closest('.grade-item');
        item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
      });
    });
    $$('#gradeList .g-btn.correct').forEach(b => b.classList.add('active'));'''

new_refresh = '''    $$('#gradeList .g-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const item = this.closest('.grade-item');
        item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
      });
    });
    // 默认全部未批改，用户必须逐词点选对/错'''

content = content.replace(old_refresh, new_refresh)

# 3. 修改 renderReviewGrading：同样删除默认全选correct
old_review = '''  $$('#reviewGradeList .g-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const item = this.closest('.grade-item');
      item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
    });
  });
  $$('#reviewGradeList .g-btn.correct').forEach(b => b.classList.add('active'));'''

new_review = '''  $$('#reviewGradeList .g-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const item = this.closest('.grade-item');
      item.querySelectorAll('.g-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
    });
  });
  // 默认全部未批改，用户必须逐词点选对/错'''

content = content.replace(old_review, new_review)

# 4. 修改 submitGradingPage：添加未批改检查
old_submit = '''function submitGradingPage() {
  const child = getActiveChild();
  if (!child) { toast('请先选择孩子'); return; }
  const date = $('#gradeDate').value || todayStr();
  const items = $$('#gradeList .grade-item');
  if (items.length === 0) { toast('没有可批改的词'); return; }
  const results = Array.from(items).map(item => {
    const wrong = item.querySelector('.g-btn.wrong.active');
    return { word: item.dataset.word, correct: !wrong };
  });'''

new_submit = '''function submitGradingPage() {
  const child = getActiveChild();
  if (!child) { toast('请先选择孩子'); return; }
  const date = $('#gradeDate').value || todayStr();
  const items = $$('#gradeList .grade-item');
  if (items.length === 0) { toast('没有可批改的词'); return; }
  // 检查是否有未批改的词（既没有选对也没有选错）
  const unchecked = Array.from(items).filter(item => !item.querySelector('.g-btn.active'));
  if (unchecked.length > 0) {
    toast(`还有 ${unchecked.length} 个词未批改，请逐词点选对或错`);
    // 滚动到第一个未批改的词
    unchecked[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  const results = Array.from(items).map(item => {
    const wrong = item.querySelector('.g-btn.wrong.active');
    return { word: item.dataset.word, correct: !wrong };
  });'''

content = content.replace(old_submit, new_submit)

# 5. 修改 submitReviewPage：同样添加未批改检查
old_review_submit = '''function submitReviewPage() {
  const child = getActiveChild();
  if (!child) { toast('请先选择孩子'); return; }
  const date = $('#gradeDate').value || todayStr();
  const items = $$('#reviewGradeList .grade-item');
  if (items.length === 0) { toast('没有复习词'); return; }
  const results = Array.from(items).map(item => {
    const wrong = item.querySelector('.g-btn.wrong.active');
    return { word: item.dataset.word, correct: !wrong };
  });'''

new_review_submit = '''function submitReviewPage() {
  const child = getActiveChild();
  if (!child) { toast('请先选择孩子'); return; }
  const date = $('#gradeDate').value || todayStr();
  const items = $$('#reviewGradeList .grade-item');
  if (items.length === 0) { toast('没有复习词'); return; }
  // 检查是否有未批改的词
  const unchecked = Array.from(items).filter(item => !item.querySelector('.g-btn.active'));
  if (unchecked.length > 0) {
    toast(`还有 ${unchecked.length} 个复习词未批改，请逐词点选对或错`);
    unchecked[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  const results = Array.from(items).map(item => {
    const wrong = item.querySelector('.g-btn.wrong.active');
    return { word: item.dataset.word, correct: !wrong };
  });'''

content = content.replace(old_review_submit, new_review_submit)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(content)

print('OK')
