from typing import Iterable

def walkModel(model):
    modelType = type(model)
    if modelType in [str, int, float, bool]: return model
    # elif modelType in [tuple, list]:
    elif isinstance(model, Iterable):
        return [walkModel(elem) for elem in model]
    else:
        attrs = [attr for attr in dir(model) if not (attr.startswith("_") or attr == "parent")]
        # walk over attributes. treat it as dict.
        return {attr: walkModel(getattr(model, attr)) for attr in attrs}