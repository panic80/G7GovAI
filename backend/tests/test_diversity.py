import unittest
import numpy as np
from diversity import DiversityReranker


class TestDiversityReranker(unittest.TestCase):
    def setUp(self):
        self.ranker = DiversityReranker()

    def test_echo_chamber(self):
        """
        Scenario:
        Query is very close to A and B.
        A and B are very close to each other (Redundant).
        C is somewhat relevant but orthogonal to A/B (Diverse).
        """
        # Simplified 2D vectors
        query = [1.0, 0.0]

        doc_a = {"id": "A", "embedding": [1.0, 0.05]}  # Very relevant (~1.0)
        doc_b = {"id": "B", "embedding": [1.0, 0.06]}  # Very relevant, duplicate of A
        doc_c = {"id": "C", "embedding": [0.7, 0.7]}  # Relevant (~0.7), but diverse

        candidates = [doc_a, doc_b, doc_c]

        # Lambda = 0.5 (Balanced)
        # MMR(B) = 0.5*1 - 0.5*1 = 0
        # MMR(C) = 0.5*0.7 - 0.5*0.7 = 0
        # Tie? Let's make C slightly better or B slightly worse redundancy

        # With Lambda = 0.4 (Favor Diversity)
        # MMR(B) = 0.4*1 - 0.6*1 = -0.2
        # MMR(C) = 0.4*0.7 - 0.6*0.7 = 0.28 - 0.42 = -0.14
        # C > B
        results = self.ranker.rerank(query, candidates, final_k=3, lambda_mult=0.4)

        ids = [d["id"] for d in results]
        print(f"\nEcho Chamber Results (ids): {ids}")

        self.assertEqual(ids[0], "A", "First should be most relevant")
        self.assertEqual(ids[1], "C", "Second should be diverse (C) not redundant (B)")
        self.assertEqual(ids[2], "B", "Third is the redundant one")

    def test_bill_c3_simulation(self):
        """
        Scenario:
        50 docs are 'Citizenship' (Cluster A)
        2 docs are 'Healthcare' (Cluster B)
        Query is 'Citizenship'
        """
        query = [1.0, 0.0]

        candidates = []

        # 50 Citizenship Docs (Cluster A) - Highly relevant
        for i in range(50):
            candidates.append(
                {
                    "id": f"Cit_{i}",
                    "embedding": [0.99, 0.01 * (i / 100)],  # Sim ~ 1.0
                    "content": "Citizenship Bill",
                }
            )

        # 2 Healthcare Docs (Cluster B) - Moderate relevance
        candidates.append(
            {
                "id": "Health_1",
                "embedding": [0.6, 0.6],  # Sim ~ 0.7
                "content": "Healthcare Bill",
            }
        )
        candidates.append(
            {"id": "Health_2", "embedding": [0.6, 0.65], "content": "Healthcare Bill 2"}
        )

        # Use Lambda = 0.3 to aggressively surface diversity against a massive majority
        # MMR(Cit_Next) = 0.3*1 - 0.7*1 = -0.4
        # MMR(Health)   = 0.3*0.7 - 0.7*0.6 (Sim to Cit) = 0.21 - 0.42 = -0.21
        # Health (-0.21) > Cit (-0.4)
        results = self.ranker.rerank(query, candidates, final_k=10, lambda_mult=0.3)

        ids = [d["id"] for d in results]
        content = [d["content"] for d in results]
        print(f"\nBill C-3 Results (Top 10): {content}")

        # Check if at least one Health doc made it to Top 10
        health_found = any("Health" in x for x in ids)
        self.assertTrue(
            health_found, "Diversity reranking should surface the minority cluster"
        )


if __name__ == "__main__":
    unittest.main()
