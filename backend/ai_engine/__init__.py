from pathlib import Path

# Define storage directory
STORAGE_DIR = Path(__file__).parent / ".." / "data" / "simple"

from .ai_engine import ask_ai, ask_ai_streaming, learn_from_interaction, load_or_build_index
from .index import load_or_build_index as load_index
from .component_recommender import DigiKeyComponentRecommender