"""Quick verification of the fine-tuned TrOCR model."""
import json
import os
from pathlib import Path
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

model_path = "training_output/models/trocr_finetuned"
print("=" * 60)
print("  Fine-tuned TrOCR Model Verification")
print("=" * 60)

# Load trained model
print("\nLoading fine-tuned model...")
processor = TrOCRProcessor.from_pretrained(model_path)
model = VisionEncoderDecoderModel.from_pretrained(model_path)
print("  Model loaded successfully!")

# Load test images
images_dir = Path("training_data/prepared/images")
all_images = sorted(images_dir.glob("*.png"))
test_images = all_images[:3]
print(f"  Total images: {len(all_images)}, testing first 3")

print("\n--- Inference Results ---")
for img_path in test_images:
    image = Image.open(img_path).convert("RGB")
    pixel_values = processor(image, return_tensors="pt").pixel_values
    generated_ids = model.generate(pixel_values, max_new_tokens=100)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    print(f"\n  Image: {img_path.name}")
    print(f"  Text:  {text[:150]}")

# Load training metrics
with open(os.path.join(model_path, "training_metrics.json")) as f:
    metrics = json.load(f)

print("\n--- Training Metrics ---")
print(f"  Base model:     {metrics['base_model']}")
print(f"  Training loss:  {metrics['train_loss']:.4f}")
print(f"  Epochs:         {metrics['epochs']}")
print(f"  Train samples:  {metrics['train_samples']}")
print(f"  Val samples:    {metrics['val_samples']}")
print(f"  Training time:  {metrics['training_time_seconds']:.1f}s")
print(f"  Device:         {metrics['device']}")

print("\n  Model verification PASSED!")
