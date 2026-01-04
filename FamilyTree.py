from graphviz import Digraph
import uuid
import pickle
import json
from collections import deque

#https://yed.yworks.com/support/manual/layout_family_tree.html

def PickleObject(object, path):
	with open(path, 'wb') as output:
		pickle.dump(object, output, pickle.HIGHEST_PROTOCOL)
	
def UnpickleObject(path):
	outObj = None
	with open(path, 'rb') as input:
		outObj = pickle.load(input)
	return outObj

class Person():

	def __init__(self, first, gender, id):
		self.FirstName = first
		self.LastName = ""
		self.MiddleNames = []
		self.MaidenName = ""
		self.Suffix = ""
		
		self.BirthDate = None
		self.DeathDate = None
		
		self.Gender = gender
		
		self.Parents = []
		self.Children = []
		self.Spouses = []
		
		self.Marriages = []
		
		self.Generation = None
		
		self.ID = id
		
	def GetNodeId(self):
		return str(self.ID)
		
	def GetId(self):
		return self.ID
		
	def GetNodeLabel(self):
		'''
		if 'surname' in self.attr:
			label += '\\n« ' + str(self.attr['surname']) + '»'
		if 'birthday' in self.attr:
			label += '\\n' + str(self.attr['birthday'])
			if 'deathday' in self.attr:
				label += ' † ' + str(self.attr['deathday'])
		elif 'deathday' in self.attr:
			label += '\\n† ' + str(self.attr['deathday'])
		if 'notes' in self.attr:
			label += '\\n' + str(self.attr['notes'])
		'''
		return self.FirstName
		
	def __str__(self):
		return self.GetNodeLabel()
		
	def graphviz(self):
		opts = ['label="' + self.GetNodeLabel() + '"']
		shape = "square" if self.Gender == "Male" else "ellipse"
		color = "cornflowerblue" if self.Gender == "Male" else "lightcoral"
		opts.append('style=filled')
		opts.append('shape=' + shape)
		opts.append('fillcolor=' + color)
		opts.append('color=' + color)
		return self.GetNodeId() + '[' + ','.join(opts) + ']'
		
class Marriage():
	next_id = 0

	def __init__(self, p1, p2, children):
		self.Person1 = p1
		self.Person2 = p2
		self.Status = None
		self.Date = None
		self.Children = children
		self.id = "m" + str(Marriage.next_id)
		Marriage.next_id += 1
		
	def GetId(self):
		return self.id
		
	def GetMainParent(self):
		return self.Person1 if self.Person1.Gender == "Female" else self.Person2
		
	def GetSpouse(self, person):
		return self.Person1 if person == self.Person2 else self.Person2

def MakeNodes(graph, people):		
	# make subgraphs per generation and add nodes
	for gen in generations:
		with graph.subgraph() as s:
			s.attr(rank="same")
			for person in gen:
				sh = "square" if person.Gender == "Male" else "ellipse"
				color = "cornflowerblue" if person.Gender == "Male" else "lightcoral"
				s.node(person.GetNodeId(), person.GetNodeLabel(), shape = sh, fillcolor = color, color = color, style="filled")
	
def MakeEdges(graph, marriage):
	graph.edge(marriage.Person1.GetNodeId(), marriage.Person2.GetNodeId(), arrowhead = 'none', color = "black:invis:black")
	mainParent = marriage.GetMainParent()
	for child in marriage.Children:
		graph.edge(mainParent.GetNodeId(), child.GetNodeId())
		
def PrintGeneration(gen):
	"""
	Outputs an entire generation in DOT format.
	"""
	
	# Formatting for invisible nodes
	invisible = '[shape=circle,label="",height=0.01,width=0.01]';
	
	# Gets all unique marriages in this generation
	genMarriages = []
	for person in gen:
		if person.Marriages:
			for marriage in person.Marriages:
				if marriage.GetId() not in [m.GetId() for m in genMarriages]:
					genMarriages.append(marriage)
	
	# Display persons and marriage nodes
	print('\t{ rank=same;')
	for marriage in genMarriages:
		print(f'\t\t{marriage.Person1.GetNodeId()} -> {marriage.GetId()} -> {marriage.Person2.GetNodeId()};')
		print(f'\t\t{marriage.GetId()}{invisible};')
	print('\t}')

	# Add marriage helper nodes
	print('\t{ rank=same;')
	for marriage in genMarriages:
		numChildren = len(marriage.Children)
		if not numChildren:
			continue;
		
		# add edges between marriage helper nodes
		marriageChildrenLayoutEdges = "\t\t"		
		for i in range(numChildren - 1):
			marriageChildrenLayoutEdges += f'{marriage.GetId()}_{i} -> '
		marriageChildrenLayoutEdges += f'{marriage.GetId()}_{numChildren - 1};'
		print(marriageChildrenLayoutEdges)
		
		# add marriage helper nodes themselves
		for i in range(numChildren):
			print(f'\t\t{marriage.GetId()}_{i}{invisible};')
	print('\t}')

	# connect helper nodes to children of marriages
	for marriage in genMarriages:
		numChildren = len(marriage.Children)
		if not numChildren:
			continue;
		
		middle = int(numChildren/2)
		print(f'\t\t{marriage.GetId()} -> {marriage.GetId()}_{middle};')
		
		for i in range(numChildren):
			print(f'\t\t{marriage.GetId()}_{i} -> {marriage.Children[i].GetNodeId()};') 
	
def PrintFamilyTree(people, generations):
		"""
		Outputs the whole family tree in DOT format.
		"""

		print('digraph {\n' + \
		      '\tnode [shape=box];\n' + \
		      '\tedge [dir=none];\n')
		      #'\tedge [dir=none];\n' + \
			  #'\tgraph [splines=ortho];\n')

		for p in people:
			print('\t' + p.graphviz() + ';')
		print('')

		for gen in generations:
			PrintGeneration(gen)

		print('}')
		
class FamilyTree():

	def __init__(self, people_file, marraiges_file):
		self.people = self._GetPeople(people_file)
		self.marriages = self._GetMarriages(marraiges_file)
		for marriage in self.marriages:
			self._SetupMarriageRelationships(marriage)
		self.generations = self._DetermineGenerations()
		
	def _GetPeople(self, filename):
		p = []
		with open(filename, "r") as file:
			obj = json.load(file)
			for person in obj['People']:
				p.append(Person(person["FirstName"], person["Gender"], person["ID"]))
		return p
	
	def _GetMarriages(self, filename):
		m = []
		with open(filename, "r") as file:
			obj = json.load(file)
			for marriage in obj['Marriages']:
				children = []
				for c in marriage['Children']:
					children.append(self.GetPersonFromID(c))
				m.append(Marriage(self.GetPersonFromID(marriage["Person1"]), self.GetPersonFromID(marriage["Person2"]),children))
		return m
		
	def _SetupMarriageRelationships(self, marriage):
		marriage.Person1.Spouses.append(marriage.Person2)
		marriage.Person1.Marriages.append(marriage)
		
		marriage.Person2.Spouses.append(marriage.Person1)
		marriage.Person2.Marriages.append(marriage)
		
		for child in marriage.Children:
			marriage.Person1.Children.append(child)
			marriage.Person2.Children.append(child)
			child.Parents.append(marriage.Person1)
			child.Parents.append(marriage.Person2)
			
	def _DetermineGenerations(self):
		# Set generations of all people
		self._SetGeneration(self.people[0], 0)
		while not self._DoAllPeopleHaveAGeneration():
			peopleWithoutGen = [person for person in self.people if person.Generation is None]
			self._SetGeneration(peopleWithoutGen[0], 0)
			
		# Normalize gens to ascend from 0 and sort the people by generation
		self._NormalizeGenerations()
		self.people.sort(key=lambda person: person.Generation)
		
		# Put people into generations
		generations = [[]]
		genIndex = 0
		for person in self.people:
			if person.Generation != genIndex:
				genIndex = genIndex + 1
				generations.append([])
			generations[genIndex].append(person)
		return generations
		
	def _NormalizeGenerations(self):
		minGen = self.people[0].Generation
		for person in self.people:
			if person.Generation < minGen:
				minGen = person.Generation
				
		adj = 0 - minGen
		for person in self.people:
			person.Generation = person.Generation + adj
			#print(f'{person.FirstName} - Generation {person.Generation}')
		
	def _SetGeneration(self, person, generation):
		person.Generation = generation
		for parent in person.Parents:
			if parent.Generation is None:
				self._SetGeneration(parent, person.Generation + 1)
		for child in person.Children:
			if child.Generation is None:
				self._SetGeneration(child, person.Generation - 1)
		for spouse in person.Spouses:
			if spouse.Generation is None:
				self._SetGeneration(spouse, person.Generation)
		
	def _DoAllPeopleHaveAGeneration(self):
		for person in self.people:
			if person.Generation is None:
				return False
		return True
		
	def _GenerationToGraphviz(self, gen):
		"""
		Outputs an entire generation in DOT format.
		"""
		# Formatting for invisible nodes
		invisible = '[shape=circle,label="",height=0.01,width=0.01]';
		
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
				continue;
			
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
				continue;
			
			middle = int(numChildren/2)
			generationDOT += f'\t\t{marriage.GetId()} -> {marriage.GetId()}_{middle};\n'
			
			for i in range(numChildren):
				generationDOT += f'\t\t{marriage.GetId()}_{i} -> {marriage.Children[i].GetNodeId()};\n' 
		
		return generationDOT
		
	def GetPersonFromID(self, id):
		p = [person for person in self.people if person.GetId() == id]
		assert(len(p) == 1)
		return p[0]
		
	def graphviz(self):
		"""
		Returns a string representing the family tree in DOT notation.
		"""
		graphstring = ""
		
		graphstring += 'digraph {\n'
		graphstring += '\tnode [shape=box];\n'
		graphstring += '\tedge [dir=none];\n'
		graphstring += '\tgraph [splines=ortho];\n'

		for p in self.people:
			graphstring += f'\t{p.graphviz()};\n'
		graphstring += '\n'

		for gen in self.generations:
			graphstring += self._GenerationToGraphviz(gen)

		graphstring += '}'
		return graphstring
		
	def GetLocalPeople(self, center_id, max_up=2, max_down=2, max_nodes=200):
		center = self.GetPersonFromID(center_id)
		included = set()
		best = {}
		q = deque()
		q.append((center, 0, 0))
		best[center.GetId()] = (0, 0)
		included.add(center)

		while q and len(included) < max_nodes:
			person, up_used, down_used = q.popleft()

			for spouse in person.Spouses:
				spouse_id = spouse.GetId()
				state = (up_used, down_used)
				prev = best.get(spouse_id)
				if prev is None or state < prev:
					best[spouse_id] = state
					included.add(spouse)
					q.append((spouse, up_used, down_used))
					if len(included) >= max_nodes:
						break
			if len(included) >= max_nodes:
				break

			if up_used < max_up:
				for parent in person.Parents:
					parent_id = parent.GetId()
					state = (up_used + 1, down_used)
					prev = best.get(parent_id)
					if prev is None or state < prev:
						best[parent_id] = state
						included.add(parent)
						q.append((parent, up_used + 1, down_used))
						if len(included) >= max_nodes:
							break
			if len(included) >= max_nodes:
				break

			if down_used < max_down:
				for child in person.Children:
					child_id = child.GetId()
					state = (up_used, down_used + 1)
					prev = best.get(child_id)
					if prev is None or state < prev:
						best[child_id] = state
						included.add(child)
						q.append((child, up_used, down_used + 1))
						if len(included) >= max_nodes:
							break

		return list(included)
		
	def GetLocalMarriages(self, local_people):
		local_ids = {p.GetId() for p in local_people}
		local_marriages = []
		for marriage in self.marriages:
			p1_in = marriage.Person1.GetId() in local_ids
			p2_in = marriage.Person2.GetId() in local_ids
			child_in = any(c.GetId() in local_ids for c in marriage.Children)
			if (p1_in and p2_in) or (child_in and (p1_in or p2_in)):
				local_marriages.append(marriage)
		return local_marriages
		
	def ComputeCanvasLayout(self, center_id, max_up=2, max_down=2, max_nodes=200, x_spacing=180, y_spacing=140, sweeps=6):
		local_people = self.GetLocalPeople(center_id, max_up=max_up, max_down=max_down, max_nodes=max_nodes)
		local_people_by_id = {p.GetId(): p for p in local_people}
		local_marriages = self.GetLocalMarriages(local_people)

		center = local_people_by_id[center_id]
		gen = {center.GetId(): 0}
		q = deque([center])
		while q:
			person = q.popleft()
			g = gen[person.GetId()]
			for spouse in person.Spouses:
				if spouse.GetId() in local_people_by_id and spouse.GetId() not in gen:
					gen[spouse.GetId()] = g
					q.append(spouse)
			for parent in person.Parents:
				if parent.GetId() in local_people_by_id and parent.GetId() not in gen:
					gen[parent.GetId()] = g - 1
					q.append(parent)
			for child in person.Children:
				if child.GetId() in local_people_by_id and child.GetId() not in gen:
					gen[child.GetId()] = g + 1
					q.append(child)

		gens = {}
		for pid, gg in gen.items():
			gens.setdefault(gg, []).append(local_people_by_id[pid])
		if not gens:
			return {"center_id": center_id, "people": [], "marriages": [], "positions": {}}
		min_g = min(gens.keys())
		max_g = max(gens.keys())

		order = {}
		for gg in range(min_g, max_g + 1):
			order[gg] = sorted(gens.get(gg, []), key=lambda p: p.GetId())

		# Map each child to the first marriage (union) that contains it.
		child_to_marriage = {}
		for marriage in local_marriages:
			for child in marriage.Children:
				cid = child.GetId()
				if cid in local_people_by_id and cid not in child_to_marriage:
					child_to_marriage[cid] = marriage

		def _index_maps():
			idx = {}
			for gg, lst in order.items():
				idx[gg] = {p.GetId(): i for i, p in enumerate(lst)}
			return idx

		def _sibling_block_bounds(pid, gg, idx_g):
			m = child_to_marriage.get(pid)
			if m is None:
				return None
			ids = [c.GetId() for c in m.Children if gen.get(c.GetId()) == gg and c.GetId() in idx_g]
			if len(ids) <= 1:
				return None
			pos = sorted(idx_g[i] for i in ids)
			return (pos[0], pos[-1])

		def _enforce_spouse_adjacency():
			for marriage in local_marriages:
				p1 = marriage.Person1
				p2 = marriage.Person2
				if p1.GetId() not in gen or p2.GetId() not in gen:
					continue
				gg = gen[p1.GetId()]
				if gen[p2.GetId()] != gg:
					continue
				lst = order.get(gg, [])
				if not lst:
					continue
				idx_g = {p.GetId(): i for i, p in enumerate(lst)}
				i1 = idx_g.get(p1.GetId())
				i2 = idx_g.get(p2.GetId())
				if i1 is None or i2 is None or abs(i1 - i2) <= 1:
					continue

				b1 = _sibling_block_bounds(p1.GetId(), gg, idx_g)
				b2 = _sibling_block_bounds(p2.GetId(), gg, idx_g)
				anchor = p1
				mover = p2
				if b2 is not None and b1 is None:
					anchor, mover = p2, p1
				elif b1 is None and b2 is None:
					anchor, mover = (p1, p2) if p1.GetId() <= p2.GetId() else (p2, p1)

				lst = order[gg]
				idx_g = {p.GetId(): i for i, p in enumerate(lst)}
				anchor_idx = idx_g.get(anchor.GetId())
				mover_idx = idx_g.get(mover.GetId())
				if anchor_idx is None or mover_idx is None:
					continue

				lst.pop(mover_idx)
				idx_g = {p.GetId(): i for i, p in enumerate(lst)}
				anchor_idx = idx_g.get(anchor.GetId())
				if anchor_idx is None:
					continue

				insert_at = anchor_idx + 1
				b_anchor = _sibling_block_bounds(anchor.GetId(), gg, idx_g)
				if b_anchor is not None:
					insert_at = b_anchor[1] + 1
				lst.insert(min(insert_at, len(lst)), mover)
				order[gg] = lst

		def _order_children_by_parent_barycenter(gg, idx_prev):
			lst = order.get(gg, [])
			if not lst:
				return
			cur_idx = {p.GetId(): i for i, p in enumerate(lst)}
			used = set()
			blocks = []

			for marriage in local_marriages:
				p1 = marriage.Person1
				p2 = marriage.Person2
				if gen.get(p1.GetId()) != gg - 1 or gen.get(p2.GetId()) != gg - 1:
					continue
				children = [c for c in marriage.Children if gen.get(c.GetId()) == gg and c.GetId() in cur_idx]
				if len(children) <= 1:
					continue
				for c in children:
					used.add(c.GetId())
				parents = [par for par in (p1, p2) if par.GetId() in idx_prev]
				b = sum(idx_prev[par.GetId()] for par in parents) / len(parents) if parents else 0
				children.sort(key=lambda c: (cur_idx[c.GetId()], c.GetId()))
				blocks.append((0, b, marriage.GetId(), children))

			for p in lst:
				pid = p.GetId()
				if pid in used:
					continue
				parents = [par for par in p.Parents if par.GetId() in idx_prev]
				b = sum(idx_prev[par.GetId()] for par in parents) / len(parents) if parents else cur_idx[pid]
				blocks.append((1, b, pid, [p]))
				used.add(pid)

			blocks.sort(key=lambda t: (t[0], t[1], t[2]))
			new_lst = []
			for _, __, ___, block in blocks:
				new_lst.extend(block)
			order[gg] = new_lst

		def _order_couples_by_children_barycenter(gg, idx_next):
			lst = order.get(gg, [])
			if not lst:
				return
			cur_idx = {p.GetId(): i for i, p in enumerate(lst)}
			used = set()
			blocks = []

			for marriage in local_marriages:
				p1 = marriage.Person1
				p2 = marriage.Person2
				if gen.get(p1.GetId()) != gg or gen.get(p2.GetId()) != gg:
					continue
				if p1.GetId() not in cur_idx or p2.GetId() not in cur_idx:
					continue
				child_positions = [idx_next[c.GetId()] for c in marriage.Children if gen.get(c.GetId()) == gg + 1 and c.GetId() in idx_next]
				b = sum(child_positions) / len(child_positions) if child_positions else (cur_idx[p1.GetId()] + cur_idx[p2.GetId()]) / 2
				pair = [p1, p2] if cur_idx[p1.GetId()] <= cur_idx[p2.GetId()] else [p2, p1]
				blocks.append((0, b, marriage.GetId(), pair))
				used.add(p1.GetId())
				used.add(p2.GetId())

			for p in lst:
				pid = p.GetId()
				if pid in used:
					continue
				child_positions = [idx_next[c.GetId()] for c in p.Children if gen.get(c.GetId()) == gg + 1 and c.GetId() in idx_next]
				b = sum(child_positions) / len(child_positions) if child_positions else cur_idx[pid]
				blocks.append((1, b, pid, [p]))
				used.add(pid)

			blocks.sort(key=lambda t: (t[0], t[1], t[2]))
			new_lst = []
			for _, __, ___, block in blocks:
				new_lst.extend(block)
			order[gg] = new_lst

		for _ in range(sweeps):
			idx = _index_maps()
			for gg in range(min_g + 1, max_g + 1):
				_order_children_by_parent_barycenter(gg, idx.get(gg - 1, {}))
			_enforce_spouse_adjacency()
			idx = _index_maps()
			for gg in range(max_g - 1, min_g - 1, -1):
				_order_couples_by_children_barycenter(gg, idx.get(gg + 1, {}))
			_enforce_spouse_adjacency()

		positions = {}
		for gg in range(min_g, max_g + 1):
			lst = order.get(gg, [])
			for i, p in enumerate(lst):
				positions[p.GetId()] = (i * x_spacing, gg * y_spacing)

		if center_id in positions:
			cx, cy = positions[center_id]
			for pid, (x, y) in list(positions.items()):
				positions[pid] = (x - cx, y - cy)

		marriage_payload = []
		for marriage in local_marriages:
			payload = {
				"id": marriage.GetId(),
				"spouses": [marriage.Person1.GetId(), marriage.Person2.GetId()],
				"children": [c.GetId() for c in marriage.Children if c.GetId() in positions],
			}
			if payload["spouses"][0] in positions or payload["spouses"][1] in positions or payload["children"]:
				marriage_payload.append(payload)

		return {
			"center_id": center_id,
			"people": [p.GetId() for p in local_people],
			"marriages": marriage_payload,
			"positions": positions,
		}
		
if __name__ == "__main__":
	tree = Digraph(comment = 'Ancestry', graph_attr = {'splines':'ortho'}, filename='familytree.gv', engine="dot")
	familyTree = FamilyTree("people.json", "marriages.json")
	
	print(familyTree.graphviz())
	
	#PrintFamilyTree(people, generations)
	#for marriage in marriages:
	#tree.view()