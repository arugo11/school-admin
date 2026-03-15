# Final E2E Subjective Eval

Date: 2026-03-15

## Overall Read
This demo is real, coherent, and much stronger than a fake dashboard. The physical-input story lands. The weak point is not reliability anymore; it is emotional sharpness in the middle of the flow. The entrance and ending are good. The OCR review and some mixed-language microcopy cool the temperature.

Overall subjective score: **78 / 100**

## Persona 1. Judge
### First Impression
- Good first read: “答案を撮るだけで、今夜の宿題まで” is understandable quickly.
- The six-student overview immediately signals classroom reality instead of a toy single-user app.

### Good Points
- Real-world input is strong: worksheet photo / confirmation test answer sheet is a believable starting point.
- Pipeline is respectable: OCR -> normalized JSON -> constrained analysis -> teacher approval.
- Replay mode is honest and practical rather than hidden magic.

### Friction / Discomfort
- OCR review is visually flat and can feel underwhelming if many answers show as `unknown` or low-information rows.
- Student detail loading flashes a blank/empty state before the stronger card appears.
- Some mode language stays half-English, half-Japanese, which makes the product feel slightly prototype-ish.

### Heart Moved Moment
- The ending lands: the teacher removes or lightens one problem and approval becomes the emotional proof that this is assistive, not autonomous.

### Cooled Off Moment
- The OCR review screen does not always feel like “wow, AI understood the sheet”; it feels more like a cautious data cleanup checkpoint.

### Top 3 Improvements
1. Make OCR review show only uncertain or important rows first, not a flat full list.
2. Polish student detail loading so the spotlight story starts immediately.
3. Unify mode and fallback wording into cleaner Japanese for exhibit polish.

## Persona 2. Cram-School Teacher
### First Impression
- I can see where this saves prep time, especially before class.
- The approval step makes me trust it more because I stay in charge.

### Good Points
- Homework stays at problem-number level, which matches how teachers actually assign work.
- “軽くする” is exactly the kind of intervention a teacher wants in the moment.
- The system does not pretend OCR is perfect; that humility helps.

### Friction / Discomfort
- If OCR review looks too empty or too uncertain, I have to narrate around it.
- Analysis text is decent, but still slightly generic; the strongest moments come when manifest-backed confirmation-test context is visible.
- For a booth setting, six full questions may be too much to ask every visitor to solve.

### Heart Moved Moment
- The teacher-note / approval combination feels like support, not replacement.

### Cooled Off Moment
- Raw technical wording like `seeded snapshot` feels internal, not teacher-facing.

### Top 3 Improvements
1. Make confirmation-test context more explicit in analysis for stronger teacher trust.
2. Turn technical fallback wording into more human operator language.
3. Encourage “solve first 3 questions” for walk-up visitors unless they volunteer for the full set.

## Persona 3. Visitor / Student
### First Impression
- The six-student screen looks like a real school tool, not a lab toy.
- I can imagine taking the test and seeing what it says about me.

### Good Points
- The system shows a result fast enough that I would wait for it.
- The approval ending makes the result feel like something a real teacher could hand me tonight.
- The confirmation test gives me a concrete thing to do, not just a passive demo.

### Friction / Discomfort
- If I am not already good at math, six MATH-500-JP-derived questions may feel a bit intimidating.
- OCR review is the least exciting screen from a student point of view.
- The UI is clear enough, but not playful; it is useful rather than delightful.

### Heart Moved Moment
- Seeing weakness + tonight’s homework appear from my own sheet is the moment that earns the “おお”.

### Cooled Off Moment
- If the operator lingers on OCR review too long, the experience becomes procedural instead of magical.

### Top 3 Improvements
1. Tell visitors they can answer only the first 2 or 3 questions and still get a result.
2. Shorten the OCR review narration to one sentence.
3. Add one stronger “your effort is visible” line on the analysis/approval end state.

## Persona 4. Product Designer
### First Impression
- The headline is clear in under 10 seconds.
- The six-student overview and spotlight case are good structural choices.

### Good Points
- The flow has a clean narrative spine.
- The approval screen is a solid ending surface.
- Replay mode is functionally strong and visually understandable.

### Friction / Discomfort
- OCR review cards repeat too much layout for too little information.
- Analysis screen is readable, but still slightly dense and text-block heavy.
- Student detail page can briefly feel empty during loading, which harms momentum.

### Heart Moved Moment
- Completion dashboard plus the judge-facing message neatly package value, implementation, experience, and future edge story.

### Cooled Off Moment
- Mixed language (`Live Mode`, `Replay Mode`, `seeded snapshot`) lowers perceived finish quality.

### Top 3 Improvements
1. Collapse or filter OCR rows to show the 1-2 interesting uncertainties first.
2. Tighten wording and language consistency across the whole flow.
3. Give the analysis screen one stronger visual hierarchy cue around the single key takeaway.

## Visitor-Participation Assessment
### Is 6 questions the right exhibit default?
- For printing, yes.
- For actual booth participation, not as a mandatory full solve.
- Best judgment: keep the sheet at 6 questions, but verbally invite most visitors to solve only the first 3.

### Solve-Time vs Result-Time Balance
- Result-time is excellent; the system returns quickly enough.
- Solve-time is the real bottleneck in an exhibition setting.

### Boredom Risk While Waiting
- Low after upload; the system is fast enough.
- Medium before upload if the visitor is expected to solve all 6 questions.

### OCR Friendliness of Answer Sheet
- Good. Separate answer sheet, large boxes, stable `test_id`, and per-question mapping all help.

### Is MATH-500-JP too hard for random visitors?
- Easy-to-medium selection is still a bit hard for a mixed exhibition crowd.
- It is acceptable if the operator steers people toward the early easier questions.

### Does the demo still work for weaker visitors?
- Yes, if the operator says partial answers are enough.
- No, if the operator implicitly expects full completion.

### Does the demo still work for stronger visitors?
- Yes. Strong visitors can still enjoy seeing targeted next-step homework.

## Harshest Cross-Persona Criticisms
- OCR review is the least emotionally persuasive screen.
- Some wording still feels internal rather than exhibit-polished.
- Six questions is slightly too ambitious if framed as a full must-do task.
- Student detail loading momentarily loses momentum.
- The strongest emotional moment happens late; the first 20 seconds need a tighter spoken hook.

## Improvement Priority Top 5
1. Booth operation: tell visitors “first 3 questionsだけでも十分です” by default.
2. Keep OCR review narration to one short sentence and move on quickly.
3. Unify mixed English/Japanese mode wording before any future polish pass.
4. Make the key takeaway on analysis screen more visually dominant.
5. Smooth the student-detail loading / transition so the spotlight story appears immediately.
