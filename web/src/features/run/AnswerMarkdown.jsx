import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Icon } from '../../components/ui';
import { linkCitations, parseCiteHref } from './citations';

/**
 * The agent's Markdown answer. Raw HTML is never rendered (react-markdown default), so model output cannot
 * inject markup. Citations become chips; clicking one calls onCite(id).
 */
export function AnswerMarkdown({ text, onCite }) {
  return (
    <div className="prose-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {
            const cite = parseCiteHref(href);
            if (cite) {
              return (
                <button
                  type="button"
                  onClick={() => onCite?.(cite.id)}
                  title={`Show source ${cite.id}`}
                  className="mx-0.5 inline-flex items-center gap-1 rounded-md border border-line bg-well px-1.5 py-0 align-baseline font-mono text-[12px] leading-5 text-ink hover:border-line-strong"
                >
                  <Icon name="menu_book" className="text-[14px]!" />
                  {children}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {linkCitations(text)}
      </ReactMarkdown>
    </div>
  );
}
