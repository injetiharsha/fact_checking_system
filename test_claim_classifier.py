#!/usr/bin/env python3
"""
Test DistilBERT Claim Type Classifier
Quick test to verify claim type classification works correctly.
"""

from claim_detection.claim_type_classifier import ClaimTypeClassifier, ClaimType


def test_classifier():
    """Test claim type classifier with sample claims."""
    
    print("\n" + "="*60)
    print("TESTING DISTILBERT CLAIM TYPE CLASSIFIER")
    print("="*60)
    
    classifier = ClaimTypeClassifier()
    
    test_claims = [
        # Factual claims
        ("The Earth revolves around the Sun.", "FACTUAL"),
        ("COVID-19 has killed over 6 million people worldwide.", "FACTUAL"),
        ("Paris is the capital of France.", "FACTUAL"),
        
        # Opinion claims
        ("Trump is the best president ever.", "OPINION"),
        ("Chocolate is the best dessert.", "OPINION"),
        ("This movie is terrible.", "OPINION"),
        
        # Numerical claims
        ("The unemployment rate rose to 5.2%.", "NUMERICAL"),
        ("India's population exceeded 1.4 billion in 2023.", "NUMERICAL"),
        ("Scientists estimate 30,000 species go extinct annually.", "NUMERICAL"),
        
        # Mixed claims
        ("The best evidence suggests COVID kills 1-2% of cases.", "MIXED"),
        ("According to most experts, AI will be the most transformative technology.", "MIXED"),
    ]
    
    correct = 0
    
    for claim, expected_type in test_claims:
        result = classifier.classify(claim)
        pred_type = result["type"].value.upper()
        confidence = result["confidence"]
        
        is_correct = (expected_type == "MIXED" and result["type"] == ClaimType.MIXED) or \
                     (expected_type == "FACTUAL" and result["type"] == ClaimType.FACTUAL) or \
                     (expected_type == "OPINION" and result["type"] == ClaimType.OPINION) or \
                     (expected_type == "NUMERICAL" and result["type"] == ClaimType.NUMERICAL)
        
        status = "OK" if is_correct else "FAIL"
        if is_correct:
            correct += 1
        
        print(f"\n{status} Claim: {claim[:50]}...")
        print(f"  Expected: {expected_type:10s} | Got: {pred_type:10s}")
        print(f"  Confidence: {confidence:.2f} | Scores: factual={result['scores']['factual']:.2f}, opinion={result['scores']['opinion']:.2f}")
    
    print("\n" + "="*60)
    accuracy = (correct / len(test_claims)) * 100
    print(f"ACCURACY: {correct}/{len(test_claims)} ({accuracy:.1f}%)")
    print("="*60)
    
    if accuracy >= 70:
        print("\nOK DistilBERT classifier is working well!")
        print("Ready to download models and run full pipeline.")
    else:
        print("\nWARN Accuracy lower than expected.")
        print("Classifier may benefit from fine-tuning on your domain.")
    
    return correct, len(test_claims)


if __name__ == "__main__":
    try:
        test_classifier()
    except Exception as e:
        print(f"\nFAIL Error: {e}")
        print("\nNote: Models may not be downloaded yet.")
        print("Run: python download_models_optimized.py (on mobile hotspot)")

