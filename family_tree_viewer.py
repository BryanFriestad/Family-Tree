import tkinter as tk
from tkinter import Canvas
from FamilyTree import FamilyTree
from family_tree_layout import compute_canvas_layout


class ViewConfig:
	node_w: int = 120
	node_h: int = 46
	node_rx: int = 10
	font: str = "SegoeUI 10"

	line_color: str = "#333333"
	male_fill: str = "cornflowerblue"
	female_fill: str = "lightcoral"

	grid_padding: int = 40


class FamilyTreeViewer(tk.Frame):
	def __init__(self, master, family_tree: FamilyTree, center_id: int):
		super().__init__(master)
		self.family_tree = family_tree
		self.center_id = center_id
		self.config = ViewConfig()

		self.max_up = 3
		self.max_down = 3
		self.layout_sweeps = 10

		self.scale = 1.0
		self.offset_x = 0.0
		self.offset_y = 0.0

		self._drag_last = None
		self._node_hitboxes = []

		self.canvas = tk.Canvas(self, background="white", highlightthickness=0)
		self.canvas.pack(fill=tk.BOTH, expand=True)

		self.canvas.bind("<ButtonPress-1>", self._on_left_down)
		self.canvas.bind("<B1-Motion>", self._on_left_drag)
		self.canvas.bind("<ButtonRelease-1>", self._on_left_up)
		self.canvas.bind("<ButtonPress-3>", self._on_right_down)

		self.canvas.bind("<MouseWheel>", self._on_mousewheel)
		self.canvas.bind("<Button-4>", self._on_mousewheel)
		self.canvas.bind("<Button-5>", self._on_mousewheel)

		self.canvas.bind("<Configure>", self._on_resize)

		self.redraw(center_on_load=True)

	def _world_to_screen(self, x, y):
		sx = (x * self.scale) + self.offset_x
		sy = (y * self.scale) + self.offset_y
		return sx, sy

	def _screen_to_world(self, sx, sy):
		x = (sx - self.offset_x) / self.scale
		y = (sy - self.offset_y) / self.scale
		return x, y

	def _on_resize(self, _event):
		self.redraw(center_on_load=False)

	def _on_left_down(self, event):
		person_id = self._hit_test(event.x, event.y)
		if person_id is not None:
			self.center_id = person_id
			self.redraw(center_on_load=True)
			return

		self._drag_last = (event.x, event.y)

	def _on_left_drag(self, event):
		if self._drag_last is None:
			return
		last_x, last_y = self._drag_last
		dx = event.x - last_x
		dy = event.y - last_y
		self.offset_x += dx
		self.offset_y += dy
		self._drag_last = (event.x, event.y)
		self.redraw(center_on_load=False)

	def _on_left_up(self, _event):
		self._drag_last = None

	def _on_right_down(self, _event):
		self.scale = 1.0
		self.redraw(center_on_load=True)

	def _on_mousewheel(self, event):
		if event.num == 5 or event.delta < 0:
			factor = 0.9
		else:
			factor = 1.1

		mx, my = event.x, event.y
		wx, wy = self._screen_to_world(mx, my)

		self.scale *= factor
		self.scale = max(0.2, min(4.0, self.scale))

		sx, sy = self._world_to_screen(wx, wy)
		self.offset_x += (mx - sx)
		self.offset_y += (my - sy)

		self.redraw(center_on_load=False)

	def _hit_test(self, sx, sy):
		for x1, y1, x2, y2, pid in self._node_hitboxes:
			if x1 <= sx <= x2 and y1 <= sy <= y2:
				return pid
		return None

	def redraw(self, center_on_load: bool):
		layout = compute_canvas_layout(
			self.family_tree,
			self.center_id,
			max_up=self.max_up,
			max_down=self.max_down,
			x_spacing=180,
			y_spacing=140,
			sweeps=self.layout_sweeps,
		)
		positions = layout["positions"]
		marriages = layout["marriages"]

		if center_on_load:
			w = max(1, self.canvas.winfo_width())
			h = max(1, self.canvas.winfo_height())
			self.offset_x = w / 2
			self.offset_y = h / 2

		self.canvas.delete("all")
		self._node_hitboxes = []

		people_by_id = {p.GetId(): p for p in self.family_tree.people}

		def draw_polyline(world_points, width=1):
			screen_points = []
			for wx, wy in world_points:
				sx, sy = self._world_to_screen(wx, wy)
				screen_points.extend([sx, sy])
			self.canvas.create_line(*screen_points, fill=self.config.line_color, width=width)

		def spouse_midpoint(p1_id, p2_id):
			if p1_id not in positions or p2_id not in positions:
				return None
			x1, y1 = positions[p1_id]
			x2, y2 = positions[p2_id]
			return ((x1 + x2) / 2, (y1 + y2) / 2)

		parent_anchor_dy = (self.config.node_h / 2) + 6
		child_anchor_dy = (self.config.node_h / 2) + 6
		bus_gap = 18
		bus_lane_count_by_parent_y = {}

		# Draw relationship lines first
		for mi, m in enumerate(marriages):
			sp = m["spouses"]
			if len(sp) != 2:
				continue
			p1_id, p2_id = sp

			if p1_id in positions and p2_id in positions:
				x1, y1 = positions[p1_id]
				x2, y2 = positions[p2_id]
				draw_polyline([(x1, y1), (x2, y2)], width=2)

			mid = spouse_midpoint(p1_id, p2_id)
			if mid is None:
				continue
			mx, my = mid
			children = [cid for cid in m["children"] if cid in positions]
			if not children:
				continue

			child_xs = [positions[cid][0] for cid in children]
			child_ys = [positions[cid][1] for cid in children]
			x_min = min(child_xs)
			x_max = max(child_xs)
			nearest_child_y = min(child_ys)
			x_left = x_min
			x_right = x_max
			sib_x = (x_left + x_right) / 2

			parent_anchor_y = my + parent_anchor_dy
			bus_y = min(nearest_child_y - child_anchor_dy - bus_gap, parent_anchor_y + 40)

			parent_y_key = int(round(my))
			lane = bus_lane_count_by_parent_y.get(parent_y_key, 0)
			bus_lane_count_by_parent_y[parent_y_key] = lane + 1
			bus_y += lane * 8
			bus_y = min(bus_y, nearest_child_y - child_anchor_dy - 6)

			# Marriage node -> sibling node (bus midpoint)
			draw_polyline([(mx, my), (mx, bus_y), (sib_x, bus_y)], width=1)
			# Sibling bus
			draw_polyline([(x_left, bus_y), (x_right, bus_y)], width=1)

			for child_id in children:
				cx, cy = positions[child_id]
				child_anchor_y = cy - child_anchor_dy
				draw_polyline([(cx, bus_y), (cx, child_anchor_y)], width=1)

		# Draw nodes on top
		for pid, (x, y) in positions.items():
			person = people_by_id.get(pid)
			if person is None:
				continue

			sx, sy = self._world_to_screen(x, y)
			w = self.config.node_w * self.scale
			h = self.config.node_h * self.scale
			x1 = sx - w / 2
			y1 = sy - h / 2
			x2 = sx + w / 2
			y2 = sy + h / 2

			fill = self.config.male_fill if person.Gender == "Male" else self.config.female_fill
			outline = "#000000" if pid == self.center_id else "#333333"

			r = max(2, int(self.config.node_rx * self.scale))
			self._rounded_rect(x1, y1, x2, y2, r, fill=fill, outline=outline, width=2)

			label = person.GetNodeLabel()
			font_size = max(6, int(10 * self.scale))
			self.canvas.create_text(
				sx,
				sy,
				text=label,
				font=("Segoe UI", font_size),
				fill="white",
			)

			self._node_hitboxes.append((x1, y1, x2, y2, pid))

	def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
		# Approximate rounded rectangle using a smoothed polygon
		points = [
			x1 + r,
			y1,
			x2 - r,
			y1,
			x2,
			y1,
			x2,
			y1 + r,
			x2,
			y2 - r,
			x2,
			y2,
			x2 - r,
			y2,
			x1 + r,
			y2,
			x1,
			y2,
			x1,
			y2 - r,
			x1,
			y1 + r,
			x1,
			y1,
		]
		return self.canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def main():
	root = tk.Tk()
	root.title("Family Tree Viewer")
	root.geometry("1200x800")

	# family_tree = FamilyTree("data/example_people.json", "data/example_marriages.json")
	family_tree = FamilyTree("data/people.json", "data/marriages.json")
	center_id = 6

	viewer = FamilyTreeViewer(root, family_tree, center_id=center_id)
	viewer.pack(fill=tk.BOTH, expand=True)

	root.mainloop()


if __name__ == "__main__":
	main()
