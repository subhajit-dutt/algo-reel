# Manim renderer image for M5. Runs untrusted LLM-generated Manim code inside the
# hardened sandbox (--network=none --read-only --cap-drop=ALL). manimcommunity/manim
# ships Manim CE + ffmpeg + a LaTeX distribution (MathTex works). We add a numeric
# non-root user matching the sandbox's --user 10001:10001 and a writable HOME so
# fontconfig/matplotlib caches work under --read-only (host mounts /tmp tmpfs).
FROM manimcommunity/manim:stable

USER root
RUN groupadd -g 10001 app \
    && useradd -m -u 10001 -g app app
# No baked entrypoint: the host passes the full `manim ...` / `ffmpeg ...` argv.
USER 10001:10001
ENTRYPOINT []
