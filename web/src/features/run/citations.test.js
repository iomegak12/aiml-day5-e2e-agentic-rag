import { describe, expect, it } from 'vitest';
import { citedIds, linkCitations, parseCiteHref } from './citations';

describe('citations', () => {
  it('turns [KB-ID, location] and [WEB-n] into #cite links', () => {
    const md = linkCitations('Check timers [KB-NET-1005, p. 2] and [WEB-1].');
    expect(md).toBe(
      'Check timers [KB-NET-1005 · p. 2](<#cite-KB-NET-1005|p.%202>) and [WEB-1](<#cite-WEB-1>).',
    );
  });

  it('links IT ticket citations [TKT-000123] and [TICKETS]', () => {
    expect(linkCitations('Open [TKT-000042]; none left [TICKETS].')).toBe(
      'Open [TKT-000042](<#cite-TKT-000042>); none left [TICKETS](<#cite-TICKETS>).',
    );
    expect(citedIds('[TKT-42] is not a ticket citation')).toEqual([]);
  });

  it('leaves fenced code untouched', () => {
    const md = '```\n[KB-NET-1005, p. 2]\n```';
    expect(linkCitations(md)).toBe(md);
  });

  it('round-trips the href', () => {
    expect(parseCiteHref('#cite-KB-MTG-2006|Table%201%20(row%202)')).toEqual({
      id: 'KB-MTG-2006',
      location: 'Table 1 (row 2)',
    });
    expect(parseCiteHref('https://example.com')).toBeNull();
  });

  it('lists unique cited ids in order', () => {
    expect(citedIds('[KB-NET-1010, p.3] x [KB-MTG-2006, p.1] y [KB-NET-1010, p.4]')).toEqual([
      'KB-NET-1010',
      'KB-MTG-2006',
    ]);
  });
});
