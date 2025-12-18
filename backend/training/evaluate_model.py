"""
Model Evaluation Script
Evaluate trained OCR models on test set with metrics (CER, WER, accuracy)
"""
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def calculate_cer(predicted: str, ground_truth: str) -> float:
    """
    Calculate Character Error Rate (CER)
    CER = (S + D + I) / N
    where S=substitutions, D=deletions, I=insertions, N=total characters
    """
    if not ground_truth:
        return 1.0 if predicted else 0.0
    
    # Simple Levenshtein distance for CER
    n = len(ground_truth)
    m = len(predicted)
    
    # Create DP table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    
    # Initialize
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    
    # Fill DP table
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ground_truth[i - 1] == predicted[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # deletion
                    dp[i][j - 1],      # insertion
                    dp[i - 1][j - 1]   # substitution
                )
    
    errors = dp[n][m]
    return errors / n if n > 0 else 1.0


def calculate_wer(predicted: str, ground_truth: str) -> float:
    """
    Calculate Word Error Rate (WER)
    WER = (S + D + I) / N
    where S=substitutions, D=deletions, I=insertions, N=total words
    """
    pred_words = predicted.split()
    gt_words = ground_truth.split()
    
    if not gt_words:
        return 1.0 if pred_words else 0.0
    
    n = len(gt_words)
    m = len(pred_words)
    
    # Create DP table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    
    # Initialize
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    
    # Fill DP table
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if gt_words[i - 1] == pred_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # deletion
                    dp[i][j - 1],      # insertion
                    dp[i - 1][j - 1]   # substitution
                )
    
    errors = dp[n][m]
    return errors / n if n > 0 else 1.0


def calculate_accuracy(predicted: str, ground_truth: str) -> float:
    """Calculate exact match accuracy"""
    return 1.0 if predicted.strip() == ground_truth.strip() else 0.0


def evaluate_trocr_model(
    model_path: str,
    test_data_path: str,
    device: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate TrOCR model on test dataset
    
    Args:
        model_path: Path to trained TrOCR model
        test_data_path: Path to test JSON file
        device: Device to use (cuda/cpu)
    
    Returns:
        Dictionary with evaluation metrics
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print("=" * 60)
    print("TrOCR Model Evaluation")
    print("=" * 60)
    print(f"Model: {model_path}")
    print(f"Test data: {test_data_path}")
    print(f"Device: {device}")
    print()
    
    # Load model and processor
    print("Loading model...")
    model = VisionEncoderDecoderModel.from_pretrained(model_path)
    processor = TrOCRProcessor.from_pretrained(model_path)
    model.to(device)
    model.eval()
    print("✅ Model loaded")
    print()
    
    # Load test data
    print("Loading test data...")
    with open(test_data_path, 'r') as f:
        test_data = json.load(f)
    print(f"✅ Test samples: {len(test_data)}")
    print()
    
    # Evaluate
    print("Running evaluation...")
    results = {
        'total_samples': len(test_data),
        'cer_scores': [],
        'wer_scores': [],
        'accuracy_scores': [],
        'predictions': []
    }
    
    with torch.no_grad():
        for i, sample in enumerate(test_data):
            if (i + 1) % 10 == 0:
                print(f"  Processing {i + 1}/{len(test_data)}...")
            
            image_path = sample['image_path']
            ground_truth = sample.get('text', '')
            
            try:
                # Load and process image
                image = Image.open(image_path).convert('RGB')
                pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)
                
                # Generate prediction
                generated_ids = model.generate(pixel_values)
                predicted = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                
                # Calculate metrics
                cer = calculate_cer(predicted, ground_truth)
                wer = calculate_wer(predicted, ground_truth)
                accuracy = calculate_accuracy(predicted, ground_truth)
                
                results['cer_scores'].append(cer)
                results['wer_scores'].append(wer)
                results['accuracy_scores'].append(accuracy)
                results['predictions'].append({
                    'image_path': image_path,
                    'ground_truth': ground_truth,
                    'predicted': predicted,
                    'cer': cer,
                    'wer': wer,
                    'accuracy': accuracy
                })
                
            except Exception as e:
                print(f"  Error processing {image_path}: {e}")
                continue
    
    # Calculate aggregate metrics
    results['avg_cer'] = sum(results['cer_scores']) / len(results['cer_scores']) if results['cer_scores'] else 0.0
    results['avg_wer'] = sum(results['wer_scores']) / len(results['wer_scores']) if results['wer_scores'] else 0.0
    results['avg_accuracy'] = sum(results['accuracy_scores']) / len(results['accuracy_scores']) if results['accuracy_scores'] else 0.0
    
    print()
    print("=" * 60)
    print("Evaluation Results")
    print("=" * 60)
    print(f"Total samples: {results['total_samples']}")
    print(f"Average CER: {results['avg_cer']:.4f} (lower is better)")
    print(f"Average WER: {results['avg_wer']:.4f} (lower is better)")
    print(f"Average Accuracy: {results['avg_accuracy']:.4f} (higher is better)")
    print()
    
    return results


def save_evaluation_report(
    results: Dict[str, Any],
    output_path: str
):
    """Save evaluation results to JSON file"""
    # Remove predictions from summary (too large)
    summary = {
        'total_samples': results['total_samples'],
        'avg_cer': results['avg_cer'],
        'avg_wer': results['avg_wer'],
        'avg_accuracy': results['avg_accuracy'],
        'cer_scores': results['cer_scores'],
        'wer_scores': results['wer_scores'],
        'accuracy_scores': results['accuracy_scores']
    }
    
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ Evaluation report saved: {output_path}")


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(description="Evaluate trained OCR model")
    parser.add_argument("model_path", help="Path to trained model")
    parser.add_argument("test_data", help="Path to test JSON file")
    parser.add_argument("--output", help="Path to save evaluation report")
    parser.add_argument("--device", choices=["cuda", "cpu"], help="Device to use")
    
    args = parser.parse_args()
    
    results = evaluate_trocr_model(
        model_path=args.model_path,
        test_data_path=args.test_data,
        device=args.device
    )
    
    if args.output:
        save_evaluation_report(results, args.output)


if __name__ == "__main__":
    main()
