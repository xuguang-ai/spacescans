# common_v2/linkage/faqsd_linkage.py
"""FAQSD daily areal linkage pattern.

Self-contained linkage for FAQSD (Fused Air Quality Surface + Downscaling) data.
Delegates all computation to the ``faqsd`` reader plugin's
``compute_patient_exposure()`` method, which reproduces the exact SQL logic
from the v1 modularized script (C4_Linkage_TRACT_FAQSD.py).

This pattern is used because FAQSD requires three inputs (text files +
tract-level area weights + patients) and produces patient-level output
directly—it does not fit the standard weights → exposure → patient pipeline.
"""

from __future__ import annotations

from pathlib import Path

from spacescans.io.readers import read_table
from spacescans.io.writers import write_table
from spacescans.linkage.helpers import load_patients
from spacescans.pipeline.registry import get_reader, register_pattern


@register_pattern("faqsd_daily_areal")
def run_faqsd_daily_areal(config, engine) -> Path:
    """Run the FAQSD self-contained daily areal linkage.

    1. Load patients from the configured patient file.
    2. Delegate computation to the ``faqsd`` plugin's
       ``compute_patient_exposure(patients)`` method.
    3. Write the result to the configured output path.
    """
    patients = load_patients(config)

    reader_cls = get_reader(config.plugin)
    reader = reader_cls(config)
    result = reader.compute_patient_exposure(patients)

    return write_table(result, config.output.path)
