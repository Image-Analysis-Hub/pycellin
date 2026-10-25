# Changelog

All notable changes to pycellin since version 0.5.1 are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

<!-- Planned v0.6.0. Covers commits up to 4c3a2fa, plus the uncommitted fix of the GEFF loader matching coordinates by axis name. Update from there with: git log 4c3a2fa..dev -->

Model merging and splitting, a lot of new properties, branch plots, and many fixes around time handling. **This release contains breaking changes**, listed first below.

### ⚠️ Breaking changes

- **Naming:** `ID` is now written in lowercase in all pycellin names, following PEP 8:
  - the core properties `cell_ID`, `lineage_ID` and `cycle_ID` are renamed `cell_id`, `lineage_id` and `cycle_id`, in DataFrames and exported files too. So are the `source_cell_ID` and `target_cell_ID` columns of `to_link_dataframe()`, the `pycellin_cell_ID` property of TrackMate exports and the `lineage_ID_Pycellin` column of trackpy exports
  - `Model` methods: `get_cell_lineage_from_ID()` → `get_cell_lineage_from_id()`, and likewise `get_cycle_lineage_from_ID()`, `get_cell_lineage_IDs()`, `get_lineage_IDs()`, `get_cycle_lineage_IDs()` and `get_next_available_lineage_ID()`
  - the `ID_prop` argument of `CellLineage` and `CycleLineage` `plot()` and `get_tree_figure()` → `id_prop`
  - the fields of the `Cell` and `Link` named tuples (e.g. returned by `get_divisions()`), and the `node_ID`, `lineage_ID`, `source_lineage_ID` and `target_lineage_ID` arguments and attributes of exceptions
  - models pickled with an earlier version keep the old names
- **Properties:** `pycellin.graph.properties` moved to `pycellin.properties`. The `pycellin.graph` package no longer exists
- **Properties:** rename the `branch_*` properties to `cycle_*`, along with their `add_*()` methods, factories and calculators:
  - `branch_total_displacement` → `cycle_total_displacement`
  - `branch_mean_displacement` → `cycle_mean_displacement`
  - `branch_mean_speed` → `cycle_mean_speed`
- **Properties:** rename the `angle` property to `turning_angle` (`add_angle()` → `add_turning_angle()`)
- **Properties:** rename the `ROI_coords` node property to `cell_contour` (TrackMate and CTC loaders, all exporters, sample GEFF data)
- **Properties:** `cycle_duration` values change: it is now the time elapsed between the first and last cells of the cycle, in the reference time unit. It was previously off by one frame and scaled by the time step a second time
- **Properties:** `cycle_total_displacement` is NaN instead of 0 for cell cycles without links, such as a cycle of a single cell
- **Properties:** rename the `custom_time_property` argument of `add_absolute_age()`, `add_cell_speed()`, `add_division_rate()`, `add_division_time()` and `add_relative_age()` to `time_prop`. Their calculators' `time_prop_name` argument is renamed to `time_prop` too, and the `use_div_time` argument of the `DivisionRate` calculator is removed
- **Properties:** `add_cycle_mean_displacement()`, `add_cycle_total_displacement()` and `add_cycle_mean_speed()` raise `MissingPropertyError` when the property they're computed from (`cell_displacement` or `cell_speed`) isn't declared yet: add it first. `add_cycle_mean_speed()` now takes `speed_prop` as first argument, so pass `include_incoming_edge` by keyword
- **Properties:** `Property` setters raise `TypeError` instead of `ValueError` when given a non-string value
- **Model:** remove the `Model.recompute_property()` and `Model.export()` stubs, which did nothing. Use the `pycellin.export_*()` functions
- **Lineages:** rename `CellLineage.get_sister_cells()` to `get_sisters()`, which also works on cycle lineages, where it returns the sister cell cycles
- **Plotting:** rename `node_color_scale` to `node_colormap` in `CellLineage` and `CycleLineage` `plot()` and `get_tree_figure()`
- **CTC:** the loader now uses a new `time` property as the reference time property, instead of `timepoint`
- **CTC:** with label images (`labels_path`), cell positions and contours are now in the space unit: their pixel coordinates are multiplied by the pixel size. They were in pixels while the model had the space unit given to the loader, so properties computed from them, such as `cell_displacement`, got that unit for values in pixels
- **trackpy:** the loader now uses a new `time` property (frame × time step) as the reference time property, instead of `frame`, and renames the trackpy coordinates `x`, `y`, `z` to `cell_x`, `cell_y`, `cell_z`
- **Export:** `export_CTC_file()`, `export_GEFF()`, `export_TrackMate_XML()` and `export_trackpy_dataframe()` raise `UpdateRequiredError` when the model requires an update: call `model.update()` first. Most of them exported the changes not yet processed as they were, e.g. a lineage left in two parts by `remove_link()`, so a GEFF file written that way couldn't be read back correctly
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
- **Model:** `get_cell_lineages_from_ids()` and `get_cycle_lineages_from_ids()`
- **Model:** `overwrite_lid` argument to `add_lineage()`
- **Model:** `lineage_props` argument to `to_cell_dataframe()`, `to_link_dataframe()` and `to_cycle_dataframe()` to include lineage properties in the DataFrame
- **Model:** `to_cycle_pair_dataframe()` to export pairs of related cell cycles with the properties of both side by side, e.g. to correlate the area at birth of mothers and daughters. The relation is any cycle property listing related cell cycles: `mother_cycle`, `daughter_cycles`, `sister_cycles`, `cousin_cycles`, or a user-defined one. `unique_pairs=True` keeps a single row for pairs listed from both sides, such as sisters
- **Metadata:** `label_img` and `label_img_path` standard metadata fields
- **Metadata:** `ModelMetadata.diff()` to list the metadata fields that differ between two models
- **Properties:** `Property.get_incompatibilities()` to compare two property declarations
- **Properties:** `pycellin.properties` now exposes the 17 core property factories (`create_cell_id_property()`, `create_time_property()`, ...), to declare properties when building a model from scratch or writing a loader
- **Properties:** `time` core property with its calculator
- **Properties:** `cycle_start_time` and `cycle_end_time` core properties, the times of the first and last cells of the cycle in the reference time unit. Like `cycle_duration`, they are computed by `add_cycle_data()`
- **Properties:** `first_cell` and `last_cell` core properties, the cell IDs of the first and last cells of the cycle. `last_cell` has the same value as `cycle_id`, but says what it is. Like `cells`, they are computed by `add_cycle_data()`. Propagated to the cells, they pick the first or last cell of each cycle in `to_cell_dataframe()`: `df[df["cell_id"] == df["first_cell"]]`
- **Properties:** morphology properties `cell_polygon`, `cell_multipolygon`, `cell_contour`, `cell_area`, `cell_perimeter`, `cell_circularity` and `cell_solidity`
  - `cell_polygon` is computed from a label image or from cell contours (e.g. loaded from TrackMate or CTC data). From a label image, it keeps the largest piece of each label and fills its holes, with a warning listing the cells concerned
  - `cell_multipolygon` is computed from a label image and keeps every piece and hole of each label
- **Properties:** morphology properties `cycle_mean_area`, `birth_area` and `division_area`
- **Properties:** intensity properties `cell_total_intensity` and `cell_mean_intensity`, measured in an intensity image over the pixels of each cell, taken from a label image or from the cell polygons. Add them once per channel to measure several channels
- **Properties:** intensity properties `cycle_mean_intensity`, `birth_intensity` and `division_intensity`
- **Properties:** the `add_*()` methods of properties computed from another property take its identifier as an argument (`polygon_prop`, `area_prop`, `displacement_prop`, `speed_prop`, `intensity_prop`), e.g. to compute `cell_area` from your own polygons. The unit of the new property is taken from that property
- **Properties:** `INPUT_PROPS` class attribute on calculators, to list the properties they read. `add_custom_property()` checks that these properties are declared with the expected property and lineage types, for custom calculators too
- **Properties:** topology lineage properties `num_cells`, `num_cycles`, `num_divs`, `num_gaps` and `num_leaves`
- **Properties:** topology lineage properties `lineage_cell_depth`, `lineage_cycle_depth` and `lineage_duration`
- **Properties:** topology cycle properties `mother_cycle`, `daughter_cycles`, `sister_cycles` and `cousin_cycles`, the IDs of the mother, daughter, sister and cousin cell cycles of each cell cycle. `mother_cycle` is None for root cycles, and `add_cousin_cycles()` takes a `degree`, like `get_cousins()`
- **Properties:** `location_tag`, a cell property read from a mask image. `mask_path_metadata_field` reads the mask path from the model metadata, and a `tag_names` dict maps pixel values to region names
- **Properties:** `normalized_age`, the relative age of a cell divided by the duration of its cell cycle, from 0 at the first cell of the cycle to 1 at the last one. With `ignore_incomplete_cycles=True`, the cells of cycles that start at the root or end with a leaf get NaN
- **Properties:** `uses_external_data()` class method on calculators
- **Exceptions:** `MissingPropertyError` (a `KeyError`), raised when a required property is missing from a node, an edge or the model
- **Lineages:** `Lineage.get_depth()`, `CellLineage.get_gaps()` and `CellLineage.get_duration()`
- **Lineages:** `get_cousins()` on cell and cycle lineages: first cousins (same grandmother, different mother) by default, more distant ones with `degree`, or all of them with `degree=None`. In cell lineages, only the cousin cells at the same timepoint are returned
- **Plotting:** `pycellin.styling` module with pycellin colors and two Plotly templates, `pycellin_white` (the new default) and `pycellin_dark`
- **Plotting:** `Model.plot_mean_cell_prop_over_time()` and `Model.get_mean_cell_prop_over_time_fig()` to plot the mean and std of a cell property over time
- **Plotting:** `CellLineage.plot_branch_profile()` and `CellLineage.get_branch_profile_figure()` to plot a cell property along one or several branches, with per-branch styling of markers and lines
- **Plotting:** `CellLineage.get_branch_lineage()` and `CellLineage.get_branch_lineage_highlight()` to extract or highlight the branch leading to a cell
- **Plotting:** branch highlights in `CellLineage.plot()` and `get_tree_figure()`, with `target_cells`, `source_cells`, `generations` and `highlight_prop` arguments
- **Plotting:** support for single-cell lineages
- **Plotting:** `y_prop` of `CellLineage` and `CycleLineage` `plot()` and `get_tree_figure()` also accepts a property identifier, used as axis label. With a `Property`, the hover text now shows its unit too
- **Plotting:** `node_colormap` also accepts a dict for discrete color maps
- **Plotting:** nodes can be styled individually through `node_marker_style`
- **TrackMate:** `ref_time_prop` argument to `load_TrackMate_XML()`, e.g. `"FRAME"` to count the time in frames
- **TrackMate:** default tracker in the exported XML, so the TrackMate wizard can be navigated back
- **TrackMate:** dimension mappings for the new properties
- **trackpy:** `computed_time_prop` argument to `load_trackpy_dataframe()`
- **Dependencies:** `notebooks` extra with what the example notebooks need: JupyterLab, ipykernel, and nbformat, without which Plotly can't show figures in notebooks. Install it with `pip install "pycellin[notebooks]"`

### Changed

- **Model:** core properties (`cell_id`, `lineage_id`, `timepoint` and the reference time property) are protected whenever they are declared
- **Model:** timepoint handling is centralized in the updater: the `timepoint` calculator is always present and up to date
- **Model:** enforce the single-cell lineage convention (lineage ID = -cell ID)
- **Properties:** data types are compared after normalizing their spelling (e.g. `float` and `float64`)
- **TrackMate:** one-node lineages are identified by their size instead of by their lineage ID sign
- **TrackMate:** document that only numeric properties are exported
- **TrackMate:** the loader declares `FRAME` with the unit "frame" instead of no unit
- **GEFF:** stricter coordinate arguments in `load_GEFF()`: they must describe a complete 2D or 3D system (x and y, plus z in 3D), and inferred coordinates are each assigned at most once. A coordinate argument or `time_prop` naming a property that isn't on every node is now reported with a warning instead of an INFO message, before the property is inferred from the GEFF metadata
- **GEFF:** without `cell_id_prop`, `load_GEFF()` uses the `cell_id` property of the file as cell identifier when its values are unique non-negative integers, instead of always creating cell IDs from the GEFF node IDs. Without `lineage_id_prop`, it also looks for a `lineage_id` property when the GEFF metadata only declares a tracklet property
- **Dependencies:** declare numpy, pillow, tifffile and geff-spec, which pycellin imports directly but only got through other packages
- **Dependencies:** raise the minimum versions of pandas (2.2.2), scikit-image (0.24), shapely (2.0.4) and plotly (5.12) to the first ones that work with NumPy 2. The previous minimums allowed installs that failed at `import pycellin`
- **Dependencies:** the test dependencies moved from the `test` extra to a `test` dependency group, installed from a clone of the repository with `pip install -e . --group test` (pip >= 25.1)

### Fixed

- **Model:** changing the time step with `set_time_step()` corrupted the `timepoint` values
- **Model:** after `set_reference_time_property()`, `cycle_duration` kept the unit of the previous reference time property, although its values are computed from the new one
- **Model:** `add_lineage()` failed with `with_CycleLineage=True` or with a lineage that had no lineage ID, and ignored its `lid` argument when given a lineage
- **Model:** `add_lineage()` silently replaced a lineage that already had the same ID. It now raises `ValueError`
- **Model:** `to_cell_dataframe()`, `to_link_dataframe()`, `to_cycle_dataframe()` and `to_lineage_dataframe()` raised a pandas `FutureWarning` when a numeric property was None everywhere in a lineage. With no lineage to export, they now raise a `ValueError` that says so
- **Model:** the columns of `to_link_dataframe()` came in a different order in each Python session. They now keep the order in which the link properties were added
- **Model:** `add_cycle_data()` silently kept the properties already declared under the identifiers of its cycle properties, e.g. cycle properties propagated to cell lineages in an exported file and loaded back, so pycellin treated them as cell lineage properties. Such a declaration is now replaced when unused (no values in cell lineages, no calculator), and `add_cycle_data()` raises `ValueError` otherwise, asking to remove it first with `remove_property()`
- **Model:** adding a property already declared, e.g. calling an `add_*()` method again with other arguments, registered the new calculator but kept the first declaration. The declaration is now replaced too, with a warning. A property declared with another property type or lineage type is replaced only when unused, and raises `ValueError` otherwise
- **Model:** `update()` with a list of properties erased the values of the other cycle properties wherever it rebuilt cycle lineages (all of them after adding a property), left the other properties uncomputed on new or changed cells, and then reported the model as up to date. All the cycle properties are now computed again on rebuilt cycle lineages, and the model still requires an update, which computes the rest. A listed property without calculator, e.g. loaded from a file, made the update fail midway with `KeyError`: it is now ignored with a warning
- **Model:** a cell, link or lineage removed and then added back with the same ID before `update()` was still treated as removed: `update()` left the cell or link without property values, and deleted the lineage. This also happened without reusing an ID on purpose: once the lineage with the highest ID is removed, the next new lineage gets that ID back (the docstring of `get_next_available_lineage_id()` wrongly said it never does). So `update()` deleted a lineage split off with `split_lineage_from_cell()`, and left a lineage it split itself without cycle lineage and its new cells without property values
- **Model:** cells moved to another lineage, by a split in `update()` (e.g. after `remove_link()`), by `split_lineage_from_cell()` or by `add_link()` between two lineages, kept the `lineage_id` of their old lineage, so a GEFF file exported afterwards couldn't be read back correctly. `update()` now sets it. A split-off lineage also copied the lineage properties of the original lineage, e.g. TrackMate's track name, index and number of spots, so TrackMate exports had several tracks with the same name and index: it now starts with its new ID only
- **Model:** `update()` failed with `KeyError` when cells or links added since the last update had been moved to another lineage by `add_link()`, or when a link had been added to a lineage removed since
- **Properties:** `turning_angle` (`angle` in 0.5.1), `absolute_age` and `relative_age` were recomputed for every lineage at each update, as their calculators were global instead of local
- **Properties:** `turning_angle` (`angle` in 0.5.1) was declared as an edge property although its values are on cells
- **Properties:** `cycle_mean_displacement` and `cycle_mean_speed` (`branch_*` in 0.5.1) raised a NumPy `RuntimeWarning` for cell cycles without links. They are now NaN without warning
- **Properties:** `cell_displacement`, `cell_speed`, `turning_angle` (`angle` in 0.5.1) and `straightness`, and the cycle properties computed from them, failed with `KeyError` on 2D models without `cell_z`, e.g. loaded from a trackpy DataFrame, CTC label images or a GEFF file. They now use `cell_x` and `cell_y`, plus `cell_z` when it is declared
- **TrackMate:** `turning_angle` (`angle` in 0.5.1) in degrees was exported as a TrackMate angle, which TrackMate reads as radians
- **TrackMate:** with `keep_all_spots=True`, spots without a track got lineage IDs already used by tracks, so some lineages were silently lost. Their lineage ID is now -cell ID
- **TrackMate:** the exporter wrote missing values (None) as the string 'None', which TrackMate can't read. They are now written as NaN, which the loader reads back as None for integer properties instead of failing
- **TrackMate:** without `propagate_cycle_props=True`, the exporter declared the cycle properties as spot features although no spot had their values. In the reloaded model, these declarations remained after `add_cycle_data()`, so pycellin treated the cycle properties as cell lineage properties: `propagate_cycle_properties()` skipped them, or raised when they were listed. Cycle properties are now only declared when propagated
- **TrackMate:** the loader failed on files without `POSITION_T`, which TrackMate doesn't require. It is now computed from `FRAME` and the frame interval of the image, with a warning
- **TrackMate:** the exporter failed with `KeyError` on a model loaded from TrackMate to which a lineage had been added, since that lineage had no `FilteredTrack` flag. A lineage without the flag is now exported as a visible track
- **TrackMate:** a model loaded from a TrackMate file with cells without contour (`ROI_N_POINTS` of 0, as the exporter writes them) couldn't be exported to TrackMate again: their contour, loaded as None, made the exporter fail with `TypeError`
- **GEFF:** the loader silently kept only one lineage when several disconnected parts of the graph had the same lineage ID. It now raises `ValueError`, except when the lineage ID was only inferred from a `lineage_id` property of the file: lineage IDs are then autogenerated
- **GEFF:** the loader overwrote the `cell_id` and `lineage_id` properties of the file (`cell_ID` and `lineage_ID` in 0.5.1) when it didn't use them as identifiers. They are now kept as `geff_cell_id` and `geff_lineage_id`, with a warning
- **GEFF:** without display hints in the file, the loader took the first space axis as x, the second as y and the third as z. But GEFF orders the axes like OME-Zarr, as the dimensions of the image, with x last, so files written by geff's own CTC converter (t, y, x) or by ultrack (t, z, y, x) loaded with x and y, or x and z, swapped, and no warning. Axes named `x`, `y` or `z` (in any case) or ending with `_x`, `_y` or `_z` (e.g. `POSITION_X`) are now used for that coordinate. Only the other space axes are assigned by position, as in OME-Zarr where x comes last, with a warning, and several axes named for the same coordinate raise `ValueError`
- **GEFF:** the loader lost coordinate values when a coordinate was read from a property named like another pycellin coordinate, e.g. with `cell_x_prop="cell_y", cell_y_prop="cell_x"`, which left the model without `cell_x`
- **GEFF:** the exporter didn't write the metadata of properties with several types (`LINEAGE | NODE`, `LINEAGE | EDGE`)
- **GEFF:** the exporter failed with a `RuntimeError` that named no property on cell or link properties whose data type GEFF can't store, such as `cells` after `propagate_cycle_properties()` or TrackMate features loaded with the `unknown` data type, and on None values. Such properties are now skipped with a warning naming them, and None values are written as missing values
- **CTC:** the loader gave cells no `timepoint`, although it was the reference time property, and no `lineage_id`
- **CTC:** the loader failed on labels with holes or made of several pieces. Their contour is now the outline of the largest piece, holes filled, and a warning lists them
- **CTC:** loading label images (`labels_path`):
  - reading the pixel size from them failed with `KeyError`. It is now read from their resolution, in the unit of the ResolutionUnit tag or of the ImageJ metadata. A resolution without unit is ignored, and so is one in inches, most likely a print default such as 72 dpi, with a warning
  - each label was matched to its cell by scanning all the cells, so the loading time grew with the square of their number (over a minute for 8,000 cells). It now grows linearly
  - 3D label images failed with "too many values to unpack", and a stack holding all the frames with that error or, when its name had no frame number, with "Can't parse frame value". The loader now says that only 2D label images, one per frame, are supported
  - a `labels_path` that wasn't a folder was silently ignored when the space unit and pixel sizes were given, leaving cell positions and contours declared without values. It now raises `ValueError`
  - the `label_imgs_location` metadata field was missing when the space unit and pixel sizes were given
- **trackpy:** the loader failed when given a `time_step`, which it applied to frames, and gave cells no `lineage_id`
- **trackpy:** the loader silently overwrote the DataFrame columns named like the properties it creates (`cell_id`, `lineage_id` and `timepoint`; `cell_ID` and `lineage_ID` in 0.5.1). It now raises `ValueError`

### Maintenance

- **Tests:** new tests for model merging and splitting, the new properties, plotting, exceptions, utils, the CTC and trackpy loaders, and `load_GEFF()` end to end
- **Docs:** use the `pc` alias consistently in the README and notebooks, update and re-run the notebooks, and explain when a calculator should be local or global
- **Properties:** make the `cycle_completeness` calculator local, since it only reads its own lineage. Its values and update cost are unchanged
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
