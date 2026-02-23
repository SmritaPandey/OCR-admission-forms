# Build Fix Notes

## Issue Fixed: tesserocr Version

**Problem**: `tesserocr==2.7.3` doesn't exist in PyPI. Available versions: 2.7.0, 2.7.1, 2.8.0, 2.9.1, 2.9.2

**Solution**: Commented out `tesserocr` in `requirements.txt` because:
1. It's optional (only used for Tesseract region detection)
2. Requires Tesseract to be installed to build
3. Main OCR functionality uses `pytesseract` which doesn't need `tesserocr`

## Updated Files

1. **`requirements.txt`**: Commented out `tesserocr` line
2. **`build_desktop.bat`**: Made dependency installation more tolerant of optional package failures

## Next Steps

Try building again:

```bash
build_desktop.bat
```

The build should now proceed past the dependency installation step.

## Note on tesserocr

If you need `tesserocr` functionality:
1. Install Tesseract OCR first: https://github.com/UB-Mannheim/tesseract/wiki
2. Add Tesseract to PATH
3. Then install: `pip install tesserocr>=2.7.0`

But for the desktop app, it's not required - `pytesseract` works fine for basic OCR.
