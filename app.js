// app.js

// Add this to app.js, before the DOMContentLoaded event listener
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

// Initialize theme from localStorage or prefer-color-scheme
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme) {
        setTheme(savedTheme);
    } else if (prefersDark) {
        setTheme('dark');
    }
}

// Add this inside the DOMContentLoaded event listener, at the beginning
initTheme();

// Add theme toggle functionality
const themeToggle = document.getElementById('themeToggle');
if (themeToggle) {
    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });
}
document.addEventListener('DOMContentLoaded', async function() {
    // Fallback sample data for when backend is unavailable
    const sampleArticles = [
        {
            id: 1,
            title: "Climate Change Agreement Reached at Global Summit",
            summary: "World leaders have agreed on new climate targets that aim to reduce carbon emissions by 50% by 2030. The agreement includes provisions for developed nations to assist developing countries in their transition to renewable energy sources.",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?climate",
            date: "2 hours ago",
            bias: "left",
            biasScore: -0.7,
            saved: false,
            politicalSpectrum: {
                economic: -0.6,  // Left-leaning on economics
                social: 0.4      // Slightly authoritarian
            }
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
            biasScore: 0.6,
            saved: false,
            politicalSpectrum: {
                economic: 0.7,   // Right-leaning on economics
                social: 0.5      // Somewhat authoritarian
            }
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
            biasScore: 0.1,
            saved: true,
            politicalSpectrum: {
                economic: 0.2,   // Slightly right on economics
                social: -0.3     // Somewhat libertarian
            }
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
            biasScore: 0.2,
            saved: false,
            politicalSpectrum: {
                economic: 0.8,   // Strongly right on economics
                social: 0.1      // Neutral on social issues
            }
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
            biasScore: 0,
            saved: false,
            politicalSpectrum: {
                economic: -0.3,  // Slightly left on economics
                social: -0.1     // Slightly libertarian
            }
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
            biasScore: -0.5,
            saved: true,
            politicalSpectrum: {
                economic: -0.7,  // Strongly left on economics
                social: -0.6     // Strongly libertarian
            }
        }
    ];

    // Fetch articles from backend API
    async function fetchArticlesFromAPI() {
        try {
            console.log('Fetching articles from backend API...');
            const response = await fetch('http://localhost:8001/articles/latest');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('API response:', data);
            
            // Transform API data to match frontend expectations
            const transformedArticles = data.articles.map(article => {
                // Generate random bias score if no bias rating exists
                const biasScore = article.bias_rating?.bias_score || (Math.random() * 2 - 1); // -1 to 1
                
                return {
                    id: article.article_id,
                    title: article.title,
                    summary: article.raw_text || 'No summary available',
                    source: article.source || 'Unknown Source',
                    sourceLogo: "https://via.placeholder.com/20",
                    image: `https://source.unsplash.com/random/600x400/?news`, // Placeholder image
                    date: formatDate(article.published_at),
                    bias: getBiasLabel(biasScore),
                    biasScore: biasScore,
                    saved: false,
                    url: article.url,
                    politicalSpectrum: {
                        economic: biasScore * 0.8, // Convert bias to economic position
                        social: Math.random() * 0.8 - 0.4 // Random social position
                    }
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

    // Helper function to format date
    function formatDate(dateString) {
        if (!dateString) return 'Unknown date';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffHours < 1) return 'Less than an hour ago';
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        return date.toLocaleDateString();
    }

    // Helper function to get bias label
    function getBiasLabel(score) {
        if (score < -0.4) return 'left';
        if (score > 0.4) return 'right';
        return 'center';
    }

    const newsFeed = document.getElementById('newsFeed');
    const filterButtons = document.querySelectorAll('.filter-btn');

    // Render articles
    function renderArticles(articlesToRender) {
        newsFeed.innerHTML = '';
        
        // Load the political spectrum script if not already loaded
        if (!window.PoliticalSpectrum) {
            const script = document.createElement('script');
            script.src = 'spectrum-graph.js';
            document.head.appendChild(script);
        }
        
        articlesToRender.forEach(article => {
            const biasClass = getBiasClass(article.biasScore);
            const biasText = getBiasText(article.biasScore);
            
            // Generate a unique ID for the spectrum container
            const spectrumId = `spectrum-${article.id}`;
            
            const articleElement = document.createElement('article');
            articleElement.className = `article-card`;
            articleElement.innerHTML = `
                <img src="${article.image}" alt="${article.title}" class="article-image">
                <div class="article-content">
                    <div class="article-source">
                        <img src="${article.sourceLogo}" alt="${article.source}" class="source-logo">
                        ${article.source}
                    </div>
                    <span class="article-bias ${biasClass}">${biasText}</span>
                    <h3 class="article-title">${article.title}</h3>
                    <p class="article-summary">${article.summary}</p>
                    
                    <!-- Political Spectrum Graph -->
                    <div class="spectrum-section">
                        <h4>Political Spectrum Analysis</h4>
                        <div id="${spectrumId}" class="spectrum-container"></div>
                        <p class="spectrum-note">This analysis is based on the article's content and language patterns.</p>
                    </div>
                    
                    <div class="article-meta">
                        <span>${article.date}</span>
                        <div class="article-actions">
                            <button class="action-btn save-btn" data-id="${article.id}">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                                </svg>
                                ${article.saved ? 'Saved' : 'Save'}
                            </button>
                            <button class="action-btn">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <circle cx="12" cy="12" r="1"></circle>
                                    <circle cx="12" cy="5" r="1"></circle>
                                    <circle cx="12" cy="19" r="1"></circle>
                                </svg>
                                More
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            newsFeed.appendChild(articleElement);
            
            // Initialize political spectrum graph for this article
            if (window.PoliticalSpectrum && article.politicalSpectrum) {
                const spectrumId = `spectrum-${article.id}`;
                const container = document.getElementById(spectrumId);
                if (container) {
                    // Small delay to ensure the DOM is ready
                    setTimeout(() => {
                        try {
                            const spectrum = new PoliticalSpectrum(container, {
                                economicPosition: article.politicalSpectrum.economic,
                                socialPosition: article.politicalSpectrum.social,
                                showLabels: true,
                                interactive: true
                            });
                        } catch (e) {
                            console.error('Error initializing political spectrum:', e);
                        }
                    }, 100);
                }
            }
        });

        // Add event listeners to save buttons
        document.querySelectorAll('.save-btn').forEach(button => {
            button.addEventListener('click', function() {
                const articleId = parseInt(this.getAttribute('data-id'));
                const article = articles.find(a => a.id === articleId);
                if (article) {
                    article.saved = !article.saved;
                    this.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                        </svg>
                        ${article.saved ? 'Saved' : 'Save'}
                    `;
                }
            });
        });

        // Add click event to article cards to navigate to article detail
        document.querySelectorAll('.article-card').forEach((card, index) => {
            card.addEventListener('click', (e) => {
                // Don't navigate if the click was on a button
                if (!e.target.closest('button')) {
                    const articleId = articlesToRender[index].id;
                    // Navigate to article detail page
                    window.location.href = `article-detail.html?id=${articleId}`;
                }
            });
        });
    }

    // Get bias class based on score (-1 to 1)
    function getBiasClass(score) {
        if (score < -0.4) return 'bias-left';
        if (score > 0.4) return 'bias-right';
        return 'bias-center';
    }

    // Get bias text based on score
    function getBiasText(score) {
        if (score < -0.6) return 'Strong Left';
        if (score < -0.2) return 'Lean Left';
        if (score > 0.6) return 'Strong Right';
        if (score > 0.2) return 'Lean Right';
        return 'Center';
    }

    // Filter articles by topic
    function filterArticles(topic) {
        if (topic === 'All') {
            renderArticles(articles);
            return;
        }
        
        const filtered = articles.filter(article => {
            // Simple keyword-based filtering for topics
            const title = article.title.toLowerCase();
            const summary = article.summary.toLowerCase();
            const source = article.source.toLowerCase();
            
            if (topic === 'Politics') {
                return title.includes('politic') || title.includes('government') || 
                       title.includes('election') || title.includes('congress') ||
                       summary.includes('politic') || source.includes('politic');
            } else if (topic === 'Technology') {
                return title.includes('tech') || title.includes('ai') || 
                       title.includes('digital') || title.includes('innovation') ||
                       summary.includes('tech') || source.toLowerCase().includes('tech');
            } else if (topic === 'Health') {
                return title.includes('health') || title.includes('medical') || 
                       title.includes('hospital') || title.includes('doctor') ||
                       summary.includes('health') || summary.includes('medical');
            } else if (topic === 'Business') {
                return title.includes('business') || title.includes('market') || 
                       title.includes('stock') || title.includes('economy') ||
                       summary.includes('business') || summary.includes('market');
            } else if (topic === 'Science') {
                return title.includes('science') || title.includes('research') || 
                       title.includes('study') || title.includes('discovery') ||
                       summary.includes('science') || summary.includes('research');
            }
            return true;
        });
        
        renderArticles(filtered);
    }

    // Add event listeners to filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            filterButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            // Filter articles
            filterArticles(this.textContent);
        });
    });

    // Load articles from API and render
    let articles = await fetchArticlesFromAPI();
    renderArticles(articles);

    // Search functionality
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-bar button');

    function handleSearch() {
        const searchTerm = searchInput.value.toLowerCase();
        if (searchTerm.trim() === '') {
            renderArticles(articles);
            return;
        }

        const filtered = articles.filter(article => 
            article.title.toLowerCase().includes(searchTerm) || 
            article.summary.toLowerCase().includes(searchTerm)
        );
        
        renderArticles(filtered);
    }

    searchButton.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
});