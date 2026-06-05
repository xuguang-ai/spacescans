"""PRISM zip extraction + cache management."""
from spacescans.pipeline.registry import register_prep

@register_prep("prism")
def prep_prism(config):
    raise NotImplementedError("Full implementation requires PRISM data")
