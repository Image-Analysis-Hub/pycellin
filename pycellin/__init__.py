import importlib.metadata

# Set before the other imports: submodules read it while the package is loading.
try:
    __version__ = importlib.metadata.version("pycellin")
except importlib.metadata.PackageNotFoundError:
    __version__ = "development"

from . import exceptions
from .classes.data import Data
from .classes.lineage import CellLineage, CycleLineage
from .classes.model import Model
from .classes.model_metadata import ModelMetadata
from .classes.property import Property
from .classes.property_calculator import (
    EdgeGlobalPropCalculator,
    EdgeLocalPropCalculator,
    LineageGlobalPropCalculator,
    LineageLocalPropCalculator,
    NodeGlobalPropCalculator,
    NodeLocalPropCalculator,
)
from .classes.props_metadata import PropsMetadata
from .io.cell_tracking_challenge.reader import read_ctc
from .io.cell_tracking_challenge.writer import write_ctc
from .io.geff.reader import read_geff
from .io.geff.writer import write_geff
from .io.pickle.reader import read_pickle
from .io.pickle.writer import write_pickle
from .io.trackmate.reader import read_trackmate_xml
from .io.trackmate.writer import write_trackmate_xml
from .io.trackpy.reader import from_trackpy
from .io.trackpy.writer import to_trackpy
from .properties import (
    get_pycellin_cell_lineage_properties,
    get_pycellin_cycle_lineage_properties,
)

__all__ = [
    "CellLineage",
    "CycleLineage",
    "Data",
    "EdgeGlobalPropCalculator",
    "EdgeLocalPropCalculator",
    "LineageGlobalPropCalculator",
    "LineageLocalPropCalculator",
    "Model",
    "ModelMetadata",
    "NodeGlobalPropCalculator",
    "NodeLocalPropCalculator",
    "Property",
    "PropsMetadata",
    "__version__",
    "exceptions",
    "from_trackpy",
    "get_pycellin_cell_lineage_properties",
    "get_pycellin_cycle_lineage_properties",
    "read_ctc",
    "read_geff",
    "read_pickle",
    "read_trackmate_xml",
    "to_trackpy",
    "write_ctc",
    "write_geff",
    "write_pickle",
    "write_trackmate_xml",
]
