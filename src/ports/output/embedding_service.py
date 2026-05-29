from __future__ import annotations

from typing import Sequence


class EmbeddingServicePort:
	"""Port for embedding services.

	The core or adapters can call an implementation of this port to obtain
	embeddings for text inputs.
	"""

	def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
		"""Return a list of embedding vectors for the provided texts.
		
		Implementations must return a list with the same length as `texts`.
		"""
		raise NotImplementedError()

