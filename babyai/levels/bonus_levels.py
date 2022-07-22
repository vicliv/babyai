import gym
import json
from gym_minigrid.envs import Key, Ball, Box, Door, IDX_TO_COLOR, IDX_TO_OBJECT
from .verifier import *
from .levelgen import *


class Level_GoToRedBlueBall(RoomGridLevel):
    """
    Go to the red ball or to the blue ball.
    There is exactly one red or blue ball, and some distractors.
    The distractors are guaranteed not to be red or blue balls.
    Language is not required to solve this level.
    """

    def __init__(self, room_size=8, num_dists=7, **kwargs):
        self.num_dists = num_dists
        super().__init__(
            num_rows=1,
            num_cols=1,
            room_size=room_size, 
            **kwargs
        )

    def gen_mission(self):
        self.place_agent()

        dists = self.add_distractors(num_distractors=self.num_dists, all_unique=False)

        # Ensure there is only one red or blue ball
        for dist in dists:
            if dist.type == 'ball' and (dist.color == 'blue' or dist.color == 'red'):
                raise RejectSampling('can only have one blue or red ball')

        color = self._rand_elem(['red', 'blue'])
        obj, _ = self.add_object(0, 0, 'ball', color)

        # Make sure no unblocking is required
        self.check_objs_reachable()

        self.instrs = GoToInstr(ObjDesc(obj.type, obj.color))


class Level_OpenRedDoor(RoomGridLevel):
    """
    Go to the red door
    (always unlocked, in the current room)
    Note: this level is intentionally meant for debugging and is
    intentionally kept very simple.
    """

    def __init__(self, **kwargs):
        super().__init__(
            num_rows=1,
            num_cols=2,
            room_size=5, 
            **kwargs
        )

    def gen_mission(self):
        obj, _ = self.add_door(0, 0, 0, 'red', locked=False)
        self.place_agent(0, 0)
        self.instrs = OpenInstr(ObjDesc('door', 'red'))


class Level_OpenDoor(RoomGridLevel):
    """
    Go to the door
    The door to open is given by its color or by its location.
    (always unlocked, in the current room)
    """

    def __init__(
        self,
        debug=False,
        select_by=None, 
        **kwargs
    ):
        self.select_by = select_by
        self.debug = debug
        super().__init__(**kwargs)

    def gen_mission(self):
        door_colors = self._rand_subset(COLOR_NAMES, 4)
        objs = []

        for i, color in enumerate(door_colors):
            obj, _ = self.add_door(1, 1, door_idx=i, color=color, locked=False)
            objs.append(obj)

        select_by = self.select_by
        if select_by is None:
            select_by = self._rand_elem(["color", "loc"])
        if select_by == "color":
            object = ObjDesc(objs[0].type, color=objs[0].color)
        elif select_by == "loc":
            object = ObjDesc(objs[0].type, loc=self._rand_elem(LOC_NAMES))

        self.place_agent(1, 1)
        self.instrs = OpenInstr(object, strict=self.debug)


class Level_OpenDoorDebug(Level_OpenDoor):
    """
    Same as OpenDoor but the level stops when any door is opened
    """

    def __init__(self, select_by=None, **kwargs):
        super().__init__(select_by=select_by, debug=True, **kwargs)


class Level_OpenDoorColor(Level_OpenDoor):
    """
    Go to the door
    The door is selected by color.
    (always unlocked, in the current room)
    """

    def __init__(self, **kwargs):
        super().__init__(select_by="color", **kwargs)


#class Level_OpenDoorColorDebug(Level_OpenDoorColor, Level_OpenDoorDebug):
    """
    Same as OpenDoorColor but the level stops when any door is opened
    """
#    pass


class Level_OpenDoorLoc(Level_OpenDoor):
    """
    Go to the door
    The door is selected by location.
    (always unlocked, in the current room)
    """

    def __init__(self, **kwargs):
        super().__init__(
            select_by="loc", **kwargs
        )


class Level_GoToDoor(RoomGridLevel):
    """
    Go to a door
    (of a given color, in the current room)
    No distractors, no language variation
    """

    def __init__(self, **kwargs):
        super().__init__(
            room_size=7, **kwargs
        )

    def gen_mission(self):
        objs = []
        for _ in range(4):
            door, _ = self.add_door(1, 1)
            objs.append(door)
        self.place_agent(1, 1)

        obj = self._rand_elem(objs)
        self.instrs = GoToInstr(ObjDesc('door', obj.color))


class Level_GoToObjDoor(RoomGridLevel):
    """
    Go to an object or door
    (of a given type and color, in the current room)
    """

    def __init__(self, **kwargs):
        super().__init__(
            room_size=8, **kwargs
        )

    def gen_mission(self):
        self.place_agent(1, 1)
        objs = self.add_distractors(1, 1, num_distractors=8, all_unique=False)

        for _ in range(4):
            door, _ = self.add_door(1, 1)
            objs.append(door)

        self.check_objs_reachable()

        obj = self._rand_elem(objs)
        self.instrs = GoToInstr(ObjDesc(obj.type, obj.color))


class Level_ActionObjDoor(RoomGridLevel):
    """
    [pick up an object] or
    [go to an object or door] or
    [open a door]
    (in the current room)
    """

    def __init__(self, **kwargs):
        super().__init__(
            room_size=7, **kwargs
        )

    def gen_mission(self):
        objs = self.add_distractors(1, 1, num_distractors=5)
        for _ in range(4):
            door, _ = self.add_door(1, 1, locked=False)
            objs.append(door)

        self.place_agent(1, 1)

        obj = self._rand_elem(objs)
        desc = ObjDesc(obj.type, obj.color)

        if obj.type == 'door':
            if self._rand_bool():
                self.instrs = GoToInstr(desc)
            else:
                self.instrs = OpenInstr(desc)
        else:
            if self._rand_bool():
                self.instrs = GoToInstr(desc)
            else:
                self.instrs = PickupInstr(desc)


class Level_UnlockLocal(RoomGridLevel):
    """
    Fetch a key and unlock a door
    (in the current room)
    """

    def __init__(self, distractors=False, **kwargs):
        self.distractors = distractors
        super().__init__(**kwargs)

    def gen_mission(self):
        door, _ = self.add_door(1, 1, locked=True)
        self.add_object(1, 1, 'key', door.color)
        if self.distractors:
            self.add_distractors(1, 1, num_distractors=3)
        self.place_agent(1, 1)

        self.instrs = OpenInstr(ObjDesc(door.type))


class Level_UnlockLocalDist(Level_UnlockLocal):
    """
    Fetch a key and unlock a door
    (in the current room, with distractors)
    """

    def __init__(self, **kwargs):
        super().__init__(distractors=True, **kwargs)


class Level_KeyInBox(RoomGridLevel):
    """
    Unlock a door. Key is in a box (in the current room).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def gen_mission(self):
        door, _ = self.add_door(1, 1, locked=True)

        # Put the key in the box, then place the box in the room
        key = Key(door.color)
        box = Box(self._rand_color(), key)
        self.place_in_room(1, 1, box)

        self.place_agent(1, 1)

        self.instrs = OpenInstr(ObjDesc(door.type))


class Level_UnlockPickup(RoomGridLevel):
    """
    Unlock a door, then pick up a box in another room
    """

    def __init__(self, distractors=False, **kwargs):
        self.distractors = distractors

        room_size = 6
        super().__init__(
            num_rows=1,
            num_cols=2,
            room_size=room_size,
            max_steps=8*room_size**2, 
            **kwargs
        )

    def gen_mission(self):
        # Add a random object to the room on the right
        obj, _ = self.add_object(1, 0, kind="box")
        # Make sure the two rooms are directly connected by a locked door
        door, _ = self.add_door(0, 0, 0, locked=True)
        # Add a key to unlock the door
        self.add_object(0, 0, 'key', door.color)
        if self.distractors:
            self.add_distractors(num_distractors=4)

        self.place_agent(0, 0)

        self.instrs = PickupInstr(ObjDesc(obj.type, obj.color))


class Level_UnlockPickupDist(Level_UnlockPickup):
    """
    Unlock a door, then pick up an object in another room
    (with distractors)
    """

    def __init__(self, **kwargs):
        super().__init__(distractors=True, **kwargs)


class Level_BlockedUnlockPickup(RoomGridLevel):
    """
    Unlock a door blocked by a ball, then pick up a box
    in another room
    """

    def __init__(self, **kwargs):
        room_size = 6
        super().__init__(
            num_rows=1,
            num_cols=2,
            room_size=room_size,
            max_steps=16*room_size**2,
            **kwargs
        )

    def gen_mission(self):
        # Add a box to the room on the right
        obj, _ = self.add_object(1, 0, kind="box")
        # Make sure the two rooms are directly connected by a locked door
        door, pos = self.add_door(0, 0, 0, locked=True)
        # Block the door with a ball
        color = self._rand_color()
        self.grid.set(pos[0]-1, pos[1], Ball(color))
        # Add a key to unlock the door
        self.add_object(0, 0, 'key', door.color)

        self.place_agent(0, 0)

        self.instrs = PickupInstr(ObjDesc(obj.type))


class Level_UnlockToUnlock(RoomGridLevel):
    """
    Unlock a door A that requires to unlock a door B before
    """

    def __init__(self, **kwargs):
        room_size = 6
        super().__init__(
            num_rows=1,
            num_cols=3,
            room_size=room_size,
            max_steps=30*room_size**2, 
            **kwargs
        )

    def gen_mission(self):
        colors = self._rand_subset(COLOR_NAMES, 2)

        # Add a door of color A connecting left and middle room
        self.add_door(0, 0, door_idx=0, color=colors[0], locked=True)

        # Add a key of color A in the room on the right
        self.add_object(2, 0, kind="key", color=colors[0])

        # Add a door of color B connecting middle and right room
        self.add_door(1, 0, door_idx=0, color=colors[1], locked=True)

        # Add a key of color B in the middle room
        self.add_object(1, 0, kind="key", color=colors[1])

        obj, _ = self.add_object(0, 0, kind="ball")

        self.place_agent(1, 0)

        self.instrs = PickupInstr(ObjDesc(obj.type))


class Level_PickupDist(RoomGridLevel):
    """
    Pick up an object
    The object to pick up is given by its type only, or
    by its color, or by its type and color.
    (in the current room, with distractors)
    """

    def __init__(self, debug=False, **kwargs):
        self.debug = debug
        super().__init__(
            num_rows = 1,
            num_cols = 1,
            room_size=7, 
            **kwargs
        )

    def gen_mission(self):
        # Add 5 random objects in the room
        objs = self.add_distractors(num_distractors=5)
        self.place_agent(0, 0)
        obj = self._rand_elem(objs)
        type = obj.type
        color = obj.color

        select_by = self._rand_elem(["type", "color", "both"])
        if select_by == "color":
            type = None
        elif select_by == "type":
            color = None

        self.instrs = PickupInstr(ObjDesc(type, color), strict=self.debug)


class Level_PickupDistDebug(Level_PickupDist):
    """
    Same as PickupDist but the level stops when any object is picked
    """

    def __init__(self, **kwargs):
        super().__init__(
            debug=True, **kwargs
        )


class Level_PickupAbove(RoomGridLevel):
    """
    Pick up an object (in the room above)
    This task requires to use the compass to be solved effectively.
    """

    def __init__(self, **kwargs):
        room_size = 6
        super().__init__(
            room_size=room_size,
            max_steps=8*room_size**2, 
            **kwargs
        )

    def gen_mission(self):
        # Add a random object to the top-middle room
        obj, pos = self.add_object(1, 0)
        # Make sure the two rooms are directly connected
        self.add_door(1, 1, 3, locked=False)
        self.place_agent(1, 1)
        self.connect_all()

        self.instrs = PickupInstr(ObjDesc(obj.type, obj.color))


class Level_OpenTwoDoors(RoomGridLevel):
    """
    Open door X, then open door Y
    The two doors are facing opposite directions, so that the agent
    Can't see whether the door behind him is open.
    This task requires memory (recurrent policy) to be solved effectively.
    """

    def __init__(self,
        first_color=None,
        second_color=None,
        strict=False, 
        **kwargs
    ):
        self.first_color = first_color
        self.second_color = second_color
        self.strict = strict

        room_size = 6
        super().__init__(
            room_size=room_size,
            max_steps=20*room_size**2, 
            **kwargs
        )

    def gen_mission(self):
        colors = self._rand_subset(COLOR_NAMES, 2)

        first_color = self.first_color
        if first_color is None:
            first_color = colors[0]
        second_color = self.second_color
        if second_color is None:
            second_color = colors[1]

        door1, _ = self.add_door(1, 1, 2, color=first_color, locked=False)
        door2, _ = self.add_door(1, 1, 0, color=second_color, locked=False)

        self.place_agent(1, 1)

        self.instrs = BeforeInstr(
            OpenInstr(ObjDesc(door1.type, door1.color), strict=self.strict),
            OpenInstr(ObjDesc(door2.type, door2.color))
        )


class Level_OpenTwoDoorsDebug(Level_OpenTwoDoors):
    """
    Same as OpenTwoDoors but the level stops when the second door is opened
    """

    def __init__(self,
        first_color=None,
        second_color=None, 
        **kwargs
    ):
        super().__init__(
            first_color,
            second_color,
            strict=True, 
            **kwargs
        )


class Level_OpenRedBlueDoors(Level_OpenTwoDoors):
    """
    Open red door, then open blue door
    The two doors are facing opposite directions, so that the agent
    Can't see whether the door behind him is open.
    This task requires memory (recurrent policy) to be solved effectively.
    """

    def __init__(self, **kwargs):
        super().__init__(
            first_color="red",
            second_color="blue", 
            **kwargs
        )


class Level_OpenRedBlueDoorsDebug(Level_OpenTwoDoorsDebug):
    """
    Same as OpenRedBlueDoors but the level stops when the blue door is opened
    """

    def __init__(self, **kwargs):
        super().__init__(
            first_color="red",
            second_color="blue", 
            **kwargs
        )


class Level_FindObjS5(RoomGridLevel):
    """
    Pick up an object (in a random room)
    Rooms have a size of 5
    This level requires potentially exhaustive exploration
    """

    def __init__(self, room_size=5, **kwargs):
        super().__init__(
            room_size=room_size,
            max_steps=20*room_size**2, 
            **kwargs
      )

    def gen_mission(self):
        # Add a random object to a random room
        i = self._rand_int(0, self.num_rows)
        j = self._rand_int(0, self.num_cols)
        obj, _ = self.add_object(i, j)
        self.place_agent(1, 1)
        self.connect_all()

        self.instrs = PickupInstr(ObjDesc(obj.type))


class Level_FindObjS6(Level_FindObjS5):
    """
    Same as the FindObjS5 level, but rooms have a size of 6
    """

    def __init__(self, **kwargs):
        super().__init__(
            room_size=6, **kwargs
        )


class Level_FindObjS7(Level_FindObjS5):
    """
    Same as the FindObjS5 level, but rooms have a size of 7
    """

    def __init__(self, **kwargs):
        super().__init__(
            room_size=7, **kwargs
        )


class KeyCorridor(RoomGridLevel):
    """
    A ball is behind a locked door, the key is placed in a
    random room.
    """

    def __init__(
        self,
        num_rows=3,
        obj_type="ball",
        room_size=6, 
        **kwargs
    ):
        self.obj_type = obj_type

        super().__init__(
            room_size=room_size,
            num_rows=num_rows,
            max_steps=30*room_size**2, **kwargs
        )

    def gen_mission(self):
        # Connect the middle column rooms into a hallway
        for j in range(1, self.num_rows):
            self.remove_wall(1, j, 3)

        # Add a locked door on the bottom right
        # Add an object behind the locked door
        room_idx = self._rand_int(0, self.num_rows)
        door, _ = self.add_door(2, room_idx, 2, locked=True)
        obj, _ = self.add_object(2, room_idx, kind=self.obj_type)

        # Add a key in a random room on the left side
        self.add_object(0, self._rand_int(0, self.num_rows), 'key', door.color)

        # Place the agent in the middle
        self.place_agent(1, self.num_rows // 2)

        # Make sure all rooms are accessible
        self.connect_all()

        self.instrs = PickupInstr(ObjDesc(obj.type))


class Level_KeyCorridorS3R1(KeyCorridor):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=3,
            num_rows=1, 
            **kwargs
        )

class Level_KeyCorridorS3R2(KeyCorridor):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=3,
            num_rows=2, 
            **kwargs
        )

class Level_KeyCorridorS3R3(KeyCorridor):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=3,
            num_rows=3, 
            **kwargs
        )

class Level_KeyCorridorS4R3(KeyCorridor):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=4,
            num_rows=3, 
            **kwargs
        )

class Level_KeyCorridorS5R3(KeyCorridor):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=5,
            num_rows=3, 
            **kwargs
        )

class Level_KeyCorridorS6R3(KeyCorridor):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=6,
            num_rows=3, 
            **kwargs
        )

class Level_1RoomS8(RoomGridLevel):
    """
    Pick up the ball
    Rooms have a size of 8
    """

    def __init__(self, room_size=8, **kwargs):
        super().__init__(
            room_size=room_size,
            num_rows=1,
            num_cols=1, 
            **kwargs
        )

    def gen_mission(self):
        obj, _ = self.add_object(0, 0, kind="ball")
        self.place_agent()
        self.instrs = PickupInstr(ObjDesc(obj.type))


class Level_1RoomS12(Level_1RoomS8):
    """
    Pick up the ball
    Rooms have a size of 12
    """

    def __init__(self, **kwargs):
        super().__init__(
            room_size=12, **kwargs
        )


class Level_1RoomS16(Level_1RoomS8):
    """
    Pick up the ball
    Rooms have a size of 16
    """

    def __init__(self, **kwargs):
        super().__init__(
            room_size=16, **kwargs
        )


class Level_1RoomS20(Level_1RoomS8):
    """
    Pick up the ball
    Rooms have a size of 20
    """

    def __init__(self, **kwargs):
        super().__init__(
            room_size=20, **kwargs
        )


class PutNext(RoomGridLevel):
    """
    Task of the form: move the A next to the B and the C next to the D.
    This task is structured to have a very large number of possible
    instructions.
    """

    def __init__(
        self,
        room_size,
        objs_per_room,
        start_carrying=False, 
        **kwargs
    ):
        assert room_size >= 4
        assert objs_per_room <= 9
        self.objs_per_room = objs_per_room
        self.start_carrying = start_carrying

        super().__init__(
            num_rows=1,
            num_cols=2,
            room_size=room_size,
            max_steps=8*room_size**2, 
            **kwargs
        )

    def gen_mission(self):
        self.place_agent(0, 0)

        # Add objects to both the left and right rooms
        # so that we know that we have two non-adjacent set of objects
        objs_l = self.add_distractors(0, 0, self.objs_per_room)
        objs_r = self.add_distractors(1, 0, self.objs_per_room)

        # Remove the wall between the two rooms
        self.remove_wall(0, 0, 0)

        # Select objects from both subsets
        a = self._rand_elem(objs_l)
        b = self._rand_elem(objs_r)

        # Randomly flip the object to be moved
        if self._rand_bool():
            t = a
            a = b
            b = t

        self.obj_a = a

        self.instrs = PutNextInstr(
            ObjDesc(a.type, a.color),
            ObjDesc(b.type, b.color)
        )

    def reset(self, **kwargs):
        obs = super().reset(**kwargs)

        # If the agent starts off carrying the object
        if self.start_carrying:
            self.grid.set(*self.obj_a.init_pos, None)
            self.carrying = self.obj_a

        return obs


class Level_PutNextS4N1(PutNext):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=4,
            objs_per_room=1, 
            **kwargs
        )


class Level_PutNextS5N1(PutNext):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=5,
            objs_per_room=1, 
            **kwargs
        )


class Level_PutNextS5N2(PutNext):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=5,
            objs_per_room=2, 
            **kwargs
        )


class Level_PutNextS6N3(PutNext):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=6,
            objs_per_room=3, 
            **kwargs
        )


class Level_PutNextS7N4(PutNext):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=7,
            objs_per_room=4, 
            **kwargs
        )


class Level_PutNextS5N2Carrying(PutNext):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=5,
            objs_per_room=2,
            start_carrying=True, 
            **kwargs
        )


class Level_PutNextS6N3Carrying(PutNext):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=6,
            objs_per_room=3,
            start_carrying=True, 
            **kwargs
        )


class Level_PutNextS7N4Carrying(PutNext):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=7,
            objs_per_room=4,
            start_carrying=True, 
            **kwargs
        )


class MoveTwoAcross(RoomGridLevel):
    """
    Task of the form: move the A next to the B and the C next to the D.
    This task is structured to have a very large number of possible
    instructions.
    """

    def __init__(
        self,
        room_size,
        objs_per_room, 
        **kwargs
    ):
        assert objs_per_room <= 9
        self.objs_per_room = objs_per_room

        super().__init__(
            num_rows=1,
            num_cols=2,
            room_size=room_size,
            max_steps=16*room_size**2, 
            **kwargs
        )

    def gen_mission(self):
        self.place_agent(0, 0)

        # Add objects to both the left and right rooms
        # so that we know that we have two non-adjacent set of objects
        objs_l = self.add_distractors(0, 0, self.objs_per_room)
        objs_r = self.add_distractors(1, 0, self.objs_per_room)

        # Remove the wall between the two rooms
        self.remove_wall(0, 0, 0)

        # Select objects from both subsets
        objs_l = self._rand_subset(objs_l, 2)
        objs_r = self._rand_subset(objs_r, 2)
        a = objs_l[0]
        b = objs_r[0]
        c = objs_r[1]
        d = objs_l[1]

        self.instrs = BeforeInstr(
            PutNextInstr(ObjDesc(a.type, a.color), ObjDesc(b.type, b.color)),
            PutNextInstr(ObjDesc(c.type, c.color), ObjDesc(d.type, d.color))
        )


class Level_MoveTwoAcrossS5N2(MoveTwoAcross):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=5,
            objs_per_room=2, 
            **kwargs
        )


class Level_MoveTwoAcrossS8N9(MoveTwoAcross):
    def __init__(self, **kwargs):
        super().__init__(
            room_size=8,
            objs_per_room=9, 
            **kwargs
        )


class OpenDoorsOrder(RoomGridLevel):
    """
    Open one or two doors in the order specified.
    """

    def __init__(
        self,
        num_doors,
        debug=False, 
        **kwargs
    ):
        assert num_doors >= 2
        self.num_doors = num_doors
        self.debug = debug

        room_size = 6
        super().__init__(
            room_size=room_size,
            max_steps=20*room_size**2, 
            **kwargs
        )

    def gen_mission(self):
        colors = self._rand_subset(COLOR_NAMES, self.num_doors)
        doors = []
        for i in range(self.num_doors):
            door, _ = self.add_door(1, 1, color=colors[i], locked=False)
            doors.append(door)
        self.place_agent(1, 1)

        door1, door2 = self._rand_subset(doors, 2)
        desc1 = ObjDesc(door1.type, door1.color)
        desc2 = ObjDesc(door2.type, door2.color)

        mode = self._rand_int(0, 3)
        if mode == 0:
            self.instrs = OpenInstr(desc1, strict=self.debug)
        elif mode == 1:
            self.instrs = BeforeInstr(OpenInstr(desc1, strict=self.debug), OpenInstr(desc2, strict=self.debug))
        elif mode == 2:
            self.instrs = AfterInstr(OpenInstr(desc1, strict=self.debug), OpenInstr(desc2, strict=self.debug))
        else:
            assert False

class Level_OpenDoorsOrderN2(OpenDoorsOrder):
    def __init__(self, **kwargs):
        super().__init__(
            num_doors=2, **kwargs
        )


class Level_OpenDoorsOrderN4(OpenDoorsOrder):
    def __init__(self, **kwargs):
        super().__init__(
            num_doors=4, **kwargs
        )


class Level_OpenDoorsOrderN2Debug(OpenDoorsOrder):
    def __init__(self, **kwargs):
        super().__init__(
            num_doors=2,
            debug=True, 
            **kwargs
        )


class Level_OpenDoorsOrderN4Debug(OpenDoorsOrder):
    def __init__(self, **kwargs):
        super().__init__(
            num_doors=4,
            debug=True, 
            **kwargs
        )

class Level_JSON(RoomGridLevel):
    """
    Generate a level from the level_config.json file
    """

    def __init__(self, **kwargs):

        with open('level_config.json') as json_file:
            self.data = json.load(json_file)
        super().__init__( 
            num_rows=self.data['num_rows'],
            num_cols=self.data['num_columns'],
            room_size=self.data['room_size'], 
            **kwargs
        )

    def gen_mission(self):
        i = self.data['agent']['room'][0]
        j = self.data['agent']['room'][1]
        pos = np.array(self.data['agent']['pos'])
        dir = self.data['agent']['dir']

        room = self.get_room(i, j)
        
        self.agent_pos = room.top + pos

        self.agent_dir = dir
        
        for object in self.data['objects']:
            i = object['i']
            j = object['j']
            kind=object['type']
            color=object['color']
            pos=np.array(object['pos'])

            assert kind in ['key', 'ball', 'box']
            if kind == 'key':
                obj = Key(color)
            elif kind == 'ball':
                obj = Ball(color)
            elif kind == 'box':
                obj = Box(color)
            
            room = self.get_room(i, j)
            top = room.top

            pos = pos + top
            self.put_obj(obj, pos[0], pos[1])
            
            room.objs.append(obj)
            

        for door in self.data['doors']:
            i = door['i']
            j = door['j']
            door_idx = door['idx']
            color = door['color']
            locked = door['locked']
            pos= door['pos']

            room = self.get_room(i, j)
            
            assert room.doors[door_idx] is None, "door already exists"

            room.locked = locked
            door = Door(color, is_locked=locked)

            x_l, y_l = (room.top[0] + 1, room.top[1] + 1)
            x_m, y_m = (room.top[0] + room.size[0] - 1, room.top[1] + room.size[1] - 1)
            
            if door_idx == 0:
                pos = (x_m, room.top[1] + pos)
            if door_idx == 1:
                pos = (room.top[0] + pos, y_m)
            if door_idx == 2:
                pos = (x_l, room.top[1] + pos)
            if door_idx == 3:
                pos = (room.top[0] + pos, y_l)
            
            room.door_pos[door_idx] = pos

            self.grid.set(*pos, door)
            door.cur_pos = pos

            neighbor = room.neighbors[door_idx]
            room.doors[door_idx] = door
            neighbor.doors[(door_idx+2) % 4] = door

        self.instrs = self.parse_instr(self.data['instr'].split())
    
    def get_object(self, instr):
        """
        Find an object based on the parsed string given in the JSON file
        """
        type = None
        color = None
        loc = None

        for s in instr:
            if s in COLOR_NAMES:
                color = s
            elif s in OBJ_TYPES:
                type = s
            elif s in LOC_NAMES:
                loc = s

        return ObjDesc(type, color, loc)


    def parse_instr(self, instr):
        """
        Create the instruction based on the string given in the JSON file
        """
        for i, s in enumerate(instr):
            if 'then' == s:
                return BeforeInstr(self.parse_instr(instr[0:i]), self.parse_instr(instr[i+1:]))
            elif 'after' == s:
                return AfterInstr(self.parse_instr(instr[0:i]), self.parse_instr(instr[i+2:]))
        
        for i, s in enumerate(instr):
            if 'and' == s:
                return AndInstr(self.parse_instr(instr[0:i]), self.parse_instr(instr[i+1:]))
        
        for i, s in enumerate(instr):
            if 'go' == s:
                return GoToInstr(self.get_object(instr[i+2:]))
            elif 'pick' == s:
                return PickupInstr(self.get_object(instr[i+2:]))
            elif 'open' == s:
                return OpenInstr(self.get_object(instr[i+1:]))
            elif 'put' == s:
                for j, st in enumerate(instr[i+1:]):
                    if st == 'next':
                        return PutNextInstr(self.get_object(instr[i+1:i+1+j]), self.get_object(instr[j+2:]))
                
class Level_parametrized(LevelGen):
    """
    Create a level based on a vector of dimension 189
    """
    def __init__(self, **kwargs):
        print(kwargs)
        if ('vector' not in kwargs.keys()):
            with open('vector_config.json') as json_file:
                self.data = np.array(json.load(json_file))
        else:
            self.data = kwargs['vector']

        super().__init__( 
            num_rows = self.data[0] if self.data[0] <= 3 else 3,
            num_cols = self.data[1] if self.data[1] <= 3 else 3,
            room_size = self.data[2] if self.data[2] <= 8 else 8, 
            **kwargs
        )
    
    def gen_mission(self):
        room = self.get_room(self.data[3],self.data[4])
        
        self.agent_pos = room.top + np.array([self.data[5], self.data[6]])
        self.agent_dir = self.data[7]
        
        objs = []
        for i in range(8, 116, 6):
            if self.data[i] == -1:
                continue

            kind = IDX_TO_OBJECT[self.data[i+2]]
            color=IDX_TO_COLOR[self.data[i+3]]
            pos=np.array([self.data[i+4], self.data[i+5]])
            
            assert kind in ['key', 'ball', 'box']
            if kind == 'key':
                obj = Key(color)
            elif kind == 'ball':
                obj = Ball(color)
            elif kind == 'box':
                obj = Box(color)
            
            assert kind in ['key', 'ball', 'box']
            if kind == 'key':
                obj = Key(color)
            elif kind == 'ball':
                obj = Ball(color)
            elif kind == 'box':
                obj = Box(color)
            
            room = self.get_room(self.data[i], self.data[i+1])
            top = room.top

            pos = pos + top
            self.put_obj(obj, pos[0], pos[1])
            
            room.objs.append(obj)
            
            objs.append([IDX_TO_OBJECT[self.data[i+2]], IDX_TO_COLOR[self.data[i+3]]])

        doors = []
        for i in range(116, 188, 6):
            if self.data[i] == -1:
                continue
            
            room = self.get_room(self.data[i], self.data[i+1])

            color = IDX_TO_COLOR[self.data[i+3]]
            locked = self.data[i+4]
            pos = self.data[i+5]
            door_idx = self.data[i+2]
            
            assert room.doors[door_idx] is None, "door already exists"

            room.locked = locked
            door = Door(color, is_locked=locked)

            x_l, y_l = (room.top[0] + 1, room.top[1] + 1)
            x_m, y_m = (room.top[0] + room.size[0] - 1, room.top[1] + room.size[1] - 1)
            
            if door_idx == 0:
                pos = (x_m, room.top[1] + pos)
            if door_idx == 1:
                pos = (room.top[0] + pos, y_m)
            if door_idx == 2:
                pos = (x_l, room.top[1] + pos)
            if door_idx == 3:
                pos = (room.top[0] + pos, y_l)
            
            room.door_pos[door_idx] = pos

            self.grid.set(*pos, door)
            door.cur_pos = pos

            neighbor = room.neighbors[door_idx]
            room.doors[door_idx] = door
            neighbor.doors[(door_idx+2) % 4] = door

            doors.append(IDX_TO_COLOR[self.data[i+3]])
        
        if self.data[188] == 0:
            obj = self._rand_elem(objs)
            self.instrs = GoToInstr(ObjDesc(obj[0], obj[1]))
        elif self.data[188] == 1:
            obj = self._rand_elem(objs)
            self.instrs =  PickupInstr(ObjDesc(obj[0], obj[1]))
        elif self.data[188] == 2:
            color = self._rand_elem(doors)
            self.instrs = OpenInstr(ObjDesc("door", color))
        elif self.data[188] == 3:
            o1, o2 = self._rand_subset(objs, 2)
            self.instrs = PutNextInstr(
            ObjDesc(o1[0], o1[1]),
            ObjDesc(o2[0], o2[1])
            )
        elif self.data[188] == 4:
            self.instrs = self.rand_instr(
            action_kinds= ['goto'],
            instr_kinds=self.instr_kinds
            )
        else:
            self.instrs = self.rand_instr(
            action_kinds= self.action_kinds,
            instr_kinds=self.instr_kinds
            )

for name, level in list(globals().items()):
    if name.startswith('Level_'):
        level.is_bonus = True

# Register the levels in this file
register_levels(__name__, globals())
