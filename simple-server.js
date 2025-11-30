const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 5000;
const FRONTEND_PATH = path.join(__dirname, 'src', 'frontend');

// Mock data
const mockArticles = {
    articles: [
        {
            id: '1',
            title: 'Global Climate Summit Reaches Historic Agreement',
            source: 'Global News Network',
            publishedAt: '2023-11-25T10:30:00Z',
            imageUrl: 'https://source.unsplash.com/random/800x450/?climate',
            summary: 'World leaders have reached a landmark agreement on climate change policies that could significantly impact global emissions and set new standards for environmental protection.',
            biasScore: 0.7,
            url: '#'
        },
        {
            id: '2',
            title: 'Tech Giant Unveils Revolutionary New Device',
            source: 'Tech Today',
            publishedAt: '2023-11-24T15:45:00Z',
            imageUrl: 'https://source.unsplash.com/random/800x450/?technology',
            summary: 'The latest innovation from the tech industry promises to change how we interact with technology in our daily lives, featuring advanced AI capabilities and a sleek design.',
            biasScore: -0.2,
            url: '#'
        },
        {
            id: '3',
            title: 'New Study Reveals Health Benefits of Mediterranean Diet',
            source: 'Health & Wellness',
            publishedAt: '2023-11-23T09:15:00Z',
            imageUrl: 'https://source.unsplash.com/random/800x450/?food',
            summary: 'Research confirms significant health improvements for those following the traditional Mediterranean eating pattern, including reduced risk of heart disease and improved longevity.',
            biasScore: 0.1,
            url: '#'
        }
    ]
};

const server = http.createServer((req, res) => {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Request-Method', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    res.setHeader('Access-Control-Allow-Headers', '*');

    // Handle preflight requests
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // API endpoint
    if (req.url === '/api/articles' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(mockArticles));
        return;
    }

    // Serve static files
    let filePath = path.join(FRONTEND_PATH, req.url === '/' ? 'index.html' : req.url);
    const extname = path.extname(filePath);
    
    // Default to index.html for any other route
    if (!extname) {
        filePath = path.join(FRONTEND_PATH, 'index.html');
    }

    // Check if file exists
    fs.readFile(filePath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                // Page not found
                fs.readFile(path.join(FRONTEND_PATH, 'index.html'), (err, content) => {
                    res.writeHead(200, { 'Content-Type': 'text/html' });
                    res.end(content, 'utf-8');
                });
            } else {
                // Server error
                res.writeHead(500);
                res.end(`Server Error: ${err.code}`);
            }
        } else {
            // Success
            const contentType = {
                '.html': 'text/html',
                '.js': 'text/javascript',
                '.css': 'text/css',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.wav': 'audio/wav',
                '.mp4': 'video/mp4',
                '.woff': 'application/font-woff',
                '.ttf': 'application/font-ttf',
                '.eot': 'application/vnd.ms-fontobject',
                '.otf': 'application/font-otf',
                '.wasm': 'application/wasm'
            }[extname] || 'application/octet-stream';

            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content, 'utf-8');
        }
    });
});

server.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
    console.log(`API endpoint: http://localhost:${PORT}/api/articles`);
    console.log(`Frontend: http://localhost:${PORT}/`);
});
