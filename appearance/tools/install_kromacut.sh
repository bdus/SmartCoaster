#!/usr/bin/env bash
# Install Kromacut v4.2.0 to /data/Documents/tools/Kromacut
# - Desktop app: official AppImage (extracted, no FUSE needed) + launcher
# - Source: v4.2.0 tag tarball, used for the headless "flat paint" bridge
# - Node bridge deps (three, jszip, vite) installed under the tool dir
# Outputs a log with sizes + sha256 + verification.
set -euo pipefail

VER=4.2.0
DEST=/data/Documents/tools/Kromacut
DOWN=$DEST/downloads
mkdir -p "$DEST"/{app,src,bin,logs,tools} "$DOWN"
LOG=$DEST/logs/install.log
exec > >(tee -a "$LOG") 2>&1
echo "=== install kromacut $VER  $(date -Is) ==="

cd "$DOWN"

# ---------- desktop AppImage ----------
APPIMG=Kromacut_${VER}_amd64.AppImage
if [ ! -s "$APPIMG" ]; then
  echo "[1/6] download AppImage (~169MB)"
  curl -fL --retry 3 --retry-delay 3 -o "$APPIMG.part" \
    "https://github.com/vycdev/Kromacut/releases/download/v${VER}/${APPIMG}"
  mv "$APPIMG.part" "$APPIMG"
else
  echo "[1/6] AppImage already present"
fi
chmod +x "$APPIMG"
sha256sum "$APPIMG" > SHA256SUMS

# ---------- source tarball (exact release tag) ----------
SRC=kromacut-${VER}-src.tar.gz
if [ ! -s "$SRC" ]; then
  echo "[2/6] download source tag v$VER"
  curl -fL --retry 3 --retry-delay 3 -o "$SRC.part" \
    "https://codeload.github.com/vycdev/Kromacut/tar.gz/refs/tags/v${VER}"
  mv "$SRC.part" "$SRC"
else
  echo "[2/6] source already present"
fi
sha256sum "$SRC" >> SHA256SUMS
tar xzf "$SRC" -C "$DEST/src"
SRCDIR=$DEST/src/Kromacut-${VER}
test -f "$SRCDIR/src/lib/flatPaint.ts"
echo "source: $SRCDIR"

# ---------- extract AppImage (works without FUSE) ----------
if [ ! -x "$DEST/app/AppRun" ]; then
  echo "[3/6] extract AppImage -> $DEST/app"
  cd "$DEST/app"
  "$DOWN/$APPIMG" --appimage-extract >/dev/null
  # squashfs-root lands in cwd
  if [ -d squashfs-root ]; then
    cp -a squashfs-root/. . && rm -rf squashfs-root
  fi
  test -x "$DEST/app/AppRun"
else
  echo "[3/6] app already extracted"
fi

# ---------- launcher ----------
cat > "$DEST/bin/kromacut" <<'EOS'
#!/usr/bin/env bash
# Kromacut launcher (extracted AppImage; FUSE not required)
D=/data/Documents/tools/Kromacut
export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"
exec "$D/app/AppRun" "$@"
EOS
chmod +x "$DEST/bin/kromacut"
mkdir -p /home/pi/.local/bin
ln -sf "$DEST/bin/kromacut" /home/pi/.local/bin/kromacut

# desktop entry + icon
ICON=$(find "$DEST/app" -name '*.png' -path '*icons*' | head -1 || true)
mkdir -p /home/pi/.local/share/applications /home/pi/.local/share/icons/hicolor/256x256/apps
cat > /home/pi/.local/share/applications/kromacut.desktop <<EOS
[Desktop Entry]
Type=Application
Name=Kromacut
Comment=Image to color-layered 3D print (Flat Paint / Auto-paint)
Exec=$DEST/bin/kromacut
Terminal=false
Categories=Graphics;3DGraphics;
EOS
[ -n "$ICON" ] && cp "$ICON" /home/pi/.local/share/icons/hicolor/256x256/apps/kromacut.png || true

# ---------- node bridge deps ----------
# Minimal package so `three`, `jszip`, `vite` resolve for the headless bridge
# that imports the Kromacut TypeScript core from $SRCDIR.
if [ ! -d "$DEST/node_modules/three" ]; then
  echo "[4/6] npm install bridge deps (three, jszip, vite)"
  cat > "$DEST/package.json" <<'EOS'
{
  "name": "kromacut-headless-host",
  "private": true,
  "version": "4.2.0",
  "type": "module",
  "description": "Runtime deps for the headless Flat Paint bridge around the Kromacut core",
  "dependencies": {
    "three": "0.180.0",
    "jszip": "3.10.1",
    "vite": "7.1.2"
  }
}
EOS
  cd "$DEST"
  npm install --no-audit --no-fund --loglevel=error
else
  echo "[4/6] bridge deps already installed"
fi
node -e "import('three').then(m=>console.log('three',m.REVISION));import('jszip').then(m=>console.log('jszip',m.default.version))"

# ---------- sanity ----------
echo "[5/6] sanity"
node -e "
import('vite').then(async ({createServer})=>{
  const s=await createServer({root:'$SRCDIR',appType:'custom',configFile:false,logLevel:'error',server:{middlewareMode:true,hmr:false}});
  const m=await s.ssrLoadModule('/src/lib/flatPaint.ts');
  console.log('flatPaint exports:', Object.keys(m).filter(k=>typeof m[k]==='function').join(','));
  const e=await s.ssrLoadModule('/src/lib/export3mf.ts');
  console.log('export3mf exports:', Object.keys(e).join(','));
  await s.close();
}).catch(e=>{console.error('BRIDGE SANITY FAIL',e);process.exit(2)});
" || echo "WARN: vite ssr sanity failed (see above)"

echo "[6/6] versions"
"$DEST/bin/kromacut" --version 2>/dev/null || echo "(GUI app: no --version support; AppRun present)"
du -sh "$DEST" "$DEST/app" "$DEST/src" 2>/dev/null
cat "$DOWN/SHA256SUMS"
echo "=== done $(date -Is) ==="
