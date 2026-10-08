"""
Flicker-free overlay textures.

setOverlayRaw/setOverlayFromFile make SteamVR create a brand-new texture on every
update, which shows up as flashing in the headset (worst in the SteamVR dashboard).
Instead we keep ONE OpenGL texture per overlay alive in a hidden window, update its
pixels in place and hand SteamVR the same texture each time - the way proper overlay
apps do it. If OpenGL isn't available for some reason, main.py falls back to raw.
"""
import openvr
from PIL import Image

try:
    import glfw
    from OpenGL import GL
except Exception:          # packages missing -> caller falls back
    glfw = GL = None


class GLUploader:
    def __init__(self, flip=True):
        if glfw is None:
            raise RuntimeError("glfw/PyOpenGL not installed (run install.bat)")
        if not glfw.init():
            raise RuntimeError("couldn't start OpenGL (glfw.init failed)")
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        glfw.window_hint(glfw.FOCUSED, glfw.FALSE)
        self.win = glfw.create_window(16, 16, "Fluff VR Stats GL", None, None)
        if not self.win:
            glfw.terminate()
            raise RuntimeError("couldn't create a hidden OpenGL window")
        glfw.make_context_current(self.win)
        self.flip = flip
        self.tex = {}     # overlay handle -> [texture id, w, h]
        self.info = GL.glGetString(GL.GL_RENDERER)
        # Drain any error left in the queue by context/window creation. Without
        # this, PyOpenGL's per-call check blames the leftover on the first real
        # GL call (seen as GL_INVALID_VALUE at glBindTexture on some drivers,
        # e.g. GTX 1650 + newest PyOpenGL), and the whole GPU path gets disabled.
        for _ in range(16):
            if GL.glGetError() == GL.GL_NO_ERROR:
                break

    def push(self, overlay, handle, img, data=None, size=None):
        """img: PIL RGBA image (or pass raw RGBA `data` + `size`)."""
        glfw.make_context_current(self.win)
        if img is None:
            img = Image.frombytes("RGBA", size, data)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        if self.flip:                      # GL textures start at the bottom row
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        w, h = img.size
        pixels = img.tobytes()
        ent = self.tex.get(handle)
        if ent is None:
            tid = int(GL.glGenTextures(1))   # newest PyOpenGL hands back np.uint32
            GL.glBindTexture(GL.GL_TEXTURE_2D, tid)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
            ent = self.tex[handle] = [tid, 0, 0]
        tid = int(ent[0])
        GL.glBindTexture(GL.GL_TEXTURE_2D, tid)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        if (ent[1], ent[2]) != (w, h):     # size changed -> reallocate once
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, w, h, 0,
                            GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, pixels)
            ent[1], ent[2] = w, h
        else:                              # same size -> update pixels in place
            GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, w, h,
                               GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, pixels)
        GL.glFinish()                      # make sure the pixels are there before SteamVR reads
        t = openvr.Texture_t()
        t.handle = int(tid)
        t.eType = openvr.TextureType_OpenGL
        t.eColorSpace = openvr.ColorSpace_Auto
        overlay.setOverlayTexture(handle, t)

    def forget(self, handle):
        ent = self.tex.pop(handle, None)
        if ent:
            try:
                glfw.make_context_current(self.win)
                GL.glDeleteTextures([ent[0]])
            except Exception:
                pass

    def close(self):
        try:
            for h in list(self.tex):
                self.forget(h)
            glfw.destroy_window(self.win)
            glfw.terminate()
        except Exception:
            pass

    def read_back(self, handle):
        """Test helper: returns the texture as a PIL image (top row first)."""
        tid, w, h = self.tex[handle]
        glfw.make_context_current(self.win)
        GL.glBindTexture(GL.GL_TEXTURE_2D, tid)
        raw = GL.glGetTexImage(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
        img = Image.frombytes("RGBA", (w, h), raw)
        return img.transpose(Image.FLIP_TOP_BOTTOM) if self.flip else img
