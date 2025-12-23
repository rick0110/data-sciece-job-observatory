"""Script to generate embeddings from the unified dataset.

This script loads `vagas_unificadas.csv` and generates embeddings using a
Sentence-Transformers model for use in the vector search system.

Usage:
    python -m data_treatment.generate_embeddings
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
from tqdm import tqdm


def get_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / 'data').exists():
            return parent
    return Path.cwd()

PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / 'data'


def generate_embeddings(
    input_path: str = "./data/vagas_unificadas.csv",
    output_path: str = "./data/embeddings.npy",
    model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    batch_size: int = 32,
) -> np.ndarray:
    """Generate embeddings for all job postings in the unified dataset.

    Args:
        input_path: Path to the unified CSV file.
        output_path: Path where the .npy file with embeddings will be saved.
        model_name: Sentence-Transformers model identifier to use.
        batch_size: Batch size for encoding.

    Returns:
        NumPy array containing the embeddings.
    """
    print("=" * 60)
    print("GENERATING EMBEDDINGS")
    print("=" * 60)
    
    # Load data
    print(f"\nLoading data from: {input_path}")
    df = pd.read_csv(input_path)
    print(f"  → {len(df)} loaded")
    
    # Load model
    print(f"\nLoading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Prepare texts for embedding
    print("\nPreparing texts for embedding...")
    
    def create_embedding_text(row):
        """Create an optimized text for embedding by combining relevant fields."""
        parts = []
        
        # role
        if pd.notna(row.get("role")):
            parts.append(str(row["role"]))
        
        # Seniority level
        if pd.notna(row.get("seniority")):
            parts.append(str(row["seniority"]))
        
        # Region
        if pd.notna(row.get("region")):
            parts.append(str(row["region"]))
        
        # work_modality
        if pd.notna(row.get("work_model")):
            parts.append(str(row["work_model"]))
        
        # Technologies
        if pd.notna(row.get("technologies")) and row.get("technologies") != "not_specified":
            parts.append(str(row["technologies"]))
        
        # Benefits
        if pd.notna(row.get("benefits")) and row.get("benefits") != "not_specified":
            parts.append(str(row["benefits"]))
        
        # Description (if available and not too long)
        if pd.notna(row.get("description")):
            desc = str(row["description"])
            # Truncate description if too long
            if len(desc) > 500:
                desc = desc[:500]
            parts.append(desc)
        
        return " ".join(parts)
    
    texts = []
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Preparando textos"):
        text = create_embedding_text(row)
        texts.append(text)
    
    # generate embeddings
    print(f"\nGenerating embeddings (batch_size={batch_size})...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    
    # Save embeddings
    print(f"\nSaving embeddings to: {output_path}")
    np.save(output_path, embeddings)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total embeddings generated: {len(embeddings)}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"File size: {Path(output_path).stat().st_size / (1024*1024):.2f} MB")
    
    return embeddings


if __name__ == "__main__":
    generate_embeddings(
        input_path=str(DATA_DIR / "vagas_unificadas.csv"),
        output_path=str(DATA_DIR / "embeddings.npy"),
    )
