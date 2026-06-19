"""Script to test the data transformation and generate embeddings."""

from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
from job_obs.service.dashboard_data import transform_data

def main() -> None:
    """Run the sample search preparation and generate embeddings."""
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

    df = pd.read_csv('./../../data/raw_data.csv')
    df, _ = transform_data(df)
    print(type(df))

    df['texto_vaga'] = (
        df['cargo'].fillna('') + ' ' +
        df['nivel'].fillna('') + ' ' +
        df['estado'].fillna('') + ' ' +
        df['modalidade_trabalho'].fillna('')
    )
    embeddings = model.encode(
        df['texto_vaga'].tolist(),
        show_progress_bar=True,
        convert_to_numpy=True
    ).astype(np.float32)

    np.save('./../../data/embeddings.npy', embeddings)
    df.to_csv('./../../data/vagas_processadas.csv', index=False)

if __name__ == "__main__":
    main()
