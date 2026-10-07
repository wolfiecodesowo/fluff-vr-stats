# Assets & credits

| File | What | License |
|---|---|---|
| `assets/logo.gif`, `assets/error.gif`, `assets/thanks.gif` | Sticker art | © the original artists (signatures kept on the art). **Not** MIT. Ask the artists before reusing, or swap in your own. |
| `assets/kitty/custom/*.png` | Lil Kitty (animated, tail wag) | © a lovely anonymous artist, **used with permission**, credit required. **Not** MIT: don't reuse it outside Fluff VR Stats without asking the artist |
| `assets/kitty/body_*.png`, `assets/kitty/tail.png` | Line-art fallback kitty | Drawn from code in `tools/make_kitty_art.py` (MIT) |
| `assets/meow*.wav`, `assets/purr.wav`, `assets/mrrp.wav`, `assets/nom.wav` | Kitty sounds | Synthesized from code in `tools/make_meows.py` (MIT) |
| `assets/startup.wav`, `assets/ding.wav` | Startup sound + timer ding | Synthesized from code in `tools/make_sound.py`, same license as the code (MIT) |
| `fonts/Fredoka-*.ttf`, `fonts/Nunito-*.ttf`, `fonts/GochiHand-Regular.ttf`, `fonts/LilitaOne-Regular.ttf` | Fonts | SIL Open Font License 1.1 (see the OFL-*.txt files) |
| `fonts/DejaVuSans.ttf` | Symbol font | DejaVu / Bitstream Vera license (free, see LICENSE-DejaVu.txt) |
| `docs/trailer.mp4` | Trailer | Made with `tools/make_trailer2.py`, original synthesized music |

## Using your own art
Drop any gif or png with a plain light background into `assets/`, using the same file names. The app turns it into a die-cut sticker by itself.
- If your drawing's lines run off the edge of the picture, set its style to `"card"` in `config.json` → `sticker_styles`.
