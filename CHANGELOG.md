# Changelog

All notable changes to pycellin since version 0.5.1 are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

<!-- Planned v0.6.0. Covers commits up to 7cb9f42. Update from there with: git log 7cb9f42..dev -->

Model merging and splitting, a lot of new properties, branch plots, and many fixes around time handling. **This release contains breaking changes**, listed first below.

### ⚠️ Breaking changes

- **Properties:** `pycellin.graph.properties` moved to `pycellin.properties`. The `pycellin.graph` package no longer exists
- **Properties:** rename the `branch_*` properties to `cycle_*`, along with their `add_*()` methods, factories and calculators:
  - `branch_total_displacement` → `cycle_total_displacement`
  - `branch_mean_displacement` → `cycle_mean_displacement`
  - `branch_mean_speed` → `cycle_mean_speed`
- **Properties:** rename the `angle` property to `turning_angle` (`add_angle()` → `add_turning_angle()`)
- **Properties:** rename the `ROI_coords` node property to `cell_contour` (TrackMate and CTC loaders, all exporters, sample GEFF data)
- **Properties:** `cycle_duration` values change: it is now the time elapsed between the first and last cells of the cycle, in the reference time unit. It was previously off by one frame and scaled by the time step a second time
- **Properties:** `Property` setters raise `TypeError` instead of `ValueError` when given a non-string value
- **Model:** remove the `Model.recompute_property()` and `Model.export()` stubs, which did nothing. Use the `pycellin.export_*()` functions
- **Plotting:** rename `node_color_scale` to `node_colormap` in `CellLineage` and `CycleLineage` `plot()` and `get_tree_figure()`
- **CTC:** the loader now uses a new `time` property as the reference time property, instead of `timepoint`
- **trackpy:** the loader now uses a new `time` property (frame × time step) as the reference time property, instead of `frame`, and renames the trackpy coordinates `x`, `y`, `z` to `cell_x`, `cell_y`, `cell_z`
- **Exceptions:** pycellin exceptions now subclass the matching built-in exception: `LineageStructureError` (so `FusionError` and `TimeFlowError`) is a `ValueError`, `UpdateRequiredError` a `RuntimeError`, `ProtectedPropertyError` an `AttributeError`
- **Logging:** pycellin no longer adds a `NullHandler` to its logger, so warnings logged by pycellin are shown on stderr by default
- **Dependencies:** matplotlib is no longer installed with pycellin: install it yourself if your code uses it. pycellin only needs it for the debug plots of the `RodWidth` and `RodLength` calculators (`debug=True`)

### Added

- **Model:** `merge()` to merge two models, and `split()` to split a model into several models from groups of lineage IDs
  - lineage ID collisions are resolved, and single-cell lineages keep the lineage ID = -cell ID convention
  - critical metadata (reference time property, time step and unit, pixel size, space unit) must match; other differing metadata values are stored as lineage properties
  - property declarations are checked for compatibility (property type, lineage type, unit, dtype)
  - calculators that rely on external data (e.g. a label image) are not kept
  - cycle data is handled when only one of the models has some
- **Model:** `rescale_time()` and `rescale_space()` to convert time or space values into another unit (e.g. frames to minutes, pixels to µm)
- **Model:** `remove_lineages()`
- **Model:** `relabel_cells()` to give cells consecutive IDs, optionally unique across the whole model
- **Model:** `remove_intercycle_links()` to remove the outgoing links of division cells
- **Model:** `get_cell_lineages_from_IDs()` and `get_cycle_lineages_from_IDs()`
- **Model:** `overwrite_lid` argument to `add_lineage()`
- **Model:** `lineage_props` argument to `to_cell_dataframe()`, `to_link_dataframe()` and `to_cycle_dataframe()` to include lineage properties in the DataFrame
- **Metadata:** `label_img` and `label_img_path` standard metadata fields
- **Metadata:** `ModelMetadata.diff()` to list the metadata fields that differ between two models
- **Properties:** `Property.get_incompatibilities()` to compare two property declarations
- **Properties:** `pycellin.properties` now exposes the 13 core property factories (`create_cell_id_property()`, `create_time_property()`, ...), to declare properties when building a model from scratch or writing a loader
- **Properties:** `time` core property with its calculator
- **Properties:** morphology properties `cell_polygon` (computed from a label image), `cell_contour`, `cell_area` and `cell_perimeter`
- **Properties:** morphology properties `cycle_mean_area`, `birth_area` and `division_area`
- **Properties:** topology lineage properties `num_cells`, `num_cycles`, `num_divs`, `num_gaps` and `num_leaves`
- **Properties:** topology lineage properties `lineage_cell_depth`, `lineage_cycle_depth` and `lineage_duration`
- **Properties:** `location_tag`, a cell property read from a mask image. `mask_path_metadata_field` reads the mask path from the model metadata, and a `tag_names` dict maps pixel values to region names
- **Properties:** `uses_external_data()` class method on calculators
- **Exceptions:** `MissingPropertyError` (a `KeyError`), raised when a required property is missing from a node, an edge or the model
- **Lineages:** `Lineage.get_depth()`, `CellLineage.get_gaps()` and `CellLineage.get_duration()`
- **Plotting:** `pycellin.styling` module with pycellin colors and two Plotly templates, `pycellin_white` (the new default) and `pycellin_dark`
- **Plotting:** `Model.plot_mean_cell_prop_over_time()` and `Model.get_mean_cell_prop_over_time_fig()` to plot the mean and std of a cell property over time
- **Plotting:** `CellLineage.plot_branch_profile()` and `CellLineage.get_branch_profile_figure()` to plot a cell property along one or several branches, with per-branch styling of markers and lines
- **Plotting:** `CellLineage.get_branch_lineage()` and `CellLineage.get_branch_lineage_highlight()` to extract or highlight the branch leading to a cell
- **Plotting:** branch highlights in `CellLineage.plot()` and `get_tree_figure()`, with `target_cells`, `source_cells`, `generations` and `highlight_prop` arguments
- **Plotting:** support for single-cell lineages
- **Plotting:** `node_colormap` also accepts a dict for discrete color maps
- **Plotting:** nodes can be styled individually through `node_marker_style`
- **TrackMate:** `ref_time_prop` argument to `load_TrackMate_XML()`
- **TrackMate:** default tracker in the exported XML, so the TrackMate wizard can be navigated back
- **TrackMate:** dimension mappings for the new properties
- **trackpy:** `computed_time_prop` argument to `load_trackpy_dataframe()`
- **Dependencies:** `notebooks` extra with what the example notebooks need: JupyterLab, ipykernel, and nbformat, without which Plotly can't show figures in notebooks. Install it with `pip install "pycellin[notebooks]"`

### Changed

- **Model:** core properties (`cell_ID`, `lineage_ID`, `timepoint` and the reference time property) are protected whenever they are declared
- **Model:** timepoint handling is centralized in the updater: the `timepoint` calculator is always present and up to date
- **Model:** enforce the single-cell lineage convention (lineage ID = -cell ID)
- **Properties:** data types are compared after normalizing their spelling (e.g. `float` and `float64`)
- **TrackMate:** one-node lineages are identified by their size instead of by their lineage ID sign
- **TrackMate:** document that only numeric properties are exported
- **GEFF:** stricter coordinate arguments in `load_GEFF()`: they must describe a complete 2D or 3D system, and inferred coordinates are each assigned at most once
- **Dependencies:** declare numpy, pillow, tifffile and geff-spec, which pycellin imports directly but only got through other packages
- **Dependencies:** raise the minimum versions of pandas (2.2.2), scikit-image (0.24), shapely (2.0.4) and plotly (5.12) to the first ones that work with NumPy 2. The previous minimums allowed installs that failed at `import pycellin`
- **Dependencies:** the test dependencies moved from the `test` extra to a `test` dependency group, installed from a clone of the repository with `pip install -e . --group test` (pip >= 25.1)

### Fixed

- **Model:** changing the time step with `set_time_step()` corrupted the `timepoint` values
- **Model:** `add_lineage()` failed with `with_CycleLineage=True` or with a lineage that had no lineage ID, and ignored its `lid` argument when given a lineage
- **Model:** `add_lineage()` silently replaced a lineage that already had the same ID. It now raises `ValueError`
- **Properties:** `turning_angle` (`angle` in 0.5.1) was recomputed for every lineage at each update, as its calculator was global instead of local
- **Properties:** `turning_angle` (`angle` in 0.5.1) was declared as an edge property although its values are on cells
- **TrackMate:** `turning_angle` (`angle` in 0.5.1) in degrees was exported as a TrackMate angle, which TrackMate reads as radians
- **GEFF:** the exporter didn't write the metadata of properties with several types (`LINEAGE | NODE`, `LINEAGE | EDGE`)
- **CTC:** the loader gave cells no `timepoint`, although it was the reference time property, and no `lineage_ID`. Reading the pixel size from label images (`labels_path`) failed
- **trackpy:** the loader failed when given a `time_step`, which it applied to frames, and gave cells no `lineage_ID`

### Maintenance

- **Tests:** new tests for model merging and splitting, the new properties, plotting, exceptions and utils
- **Docs:** use the `pc` alias consistently in the README and notebooks, update and re-run the notebooks
- **Packaging:** find packages automatically in `pyproject.toml`
- **Packaging:** declare the license as an SPDX expression (`BSD-3-Clause`) instead of the deprecated classifier. Building pycellin now needs setuptools >= 77
- **Packaging:** between releases, the version on `dev` ends with `.dev0` (e.g. `0.6.0.dev0`), so models made with development code say so in their `pycellin_version` metadata
- **CI:** bump `actions/setup-python` from 6 to 7
- **CI:** the deploy workflow stops before building if the release tag doesn't match the package version
- **CI:** fix releases starting the deploy workflow twice, which made one of the two runs fail at the PyPI upload
- fix typos, type hints, docstrings and formatting

### New Contributors

- [@marcelaxrivera](https://github.com/marcelaxrivera) made their first contribution in [#50](https://github.com/Image-Analysis-Hub/pycellin/pull/50)

## Earlier versions

Versions up to 0.5.1 are documented in the [GitHub releases](https://github.com/Image-Analysis-Hub/pycellin/releases).

[Unreleased]: https://github.com/Image-Analysis-Hub/pycellin/compare/v0.5.1...dev
