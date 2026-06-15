# Trusted-command FFmpeg sandbox image: M4 trivial renders, M5 compose, and the M5
# manim audio-mux step. Manim itself runs in the separate docker/manim image.
FROM alpine:3.20

RUN apk add --no-cache ffmpeg ttf-dejavu \
    && cp /usr/share/fonts/dejavu/DejaVuSans.ttf /opt/font.ttf \
    && addgroup -g 10001 app \
    && adduser -D -u 10001 -G app app

USER 10001:10001
# No baked entrypoint: the host passes the full `ffmpeg ...` argv as the command.
ENTRYPOINT []
