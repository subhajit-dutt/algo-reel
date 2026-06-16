from arq.constants import health_check_key_suffix

ORCHESTRATOR_QUEUE = "orchestrator_pool"
RENDER_QUEUE = "render_pool"

# Arq workers maintain these keys in Redis while alive (TTL = health_check_interval + 1s).
# Absence means nothing is consuming the queue, so enqueued work would hang instead of
# failing with an actionable error.
ORCHESTRATOR_POOL_HEALTH_KEY = ORCHESTRATOR_QUEUE + health_check_key_suffix
RENDER_POOL_HEALTH_KEY = RENDER_QUEUE + health_check_key_suffix
