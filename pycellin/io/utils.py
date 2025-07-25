import warnings

from pycellin.classes import Model


def check_fusions(model: Model) -> None:
    """
    Check if the model contains fusions and issue a warning if so.

    Parameters
    ----------
    model : Model
        The pycellin model to check for fusions.

    Returns
    -------
    None
    """
    all_fusions = model.get_fusions()
    if all_fusions:
        # TODO: link toward correct documentation when it is written.
        fusion_warning = (
            f"Unsupported data, {len(all_fusions)} cell fusions detected. "
            "It is advised to deal with them before any other processing, "
            "especially for tracking related features. Crashes and incorrect "
            "results can occur. See documentation for more details."
        )
        warnings.warn(fusion_warning)
