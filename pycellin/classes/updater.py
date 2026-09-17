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
        self._added_lineages = set()  # set of lineage_ID
        self._removed_lineages = set()
        self._modified_lineages = set()

        self._calculators = {}  # {prop_name: PropertyCalculator}

        # TODO: add something to store the order in which properties are computed?
        # Or maybe add an argument to update() to specify the order? We need to be able
        # to specify the order only for properties that have dependencies. So it might be
        # easier to put this as an argument to the update() method, and have a default
        # order for the other properties that is the order of registration (order of keys
        # in the _calculators dictionary). Even better would be to have a solver.
        # => keep this for later
        # On a related note, currently cell properties are computed before cycle properties.
        # So if a cell property depends on a cycle property, it will not be computed
        # correctly. In that case, the solution is to add the cycle properties first,
        # then update, then add the cell properties and update again.

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

        Parameters
        ----------
        calculator : PropertyCalculator
            The calculator to use to compute the property.
        """
        self._calculators[calculator.prop.identifier] = calculator

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
    ) -> None:
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

        Warnings
        --------
        This method does not resolve properties dependencies. It is the responsibility
        of the user to ensure that properties are updated in the correct order, if needed.
        For example, cell lineage properties are computed before cycle lineage properties,
        so if a cell lineage property depends on a cycle lineage property, it will not be
        computed correctly. In that case, the solution is to add the cycle properties
        first, then update, then add the cell properties and update again.
        """
        # TODO: refactor, this method is too long and does too many things.

        # Remove empty lineages.
        for lin_ID in (
            self._added_lineages | self._modified_lineages
        ) - self._removed_lineages:
            if len(data.cell_data[lin_ID]) == 0:
                del data.cell_data[lin_ID]
                self._removed_lineages.add(lin_ID)
        # Remove removed lineages.
        for lin_ID in self._removed_lineages:
            if lin_ID in data.cell_data:
                del data.cell_data[lin_ID]

        # Split lineages with several unconnected components.
        lineages = list(data.cell_data.values())
        for lin in lineages:
            splitted_lins = [
                CellLineage(lin.subgraph(c).copy())
                for c in nx.weakly_connected_components(lin)
            ]
            if len(splitted_lins) == 1:
                continue

            original_lin_id = lin.graph["lineage_ID"]

            # The largest lineage is considered to be the original one
            # and will keep its lineage ID.
            largest_lin = CellLineage()
            for lin in splitted_lins:
                if len(lin) > len(largest_lin):
                    largest_lin = lin
            # We replace it in the data, otherwise the unsplitted lineage
            # will be kept.
            data.cell_data[largest_lin.graph["lineage_ID"]] = largest_lin
            self._modified_lineages.add(largest_lin.graph["lineage_ID"])
            splitted_lins.remove(largest_lin)

            # The other lineages are considered as new lineages.
            for split_lin in splitted_lins:
                if len(split_lin) == 1:
                    # ID of a one-node lineage is minus the ID of the node.
                    original_cell_id = next(iter(split_lin.nodes()))
                    new_lin_ID = -original_cell_id
                    if new_lin_ID in data.cell_data:
                        # ID is already taken, so we get a new one based on the
                        # next available lineage ID. We want a negative lineage ID
                        # since it is a one-cell lineage.
                        new_cell_ID = -data._get_next_available_lineage_ID(positive=False)
                        cell_props = split_lin._remove_cell(original_cell_id)
                        time_value = cell_props.pop(time_prop)
                        assert len(split_lin) == 0
                        split_lin._add_cell(
                            new_cell_ID,
                            time_prop_name=time_prop,
                            time_prop_value=time_value,
                            **cell_props,
                        )
                        # Track the cell ID change.
                        self._removed_cells.add(
                            Cell(cell_ID=original_cell_id, lineage_ID=original_lin_id)
                        )
                        self._added_cells.add(
                            Cell(cell_ID=new_cell_ID, lineage_ID=-new_cell_ID)
                        )
                        split_lin.graph["lineage_ID"] = -new_cell_ID
                        data.cell_data[-new_cell_ID] = split_lin
                        self._added_lineages.add(-new_cell_ID)
                    else:
                        # Track that the cell moved to a new lineage.
                        self._removed_cells.add(
                            Cell(cell_ID=original_cell_id, lineage_ID=original_lin_id)
                        )
                        self._added_cells.add(
                            Cell(cell_ID=original_cell_id, lineage_ID=new_lin_ID)
                        )
                        split_lin.graph["lineage_ID"] = new_lin_ID
                        data.cell_data[new_lin_ID] = split_lin
                        self._added_lineages.add(new_lin_ID)
                else:
                    new_lin_ID = data._get_next_available_lineage_ID(positive=True)
                    # Track all cells moving to the new lineage.
                    for cell_id in split_lin.nodes():
                        self._removed_cells.add(
                            Cell(cell_ID=cell_id, lineage_ID=original_lin_id)
                        )
                        self._added_cells.add(
                            Cell(cell_ID=cell_id, lineage_ID=new_lin_ID)
                        )
                    # Track all edges moving to the new lineage.
                    for source, target in split_lin.edges():
                        self._removed_links.add(
                            Link(
                                source_cell_ID=source,
                                target_cell_ID=target,
                                lineage_ID=original_lin_id,
                            )
                        )
                        self._added_links.add(
                            Link(
                                source_cell_ID=source,
                                target_cell_ID=target,
                                lineage_ID=new_lin_ID,
                            )
                        )
                    split_lin.graph["lineage_ID"] = new_lin_ID
                    data.cell_data[new_lin_ID] = split_lin
                    self._added_lineages.add(new_lin_ID)

        # The timepoint property is always kept present and up to date.
        timepoint_built = self._ensure_timepoint_calculator(data, time_prop, time_step)

        # Update cell lineage properties.
        # TODO: Deal with property dependencies. See comments in __init__.
        if props_to_update is None:
            cell_calculators = [
                calc
                for calc in self._calculators.values()
                if calc.prop.lin_type == "CellLineage"
            ]
        else:
            cell_calculators = [
                self._calculators[prop]
                for prop in props_to_update
                if self._calculators[prop].prop.lin_type == "CellLineage"
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
            if cell.lineage_ID in lins_to_process
        ]
        # Also include the nodes of added and modified lineages that weren't explicitly
        # added/removed.
        for lin_ID in lins_to_process:
            if lin_ID in data.cell_data:
                for cell_id in data.cell_data[lin_ID].nodes():
                    cell = Cell(cell_ID=cell_id, lineage_ID=lin_ID)
                    if cell not in self._removed_cells:
                        nodes_to_process.append(cell)
        # Remove duplicates.
        nodes_to_process = list(set(nodes_to_process))

        # Prepare the list of edges to process.
        edges_to_process = list(self._added_links - self._removed_links)
        # Also include the edges of added and modified lineages.
        for lin_ID in lins_to_process:
            if lin_ID in data.cell_data:
                for source, target in data.cell_data[lin_ID].edges():
                    link = Link(
                        source_cell_ID=source, target_cell_ID=target, lineage_ID=lin_ID
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
                Cell(cell_ID=cid, lineage_ID=lid)
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
        for lin_ID in lins_to_process:
            if data.cycle_data is not None:
                # To preserve references, but cannot work on frozen lineages...:
                # new_cycle_data = data._compute_cycle_lineage(lin_ID)
                # if lin_ID in data.cycle_data:
                #     data.cycle_data.update({lin_ID: new_cycle_data})
                # else:
                #     data.cycle_data[lin_ID] = new_cycle_data
                data.cycle_data[lin_ID] = data._compute_cycle_lineage(
                    time_prop, time_step, lin_ID
                )
        # Remove cycle lineages whose cell lineage has been removed.
        for lin_ID in self._removed_lineages:
            if data.cycle_data is not None and lin_ID in data.cycle_data:
                del data.cycle_data[lin_ID]
        # Update cycle lineages with cycle properties.
        if data.cycle_data is not None:
            if props_to_update is None:
                cycle_calculators = [
                    calc
                    for calc in self._calculators.values()
                    if calc.prop.lin_type in ("CycleLineage", "Lineage")
                ]
            else:
                cycle_calculators = [
                    self._calculators[prop]
                    for prop in props_to_update
                    if self._calculators[prop].prop.lin_type
                    in ("CycleLineage", "Lineage")
                ]
            # Since cycle lineages are recreated at each update, every element
            # of the lineages need to be updated with its properties.
            cycle_nodes = [
                Cell(cycle_ID, lin_ID)
                for lin_ID in data.cycle_data
                for cycle_ID in data.cycle_data[lin_ID].nodes()
            ]
            cycle_edges = [
                Link(source, target, lin_ID)
                for lin_ID in data.cycle_data
                for source, target in data.cycle_data[lin_ID].edges()
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

        # Update is done, we can clean up.
        self._reinit()
