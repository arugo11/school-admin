# Final Demo Judging Eval

Date: 2026-03-15

## Provisional Scorecard
| Axis | Provisional Score | Notes |
| --- | --- | --- |
| 現場価値 | 22 / 25 | Real worksheet/photo input, teacher approval, and six-student classroom framing are strong and believable. |
| 技術実装 | 20 / 25 | OCR -> normalized JSON -> validated analysis -> catalog-constrained approval is solid; live + replay resilience adds maturity. |
| デモ体験 | 30 / 40 | The opening and ending are good, but the middle is less emotionally sharp, especially OCR review. |
| 発展性 | 8 / 10 | Edge narrative is coherent because local control boundaries are visible and documented. |
| Total | **80 / 100** | Strong booth demo with one clear polish gap: emotional pacing through the middle. |

## 現場価値
Strong.
- The demo starts from paper, not from an invented dashboard input.
- Problem-number homework is credible for cram-school practice.
- Teacher override is not a cosmetic checkbox; it is the closing action.
- The six-student framing helps judges picture actual prep-time savings.

## 技術実装
Also strong.
- Azure Vision + Azure OpenAI are used in a disciplined way.
- OCR is normalized before analysis.
- LLM output is schema-constrained and catalog-bounded.
- Replay mode makes the demo operationally serious.
- Confirmation-test PDF generation extends the story without breaking the original MVP.

## デモ体験
Good, but not yet elite.
- The headline is quick to grasp.
- The completion screen is satisfying.
- The live/replay resilience story is strong for a real exhibition.
- The weak link is the OCR review stage, which can feel procedural rather than magical.
- The confirmation-test solve burden is a risk if the operator asks random visitors to do all 6 questions.

## 発展性
Convincing.
- The team can honestly say this run prioritizes Azure reliability for the hackathon.
- The local web/API boundary leaves room for OCR preprocessing, OCR execution, caching, and analysis to move edge-side later.
- This is a believable roadmap, not a buzzword appendage.

## Competition Outlook
### Top-10 Prediction
- Subjective forecast: **slightly above the bubble, around 60-70% top-10 likelihood** if operated well.

### Why
- Stronger than many “AI education” demos because the input is physical and the teacher remains central.
- Stronger than many OCR demos because it ends in a concrete action: tonight’s homework approval.
- Weaker than the very top tier if the operator lets the middle of the flow drag or makes visitors solve too much before the payoff.

## What Will Decide It
1. Whether the first 20 seconds clearly sell “授業前20分の準備を圧縮する” rather than just “OCR できます”.
2. Whether the operator uses replay decisively instead of apologetically when live wobbles.
3. Whether visitors are guided to solve only a few questions so the emotional payoff arrives fast.
4. Whether OCR review is narrated briefly and confidently instead of over-explained.

## Overall Judgment
This is demo-ready and credible. It is not a toy. The main remaining risk is not technical breakage; it is pacing discipline. If the operator keeps the story tight, this can absolutely feel like a serious booth experience rather than a hackathon prototype.
