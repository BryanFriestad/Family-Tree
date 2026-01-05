"""
Family tree layout engine.
Provides canvas layout with generation ranks, marriage-aware ordering, and pseudo-node constraints.
"""

from collections import deque
from typing import Dict, List, Tuple, Any


def compute_canvas_layout(
    family_tree,
    center_id: int,
    max_up: int = 2,
    max_down: int = 2,
    max_nodes: int = 200,
    x_spacing: int = 180,
    y_spacing: int = 140,
    sweeps: int = 6,
) -> Dict[str, Any]:
    """
    Compute a deterministic canvas layout for a local subgraph around a center person.
    Returns a dict with people, marriages, and (x, y) positions.
    """
    local_people = family_tree.GetLocalPeople(center_id, max_up=max_up, max_down=max_down, max_nodes=max_nodes)
    local_people_by_id = {p.GetId(): p for p in local_people}
    local_marriages = family_tree.GetLocalMarriages(local_people)

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

    spouse_degree_in_gen = {}
    for marriage in local_marriages:
        p1 = marriage.Person1
        p2 = marriage.Person2
        if p1.GetId() not in gen or p2.GetId() not in gen:
            continue
        gg = gen[p1.GetId()]
        if gen.get(p2.GetId()) != gg:
            continue
        spouse_degree_in_gen[(gg, p1.GetId())] = spouse_degree_in_gen.get((gg, p1.GetId()), 0) + 1
        spouse_degree_in_gen[(gg, p2.GetId())] = spouse_degree_in_gen.get((gg, p2.GetId()), 0) + 1

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
            if spouse_degree_in_gen.get((gg, p1.GetId()), 0) > 1 or spouse_degree_in_gen.get((gg, p2.GetId()), 0) > 1:
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

    # Build sibling-group map: child -> list of siblings (including self) in same generation.
    sibling_groups = {}
    for marriage in local_marriages:
        children_in_gen = [c for c in marriage.Children if gen.get(c.GetId()) == gg]
        if len(children_in_gen) <= 1:
            continue
        gids = [c.GetId() for c in children_in_gen]
        for cid in gids:
            sibling_groups[cid] = gids

    def _order_children_by_parent_barycenter(gg, idx_prev):
        lst = order.get(gg, [])
        if not lst:
            return
        cur_idx = {p.GetId(): i for i, p in enumerate(lst)}
        used = set()
        blocks = []

        # Sibling blocks first: keep siblings together.
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

        # Remaining singles.
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

        # Couples with children: order by children barycenter; keep spouses together.
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

        # Remaining singles (including people with multiple spouses in same gen).
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

    # Build sibling-group map for adjacency enforcement: child -> list of siblings (including self) in same generation.
    sibling_groups = {}
    for marriage in local_marriages:
        children_in_gen = [c for c in marriage.Children if gen.get(c.GetId()) == gg]
        if len(children_in_gen) <= 1:
            continue
        gids = [c.GetId() for c in children_in_gen]
        for cid in gids:
            sibling_groups[cid] = gids

    for _ in range(sweeps):
        idx = _index_maps()
        for gg in range(min_g + 1, max_g + 1):
            _order_children_by_parent_barycenter(gg, idx.get(gg - 1, {}))
        _enforce_spouse_adjacency()
        idx = _index_maps()
        for gg in range(max_g - 1, min_g - 1, -1):
            _order_couples_by_children_barycenter(gg, idx.get(gg + 1, {}))
        _enforce_spouse_adjacency()

    # Refine X positions using implicit pseudo-nodes:
    # - marriage node: fixed spouse spacing, marriage midpoint is the block center
    # - sibling node: midpoint of the sibling bus (leftmost/rightmost child)
    # We shift couple blocks so their marriage midpoint aligns with the sibling-bus midpoint.
    spouse_dx = float(x_spacing)
    min_gap = float(x_spacing)

    # Initial x by current ordering.
    x_by_id = {}
    for gg in range(min_g, max_g + 1):
        lst = order.get(gg, [])
        for i, p in enumerate(lst):
            x_by_id[p.GetId()] = float(i) * float(x_spacing)

    # Build quick lookup: marriages whose spouses are in same generation.
    marriages_by_gen = {}
    deg_in_gen = {}
    for m in local_marriages:
        p1 = m.Person1
        p2 = m.Person2
        if p1.GetId() not in gen or p2.GetId() not in gen:
            continue
        gg = gen[p1.GetId()]
        if gen[p2.GetId()] != gg:
            continue
        marriages_by_gen.setdefault(gg, []).append(m)
        deg_in_gen[(gg, p1.GetId())] = deg_in_gen.get((gg, p1.GetId()), 0) + 1
        deg_in_gen[(gg, p2.GetId())] = deg_in_gen.get((gg, p2.GetId()), 0) + 1

    def _atom_bounds(center_x, is_couple):
        if not is_couple:
            return (center_x, center_x)
        hw = spouse_dx / 2.0
        return (center_x - hw, center_x + hw)

    # Process from bottom upwards so parents can align to already-placed children.
    for gg in range(max_g - 1, min_g - 1, -1):
        lst = order.get(gg, [])
        if not lst:
            continue
        idx_g = {p.GetId(): i for i, p in enumerate(lst)}
        used = set()
        atoms = []  # list of dicts: {type, ids, desired, center}

        # Add couple atoms (skip people with multiple spouses in the same generation).
        for m in marriages_by_gen.get(gg, []):
            p1 = m.Person1.GetId()
            p2 = m.Person2.GetId()
            if p1 not in idx_g or p2 not in idx_g:
                continue
            if deg_in_gen.get((gg, p1), 0) > 1 or deg_in_gen.get((gg, p2), 0) > 1:
                continue
            if p1 in used or p2 in used:
                continue

            child_xs = []
            for ch in m.Children:
                cid = ch.GetId()
                if gen.get(cid) == gg + 1 and cid in x_by_id:
                    child_xs.append(x_by_id[cid])
            if child_xs:
                desired = (min(child_xs) + max(child_xs)) / 2.0
            else:
                desired = (x_by_id.get(p1, 0.0) + x_by_id.get(p2, 0.0)) / 2.0

            # Keep deterministic spouse ordering left-to-right.
            left_id, right_id = (p1, p2) if p1 < p2 else (p2, p1)
            atoms.append({
                "type": "couple",
                "ids": [left_id, right_id],
                "desired": desired,
                "order_key": min(idx_g[left_id], idx_g[right_id]),
            })
            used.add(p1)
            used.add(p2)

        # Add remaining singles.
        for p in lst:
            pid = p.GetId()
            if pid in used:
                continue
            child_xs = [x_by_id[c.GetId()] for c in p.Children if gen.get(c.GetId()) == gg + 1 and c.GetId() in x_by_id]
            desired = (sum(child_xs) / len(child_xs)) if child_xs else x_by_id.get(pid, 0.0)
            atoms.append({
                "type": "single",
                "ids": [pid],
                "desired": desired,
                "order_key": idx_g[pid],
            })
            used.add(pid)

        atoms.sort(key=lambda a: (a["order_key"], a["ids"][0]))

        # Start at desired centers.
        centers = [float(a["desired"]) for a in atoms]
        is_couple = [a["type"] == "couple" for a in atoms]

        # Constraint solve: enforce min gaps between atom extents.
        for _pass in range(3):
            # Left-to-right
            for i in range(1, len(atoms)):
                prev_l, prev_r = _atom_bounds(centers[i - 1], is_couple[i - 1])
                cur_l, cur_r = _atom_bounds(centers[i], is_couple[i])
                need = (prev_r + min_gap) - cur_l
                if need > 0:
                    centers[i] += need
            # Right-to-left
            for i in range(len(atoms) - 2, -1, -1):
                cur_l, cur_r = _atom_bounds(centers[i], is_couple[i])
                nxt_l, nxt_r = _atom_bounds(centers[i + 1], is_couple[i + 1])
                need = cur_r - (nxt_l - min_gap)
                if need > 0:
                    centers[i] -= need

        # Commit x positions back to people.
        for a, cx in zip(atoms, centers):
            if a["type"] == "single":
                x_by_id[a["ids"][0]] = cx
            else:
                left_id, right_id = a["ids"]
                x_by_id[left_id] = cx - (spouse_dx / 2.0)
                x_by_id[right_id] = cx + (spouse_dx / 2.0)

    positions = {}
    for gg in range(min_g, max_g + 1):
        lst = order.get(gg, [])
        for i, p in enumerate(lst):
            positions[p.GetId()] = (x_by_id.get(p.GetId(), float(i) * float(x_spacing)), gg * y_spacing)

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
