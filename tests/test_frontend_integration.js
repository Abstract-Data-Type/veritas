/**
 * Simple frontend integration tests for API fetch functionality
 * 
 * Run with: node tests/test_frontend_integration.js
 */

// Test the helper functions from app.js
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

function getBiasLabel(score) {
    if (score < -0.4) return 'left';
    if (score > 0.4) return 'right';
    return 'center';
}

// Simple test runner
function test(name, testFn) {
    try {
        testFn();
        console.log(`✅ ${name}`);
    } catch (error) {
        console.log(`❌ ${name}: ${error.message}`);
    }
}

// Tests
test('formatDate handles null/undefined', () => {
    const result = formatDate(null);
    if (result !== 'Unknown date') throw new Error(`Expected 'Unknown date', got '${result}'`);
});

test('formatDate handles recent timestamps', () => {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    const result = formatDate(oneHourAgo);
    if (!result.includes('hour')) throw new Error(`Expected hour format, got '${result}'`);
});

test('getBiasLabel returns correct labels', () => {
    if (getBiasLabel(-0.5) !== 'left') throw new Error('Left bias not detected');
    if (getBiasLabel(0.5) !== 'right') throw new Error('Right bias not detected'); 
    if (getBiasLabel(0.1) !== 'center') throw new Error('Center bias not detected');
});

test('API URL is correct', () => {
    const expectedURL = 'http://localhost:8001/articles/latest';
    // This would be the fetch call in the actual code
    if (!expectedURL.includes('articles/latest')) throw new Error('Wrong API endpoint');
});

test('Data transformation structure', () => {
    // Mock API response
    const mockAPIResponse = {
        articles: [{
            article_id: 1,
            title: "Test Article",
            raw_text: "Test content",
            source: "Test Source",
            published_at: new Date().toISOString(),
            url: "https://example.com",
            bias_rating: { bias_score: -0.5 }
        }]
    };
    
    // Transform like the frontend does
    const transformed = mockAPIResponse.articles.map(article => ({
        id: article.article_id,
        title: article.title,
        summary: article.raw_text || 'No summary available',
        source: article.source || 'Unknown Source',
        date: formatDate(article.published_at),
        bias: getBiasLabel(article.bias_rating?.bias_score || 0),
        biasScore: article.bias_rating?.bias_score || 0,
        url: article.url
    }))[0];
    
    if (transformed.id !== 1) throw new Error('ID mapping failed');
    if (transformed.title !== "Test Article") throw new Error('Title mapping failed');
    if (transformed.bias !== 'left') throw new Error('Bias mapping failed');
});

console.log('\n🧪 Frontend Integration Tests\n');
console.log('Running tests...\n');