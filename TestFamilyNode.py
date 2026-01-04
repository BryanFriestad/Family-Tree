if __name__ == '__main__':
	from graphviz import Digraph
	tree = Digraph(comment = 'Ancestry', graph_attr = {'splines':'ortho'}, filename='test.gv', engine="dot")
	
	with tree.subgraph() as s:
		s.attr(rank="same")
		s.node("Dad", shape = "square", fillcolor = "cornflowerblue", color = "cornflowerblue", style="filled")
		s.node("family", shape = "point")
		s.node("Mom", shape = "ellipse", fillcolor = "lightcoral", color = "lightcoral", style="filled")
		s.edge("Dad", "family", color = "white", arrowhead = None)
		s.edge("family", "Mom", color = "white", arrowhead = None)
		
	with tree.subgraph() as s:
		s.attr(rank="same")
		s.node("me", shape = "square", fillcolor = "cornflowerblue", color = "cornflowerblue", style="filled")
		s.node("Sister", shape = "ellipse", fillcolor = "lightcoral", color = "lightcoral", style="filled")
		
	tree.edge("Mom", "family", arrowhead = None)
	tree.edge("Dad", "family", arrowhead = None)
	tree.edge("family", "me", arrowhead = None)
	tree.edge("family", "Sister", arrowhead = None)
	
	tree.view()