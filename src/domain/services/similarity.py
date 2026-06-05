from __future__ import annotations

import math
from collections.abc import Sequence


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
	"""Return cosine similarity in [-1, 1], or 0.0 when vectors cannot be compared."""
	if len(a) != len(b) or not a or not b:
		return 0.0

	dot = sum(x * y for x, y in zip(a, b, strict=True))
	norm_a = math.sqrt(sum(x * x for x in a))
	norm_b = math.sqrt(sum(x * x for x in b))
	if norm_a == 0.0 or norm_b == 0.0:
		return 0.0

	return dot / (norm_a * norm_b)
