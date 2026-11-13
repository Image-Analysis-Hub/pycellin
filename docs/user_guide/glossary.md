# Glossary

:::{glossary}
lineage
  A cell and all its descendants through time. Pycellin models a lineage as a directed rooted tree. In a {class}`~pycellin.CellLineage`, a node is a cell at a specific point in time and space, and an edge links it to the same cell, or to its daughter cells after a division, at a later time point. A {class}`~pycellin.CycleLineage` shows the same lineage at the cell cycle level: a node is a whole cell cycle, from just after a division to the next division.
:::
