// Political Spectrum Graph Module
class PoliticalSpectrum {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
            
        this.options = {
            economicPosition: 0,  // -1 (left) to 1 (right)
            socialPosition: 0,    // -1 (libertarian) to 1 (authoritarian)
            showLabels: true,
            interactive: true,
            ...options
        };

        this.init();
    }

    init() {
        this.createGraph();
        this.updatePosition(this.options.economicPosition, this.options.socialPosition);
        
        if (this.options.interactive) {
            this.setupInteractivity();
        }
    }

    createGraph() {
        // Create the graph container
        this.graph = document.createElement('div');
        this.graph.className = 'spectrum-graph';
        
        // Create axes
        this.graph.innerHTML = `
            <div class="spectrum-axes">
                <div class="axis-x"></div>
                <div class="axis-y"></div>
                ${this.options.showLabels ? `
                    <div class="axis-label top">Authoritarian</div>
                    <div class="axis-label right">Economic Right</div>
                    <div class="axis-label bottom">Libertarian</div>
                    <div class="axis-label left">Economic Left</div>
                ` : ''}
            </div>
            <div class="spectrum-point"></div>
            <div class="spectrum-tooltip"></div>
        `;
        
        this.container.innerHTML = '';
        this.container.appendChild(this.graph);
        this.point = this.container.querySelector('.spectrum-point');
        this.tooltip = this.container.querySelector('.spectrum-tooltip');
    }

    updatePosition(economic, social) {
        // Ensure values are within bounds
        const economicPos = Math.max(-1, Math.min(1, economic));
        const socialPos = Math.max(-1, Math.min(1, social));
        
        // Calculate positions (0-100% from top/left)
        const x = 50 + (economicPos * 50);
        const y = 50 - (socialPos * 50);
        
        // Update point position
        this.point.style.left = `${x}%`;
        this.point.style.top = `${y}%`;
        
        // Update tooltip
        const economicLabel = economicPos < 0 ? 'Left' : 'Right';
        const socialLabel = socialPos < 0 ? 'Libertarian' : 'Authoritarian';
        this.tooltip.textContent = `${Math.abs(Math.round(economicPos * 100))}% ${economicLabel}, ${Math.abs(Math.round(socialPos * 100))}% ${socialLabel}`;
        
        // Position tooltip above the point
        const tooltipY = y < 30 ? y + 10 : y - 10;
        const tooltipX = x > 70 ? 'auto' : (x < 30 ? 'auto' : x);
        const tooltipRight = x > 70 ? '10px' : 'auto';
        const tooltipLeft = x < 30 ? '10px' : 'auto';
        
        this.tooltip.style.top = `${tooltipY}%`;
        this.tooltip.style.left = tooltipX === 'auto' ? 'auto' : `${tooltipX}%`;
        this.tooltip.style.right = tooltipRight;
        this.tooltip.style.left = tooltipLeft;
        this.tooltip.style.transform = `translateX(${x > 70 ? 0 : (x < 30 ? 0 : '-50%')}) translateY(${y < 30 ? '0' : '-100%'})`;
        
        // Update colors based on quadrant
        this.updatePointColor(economicPos, socialPos);
    }
    
    updatePointColor(economicPos, socialPos) {
        // Calculate color based on position
        // Using HSL color model for smooth transitions
        let hue = 0;
        let saturation = 80;
        let lightness = 50;
        
        if (economicPos >= 0 && socialPos >= 0) {
            // Top-right (Authoritarian Right) - Red
            hue = 0;
        } else if (economicPos < 0 && socialPos >= 0) {
            // Top-left (Authoritarian Left) - Blue
            hue = 240;
        } else if (economicPos < 0 && socialPos < 0) {
            // Bottom-left (Libertarian Left) - Green
            hue = 120;
        } else {
            // Bottom-right (Libertarian Right) - Purple
            hue = 280;
        }
        
        // Adjust saturation and lightness based on distance from center
        const distance = Math.sqrt(economicPos * economicPos + socialPos * socialPos) / Math.SQRT2;
        saturation = 80 + (distance * 20);
        lightness = 60 - (distance * 10);
        
        this.point.style.backgroundColor = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
        this.point.style.boxShadow = `0 0 8px hsla(${hue}, ${saturation}%, ${lightness}%, 0.5)`;
    }
    
    setupInteractivity() {
        let isDragging = false;
        
        const onMouseDown = (e) => {
            isDragging = true;
            this.graph.classList.add('dragging');
            this.updateFromEvent(e);
            e.preventDefault();
        };
        
        const onMouseMove = (e) => {
            if (!isDragging) return;
            this.updateFromEvent(e);
            e.preventDefault();
        };
        
        const onMouseUp = () => {
            isDragging = false;
            this.graph.classList.remove('dragging');
        };
        
        // For touch devices
        const onTouchStart = (e) => {
            isDragging = true;
            this.graph.classList.add('dragging');
            this.updateFromEvent(e.touches[0]);
            e.preventDefault();
        };
        
        const onTouchMove = (e) => {
            if (!isDragging) return;
            this.updateFromEvent(e.touches[0]);
            e.preventDefault();
        };
        
        this.graph.addEventListener('mousedown', onMouseDown);
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        
        this.graph.addEventListener('touchstart', onTouchStart, { passive: false });
        this.graph.addEventListener('touchmove', onTouchMove, { passive: false });
        document.addEventListener('touchend', onMouseUp);
        
        // Prevent scrolling when interacting with the graph on touch devices
        this.graph.addEventListener('touchstart', (e) => {
            if (e.target === this.graph || this.graph.contains(e.target)) {
                e.preventDefault();
            }
        }, { passive: false });
    }
    
    updateFromEvent(e) {
        const rect = this.graph.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        
        // Convert to -1 to 1 range
        const economicPos = (x * 2) - 1;
        const socialPos = 1 - (y * 2); // Invert Y axis
        
        this.updatePosition(economicPos, socialPos);
        
        // Dispatch custom event
        const event = new CustomEvent('positionChange', {
            detail: {
                economic: economicPos,
                social: socialPos
            }
        });
        this.container.dispatchEvent(event);
    }
    
    // Public method to update the graph position programmatically
    setPosition(economic, social) {
        this.updatePosition(economic, social);
    }
    
    // Public method to get current position
    getPosition() {
        const x = parseFloat(this.point.style.left) / 100;
        const y = parseFloat(this.point.style.top) / 100;
        
        return {
            economic: (x * 2) - 1,
            social: 1 - (y * 2)
        };
    }
}

// Export for ES modules
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
    module.exports = PoliticalSpectrum;
} else {
    window.PoliticalSpectrum = PoliticalSpectrum;
}
