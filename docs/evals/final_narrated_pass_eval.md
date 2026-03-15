# Final Narrated Pass Eval

Date: 2026-03-15

## Method
- Browser-driven rehearsal with deliberate narration pauses inserted at each beat.
- 60-second pass used replay mode to model a fast hallway explanation.
- 120-second pass used live mode with the confirmation-test sample to model the main booth story.
- Evidence: `docs/evals/evidence/final/narrated-pass-runs-final.json`

## Pass 1. 60-Second Version
- Mode: replay
- Total: `47.229 s`

### Beat Timing
| Beat | Time |
| --- | --- |
| students | 0.056 s |
| student-detail | 7.103 s |
| upload | 13.117 s |
| ocr-review | 19.146 s |
| analysis | 27.178 s |
| homework-review | 37.200 s |
| demo-dashboard | 43.228 s |

### Evaluation
- Pass / fail: pass
- Value clear in first 20 seconds: yes
- Where narration felt awkward: the upload screen still contains slightly technical fallback wording, so the operator should paraphrase instead of reading labels.
- Does it get stuck: no
- Is the ending satisfying: yes, approval and final homework card close cleanly

### Best 60s Script Shape
1. 6人クラスで全員分の宿題を考えるのは重い
2. 今日は主役の Yuna だけ見ます
3. 答案を撮ると、要確認箇所だけ OCR review に出します
4. そのまま弱点と宿題候補を返します
5. 最後は講師が軽くして承認します

## Pass 2. 120-Second Version
- Mode: live
- Total: `88.623 s`

### Beat Timing
| Beat | Time |
| --- | --- |
| students | 0.036 s |
| student-detail | 8.080 s |
| upload | 17.097 s |
| ocr-review | 28.843 s |
| analysis | 47.554 s |
| homework-review | 69.594 s |
| demo-dashboard | 81.623 s |

### Evaluation
- Pass / fail: pass
- Under 2 minutes while explaining: yes
- Value clear in first 20 seconds: yes, by the upload step
- Where narration felt awkward: OCR review remains the softest beat; do not linger there
- Does it get stuck: no
- Is the ending satisfying: yes, approval is the right closing interaction

## Recommended Spoken Framing
### 60s
- “授業前20分で6人分の宿題を考えるのは大変です。”
- “この子の答案を撮ると、OCR は完璧扱いせず、要確認だけ出します。”
- “その上で弱点と今夜の宿題候補を problem number で返します。”
- “最後は講師が1問外して確定します。”

### 120s
- “来場者にはこの確認テストを全部でなくてもよいので数問だけ解いてもらいます。”
- “撮った答案は OCR に通しますが、ここでは完璧主義にせず、怪しい箇所だけ講師が見ます。”
- “その結果をもとに、弱点と今夜の宿題候補を教材 DB の問題番号で返します。”
- “最後は講師が重ければ軽くして承認します。AIが勝手に決めないのがポイントです。”

## Narrated-Pass Conclusion
- 60秒版: 余裕あり
- 120秒版: 十分余裕あり
- The timing budget is not the problem; the operator’s discipline is. The middle must stay concise.
