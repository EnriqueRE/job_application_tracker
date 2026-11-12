/**
 * Form text as the API wants it: `null` when empty or only whitespace, otherwise
 * trimmed. Pass `keepWhitespace` for Markdown, where leading spaces and newlines matter.
 */
export function blankToNull(
  value: string,
  { keepWhitespace = false }: { keepWhitespace?: boolean } = {},
): string | null {
  const trimmed = value.trim()
  if (trimmed === '') return null
  return keepWhitespace ? value : trimmed
}
