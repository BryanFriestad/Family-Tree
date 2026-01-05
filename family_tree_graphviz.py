"""
GraphViz export for family trees.
Generates DOT notation for family tree visualization.
"""


def _generation_to_graphviz(gen):
    """
    Outputs an entire generation in DOT format.
    """
    # Formatting for invisible nodes
    invisible = '[shape=circle,label="",height=0.01,width=0.01]'

    generationDOT = ""

    # Gets all unique marriages in this generation
    genMarriages = []
    for person in gen:
        if person.Marriages:
            for marriage in person.Marriages:
                if marriage.GetId() not in [m.GetId() for m in genMarriages]:
                    genMarriages.append(marriage)

    # Display persons and marriage nodes
    generationDOT += '\t{ rank=same;\n'
    for marriage in genMarriages:
        generationDOT += f'\t\t{marriage.Person1.GetNodeId()} -> {marriage.GetId()} -> {marriage.Person2.GetNodeId()};\n'
        generationDOT += f'\t\t{marriage.GetId()}{invisible};\n'
    generationDOT += '\t}\n'

    # Add marriage helper nodes
    generationDOT += '\t{ rank=same;\n'
    for marriage in genMarriages:
        numChildren = len(marriage.Children)
        if not numChildren:
            continue

        # add edges between marriage helper nodes
        marriageChildrenLayoutEdges = "\t\t"
        for i in range(numChildren - 1):
            marriageChildrenLayoutEdges += f'{marriage.GetId()}_{i} -> '
        marriageChildrenLayoutEdges += f'{marriage.GetId()}_{numChildren - 1};'
        generationDOT += marriageChildrenLayoutEdges + "\n"

        # add marriage helper nodes themselves
        for i in range(numChildren):
            generationDOT += f'\t\t{marriage.GetId()}_{i}{invisible};\n'
    generationDOT += '\t}\n'

    # connect helper nodes to children of marriages
    for marriage in genMarriages:
        numChildren = len(marriage.Children)
        if not numChildren:
            continue

        middle = int(numChildren / 2)
        generationDOT += f'\t\t{marriage.GetId()} -> {marriage.GetId()}_{middle};\n'

        for i in range(numChildren):
            generationDOT += f'\t\t{marriage.GetId()}_{i} -> {marriage.Children[i].GetNodeId()};\n'

    return generationDOT


def to_graphviz(family_tree):
    """
    Returns a string representing the family tree in DOT notation.
    """
    graphstring = ""

    graphstring += 'digraph {\n'
    graphstring += '\tnode [shape=box];\n'
    graphstring += '\tedge [dir=none];\n'
    graphstring += '\tgraph [splines=ortho];\n'

    for p in family_tree.people:
        graphstring += f'\t{p.graphviz()};\n'
    graphstring += '\n'

    for gen in family_tree.generations:
        graphstring += _generation_to_graphviz(gen)

    graphstring += '}'
    return graphstring
