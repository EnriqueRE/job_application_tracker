import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

// Raw HTML is allowed through markdown-it so pasted postings keep their formatting,
// then everything is sanitized by DOMPurify so scripts and event handlers never run.
const md = new MarkdownIt({ html: true, linkify: true, breaks: true })

/** Render Markdown to HTML that is safe to insert with `v-html`. */
export function renderMarkdown(source: string): string {
  return DOMPurify.sanitize(md.render(source))
}
