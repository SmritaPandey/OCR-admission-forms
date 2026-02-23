# Build Fixes Applied

## Issue 1: OpenCV Version Conflict

**Problem**: `opencv-python==4.10.0.84` conflicted with `craft-text-detector` which requires `opencv-python<4.5.4.62`. When trying to install an older version (4.5.4.60), it tried to build from source and required `numpy==1.21.2` which doesn't exist for Python 3.13.

**Solution**: Updated to `opencv-python>=4.0.0,<4.6.0` which:
- Has pre-built wheels for Python 3.13
- Is compatible with craft-text-detector (version 0.4.3 may work with slightly newer opencv)
- Avoids building from source

**Note**: If craft-text-detector still has issues, you can:
1. Update craft-text-detector to a newer version
2. Make CRAFT+TR-OCR optional in the build
3. Use a different opencv version

## Issue 2: PyInstaller Spec File Error

**Problem**: `__file__` is not defined in PyInstaller spec file context, causing `NameError: name '__file__' is not defined`.

**Solution**: Changed from:
```python
project_root = Path(__file__).parent.absolute()
```
To:
```python
project_root = Path(os.getcwd()).absolute()
```

This uses the current working directory when the spec file is executed, which is the project root.

## Files Updated

1. `requirements.txt` - OpenCV version constraint
2. `build_backend.spec` - Fixed `__file__` reference

## Next Steps

Try building again:
```bash
build_desktop.bat
```

If opencv-python still has issues, you may need to:
- Install a specific version manually: `pip install opencv-python==4.5.5.64`
- Or update craft-text-detector to support newer opencv versions
