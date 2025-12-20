# How to Fix CORS Issues

## Problem
CORS errors are blocking API requests from the frontend.

## Solution

The backend server needs to be **restarted** to pick up the new CORS configuration.

### Steps:

1. **Stop the current server** (if running):
   - Press `Ctrl+C` in the terminal where the server is running

2. **Restart the server**:
   ```bash
   ./start_app.sh
   ```

3. **Wait for both servers to start**:
   - Backend should show: `✅ Backend started`
   - Frontend should show: `ready in XX ms`

4. **Test in browser**:
   - Open `http://localhost:5174` (or the port shown)
   - Open Developer Tools (F12) → Console
   - You should see API requests being logged
   - No more CORS errors!

## What Changed

The CORS configuration now uses a regex pattern to allow **any localhost port**:
- `http://localhost:*` (any port)
- `http://127.0.0.1:*` (any port)

This means you won't need to update CORS settings every time Vite picks a different port.

## If CORS Errors Persist

1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy"}`

2. **Check CORS headers**:
   Open browser DevTools → Network tab → Click on a failed request → Check Response Headers
   Should see: `Access-Control-Allow-Origin: http://localhost:5174`

3. **Hard refresh browser**:
   - Press `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
   - This clears cached CORS responses

4. **Check backend logs**:
   Look for any errors in the terminal where backend is running


