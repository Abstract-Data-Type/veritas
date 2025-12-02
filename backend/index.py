import sys
import os

# Add src to sys.path so we can import veritas_news
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from veritas_news.main import app
