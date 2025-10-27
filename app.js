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
document.addEventListener('DOMContentLoaded', function() {
    // Sample data - in a real app, this would come from your backend
    const articles = [
        {
            id: 1,
            title: "Climate Change Agreement Reached at Global Summit",
            summary: "World leaders have agreed on new climate targets that aim to reduce carbon emissions by 50% by 2030. The agreement includes provisions for developed nations to assist developing countries in their transition to renewable energy sources.",
            source: "Global News Network",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?climate",
            date: "2 hours ago",
            bias: "left",
            biasScore: -0.7,
            saved: false
        },
        {
            id: 2,
            title: "New Study Questions Climate Change Consensus",
            summary: "A peer-reviewed study suggests that climate models may have overestimated the impact of carbon emissions on global temperatures. The research has sparked debate among scientists about the urgency of climate policies.",
            source: "Daily Chronicle",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?research,lab",
            date: "5 hours ago",
            bias: "right",
            biasScore: 0.6,
            saved: false
        },
        {
            id: 3,
            title: "Tech Giant Unveils Revolutionary AI Assistant",
            summary: "The new AI assistant can understand and respond to complex queries with human-like understanding. Early tests show it outperforming existing models in both accuracy and response time.",
            source: "Tech Today",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?ai,technology",
            date: "1 day ago",
            bias: "center",
            biasScore: 0.1,
            saved: true
        },
        {
            id: 4,
            title: "Stock Markets Reach All-Time High",
            summary: "Global markets surged to record levels today following positive economic indicators and strong corporate earnings. Analysts remain cautiously optimistic about sustained growth.",
            source: "Financial Times",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?stock,market",
            date: "3 hours ago",
            bias: "center",
            biasScore: -0.2,
            saved: false
        },
        {
            id: 5,
            title: "Healthcare Reform Bill Passes Senate",
            summary: "The Senate approved a sweeping healthcare reform bill that aims to lower prescription drug costs and expand coverage. The bill now moves to the House where it faces an uncertain future.",
            source: "National Report",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?healthcare,doctor",
            date: "1 day ago",
            bias: "left",
            biasScore: -0.8,
            saved: false
        },
        {
            id: 6,
            title: "Border Security Bill Gains Bipartisan Support",
            summary: "Lawmakers from both parties have reached a compromise on border security funding. The deal includes increased funding for border patrol and new processing centers for asylum seekers.",
            source: "Capital Journal",
            sourceLogo: "https://via.placeholder.com/20",
            image: "https://source.unsplash.com/random/600x400/?border,security",
            date: "4 hours ago",
            bias: "right",
            biasScore: 0.5,
            saved: false
        }
    ];

    const newsFeed = document.getElementById('newsFeed');
    const filterButtons = document.querySelectorAll('.filter-btn');

    // Render articles
    function renderArticles(articlesToRender) {
        newsFeed.innerHTML = '';
        
        articlesToRender.forEach(article => {
            const biasClass = getBiasClass(article.biasScore);
            const biasText = getBiasText(article.biasScore);
            
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
                    // In a real app, you would navigate to the article detail page
                    console.log(`Navigating to article ${articleId}`);
                    // window.location.href = `/article/${articleId}`;
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
            // In a real app, you would filter by actual topic
            // This is just a simple example
            if (topic === 'Politics') {
                return article.id === 1 || article.id === 5 || article.id === 6;
            } else if (topic === 'Technology') {
                return article.id === 3;
            } else if (topic === 'Health') {
                return article.id === 5;
            } else if (topic === 'Business') {
                return article.id === 4;
            } else if (topic === 'Science') {
                return article.id === 2;
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

    // Initial render
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