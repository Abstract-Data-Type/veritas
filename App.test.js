import { render, screen, fireEvent } from '@testing-library/dom';
import '@testing-library/jest-dom';
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

// Set up JSDOM
const html = fs.readFileSync(path.resolve(__dirname, '../index.html'), 'utf8');
const dom = new JSDOM(html, { runScripts: 'dangerously' });
global.document = dom.window.document;
global.window = dom.window;

// Load the app.js
require('../app');

describe('App', () => {
  beforeEach(() => {
    document.body.innerHTML = html;
    // Re-initialize the app
    jest.resetModules();
    require('../app');
  });

  test('renders article cards', () => {
    const articleCards = document.querySelectorAll('.article-card');
    expect(articleCards.length).toBeGreaterThan(0);
  });

  test('filters articles by topic', () => {
    const techButton = screen.getByText('Technology');
    fireEvent.click(techButton);
    
    const articleTitles = Array.from(document.querySelectorAll('.article-title'))
      .map(el => el.textContent);
    
    // Should only show tech-related articles
    expect(articleTitles).toContain('Tech Giant Unveils Revolutionary AI Assistant');
  });

  test('toggles save state on button click', () => {
    const saveButtons = document.querySelectorAll('.save-btn');
    const firstButton = saveButtons[0];
    
    // Initial state
    expect(firstButton.textContent).toContain('Save');
    
    // Click to save
    fireEvent.click(firstButton);
    expect(firstButton.textContent).toContain('Saved');
    
    // Click to unsave
    fireEvent.click(firstButton);
    expect(firstButton.textContent).toContain('Save');
  });

  test('searches articles by keyword', () => {
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-bar button');
    
    // Search for "climate"
    fireEvent.change(searchInput, { target: { value: 'climate' } });
    fireEvent.click(searchButton);
    
    const articleTitles = Array.from(document.querySelectorAll('.article-title'))
      .map(el => el.textContent);
    
    // Should only show articles with "climate" in title or summary
    expect(articleTitles).toContain('Climate Change Agreement Reached at Global Summit');
    expect(articleTitles).not.toContain('Tech Giant Unveils Revolutionary AI Assistant');
  });
});