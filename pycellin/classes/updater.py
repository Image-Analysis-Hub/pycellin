#!/usr/bin/env python3

import networkx as nx

from pycellin.classes import Data
from pycellin.classes.lineage import CellLineage
from pycellin.classes.property_calculator import PropertyCalculator
from pycellin.custom_types import Cell, Link
from pycellin.properties.core import Timepoint, create_timepoint_property


class ModelUpdater:
    def __init__(self):
        self._update_required = False
        self._full_data_update = False

        # TODO: is a set a good idea? Maybe better to pool the nodes per lineage...
        # In this case I need to be able to modify the content of the collection
        # TODO: what is the use of saving which objects have been removed? Do
        # we have properties that need recomputing in that case?
        # => no but in that case we can remove the matching cycle lineage
        self._added_cells = set()  # set of Cell()
        self._removed_cells = set()
        self._added_links = set()  # set of Link()
        self._removed_links = set()
        self._added_lineages = set()  # set of lineage_id
        self._removed_lineages = set()
        self._modified_lineages = set()

        self._calculators = {}  # {prop_name: PropertyCalculator}

        # Cell properties are computed before cycle properties, whatever the order of
        # the calculators (see _order_calculators()). So if a cell property depends on
        # a cycle property, it will not be computed correctly. In that case, the
        # solution is to add the cycle properties first, then update, then add the cell
        # properties and update again.

    def _ensure_timepoint_calculator(
        self, data: Data, time_prop: str, time_step: int | float
    ) -> bool:
        """
        Build the timepoint calculator when it is missing or outdated.

        The timepoint property is relied upon throughout pycellin, so it must always be
        present and up to date. No calculator is needed when timepoint is the
        reference time property itself, nor when there is no data.

        Parameters
        ----------
        data : Data
            The data of the model.
        time_prop : str
            The name of the reference time property of the model.
        time_step : int | float
            The time step of the model.

        Returns
        -------
        bool
            True if a calculator was built, False otherwise.
        """
        if time_prop == "timepoint" or not data.cell_data:
            return False
        calc = self._calculators.get("timepoint")
        if (
            isinstance(calc, Timepoint)
            and calc.ref_time_prop == time_prop
            and calc.time_step == time_step
        ):
            return False
        new_calc = Timepoint(
            property=create_timepoint_property(),
            data=data,
            time_step=time_step,
            reference_time_property=time_prop,
        )
        # Registered first, so that timepoint is computed before the other properties.
        others = {k: v for k, v in self._calculators.items() if k != "timepoint"}
        self._calculators = {"timepoint": new_calc, **others}
        return True

    def _reinit(self) -> None:
        """
        Reset the state of the updater.
        """
        self._update_required = False
        self._full_data_update = False
        self._added_cells.clear()
        self._removed_cells.clear()
        self._added_links.clear()
        self._removed_links.clear()
        self._added_lineages.clear()
        self._removed_lineages.clear()
        self._modified_lineages.clear()

    def _discard_removals(self, lineage: CellLineage) -> None:
        """
        Discard the removals recorded for an added lineage, and for its cells and links.

        The lineage ID, or the IDs of its cells and links, may have been removed since
        the last update, e.g. when a removed lineage is added back, or when a new
        lineage gets the ID of a removed one. The update would otherwise treat them as
        removed: it would delete the lineage and skip its cells and links.

        Parameters
        ----------
        lineage : CellLineage
            The added lineage, with its lineage ID set.
        """
        lin_id = lineage.graph["lineage_id"]
        self._removed_lineages.discard(lin_id)
        self._removed_cells -= {Cell(cell_id, lin_id) for cell_id in lineage.nodes}
        self._removed_links -= {
            Link(source, target, lin_id) for source, target in lineage.edges
        }

    def _print_state(self) -> None:
        """
        Print the state of the updater.
        """
        print("Update required:", self._update_required)
        print("Full data update:", self._full_data_update)
        print("Added cells:", self._added_cells)
        print("Removed cells:", self._removed_cells)
        print("Added links:", self._added_links)
        print("Removed links:", self._removed_links)
        print("Added lineages:", self._added_lineages)
        print("Removed lineages:", self._removed_lineages)
        print("Modified lineages:", self._modified_lineages)

    def register_calculator(
        self,
        calculator: PropertyCalculator,
    ) -> None:
        """
        Register a calculator for a property.

        Calculators run in registration order, except that a calculator runs after
        the calculators of the properties it reads (see `_order_calculators()`).

        Parameters
        ----------
        calculator : PropertyCalculator
            The calculator to use to compute the property.
        """
        self._calculators[calculator.prop.identifier] = calculator
        self._order_calculators()

    def _order_calculators(self) -> None:
        """
        Order the calculators so that each one runs after the calculators of the
        properties it reads.

        The properties a calculator reads are the ones of its `INPUT_PROPS`. This
        matters when a property gets its calculator after a property computed from it,
        e.g. a property loaded from a file, then added again with its add method: the
        property computed from it would otherwise be computed first, from the old
        values. Such a calculator is moved just before the first calculator reading its
        property, together with the calculators of its own inputs. The reader is not
        moved after it instead, since the calculators registered in between may read
        the reader without declaring it. Otherwise, the registration order is kept, and
        the timepoint calculator stays first. With circular dependencies, a calculator
        necessarily runs before one it reads.
        """
        ordered: dict[str, PropertyCalculator] = {}
        visited: set[str] = set()

        def place(prop_id: str) -> None:
            # The calculators of the properties read are placed first.
            if prop_id in visited:  # Already placed, or circular dependency.
                return
            visited.add(prop_id)
            calc = self._calculators[prop_id]
            for input_id, _, _ in calc.get_input_props().values():
                if input_id in self._calculators:
                    place(input_id)
            ordered[prop_id] = calc

        if "timepoint" in self._calculators:
            place("timepoint")
        for prop_id in self._calculators:
            place(prop_id)
        self._calculators = ordered

    def delete_calculator(self, prop_name: str) -> None:
        """
        Delete the calculator for a property.

        Parameters
        ----------
        prop_name : str
            The name of the property for which to delete the calculator.

        Raises
        ------
        KeyError
            If the property has no registered calculator.
        """
        if prop_name in self._calculators:
            del self._calculators[prop_name]
        else:
            raise KeyError(f"Property {prop_name} has no registered calculator.")

    def _update(
        self,
        data: Data,
        time_prop: str,
        time_step: int | float,
        props_to_update: list[str] | None = None,
    ) -> bool:
        """
        Update the property values of the data.

        Parameters
        ----------
        data : Data
            The data to update.
        time_prop : str
            The name of the time property to use for the update.
        time_step : int | float
            The time step to use for the update.
        props_to_update : list of str, optional
            List of properties to update. If None, all properties are updated.
            Properties without calculator are skipped. All the cycle lineage
            properties are computed on rebuilt cycle lineages, listed or not.

        Returns
        -------
        bool
            False if the update left out cell lineage properties that have to be
            computed on the cells, links and lineages that changed, i.e. a partial
            update that did not list them. True otherwise.

        Warnings
        --------
        A property is computed after the properties it reads (`INPUT_PROPS`), but cell
        lineage properties are computed before cycle lineage properties. So if a cell
        lineage property depends on a cycle lineage property, it will not be computed
        correctly. In that case, the solution is to add the cycle properties first,
        then update, then add the cell properties and update again.
        """
        # TODO: refactor, this method is too long and does too many things.

        # Remove empty lineages.
        for lin_id in (
            self._added_lineages | self._modified_lineages
        ) - self._removed_lineages:
            if len(data.cell_data[lin_id]) == 0:
                del data.cell_data[lin_id]
                self._removed_lineages.add(lin_id)
        # Remove removed lineages.
        for lin_id in self._removed_lineages:
            if lin_id in data.cell_data:
                del data.cell_data[lin_id]

        # Split lineages with several unconnected components.
        lineages = list(data.cell_data.values())
        for lin in lineages:
            splitted_lins = [
                CellLineage(lin.subgraph(c).copy())
                for c in nx.weakly_connected_components(lin)
            ]
            if len(splitted_lins) == 1:
                continue

            original_lin_id = lin.graph["lineage_id"]

            # The largest lineage is considered to be the original one
            # and will keep its lineage ID.
            largest_lin = CellLineage()
            for lin in splitted_lins:
                if len(lin) > len(largest_lin):
                    largest_lin = lin
            # We replace it in the data, otherwise the unsplitted lineage
            # will be kept.
            data.cell_data[largest_lin.graph["lineage_id"]] = largest_lin
            self._modified_lineages.add(largest_lin.graph["lineage_id"])
            splitted_lins.remove(largest_lin)

            # The other lineages are considered as new lineages.
            for split_lin in splitted_lins:
                if len(split_lin) == 1:
                    # ID of a one-node lineage is minus the ID of the node.
                    original_cell_id = next(iter(split_lin.nodes()))
                    new_lin_id = -original_cell_id
                    if new_lin_id in data.cell_data:
                        # ID is already taken, so we get a new one based on the
                        # next available lineage ID. We want a negative lineage ID
                        # since it is a one-cell lineage.
                        new_cell_id = -data._get_next_available_lineage_id(positive=False)
                        cell_props = split_lin._remove_cell(original_cell_id)
                        time_value = cell_props.pop(time_prop)
                        assert len(split_lin) == 0
                        split_lin._add_cell(
                            new_cell_id,
                            time_prop=time_prop,
                            time_prop_value=time_value,
                            **cell_props,
                        )
                        # Track the cell ID change.
                        self._removed_cells.add(
                            Cell(cell_id=original_cell_id, lineage_id=original_lin_id)
                        )
                        self._added_cells.add(
                            Cell(cell_id=new_cell_id, lineage_id=-new_cell_id)
                        )
                        split_lin.graph["lineage_id"] = -new_cell_id
                        data.cell_data[-new_cell_id] = split_lin
                        self._added_lineages.add(-new_cell_id)
                        self._discard_removals(split_lin)
                    else:
                        # Track that the cell moved to a new lineage.
                        self._removed_cells.add(
                            Cell(cell_id=original_cell_id, lineage_id=original_lin_id)
                        )
                        self._added_cells.add(
                            Cell(cell_id=original_cell_id, lineage_id=new_lin_id)
                        )
                        split_lin.graph["lineage_id"] = new_lin_id
                        data.cell_data[new_lin_id] = split_lin
                        self._added_lineages.add(new_lin_id)
                        self._discard_removals(split_lin)
                else:
                    new_lin_id = data._get_next_available_lineage_id(positive=True)
                    # Track all cells moving to the new lineage.
                    for cell_id in split_lin.nodes():
                        self._removed_cells.add(
                            Cell(cell_id=cell_id, lineage_id=original_lin_id)
                        )
                        self._added_cells.add(
                            Cell(cell_id=cell_id, lineage_id=new_lin_id)
                        )
                    # Track all edges moving to the new lineage.
                    for source, target in split_lin.edges():
                        self._removed_links.add(
                            Link(
                                source_cell_id=source,
                                target_cell_id=target,
                                lineage_id=original_lin_id,
                            )
                        )
                        self._added_links.add(
                            Link(
                                source_cell_id=source,
                                target_cell_id=target,
                                lineage_id=new_lin_id,
                            )
                        )
                    split_lin.graph["lineage_id"] = new_lin_id
                    data.cell_data[new_lin_id] = split_lin
                    self._added_lineages.add(new_lin_id)
                    self._discard_removals(split_lin)

        # The timepoint property is always kept present and up to date.
        timepoint_built = self._ensure_timepoint_calculator(data, time_prop, time_step)

        # Update cell lineage properties, in the order of the calculators, which puts
        # a property after the properties it reads.
        if props_to_update is None:
            cell_calculators = [
                calc
                for calc in self._calculators.values()
                if calc.prop.lin_type == "CellLineage"
            ]
        else:
            cell_calculators = [
                calc
                for prop_id, calc in self._calculators.items()
                if prop_id in props_to_update and calc.prop.lin_type == "CellLineage"
            ]

        # The timepoint property is computed first, since other properties rely on it.
        timepoint_calc = self._calculators.get("timepoint")
        if timepoint_calc is not None:
            cell_calculators = [timepoint_calc] + [
                calc for calc in cell_calculators if calc is not timepoint_calc
            ]

        lins_to_process = (
            self._added_lineages | self._modified_lineages
        ) - self._removed_lineages

        # Prepare the list of nodes to process.
        nodes_to_process = [
            cell
            for cell in self._added_cells - self._removed_cells
            if cell.lineage_id in lins_to_process
        ]
        # Also include the nodes of added and modified lineages that weren't explicitly
        # added/removed.
        for lin_id in lins_to_process:
            if lin_id in data.cell_data:
                for cell_id in data.cell_data[lin_id].nodes():
                    cell = Cell(cell_id=cell_id, lineage_id=lin_id)
                    if cell not in self._removed_cells:
                        nodes_to_process.append(cell)
        # Remove duplicates.
        nodes_to_process = list(set(nodes_to_process))

        # Prepare the list of edges to process.
        edges_to_process = list(self._added_links - self._removed_links)
        # Also include the edges of added and modified lineages.
        for lin_id in lins_to_process:
            if lin_id in data.cell_data:
                for source, target in data.cell_data[lin_id].edges():
                    link = Link(
                        source_cell_id=source, target_cell_id=target, lineage_id=lin_id
                    )
                    if link not in self._removed_links:
                        edges_to_process.append(link)
        # Remove duplicates.
        edges_to_process = list(set(edges_to_process))

        # Recompute the properties as needed. A newly built timepoint calculator
        # computes the timepoint of all cells.
        all_nodes = []
        if timepoint_built:
            all_nodes = [
                Cell(cell_id=cid, lineage_id=lid)
                for lid, lin in data.cell_data.items()
                for cid in lin.nodes()
            ]
        for calc in cell_calculators:
            if timepoint_built and calc is timepoint_calc:
                nodes = all_nodes
            else:
                nodes = nodes_to_process
            # Depending on the class of the calculator, a different version of
            # the enrich() method is called.
            calc.enrich(
                data,
                nodes_to_enrich=nodes,  # self._added_cells,
                edges_to_enrich=edges_to_process,  # self._added_links,
                lineages_to_enrich=lins_to_process,  # self._added_lineages | self._modified_lineages
            )

        # In case of modifications in the structure of some cell lineages,
        # we need to recompute the cycle lineages and their properties.
        # TODO: optimize so we don't have to recompute EVERYTHING for cycle lineages?
        cycle_lineages_rebuilt = False
        for lin_id in lins_to_process:
            if data.cycle_data is not None:
                cycle_lineages_rebuilt = True
                # To preserve references, but cannot work on frozen lineages...:
                # new_cycle_data = data._compute_cycle_lineage(lin_id)
                # if lin_id in data.cycle_data:
                #     data.cycle_data.update({lin_id: new_cycle_data})
                # else:
                #     data.cycle_data[lin_id] = new_cycle_data
                data.cycle_data[lin_id] = data._compute_cycle_lineage(
                    time_prop, time_step, lin_id
                )
        # Remove cycle lineages whose cell lineage has been removed.
        for lin_id in self._removed_lineages:
            if data.cycle_data is not None and lin_id in data.cycle_data:
                del data.cycle_data[lin_id]
        # Update cycle lineages with cycle properties.
        if data.cycle_data is not None:
            # Rebuilt cycle lineages only hold their core properties, so all the cycle
            # lineage properties are computed again, even in a partial update.
            if props_to_update is None or cycle_lineages_rebuilt:
                cycle_calculators = [
                    calc
                    for calc in self._calculators.values()
                    if calc.prop.lin_type in ("CycleLineage", "Lineage")
                ]
            else:
                cycle_calculators = [
                    calc
                    for prop_id, calc in self._calculators.items()
                    if prop_id in props_to_update
                    and calc.prop.lin_type in ("CycleLineage", "Lineage")
                ]
            # Since cycle lineages are recreated at each update, every element
            # of the lineages need to be updated with its properties.
            cycle_nodes = [
                Cell(cycle_id, lin_id)
                for lin_id in data.cycle_data
                for cycle_id in data.cycle_data[lin_id].nodes()
            ]
            cycle_edges = [
                Link(source, target, lin_id)
                for lin_id in data.cycle_data
                for source, target in data.cycle_data[lin_id].edges()
            ]
            for calc in cycle_calculators:
                # Depending on the class of the calculator, a different version of
                # the enrich() method is called.
                calc.enrich(
                    data,
                    nodes_to_enrich=cycle_nodes,
                    edges_to_enrich=cycle_edges,
                    lineages_to_enrich=data.cycle_data.keys(),
                )

        # A partial update leaves out the cell lineage properties it doesn't list, on
        # the cells, links and lineages that changed.
        complete = (
            props_to_update is None
            or not lins_to_process
            or all(
                calc in cell_calculators
                for calc in self._calculators.values()
                if calc.prop.lin_type == "CellLineage"
            )
        )

        # Update is done, we can clean up.
        self._reinit()
        return complete
