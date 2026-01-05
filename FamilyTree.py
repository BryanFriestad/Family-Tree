import json
from collections import deque

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

		self.Person1.Spouses.append(self.Person2)
		self.Person1.Marriages.append(self)
		
		self.Person2.Spouses.append(self.Person1)
		self.Person2.Marriages.append(self)
		
		for child in self.Children:
			self.Person1.Children.append(child)
			self.Person2.Children.append(child)
			child.Parents.append(self.Person1)
			child.Parents.append(self.Person2)
		
	def GetId(self):
		return self.id
		
	def GetMainParent(self):
		return self.Person1 if self.Person1.Gender == "Female" else self.Person2
		
	def GetSpouse(self, person):
		return self.Person1 if person == self.Person2 else self.Person2

class FamilyTree():

	def __init__(self, people_file, marraiges_file):
		self.people = self._GetPeople(people_file)
		self.marriages = self._GetMarriages(marraiges_file)
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
				m.append(Marriage(self.GetPersonFromID(marriage["Person1"]), self.GetPersonFromID(marriage["Person2"]), children))
		return m
			
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
		
	def GetPersonFromID(self, id):
		p = [person for person in self.people if person.GetId() == id]
		assert(len(p) == 1)
		return p[0]

	def IsAncestor(self, potential_ancestor, subject) -> bool:
		return potential_ancestor in self.GetAncestorsOf(subject)

	def GetAncestorsOf(self, subject: Person):
		ancestors = set()
		for p in subject.Parents:
			ancestors.add(p)
			for a in self.GetAncestorsOf(p):
				ancestors.add(a)
		return ancestors

		
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
		
if __name__ == "__main__":
	familyTree = FamilyTree("data/my_people.json", "data/my_marriages.json")
	me = familyTree.GetPersonFromID(14)
	print([str(a) for a in familyTree.GetAncestorsOf(me)])