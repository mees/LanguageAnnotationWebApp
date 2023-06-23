from typing import List, Tuple

from sentence_transformers import SentenceTransformer
import torch
import torch.nn as nn


class SBert(nn.Module):
    def __init__(self, nlp_model: str, *args, **kwargs):
        #  choose model from https://www.sbert.net/docs/pretrained_models.html
        super().__init__()
        self.name = "lang_%s" % nlp_model
        assert isinstance(nlp_model, str)
        self.model = SentenceTransformer(nlp_model)

    def forward(self, x: List, show_progress_bar: bool = False) -> torch.Tensor:
        emb = self.model.encode(x, convert_to_tensor=True, show_progress_bar=show_progress_bar)
        return torch.unsqueeze(emb, 1)
