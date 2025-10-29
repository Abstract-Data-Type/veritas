import { filterArticles, searchArticles } from '../src/utils/articleUtils';

const mockArticles = [
  { id: 1, title: 'Climate Change Summit', summary: 'Global leaders meet...', bias: 'left', topics: ['politics', 'environment'] },
  { id: 2, title: 'Tech Breakthrough', summary: 'New AI model...', bias: 'center', topics: ['technology'] },
  { id: 3, title: 'Market Update', summary: 'Stocks reach...', bias: 'right', topics: ['business'] }
];

describe('Article Utils', () => {
  test('filterArticles returns correct articles by topic', () => {
    const filtered = filterArticles(mockArticles, 'technology');
    expect(filtered).toHaveLength(1);
    expect(filtered[0].title).toBe('Tech Breakthrough');
  });

  test('filterArticles returns all articles for "All" topic', () => {
    const filtered = filterArticles(mockArticles, 'All');
    expect(filtered).toHaveLength(3);
  });

  test('searchArticles returns matching articles', () => {
    const results = searchArticles(mockArticles, 'climate');
    expect(results).toHaveLength(1);
    expect(results[0].title).toMatch(/climate/i);
  });

  test('searchArticles is case insensitive', () => {
    const results = searchArticles(mockArticles, 'CLIMATE');
    expect(results).toHaveLength(1);
  });

  test('searchArticles returns empty array for no matches', () => {
    const results = searchArticles(mockArticles, 'nonexistent');
    expect(results).toHaveLength(0);
  });
});