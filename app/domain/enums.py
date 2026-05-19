from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    SCRIPTING = "scripting"
    SCRIPT_READY = "script_ready"
    RENDERING = "rendering"
    COMPOSING = "composing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_FAILED = "partially_failed"


class SceneStatus(StrEnum):
    PENDING = "pending"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class Renderer(StrEnum):
    MANIM = "manim"
    AI_IMAGE = "ai_image"


class AssetKind(StrEnum):
    AUDIO = "audio"
    SCENE_MP4 = "scene_mp4"
    FINAL_MP4 = "final_mp4"
    IMAGE = "image"
    MANIM_LOG = "manim_log"
