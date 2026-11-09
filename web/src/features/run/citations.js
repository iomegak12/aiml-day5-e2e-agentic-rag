// Inline citations produced by the agent: [KB-NET-1003, Table 1], [WEB-2], [TKT-000123] or [TICKETS]
// (same pattern as scripts/agentic_rag/guardrails.py CITATION).
export const CITATION = /\[(KB-[A-Z]{3}-\d{4}|WEB-\d+|TKT-\d{6}|TICKETS)(?:,\s*([^\]]*))?\]/g;

export const CITE_PREFIX = '#cite-';

/** DOM id of a source row in the Sources tab (target of the citation jump). */
export const sourceDomId = (id) => `source-${id}`;

/**
 * Rewrite citations as Markdown links (#cite-<id>|<location>) so the Markdown renderer can turn them into
 * clickable chips. Code blocks are left untouched.
 */
export function linkCitations(markdown = '') {
  return markdown
    .split(/(```[\s\S]*?```)/g)
    .map((part) =>
      part.startsWith('```')
        ? part
        : part.replace(CITATION, (_m, id, loc) => {
            const label = loc ? `${id} · ${loc.trim()}` : id;
            const href = `${CITE_PREFIX}${encodeURIComponent(id)}${loc ? `|${encodeURIComponent(loc.trim())}` : ''}`;
            return `[${label}](<${href}>)`; // <...> keeps "(" / ")" in locations safe
          }),
    )
    .join('');
}

/** Parse a #cite- href back into {id, location}. */
export function parseCiteHref(href = '') {
  if (!href.startsWith(CITE_PREFIX)) return null;
  const [id, loc] = href.slice(CITE_PREFIX.length).split('|');
  return { id: decodeURIComponent(id), location: loc ? decodeURIComponent(loc) : null };
}

/** Unique cited ids, in order of appearance. */
export function citedIds(markdown = '') {
  return [...new Set([...markdown.matchAll(CITATION)].map((m) => m[1]))];
}
