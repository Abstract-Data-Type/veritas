// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// DOM Elements
const newsFeed = document.getElementById('news-feed');
const loadingIndicator = document.getElementById('loading-indicator');
const errorMessage = document.getElementById('error-message');
const loadMoreButton = document.getElementById('load-more');

// State
let currentPage = 1;
const articlesPerPage = 6;
let allArticles = [];

// Fetch articles from the backend API
async function fetchArticles() {
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}/articles`);
        if (!response.ok) {
            throw new Error('Failed to fetch articles');
        }
        const data = await response.json();
        allArticles = data.articles || [];
        displayArticles();
    } catch (error) {
        console.error('Error fetching articles:', error);
        showError('Failed to load articles. Please try again later.');
    } finally {
        hideLoading();
    }
}

// Display articles in the UI
function displayArticles() {
    const startIndex = (currentPage - 1) * articlesPerPage;
    const endIndex = startIndex + articlesPerPage;
    const articlesToShow = allArticles.slice(0, endIndex);
    
    if (articlesToShow.length === 0) {
        showError('No articles found.');
        return;
    }

    newsFeed.innerHTML = articlesToShow.map(article => createArticleCard(article)).join('');
    
    // Show/hide load more button
    loadMoreButton.style.display = endIndex < allArticles.length ? 'block' : 'none';
}

// Create article card HTML
function createArticleCard(article) {
    const biasClass = getBiasClass(article.biasScore);
    const biasText = getBiasText(article.biasScore);
    const formattedDate = formatDate(article.publishedAt);
    
    return `
        <article class="article-card">
            <img src="${article.imageUrl}" alt="${article.title}" class="article-image">
            <div class="article-content">
                <div class="article-meta">
                    <span class="source">${article.source}</span>
                    <span class="divider">•</span>
                    <span class="date">${formattedDate}</span>
                </div>
                <h2 class="article-title">${article.title}</h2>
                <p class="article-summary">${article.summary}</p>
                <div class="article-footer">
                    <span class="bias-indicator ${biasClass}">${biasText}</span>
                    <a href="${article.url}" class="read-more">Read more</a>
                </div>
            </div>
        </article>
    `;
}

// Get bias class based on score
function getBiasClass(score) {
    if (score <= -0.3) return 'bias-left';
    if (score >= 0.3) return 'bias-right';
    return 'bias-center';
}

// Get bias text based on score
function getBiasText(score) {
    if (score <= -0.6) return 'Strong Left';
    if (score <= -0.3) return 'Left Leaning';
    if (score < 0.3) return 'Centrist';
    if (score < 0.6) return 'Right Leaning';
    return 'Strong Right';
}

// Format date
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Show loading state
function showLoading() {
    loadingIndicator.style.display = 'flex';
    errorMessage.style.display = 'none';
}

// Hide loading state
function hideLoading() {
    loadingIndicator.style.display = 'none';
}

// Show error message
function showError(message) {
    errorMessage.querySelector('p').textContent = message;
    errorMessage.style.display = 'block';
}

// Event Listeners
loadMoreButton.addEventListener('click', () => {
    currentPage++;
    displayArticles();
});

document.getElementById('retry-button').addEventListener('click', fetchArticles);

// Initialize
fetchArticles();
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}/articles`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        displayArticles(data);
    } catch (error) {
        console.error('Error fetching articles:', error);
        showError('Failed to load articles. Please try again later.');
    } finally {
        hideLoading();
    }
}

// Display articles in the UI
function displayArticles(articles) {
    if (!articles || articles.length === 0) {
        newsFeed.innerHTML = '<p class="no-articles">No articles found.</p>';
        return;
    }

    const articlesHTML = articles.map(article => `
        <article class="article-card" data-article-id="${article.id}">
            <div class="article-header">
                <h2 class="article-title">${article.title}</h2>
                <div class="article-source">${article.source}</div>
                <div class="article-date">${new Date(article.publishedAt).toLocaleDateString()}</div>
            </div>
            
            ${article.imageUrl ? `
                <div class="article-image">
                    <img src="${article.imageUrl}" alt="${article.title}">
                </div>` : ''
            }
            
            <div class="article-summary">
                <h3>Summary</h3>
                <p>${article.summary || 'No summary available'}</p>
            </div>
            
            <div class="article-bias">
                <div class="bias-indicator ${getBiasClass(article.biasScore)}">
                    <div class="bias-label">Political Leaning:</div>
                    <div class="bias-value">${formatBias(article.biasScore)}</div>
                    <div class="bias-meter">
                        <div class="bias-track">
                            <div class="bias-thumb" style="left: ${calculateBiasPosition(article.biasScore)}%"></div>
                        </div>
                        <div class="bias-labels">
                            <span>Left</span>
                            <span>Center</span>
                            <span>Right</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="article-actions">
                <a href="/article-detail.html?id=${article.id}" class="read-more">Read Full Analysis</a>
            </div>
        </article>
    `).join('');

    newsFeed.innerHTML = articlesHTML;
}

// Helper functions
function showLoading() {
    loadingIndicator.style.display = 'block';
    newsFeed.style.display = 'none';
    errorMessage.style.display = 'none';
}

function hideLoading() {
    loadingIndicator.style.display = 'none';
    newsFeed.style.display = 'grid';
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    newsFeed.style.display = 'none';
}

function getBiasClass(score) {
    if (score < -0.33) return 'bias-left';
    if (score > 0.33) return 'bias-right';
    return 'bias-center';
}

function formatBias(score) {
    if (score < -0.66) return 'Strong Left';
    if (score < -0.33) return 'Lean Left';
    if (score > 0.66) return 'Strong Right';
    if (score > 0.33) return 'Lean Right';
    return 'Center';
}

function calculateBiasPosition(score) {
    // Convert from [-1, 1] to [0, 100] for percentage
    return ((score + 1) / 2) * 100;
}

// Initialize the news feed when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    fetchArticles();
    
    // Set up auto-refresh every 5 minutes
    setInterval(fetchArticles, 5 * 60 * 1000);
});
