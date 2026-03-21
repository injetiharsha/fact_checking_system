# evidence/domain_diversity_filter.py
"""
Domain Diversity Filter
Ensure evidence comes from diverse sources for better credibility.
"""

from urllib.parse import urlparse
from typing import List, Dict, Tuple


class DomainDiversityFilter:
    """
    Filter evidence to ensure diversity across different domains/sources.
    Prevents over-reliance on single sources.
    """
    
    def __init__(self, max_per_domain: int = 2):
        """
        Args:
            max_per_domain: Maximum evidence items from single domain (default: 2)
        """
        self.max_per_domain = max_per_domain
    
    def filter(self, evidence_list: List[Dict]) -> List[Dict]:
        """
        Filter evidence to ensure domain diversity.
        
        Args:
            evidence_list: List of evidence items with 'url' or 'source_url' field
        
        Returns:
            Filtered evidence list with max N items per domain
        """
        
        if not evidence_list:
            return []

        dynamic_cap = self._compute_dynamic_cap(len(evidence_list))
        domain_counts = {}
        url_counts = {}
        filtered_evidence = []

        # Prefer stronger evidence first, then apply domain cap.
        ranked_evidence = sorted(
            evidence_list,
            key=self._evidence_priority,
            reverse=True,
        )

        for evidence in ranked_evidence:
            url = evidence.get('url') or evidence.get('source_url', '')
            domain = self._extract_domain(url)
            current_count = domain_counts.get(domain, 0)
            current_url_count = url_counts.get(url, 0)

            allow_same_document_followup = (
                bool(url)
                and current_url_count < 2
                and any((row.get('url') or row.get('source_url', '')) == url for row in filtered_evidence)
            )

            if current_count < dynamic_cap or allow_same_document_followup:
                filtered_evidence.append(evidence)
                domain_counts[domain] = current_count + 1
                if url:
                    url_counts[url] = current_url_count + 1
        
        return filtered_evidence
    
    def get_domain_distribution(self, evidence_list: List[Dict]) -> Dict[str, int]:
        """
        Get domain distribution statistics.
        
        Returns:
            Dict mapping domain to count of evidence items
        """
        
        distribution = {}
        
        for evidence in evidence_list:
            url = evidence.get('url') or evidence.get('source_url', '')
            domain = self._extract_domain(url)
            distribution[domain] = distribution.get(domain, 0) + 1
        
        return distribution
    
    def get_diversity_score(self, evidence_list: List[Dict]) -> float:
        """
        Calculate diversity score (0-1).
        1.0 = perfect diversity, 0.0 = all from same source
        """
        
        if not evidence_list:
            return 0.0
        
        distribution = self.get_domain_distribution(evidence_list)
        num_domains = len(distribution)
        max_possible_domains = len(evidence_list)
        
        # Diversity = unique domains / total items
        diversity = num_domains / max_possible_domains
        
        return min(diversity, 1.0)
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """
        Extract domain from URL.
        Example: https://www.bbc.com/news -> bbc.com
        """
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except:
            return "unknown"
    
    def rank_by_diversity(self, evidence_list: List[Dict], 
                         max_items: int = 5) -> List[Dict]:
        """
        Select top diverse evidence items.
        Prefers evidence from different domains.
        
        Args:
            evidence_list: List of evidence items (must have 'score' field)
            max_items: Maximum evidence to return
        
        Returns:
            Top diverse evidence items
        """
        
        selected = []
        domains_used = set()
        
        # Sort by quality-aware evidence priority.
        sorted_evidence = sorted(
            evidence_list,
            key=self._evidence_priority,
            reverse=True
        )
        
        for evidence in sorted_evidence:
            if len(selected) >= max_items:
                break
            
            url = evidence.get('url') or evidence.get('source_url', '')
            domain = self._extract_domain(url)
            
            # Prefer new domains
            if domain not in domains_used:
                selected.append(evidence)
                domains_used.add(domain)
            elif len(domains_used) < max_items / 2:
                # Allow some repeats only if not enough unique domains
                selected.append(evidence)
        
        return selected

    def _compute_dynamic_cap(self, total_items: int) -> int:
        """
        Dynamic per-domain cap based on list size.
        - small sets: allow 1/domain
        - medium sets: allow 2/domain
        - larger sets: allow 3/domain
        """
        if total_items <= 4:
            return 1
        if total_items <= 10:
            return min(self.max_per_domain, 2)
        return min(max(self.max_per_domain, 2), 3)

    @staticmethod
    def _evidence_priority(evidence: Dict) -> float:
        """
        Rank evidence by strongest available score signals.
        """
        combined = float(evidence.get("combined_score", 0) or 0)
        relevance = float(evidence.get("relevance_score", 0) or 0)
        quality = float(evidence.get("quality_score", 0) or 0)
        weight = float(evidence.get("weight", 0) or 0)
        confidence = float(evidence.get("confidence", 0) or 0)
        fallback_score = float(evidence.get("score", 0) or 0)
        return (
            combined * 0.5
            + (relevance * quality) * 0.2
            + (weight * confidence) * 0.2
            + fallback_score * 0.1
        )
