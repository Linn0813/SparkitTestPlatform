import { describe, expect, it } from 'vitest';
import { linkLabel, parseUrlsFromText } from './parseUrls';

describe('parseUrlsFromText', () => {
  it('parses two space-separated URLs', () => {
    expect(parseUrlsFromText('https://a.com https://b.com/path')).toEqual([
      'https://a.com',
      'https://b.com/path',
    ]);
  });

  it('parses newline-separated URLs', () => {
    expect(parseUrlsFromText('https://a.com\nhttps://b.com')).toEqual([
      'https://a.com',
      'https://b.com',
    ]);
  });

  it('parses comma-separated URLs', () => {
    expect(parseUrlsFromText('https://a.com, https://b.com')).toEqual([
      'https://a.com',
      'https://b.com',
    ]);
  });

  it('returns single URL when only one present', () => {
    expect(parseUrlsFromText('https://doc.example/prd')).toEqual(['https://doc.example/prd']);
  });

  it('strips trailing punctuation from URLs', () => {
    expect(parseUrlsFromText('见 https://a.com. 与 https://b.com!')).toEqual([
      'https://a.com',
      'https://b.com',
    ]);
  });

  it('returns empty for plain text without URLs', () => {
    expect(parseUrlsFromText('暂无 PRD')).toEqual([]);
  });

  it('deduplicates repeated URLs by default', () => {
    expect(parseUrlsFromText('https://a.com https://a.com')).toEqual(['https://a.com']);
  });

  it('keeps duplicate URLs when dedupe is false', () => {
    expect(parseUrlsFromText('https://a.com https://a.com', { dedupe: false })).toEqual([
      'https://a.com',
      'https://a.com',
    ]);
  });

  it('parses semicolon-separated WeChat-style URLs', () => {
    const url =
      'https://doc.weixin.qq.com/doc/w3_ABC?scode=ANY&isEnterEdit=1; https://doc.weixin.qq.com/doc/w3_XYZ?scode=ANY&isEnterEdit=2;';
    expect(parseUrlsFromText(url, { dedupe: false })).toHaveLength(2);
  });
});

describe('linkLabel', () => {
  it('truncates long URLs', () => {
    const long = 'https://example.com/' + 'x'.repeat(60);
    expect(linkLabel(long, 20).endsWith('…')).toBe(true);
  });
});
