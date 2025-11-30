// app.js

// ---------- THEME HELPERS (optional) ----------
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia &&
        window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme) {
        setTheme(savedTheme);
    } else if (prefersDark) {
        setTheme('dark');
    } else {
        setTheme('light');
    }
}

// ---------- APP ----------
document.addEventListener('DOMContentLoaded', async function () {
    // Init theme
    initTheme();

    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            setTheme(currentTheme === 'dark' ? 'light' : 'dark');
        });
    }

    // ---------- SAMPLE DATA ----------
    const sampleArticles = [
        {
            id: 1,
            title: "Climate Change Agreement Reached at Global Summit",
            summary: "World leaders have agreed on new climate targets that aim to reduce carbon emissions by 50% by 2030. The agreement includes provisions for developed nations to assist developing countries in their transition to renewable energy sources.",
            source: "Global Times",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?climate",
            date: "2 hours ago",
            bias: "left",
            biasScore: -0.7
        },
        {
            id: 2,
            title: "New Study Questions Climate Change Consensus",
            summary: "A peer-reviewed study suggests that climate models may have overestimated the impact of carbon emissions on global temperatures. The research has sparked debate among scientist about the urgency of climate policies.",
            source: "National Report",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?science",
            date: "5 hours ago",
            bias: "right",
            biasScore: 0.6
        },
        {
            id: 3,
            title: "Tech Giant Unveils Revolutionary AI Assistant",
            summary: "The new AI assistant can understand and respond to complex queries with human-like understanding. Experts say this represents a significant leap forward in natural language processing technology.",
            source: "Tech Today",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?ai",
            date: "1 day ago",
            bias: "center",
            biasScore: 0.1
        },
        {
            id: 4,
            title: "Stock Market Reaches All-Time High",
            summary: "The S&P 500 hit a new record high today, driven by strong earnings reports from major tech companies. Analysts remain optimistic about the market's performance for the rest of the year.",
            source: "Financial Times",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?stock-market",
            date: "3 hours ago",
            bias: "center",
            biasScore: 0.2
        },
        {
            id: 5,
            title: "New Healthcare Bill Faces Opposition",
            summary: "Proposed healthcare legislation has drawn criticism from both sides of the aisle, with progressives calling for more comprehensive coverage and conservatives concerned about costs. The bill's future remains uncertain as negotiations continue.",
            source: "Capital Journal",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?healthcare",
            date: "7 hours ago",
            bias: "center",
            biasScore: 0
        },
        {
            id: 6,
            title: "Breakthrough in Renewable Energy Storage",
            summary: "Scientists have developed a new battery technology that could make renewable energy more viable by solving the storage problem. The innovation could accelerate the transition away from fossil fuels.",
            source: "Eco News",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?renewable-energy",
            date: "1 day ago",
            bias: "left",
            biasScore: -0.5
        }
    ];

    // ---------- HELPERS ----------
    function formatDate(dateString) {
        if (!dateString) return 'Unknown date';

        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            // Already something like "2 hours ago" etc
            return dateString;
        }

        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 1) return 'Less than an hour ago';
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        return date.toLocaleDateString();
    }

    function getBiasLabel(score) {
        if (score < -0.4) return 'left';
        if (score > 0.4) return 'right';
        return 'center';
    }

    // Fetch from backend, fall back to sample data
    async function fetchArticlesFromAPI() {
        try {
            console.log('Fetching articles from backend API...');
            const response = await fetch('http://localhost:8001/articles/latest');

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('API response:', data);

            const transformedArticles = (data.articles || []).map(article => {
                const biasScore =
                    (article.bias_rating && typeof article.bias_rating.bias_score === 'number')
                        ? article.bias_rating.bias_score
                        : (Math.random() * 2 - 1);

                return {
                    id: article.article_id,
                    title: article.title,
                    summary: article.raw_text || 'No summary available',
                    source: article.source || 'Unknown Source',
                    sourceLogo: "https://via.placeholder.com/20",
                    image: `https://source.unsplash.com/random/600x400/?news`,
                    date: formatDate(article.published_at),
                    bias: getBiasLabel(biasScore),
                    biasScore: biasScore,
                    url: article.url
                };
            });

            console.log('Transformed articles:', transformedArticles);
            return transformedArticles;
        } catch (error) {
            console.error('Error fetching articles from API:', error);
            console.log('Falling back to sample data');
            return sampleArticles;
        }
    }

    // ---------- DOM ELEMENTS ----------
    const newsFeed = document.getElementById('newsFeed');
    const categoryButtons = document.querySelectorAll('.category-btn');
    const searchInput = document.querySelector('.search-bar input');

    // ---------- RENDER ----------
    function renderArticles(articlesToRender) {
        if (!newsFeed) return;

        newsFeed.innerHTML = '';

        articlesToRender.forEach(article => {
            const articleElement = document.createElement('article');
            articleElement.className = 'article-card';
            articleElement.innerHTML = `
                <div class="article-tags">
                    <span class="tag">${(article.bias || '').toUpperCase()}</span>
                    <span class="tag">${article.source || ''}</span>
                </div>
                <div class="article-content">
                    <h3 class="article-title">${article.title}</h3>
                    <div class="article-meta">${article.date}</div>
                    <p class="article-summary">${article.summary}</p>
                    <a href="${article.url || '#'}" class="read-more" target="_blank" rel="noopener noreferrer">
                        Read Full Article <i class="fas fa-chevron-right"></i>
                    </a>
                </div>
            `;
            newsFeed.appendChild(articleElement);
        });
    }

    function filterArticlesByTopic(topic, allArticles) {
        if (topic === 'All') {
            renderArticles(allArticles);
            return;
        }

        const filtered = allArticles.filter(article => {
            const title = article.title.toLowerCase();
            const summary = article.summary.toLowerCase();
            const source = (article.source || '').toLowerCase();

            switch (topic) {
                case 'Politics':
                    return title.includes('politic') || title.includes('government') ||
                        title.includes('election') || summary.includes('politic') ||
                        source.includes('politic');
                case 'Business':
                    return title.includes('business') || title.includes('market') ||
                        title.includes('stock') || summary.includes('business') ||
                        summary.includes('market');
                case 'Technology':
                    return title.includes('tech') || title.includes('ai') ||
                        title.includes('digital') || title.includes('innovation') ||
                        summary.includes('tech') || source.includes('tech');
                case 'Science':
                    return title.includes('science') || title.includes('research') ||
                        title.includes('study') || title.includes('discovery') ||
                        summary.includes('science') || summary.includes('research');
                case 'Health':
                    return title.includes('health') || title.includes('medical') ||
                        title.includes('hospital') || summary.includes('health') ||
                        summary.includes('medical');
                default:
                    return true;
            }
        });

        renderArticles(filtered);
    }

    // ---------- DATA & INITIAL RENDER ----------
    let articles = [];

    // Show loading state
    if (newsFeed) {
        newsFeed.innerHTML = '<div class="loading-indicator">Loading articles...</div>';
    }

    try {
        const fetchedArticles = await fetchArticlesFromAPI();
        // If API returns empty list, fall back to sample data (for demo purposes)
        if (fetchedArticles && fetchedArticles.length > 0) {
            articles = fetchedArticles;
        } else {
            console.log('API returned empty list, using sample data');
            articles = sampleArticles;
        }
    } catch (e) {
        console.error('Fatal error fetching articles:', e);
        articles = sampleArticles;
    }

    renderArticles(articles);

    // ---------- CATEGORY FILTER EVENTS ----------
    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            categoryButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            const topic = button.dataset.topic || 'All';
            filterArticlesByTopic(topic, articles);
        });
    });

    // ---------- SEARCH ----------
    function handleSearch() {
        if (!articles || articles.length === 0) return;

        const term = (searchInput?.value || '').toLowerCase().trim();
        console.log('Search term:', term);
        console.log('Total articles available:', articles.length);

        // Empty search → show everything again
        if (!term) {
            console.log('Clearing search, showing all articles');
            renderArticles(articles);
            return;
        }

        const filtered = articles.filter(article => {
            const text = `${article.title} ${article.summary} ${article.source || ''}`.toLowerCase();
            return text.includes(term);
        });

        if (filtered.length === 0) {
            newsFeed.innerHTML = `
                <div class="no-results">
                    <p>No articles found matching "${term}"</p>
                    <button class="clear-search-btn">Clear Search</button>
                </div>
            `;
            // Add listener to the clear button
            document.querySelector('.clear-search-btn')?.addEventListener('click', () => {
                searchInput.value = '';
                renderArticles(articles);
                searchInput.focus();
            });
            return;
        }

        console.log('Filtered count:', filtered.length);
        renderArticles(filtered);
    }

    if (searchInput) {
        // Live search as you type
        searchInput.addEventListener('input', handleSearch);

        // Handle 'x' button clear in some browsers
        searchInput.addEventListener('search', handleSearch);

        // Also search on Enter
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSearch();
            }
        });
    }
});
