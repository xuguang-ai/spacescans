"""MODIS HDF to TIF conversion."""
from spacescans.pipeline.registry import register_prep

@register_prep("modis")
def prep_modis(config):
    raise NotImplementedError("Full implementation requires MODIS HDF data")
