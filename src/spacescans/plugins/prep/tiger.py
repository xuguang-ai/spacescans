"""TIGER road shapefile download + local cache via pygris."""
from spacescans.pipeline.registry import register_prep

@register_prep("tiger")
def prep_tiger(config):
    raise NotImplementedError("Full implementation requires network access for pygris")
