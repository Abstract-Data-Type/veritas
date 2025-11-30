const express = require('express');
const cors = require('cors');
const path = require('path');
const app = express();
const port = 5000;

// Enable CORS for all routes
app.use(cors());

// Serve static files from the src/frontend directory
app.use(express.static(path.join(__dirname, 'src/frontend')));

// Mock API endpoint
app.get('/api/articles', (req, res) => {
    const mockArticles = [
        {
            id: '1',
            title: 'Global Climate Summit Reaches Historic Agreement',
            source: 'Global News Network',
            publishedAt: '2023-11-25T10:30:00Z',
            imageUrl: 'https://source.unsplash.com/random/800x450/?climate',
            summary: 'World leaders have reached a landmark agreement on climate change policies that could significantly impact global emissions and set new standards for environmental protection.',
            biasScore: 0.7, // Right-leaning
            url: '#'
        },
        {
            id: '2',
            title: 'Tech Giant Unveils Revolutionary New Device',
            source: 'Tech Today',
            publishedAt: '2023-11-24T15:45:00Z',
            imageUrl: 'https://source.unsplash.com/random/800x450/?technology',
            summary: 'The latest innovation from the tech industry promises to change how we interact with technology in our daily lives, featuring advanced AI capabilities and a sleek design.',
            biasScore: -0.2, // Slightly left-leaning
            url: '#'
        },
        {
            id: '3',
            title: 'New Study Reveals Health Benefits of Mediterranean Diet',
            source: 'Health & Wellness',
            publishedAt: '2023-11-23T09:15:00Z',
            imageUrl: 'https://source.unsplash.com/random/800x450/?food',
            summary: 'Research confirms significant health improvements for those following the traditional Mediterranean eating pattern, including reduced risk of heart disease and improved longevity.',
            biasScore: 0.1, // Centrist
            url: '#'
        }
    ];
    
    res.json({ articles: mockArticles });
});

// Serve the main HTML file for any other GET request
app.get('*', (req, res, next) => {
    // Skip API routes
    if (req.path.startsWith('/api')) return next();
    
    // Serve the frontend for all other routes
    res.sendFile(path.join(__dirname, 'src/frontend/index.html'));
});

app.listen(port, () => {
    console.log(`Mock server running at http://localhost:${port}`);
    console.log(`API endpoint: http://localhost:${port}/api/articles`);
});
