# Glossary

This page defines the terms that Pycellin uses with a specific meaning, grouped by topic. The last section gives the words that other tools use for some of them.

## Lineages

:::{glossary}
:sorted:
branch
  The cells on the path of a {term}`cell lineage` from a cell, by default the {term}`root`, down to one of its descendants, the target cell. Unlike a {term}`cell cycle`, a branch can go through several {term}`divisions <division>`. {meth}`~pycellin.CellLineage.get_branch_lineage` extracts one, and {meth}`~pycellin.CellLineage.plot_branch_profile` plots a property along branches.

cell
  One detection of a biological cell at one time point: a {term}`node` of a {term}`cell lineage`. It holds the values of the cell properties, such as the position of the cell. A biological cell observed over several time points is therefore a series of cells, joined by {term}`links <link>`. TrackMate calls a cell a spot.

cell cycle
  The cells of a biological cell between two divisions. A cell cycle starts at the {term}`root` of its lineage or at a daughter of a {term}`division` cell, and ends with the next division cell or with a {term}`leaf`. It is identified by its {term}`cycle ID`, the {term}`cell ID` of its last cell. A cell cycle is complete when it starts just after a division and ends with a division, so that its whole duration is observed. In a {term}`cycle lineage`, each cell cycle is a node. GEFF calls a cell cycle a tracklet, and the CTC format calls it a {term}`track`.

cell lineage
  A {term}`lineage` at the cell level: a {class}`~pycellin.CellLineage`, whose nodes are {term}`cells <cell>` and whose edges are {term}`links <link>`. Readers build the cell lineages of a {term}`model` from the tracking data.

cycle lineage
  A {term}`lineage` at the cell cycle level: a {class}`~pycellin.CycleLineage`, whose nodes are {term}`cell cycles <cell cycle>`, and whose edges join each cell cycle to those of its daughter cells. {meth}`~pycellin.Model.add_cycle_lineages` builds the cycle lineages of a {term}`model` from its {term}`cell lineages <cell lineage>`, and each {term}`update` rebuilds those whose cell lineage changed. A cycle lineage has the {term}`lineage ID` of its cell lineage, and can't be edited.

division
  A cell with more than one child, i.e. more than one outgoing {term}`link`, even if it is also a {term}`fusion`. A division cell is the last cell of its {term}`cell cycle`, and each of its children starts a new one.

edge
  An element of a graph that joins two {term}`nodes <node>`. In a {term}`cell lineage`, the edges are {term}`links <link>`, and in a {term}`cycle lineage`, they join each cell cycle to those of its daughter cells. A property of {term}`property type` `"edge"` stores its values on edges.

fusion
  A cell with more than one parent, i.e. more than one incoming {term}`link`: several cells merge into one, in the sample or through a tracking error. Pycellin doesn't support fusions: readers load them with a warning, but the {term}`cell cycles <cell cycle>` and the properties computed on them can be wrong. {meth}`~pycellin.Model.get_fusions` lists them, and {meth}`~pycellin.Model.remove_link` removes the extra links.

gap
  A {term}`link` between two cells that aren't on consecutive {term}`timepoints <timepoint>`, e.g. when the tracking bridges time points where the cell wasn't detected. {meth}`~pycellin.CellLineage.get_gaps` lists them.

leaf
  A {term}`node` without child. In a {term}`cell lineage`, a leaf is a cell whose tracking ends, e.g. at the end of the movie, or when the cell leaves the field of view or is lost by the tracking.

lineage
  A cell and all its descendants through time. Pycellin represents each lineage in two ways: as a {term}`cell lineage`, cell by cell, and, once added, as a {term}`cycle lineage`, cell cycle by cell cycle. Both are directed rooted trees, unless they contain {term}`fusions <fusion>`.

link
  An {term}`edge` of a {term}`cell lineage`: it joins a {term}`cell` to the next cell of the same biological cell, or a {term}`division` cell to the first cell of each daughter. Link properties, such as the cell speed, are stored on links. TrackMate calls a link an edge.

node
  An element of a graph, which {term}`edges <edge>` can join to other nodes. In a {term}`cell lineage`, the nodes are {term}`cells <cell>`, and in a {term}`cycle lineage`, {term}`cell cycles <cell cycle>`. A property of {term}`property type` `"node"` stores its values on nodes.

root
  A {term}`node` without parent: the first node of a {term}`lineage`. A lineage has a single root, unless a {term}`fusion` merges cells with no common ancestor.
:::

## Identifiers

:::{glossary}
:sorted:
cell ID
  The `cell_id` property: an integer that identifies a {term}`cell` within its {term}`lineage`, and the ID of its node in the {term}`cell lineage`. Cells of different lineages can have the same ID, e.g. after {meth}`~pycellin.Model.add_cell` or {meth}`~pycellin.Model.merge`. {meth}`~pycellin.Model.relabel_cells` with `unique_in_model=True` gives each cell of the {term}`model` its own ID.

cycle ID
  The `cycle_id` property: the identifier of a {term}`cell cycle`, which is the {term}`cell ID` of its last cell, so it is unique within its {term}`lineage` only. It is the ID of the cell cycle's node in the {term}`cycle lineage`, and the `last_cell` property holds the same value.

lineage ID
  The `lineage_id` property: an integer that identifies a {term}`lineage` within a {term}`model`. A {term}`cycle lineage` has the lineage ID of its {term}`cell lineage`, and the cells and cell cycles of a lineage store it too. Readers take it from the file when they can, e.g. TrackMate's `TRACK_ID`, and create one otherwise.
:::

## Properties

:::{glossary}
:sorted:
calculator
  An object that computes the values of a {term}`property`, at each {term}`update` of the {term}`model`. A local calculator only reads the lineage that holds the cell, link or lineage it describes, so an update only recomputes it on the lineages changed since the previous update. A global calculator can read any lineage of the model, typically the matching {term}`cell lineage` for a cycle property computed from the cells of each cell cycle, so an update recomputes it on all the lineages. On {term}`cycle lineages <cycle lineage>`, an update recomputes both kinds on all the lineages. A calculator can read {term}`input properties <input property>`, whose identifiers you can choose. The "Custom properties" tutorial, listed in {doc}`tutorials`, shows how to write one.

core property
  A {term}`property` that Pycellin sets by itself, without an `add_` method. Reading a file sets cell, link and lineage properties such as `cell_id`, `lineage_id`, `timepoint` or `cell_x`, and {meth}`~pycellin.Model.add_cycle_lineages` sets cycle properties such as `cycle_id` or `cycle_duration`. Some core properties are {term}`protected <protected property>`.

custom property
  A {term}`property` computed by a {term}`calculator` that you write, and added with {meth}`~pycellin.Model.add_custom_property`, unlike a {term}`predefined property`. The "Custom properties" tutorial, listed in {doc}`tutorials`, shows how.

input property
  A {term}`property` that a {term}`calculator` reads, and whose identifier you can choose when you add the property it computes, e.g. with the `time_prop` argument of {meth}`~pycellin.Model.add_absolute_age`. When you add that property, the model checks that its input properties are declared, with the {term}`property type` and {term}`lineage type` that the calculator expects, and raises an error otherwise. A calculator you write lists them in its `INPUT_PROPS` attribute.

lineage property
  A {term}`property` of {term}`property type` `"lineage"`, stored on each lineage as a whole, such as the lineage duration or TrackMate's track features. {meth}`~pycellin.Model.get_lineage_properties` lists them. Not to be confused with a cell lineage property or a cycle lineage property: any property of {term}`lineage type` `"cell"` or `"cycle"`, whether stored on cells, links or lineages.

lineage type
  Which lineages hold the values of a {term}`property`: `"cell"` for the {term}`cell lineages <cell lineage>`, whose properties are called cell lineage properties, `"cycle"` for the {term}`cycle lineages <cycle lineage>`, whose properties are called cycle lineage properties or cycle properties, or `"both"` for the few properties stored on both, such as `lineage_id`. A {term}`propagated property` keeps its lineage type `"cycle"`.

predefined property
  A {term}`property` that Pycellin can compute, listed in {doc}`/api/predefined_properties`. Add one with its method, such as {meth}`~pycellin.Model.add_absolute_age`, or with {meth}`~pycellin.Model.add_pycellin_property` and its identifier. The API calls them Pycellin properties.

propagated property
  A cycle property whose values were copied onto the cells, or links, of each {term}`cell cycle` by {meth}`~pycellin.Model.propagate_cycle_properties`, e.g. to export them, since the file formats have no cycle lineages. It keeps its {term}`lineage type` `"cycle"`. {meth}`~pycellin.Model.get_propagated_properties` lists the propagated properties.

property
  A quantity stored on the {term}`cells <cell>`, {term}`links <link>`, {term}`cell cycles <cell cycle>` or {term}`lineages <lineage>` of a {term}`model`, such as the cell area. A property has a declaration and values. The declaration, a {class}`~pycellin.Property`, gives its identifier, name, description, provenance, {term}`property type`, {term}`lineage type`, data type and unit. The values are computed by a {term}`calculator` or read from a file. TrackMate calls properties features.

property type
  Where the values of a {term}`property` are stored: on {term}`nodes <node>` (`"node"`), {term}`edges <edge>` (`"edge"`) or lineages (`"lineage"`). In a {term}`cell lineage`, node and edge properties are also called cell and link properties. A property can have several types: `lineage_id` is stored both on nodes and on lineages.

protected property
  A {term}`property` that Pycellin relies on: `cell_id`, `lineage_id`, `timepoint`, the {term}`reference time property` and, once the {term}`cycle lineages <cycle lineage>` are added, their {term}`core properties <core property>`, such as `cycle_id`. {meth}`~pycellin.Model.remove_property` refuses to remove a protected property, and raises a {exc}`~pycellin.exceptions.ProtectedPropertyError`.

Pycellin property
  The API's name for a {term}`predefined property`, as in {meth}`~pycellin.Model.add_pycellin_property`.
:::

## Time

:::{glossary}
:sorted:
frame
  The index of an image in the movie, such as TrackMate's `FRAME` or the frames of a CTC dataset. It can differ from the {term}`timepoint`, e.g. when the movie starts before the first cell appears.

reference time property
  The cell property that gives the time of each {term}`cell`, by default `POSITION_T` for TrackMate data. {term}`Timepoints <timepoint>` are computed from it, and the {class}`~pycellin.Model` methods with a `time_prop` argument, such as {meth}`~pycellin.Model.add_absolute_age`, use it by default. {meth}`~pycellin.Model.set_reference_time_prop` changes it.

time step
  The interval between two consecutive time points, in the unit of the {term}`reference time property`. The model metadata can give it; otherwise, Pycellin computes it from the reference times. {meth}`~pycellin.Model.set_time_step` changes it.

timepoint
  The `timepoint` property: the number of {term}`time steps <time step>` between the reference time of a {term}`cell` and that of the earliest {term}`root` of the {term}`model`, so the first cells have timepoint 0. It is a {term}`core property`, which Pycellin computes at each {term}`update`, unless `timepoint` is itself the {term}`reference time property`. Several methods use it as their default time, such as {meth}`~pycellin.CellLineage.plot_branch_profile`. A timepoint is neither a {term}`frame` nor a time, and "time point", in two words, just means a moment of the movie.
:::

## Model

:::{glossary}
:sorted:
label image
  A stack of images, one per time point, in which the pixels of each cell hold the label of the cell, an integer. Also called a segmentation mask. Pycellin reads one to compute cell shapes and intensities, e.g. with {meth}`~pycellin.Model.add_cell_polygon`. It finds each cell in the image through a cell property holding the cell's label, `label` by default. You pass the image or its path, or the model metadata gives it.

model
  A {class}`~pycellin.Model`: the {term}`cell lineages <cell lineage>` of a tracking dataset, their {term}`cycle lineages <cycle lineage>` once added, the declarations and {term}`calculators <calculator>` of their {term}`properties <property>`, and metadata such as the {term}`time step` and the units, in a {class}`~pycellin.ModelMetadata`. Readers such as {func}`~pycellin.read_trackmate_xml` create models, and writers export them.

update
  Bringing a {term}`model` up to date. After changes to the lineages, e.g. with {meth}`~pycellin.Model.add_cell` or {meth}`~pycellin.Model.remove_link`, or after adding properties, the model requires an update: {meth}`~pycellin.Model.update` then computes the new property values. It also applies the changes of structure. For example, a lineage that `remove_link()` cut in two becomes two lineages. Writers refuse a model that requires an update, with an {exc}`~pycellin.exceptions.UpdateRequiredError`.
:::

## Other tools' terms

:::{glossary}
:sorted:
feature
  TrackMate's word for a {term}`property`.

particle
  trackpy's word for a track: {func}`~pycellin.from_trackpy` reads each particle as a {term}`lineage`, and {func}`~pycellin.to_trackpy` writes each {term}`cell cycle` as a particle.

spot
  TrackMate's word for a {term}`cell`.

track
  A word whose meaning depends on the tool. In TrackMate, a track is a whole {term}`lineage`, and its `TRACK_ID` becomes the {term}`lineage ID`. In the CTC format, a track is a single {term}`cell cycle`, linked to the track of its mother cell. In trackpy, a track is a particle: {func}`~pycellin.from_trackpy` reads each particle as a lineage, and {func}`~pycellin.to_trackpy` writes each cell cycle as a particle.

tracklet
  GEFF's word for a {term}`cell cycle`.
:::
