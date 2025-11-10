// Article Detail Page JavaScript

// Sample data for different outlets covering the same story
const sampleArticleData = {
    1: {
        title: "Climate Change Agreement Reached at Global Summit",
        unbiasedSummary: "World leaders at the Global Climate Summit have reached a consensus on new environmental targets. The agreement establishes a framework for reducing global carbon emissions by 50% by 2030, with specific provisions for financial assistance from developed to developing nations. The accord includes binding commitments for renewable energy adoption and creates monitoring mechanisms for implementation. Key provisions include technology transfer agreements, carbon pricing mechanisms, and adaptation funding for vulnerable countries.",
        publishedDate: "2 hours ago",
        category: "Environment",
        tags: ["Climate Change", "International Relations", "Environment Policy", "Global Summit"],
        outlets: [
            {
                id: 1,
                name: "CNN",
                logo: "https://via.placeholder.com/32",
                bias: "left",
                biasScore: -0.6,
                summary: "Historic climate agreement marks unprecedented global cooperation in fighting climate crisis. World leaders unite to combat existential threat to humanity with ambitious emission reduction targets. The deal represents a victory for environmental activists and progressive climate policies, showing that urgent action is possible when nations prioritize the planet over profits.",
                publishedTime: "2 hours ago",
                url: "https://cnn.com/sample-climate-article",
                keyQuotes: [
                    "This agreement represents humanity's last, best hope to avert climate catastrophe",
                    "Developed nations must lead by example in this crucial transition"
                ]
            },
            {
                id: 2,
                name: "BBC News",
                logo: "https://via.placeholder.com/32",
                bias: "center",
                biasScore: 0.1,
                summary: "International climate summit concludes with agreement on emission reduction targets. The accord sets framework for global cooperation on environmental issues, though implementation challenges remain. Nations have committed to specific targets while acknowledging economic and technological hurdles that must be addressed through coordinated international effort.",
                publishedTime: "1.5 hours ago",
                url: "https://bbc.com/sample-climate-article",
                keyQuotes: [
                    "The agreement balances environmental necessity with economic realities",
                    "Success will depend on effective implementation and monitoring"
                ]
            },
            {
                id: 3,
                name: "Fox News",
                logo: "https://via.placeholder.com/32",
                bias: "right",
                biasScore: 0.7,
                summary: "Climate summit produces costly agreement that could burden American taxpayers and businesses. The deal imposes significant financial obligations on developed nations while allowing developing countries more lenient standards. Critics warn the agreement may harm economic competitiveness and job creation in key industries without guaranteeing meaningful environmental results.",
                publishedTime: "2.5 hours ago",
                url: "https://foxnews.com/sample-climate-article",
                keyQuotes: [
                    "American families will bear the cost of this expensive international commitment",
                    "The agreement creates unfair advantages for competing economies"
                ]
            },
            {
                id: 4,
                name: "Reuters",
                logo: "https://via.placeholder.com/32",
                bias: "center",
                biasScore: -0.1,
                summary: "Global climate summit reaches agreement on emission reduction framework after extended negotiations. The accord establishes measurable targets and financing mechanisms, though questions remain about enforcement and compliance monitoring. Market analysts note potential impacts on energy sector investments and international trade patterns.",
                publishedTime: "1 hour ago",
                url: "https://reuters.com/sample-climate-article",
                keyQuotes: [
                    "The framework provides structure while allowing flexibility for individual nations",
                    "Implementation will require sustained political commitment across administrations"
                ]
            }
        ],
        sources: [
            {
                type: "Official Document",
                title: "Global Climate Summit Final Declaration",
                url: "https://climate-summit.org/final-declaration-2024",
                description: "Complete text of the official agreement reached at the summit"
            },
            {
                type: "Research",
                title: "IPCC Climate Assessment Report 2024",
                url: "https://ipcc.ch/assessment-2024",
                description: "Scientific basis for the emission reduction targets"
            },
            {
                type: "Government",
                title: "US State Department Climate Policy Statement",
                url: "https://state.gov/climate-policy-2024",
                description: "Official US government position on the agreement"
            },
            {
                type: "Academic",
                title: "Economic Impact Analysis - MIT Climate Lab",
                url: "https://climate.mit.edu/economic-impact-2024",
                description: "Independent analysis of economic implications"
            }
        ]
    },
    // Add more sample data for other articles as needed
    2: {
        title: "New Study Questions Climate Change Consensus",
        unbiasedSummary: "A peer-reviewed study published in the Journal of Climate Science has presented alternative interpretations of recent climate data. The research, conducted by a team of atmospheric scientists, suggests that current climate models may not fully account for natural climate variability. While the study does not dispute the reality of climate change, it raises questions about the precision of temperature projections and the relative contributions of human versus natural factors.",
        publishedDate: "5 hours ago",
        category: "Science",
        tags: ["Climate Science", "Research", "Scientific Debate", "Climate Models"],
        outlets: [
            {
                id: 1,
                name: "Wall Street Journal",
                logo: "https://via.placeholder.com/32",
                bias: "right",
                biasScore: 0.5,
                summary: "New scientific research challenges prevailing climate orthodoxy, suggesting models may overestimate human impact. The peer-reviewed study raises important questions about the reliability of climate projections that have driven costly policy decisions. Scientists call for more balanced approach to climate policy that accounts for natural variability.",
                publishedTime: "5 hours ago",
                url: "https://wsj.com/sample-climate-study",
                keyQuotes: [
                    "The study highlights significant uncertainties in current climate modeling",
                    "Policy decisions should be based on complete scientific understanding"
                ]
            },
            {
                id: 2,
                name: "The Guardian",
                logo: "https://via.placeholder.com/32",
                bias: "left",
                biasScore: -0.7,
                summary: "Climate denial study funded by fossil fuel interests attempts to undermine scientific consensus. Despite peer review, experts note serious methodological flaws and question the research's timing amid crucial climate negotiations. The overwhelming majority of climate scientists maintain that urgent action remains necessary to prevent catastrophic warming.",
                publishedTime: "4.5 hours ago",
                url: "https://guardian.com/sample-climate-study",
                keyQuotes: [
                    "This study appears designed to create doubt during critical climate talks",
                    "The scientific consensus on climate change remains overwhelming"
                ]
            }
        ],
        sources: [
            {
                type: "Research Paper",
                title: "Natural Climate Variability and Model Uncertainty",
                url: "https://journal-climate.org/study-2024",
                description: "Original peer-reviewed research paper"
            },
            {
                type: "Academic Response",
                title: "Climate Science Community Response",
                url: "https://climate-scientists.org/response-2024",
                description: "Peer response from climate science community"
            }
        ]
    }
};

// Get article ID from URL parameters
function getArticleId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('id') || '1'; // Default to article 1 if no ID provided
}

// Get bias text and class
function getBiasText(score) {
    if (score < -0.6) return 'Strong Left';
    if (score < -0.2) return 'Lean Left';
    if (score > 0.6) return 'Strong Right';
    if (score > 0.2) return 'Lean Right';
    return 'Center';
}

function getBiasClass(score) {
    if (score < -0.2) return 'left';
    if (score > 0.2) return 'right';
    return 'center';
}

// Initialize theme (same as main app)
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme) {
        setTheme(savedTheme);
    } else if (prefersDark) {
        setTheme('dark');
    }
}

// Render the article detail page
function renderArticleDetail(articleData) {
    const container = document.getElementById('articleDetailContent');
    const breadcrumb = document.getElementById('articleBreadcrumb');
    
    // Update breadcrumb
    breadcrumb.textContent = articleData.title;
    
    // Create the main content
    container.innerHTML = `
        <a href="index.html" class="back-nav">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Back to News Feed
        </a>

        <!-- Unbiased Summary Section -->
        <section class="unbiased-summary">
            <h1>${articleData.title}</h1>
            <div class="summary-meta">
                <span>📅 ${articleData.publishedDate}</span>
                <span>📂 ${articleData.category}</span>
                <span>📰 ${articleData.outlets.length} outlets covering</span>
            </div>
            <div class="summary-text">
                ${articleData.unbiasedSummary}
            </div>
            <div class="summary-tags">
                ${articleData.tags.map(tag => `<span class="summary-tag">${tag}</span>`).join('')}
            </div>
        </section>

        <!-- Source Coverage Section -->
        <section class="source-coverage">
            <h2>
                News Outlet Coverage
                <span class="coverage-count">${articleData.outlets.length} Sources</span>
            </h2>
            
            <!-- Bias Legend -->
            <div class="bias-legend-detail">
                <div class="legend-item-detail">
                    <span class="legend-color-detail left"></span>
                    <span>Left Leaning</span>
                </div>
                <div class="legend-item-detail">
                    <span class="legend-color-detail center"></span>
                    <span>Center</span>
                </div>
                <div class="legend-item-detail">
                    <span class="legend-color-detail right"></span>
                    <span>Right Leaning</span>
                </div>
            </div>

            <!-- Outlet Grid -->
            <div class="outlet-grid">
                ${articleData.outlets.map(outlet => `
                    <div class="outlet-card">
                        <div class="outlet-header">
                            <div class="outlet-info">
                                <img src="${outlet.logo}" alt="${outlet.name}" class="outlet-logo">
                                <span class="outlet-name">${outlet.name}</span>
                            </div>
                            <span class="outlet-bias ${getBiasClass(outlet.biasScore)}">${getBiasText(outlet.biasScore)}</span>
                        </div>
                        
                        <div class="outlet-summary">${outlet.summary}</div>
                        
                        <div class="outlet-meta">
                            <span>Published: ${outlet.publishedTime}</span>
                            <span>Bias Score: ${outlet.biasScore > 0 ? '+' : ''}${outlet.biasScore}</span>
                        </div>

                        ${outlet.keyQuotes && outlet.keyQuotes.length > 0 ? `
                            <div style="margin: 1rem 0;">
                                <strong>Key Quotes:</strong>
                                <ul style="margin: 0.5rem 0; padding-left: 1.5rem; font-style: italic; font-size: 0.9rem;">
                                    ${outlet.keyQuotes.map(quote => `<li>"${quote}"</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        <div class="outlet-actions">
                            <button class="outlet-btn" onclick="window.open('${outlet.url}', '_blank')">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/>
                                </svg>
                                Read Original
                            </button>
                            <button class="outlet-btn secondary" onclick="showOutletAnalysis('${outlet.name}')">
                                📊 Analysis
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        </section>

        <!-- Sources and Citations -->
        <section class="sources-section">
            <h2>📚 Sources and References</h2>
            <div class="sources-list">
                ${articleData.sources.map(source => `
                    <div class="source-item">
                        <svg class="source-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14,2 14,8 20,8"></polyline>
                            <line x1="16" y1="13" x2="8" y2="13"></line>
                            <line x1="16" y1="17" x2="8" y2="17"></line>
                            <polyline points="10,9 9,9 8,9"></polyline>
                        </svg>
                        <div style="flex: 1;">
                            <a href="${source.url}" target="_blank" class="source-link">${source.title}</a>
                            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem;">
                                ${source.description}
                            </div>
                        </div>
                        <span class="source-type">${source.type}</span>
                    </div>
                `).join('')}
            </div>
        </section>
    `;
}

// Show outlet analysis (placeholder function)
function showOutletAnalysis(outletName) {
    alert(`Detailed bias analysis for ${outletName} would be shown here. This feature shows the methodology behind bias scoring and linguistic analysis patterns.`);
}

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme
    initTheme();
    
    // Add theme toggle functionality
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            setTheme(currentTheme === 'dark' ? 'light' : 'dark');
        });
    }
    
    // Get article ID and render content
    const articleId = getArticleId();
    const articleData = sampleArticleData[articleId];
    
    if (articleData) {
        renderArticleDetail(articleData);
        // Update page title
        document.title = `${articleData.title} - Perspectiva`;
    } else {
        // Handle case where article not found
        document.getElementById('articleDetailContent').innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <h2>Article Not Found</h2>
                <p>The requested article could not be found.</p>
                <a href="index.html" class="back-nav">Back to News Feed</a>
            </div>
        `;
    }
});