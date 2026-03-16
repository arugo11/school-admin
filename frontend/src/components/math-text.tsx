import katex from 'katex'

type MathTextProps = {
  text?: string | null
  inline?: boolean
  className?: string
  fallback?: string
}

type Segment =
  | { type: 'text'; value: string }
  | { type: 'math'; value: string; displayMode: boolean }

const INLINE_PATTERN = /(\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g
const RAW_COMMANDS = new Set([
  'alpha', 'beta', 'boxed', 'cdot', 'cos', 'cot', 'div', 'frac', 'gamma', 'geq', 'lambda', 'leq',
  'ln', 'log', 'mu', 'neq', 'pi', 'pm', 'right', 'left', 'sin', 'sqrt', 'sum', 'tan', 'theta', 'times',
])

function normalizeMathSource(raw: string): { value: string; displayMode: boolean } {
  const trimmed = raw.trim()
  if (trimmed.startsWith('$$') && trimmed.endsWith('$$')) {
    return { value: trimmed.slice(2, -2).trim(), displayMode: true }
  }
  if (trimmed.startsWith('\\[') && trimmed.endsWith('\\]')) {
    return { value: trimmed.slice(2, -2).trim(), displayMode: true }
  }
  if (trimmed.startsWith('$') && trimmed.endsWith('$')) {
    return { value: trimmed.slice(1, -1).trim(), displayMode: false }
  }
  if (trimmed.startsWith('\\(') && trimmed.endsWith('\\)')) {
    return { value: trimmed.slice(2, -2).trim(), displayMode: false }
  }
  return { value: trimmed, displayMode: false }
}

function looksLikeMathFragment(text: string): boolean {
  const trimmed = text.trim()
  if (!trimmed || /[\u3040-\u30ff\u3400-\u9fff]/.test(trimmed)) {
    return false
  }
  if (/\\[a-zA-Z]+/.test(trimmed)) {
    return true
  }
  if (!/[=+\-*/^_<>]|\\cdot|\\times|\\div/.test(trimmed)) {
    return false
  }
  return /^[a-zA-Z0-9\s{}()[\],.+\-*/=<>^_\\|:;]+$/.test(trimmed)
}

function splitMathSegments(text: string): Segment[] {
  const trimmed = text.trim()
  if (!trimmed) {
    return [{ type: 'text', value: text }]
  }

  if ((trimmed.startsWith('$$') && trimmed.endsWith('$$')) || (trimmed.startsWith('\\[') && trimmed.endsWith('\\]'))) {
    const normalized = normalizeMathSource(trimmed)
    return [{ type: 'math', value: normalized.value, displayMode: true }]
  }

  if (looksLikeMathFragment(trimmed)) {
    return [{ type: 'math', value: trimmed, displayMode: false }]
  }

  const parts: Segment[] = []
  let cursor = 0

  for (const match of text.matchAll(INLINE_PATTERN)) {
    const matched = match[0]
    const index = match.index ?? 0
    if (index > cursor) {
      parts.push(...splitRawMathFragments(text.slice(cursor, index)))
    }
    const normalized = normalizeMathSource(matched)
    parts.push({ type: 'math', value: normalized.value, displayMode: normalized.displayMode })
    cursor = index + matched.length
  }

  if (cursor < text.length) {
    parts.push(...splitRawMathFragments(text.slice(cursor)))
  }

  return parts.length > 0 ? parts : [{ type: 'text', value: text }]
}

function splitRawMathFragments(text: string): Segment[] {
  const parts: Segment[] = []
  let index = 0
  let buffer = ''

  while (index < text.length) {
    if (text[index] !== '\\') {
      buffer += text[index]
      index += 1
      continue
    }

    const fragment = extractLatexCommand(text, index)
    if (!fragment) {
      buffer += text[index]
      index += 1
      continue
    }

    if (buffer) {
      parts.push({ type: 'text', value: buffer })
      buffer = ''
    }
    parts.push({ type: 'math', value: fragment.value, displayMode: false })
    index = fragment.end
  }

  if (buffer) {
    parts.push({ type: 'text', value: buffer })
  }

  return parts
}

function extractLatexCommand(text: string, start: number): { value: string; end: number } | null {
  let index = start + 1
  while (index < text.length && /[a-zA-Z]/.test(text[index])) {
    index += 1
  }
  const command = text.slice(start + 1, index)
  if (!RAW_COMMANDS.has(command)) {
    return null
  }

  let end = index
  while (end < text.length) {
    while (end < text.length && /\s/.test(text[end])) {
      end += 1
    }
    if (end >= text.length) break

    if (text[end] === '{') {
      const groupEnd = consumeBalancedGroup(text, end)
      if (groupEnd === -1) break
      end = groupEnd
      continue
    }

    if (text[end] === '^' || text[end] === '_') {
      end += 1
      if (text[end] === '{') {
        const groupEnd = consumeBalancedGroup(text, end)
        if (groupEnd === -1) break
        end = groupEnd
      } else {
        end += 1
      }
      continue
    }

    if (/[A-Za-z0-9()+\-=/|]/.test(text[end])) {
      end += 1
      continue
    }
    break
  }

  return { value: text.slice(start, end), end }
}

function consumeBalancedGroup(text: string, start: number): number {
  let depth = 0
  for (let index = start; index < text.length; index += 1) {
    if (text[index] === '{') depth += 1
    if (text[index] === '}') {
      depth -= 1
      if (depth === 0) {
        return index + 1
      }
    }
  }
  return -1
}

function renderMath(value: string, displayMode: boolean): string | null {
  try {
    return katex.renderToString(value, {
      displayMode,
      throwOnError: false,
      strict: 'ignore',
      output: 'html',
    })
  } catch {
    return null
  }
}

export function MathText({ text, inline = false, className, fallback = '未入力' }: MathTextProps) {
  if (!text || !text.trim()) {
    return <span className={className}>{fallback}</span>
  }

  const segments = splitMathSegments(text)
  const allMath = segments.every((segment) => segment.type === 'math')
  const Wrapper = inline ? 'span' : 'div'
  const combinedClassName = [className, inline ? 'math-inline-text' : 'math-block-text'].filter(Boolean).join(' ')

  if (allMath && segments.length === 1) {
    const segment = segments[0]
    const html = renderMath(segment.value, inline ? false : segment.displayMode)
    if (html) {
      return <Wrapper className={combinedClassName} dangerouslySetInnerHTML={{ __html: html }} />
    }
  }

  return (
    <Wrapper className={combinedClassName}>
      {segments.map((segment, index) => {
        if (segment.type === 'text') {
          return <span key={`text-${index}`}>{segment.value}</span>
        }
        const html = renderMath(segment.value, segment.displayMode)
        if (!html) {
          return <span key={`math-fallback-${index}`}>{segment.value}</span>
        }
        const Tag = segment.displayMode && !inline ? 'div' : 'span'
        return <Tag key={`math-${index}`} className={segment.displayMode ? 'math-segment-block' : 'math-segment-inline'} dangerouslySetInnerHTML={{ __html: html }} />
      })}
    </Wrapper>
  )
}
