import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  breaks: true,
  linkify: true,
})

export function renderMarkdown(text: string) {
  return md.render(text)
}
