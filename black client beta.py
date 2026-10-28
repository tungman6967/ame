import math
import json
import os
import random
import sys
import tempfile
import time
from functools import lru_cache
from pathlib import Path

import pygame


WINDOWED_WIDTH = 960
WINDOWED_HEIGHT = 600
SCREEN_WIDTH = WINDOWED_WIDTH
SCREEN_HEIGHT = WINDOWED_HEIGHT
WORLD_SIZE = 512
WORLD_HEIGHT = 18
CHUNK_SIZE = 16
FIELD_OF_VIEW = math.radians(90)
PLAYER_HEIGHT = 1.62
PLAYER_RADIUS = 0.22
MOVE_SPEED = 5.0
GRAVITY = 20.0
JUMP_SPEED = 7.2
MAX_REACH = 7.0
CONTAINER_SLOT_COUNT = 9
MOD_MENU_OPTIONS = (
    ("chest_esp", "Chest ESP"),
    ("esp", "Block ESP"),
    ("aimbot", "Block Aim Assist"),
    ("god_mode", "God Mode"),
    ("fly", "Fly"),
    ("speed_boost", "Speed Boost"),
    ("auto_mine", "Auto Mine"),
    ("sus_chunk_finder", "Sus Chunk Finder"),
    ("world_color", "World Color"),
)
WORLD_COLORS = (
    ("Natural", (92, 110, 72)),
    ("Purple", (89, 62, 112)),
    ("Desert", (166, 132, 84)),
    ("Ice", (105, 150, 172)),
    ("Neon Asphalt", (19, 15, 38)),
)
SKYBOXES = (
    ("Blue", (86, 155, 221)),
    ("Sunset", (224, 116, 91)),
    ("Purple", (133, 105, 194)),
    ("Night", (25, 34, 68)),
    ("Mint", (76, 176, 161)),
    ("Neon Night", (18, 10, 34)),
)
BUTTON_THEMES = (
    ("Charcoal", (36, 36, 40), (56, 56, 62), (112, 112, 120)),
    ("Blue", (34, 58, 82), (50, 88, 122), (104, 151, 190)),
    ("Purple", (58, 42, 72), (88, 61, 108), (151, 115, 174)),
    ("Green", (36, 62, 48), (54, 91, 66), (111, 160, 121)),
    ("Red", (72, 39, 42), (105, 55, 60), (174, 113, 116)),
)
SPECIAL_BLOCKS = ("chest", "ender_chest", "shulker", "spawner")
CONTAINER_BLOCKS = ("chest", "ender_chest", "shulker")
SPECIAL_BLOCK_LABELS = {
    "chest": "Chest",
    "ender_chest": "Ender Chest",
    "shulker": "Shulker",
    "spawner": "Spawner",
}
ESP_BLOCK_COLORS = {
    "chest": (255, 70, 190),
    "ender_chest": (60, 255, 240),
    "shulker": (220, 80, 255),
    "spawner": (255, 110, 45),
}
QUALITY_LEVELS = {
    "Poop": 0.08,
    "Low": 0.13,
    "Medium": 0.20,
    "High": 0.30,
    "Very High": 0.40,
    "Ultra": 0.50,
}
DISPLAY_RESOLUTIONS = {
    "960x600": (960, 600),
    "1280x720": (1280, 720),
    "1600x900": (1600, 900),
    "1920x1080": (1920, 1080),
}
WORLD_PRESETS = {
    "Test": {"seed": 8, "roughness": 0.22, "max_height": 7, "tree_chance": 0.025},
    "Forest": {"seed": 24, "roughness": 0.20, "max_height": 8, "tree_chance": 0.075},
    "Highlands": {"seed": 51, "roughness": 0.38, "max_height": 13, "tree_chance": 0.015},
    "Flatlands": {"seed": 93, "roughness": 0.08, "max_height": 5, "tree_chance": 0.01},
}
SAVE_DIRECTORY = Path(__file__).resolve().parent / "saves"

BLOCK_COLORS = {
    "grass": (92, 174, 62),
    "dirt": (139, 90, 43),
    "stone": (132, 135, 139),
    "wood": (134, 88, 49),
    "leaves": (49, 139, 62),
    "planks": (174, 127, 78),
    "crafting_table": (139, 94, 56),
    "chest": (177, 115, 43),
    "ender_chest": (22, 38, 48),
    "shulker": (151, 75, 178),
    "spawner": (61, 66, 72),
    "water": (40, 112, 205),
}
RENDER_BLOCK_TYPES = ("", *BLOCK_COLORS)
RENDER_BLOCK_IDS = {
    block: block_id for block_id, block in enumerate(RENDER_BLOCK_TYPES) if block
}
RENDER_GRID_STRIDE = WORLD_SIZE + 2
RENDER_GRID_Y_STRIDE = RENDER_GRID_STRIDE
RENDER_GRID_X_STRIDE = WORLD_HEIGHT * RENDER_GRID_STRIDE
ITEM_COLORS = {
    "sword": (215, 220, 230),
    "wood_sword": (174, 127, 78),
    "stone_sword": (150, 154, 162),
    "apple": (220, 55, 55),
    "steak": (155, 76, 48),
    "pickaxe": (190, 195, 205),
    "axe": (190, 195, 205),
    "wood_pickaxe": (174, 127, 78),
    "stone_pickaxe": (150, 154, 162),
    "wood_axe": (174, 127, 78),
    "stone_axe": (150, 154, 162),
    "stick": (157, 105, 61),
}
FOOD_ITEMS = {"apple": 6, "steak": 9}
FOOD_HEAL = {"apple": 3, "steak": 6}
HOTBAR = [
    "sword", "pickaxe", "axe", "dirt", "stone", "wood", "leaves", "planks",
    "crafting_table", "water", "apple", "steak", "stick", *SPECIAL_BLOCKS,
]
SEA_LEVEL = 4
MOB_SPAWN_COUNT = 18
BLOCK_BREAK_SECONDS = {
    "default": 0.32,
    "wood_hand": 1.1,
    "wood_axe": 0.32,
    "stone_pickaxe": 0.48,
}


@lru_cache(maxsize=512)
def render_text(font, text, color):
    return font.render(text, True, color)


HUD_PANEL = None


def make_world(seed=8, roughness=0.22, max_height=7, tree_chance=0.025):
    rng = random.Random(seed)
    blocks = {}
    heights = {}
    height = 4

    def ocean_noise(grid_x, grid_z):
        value = (
            grid_x * 374761393 + grid_z * 668265263 + seed * 69069
        ) & 0xFFFFFFFF
        value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
        return value / 0xFFFFFFFF

    def is_ocean(x, z):
        if (x - WORLD_SIZE // 2) ** 2 + (z - WORLD_SIZE // 2) ** 2 < 28 ** 2:
            return False
        grid_x, grid_z = x // 48, z // 48
        blend_x, blend_z = (x % 48) / 48, (z % 48) / 48
        blend_x = blend_x * blend_x * (3 - 2 * blend_x)
        blend_z = blend_z * blend_z * (3 - 2 * blend_z)
        near = ocean_noise(grid_x, grid_z)
        east = ocean_noise(grid_x + 1, grid_z)
        south = ocean_noise(grid_x, grid_z + 1)
        southeast = ocean_noise(grid_x + 1, grid_z + 1)
        top = near + (east - near) * blend_x
        bottom = south + (southeast - south) * blend_x
        return top + (bottom - top) * blend_z > 0.54

    for x in range(WORLD_SIZE):
        for z in range(WORLD_SIZE):
            if rng.random() < roughness:
                height += rng.choice((-1, 0, 1))
            height = max(2, min(max_height, height))
            ocean = is_ocean(x, z)
            ground_height = 2 if ocean else height
            heights[(x, z)] = ground_height
            for y in range(ground_height + 1):
                if y == ground_height:
                    block = "grass"
                elif y >= ground_height - 2:
                    block = "dirt"
                else:
                    block = "stone"
                blocks[(x, y, z)] = block
            if ocean:
                for y in range(ground_height + 1, min(SEA_LEVEL, WORLD_HEIGHT - 1) + 1):
                    blocks[(x, y, z)] = "water"

    for x in range(3, WORLD_SIZE - 3):
        for z in range(3, WORLD_SIZE - 3):
            ground = heights[(x, z)]
            if blocks.get((x, ground + 1, z)) == "water":
                continue
            if rng.random() < 0.0015:
                blocks[(x, ground + 1, z)] = "chest"
            special_block = None
            if rng.random() < 0.001:
                special_block = rng.choice(("ender_chest", "shulker", "spawner"))
            if rng.random() < tree_chance:
                for y in range(ground + 1, ground + 4):
                    blocks[(x, y, z)] = "wood"
                for dx in range(-2, 3):
                    for dz in range(-2, 3):
                        for dy in range(2, 5):
                            if abs(dx) + abs(dz) + abs(dy - 3) < 5:
                                position = (x + dx, ground + dy, z + dz)
                                blocks.setdefault(position, "leaves")
            if special_block == "ender_chest":
                blocks[(x, ground + 1, z)] = special_block
            elif special_block is not None:
                blocks[(x, max(0, ground - rng.randint(1, 3)), z)] = special_block
    return blocks, heights


def world_spawn(heights):
    spawn_x = WORLD_SIZE // 2
    spawn_z = WORLD_SIZE // 2
    return spawn_x + 0.5, spawn_z + 0.5, heights[(spawn_x, spawn_z)] + 1.0


def spawn_mobs(heights, blocks, seed, count=MOB_SPAWN_COUNT):
    rng = random.Random(seed + 1701)
    center_x = WORLD_SIZE // 2
    center_z = WORLD_SIZE // 2
    mobs = []
    attempts = 0
    while len(mobs) < count and attempts < count * 20:
        attempts += 1
        x = center_x + rng.randint(-48, 48)
        z = center_z + rng.randint(-48, 48)
        if not 1 <= x < WORLD_SIZE - 1 or not 1 <= z < WORLD_SIZE - 1:
            continue
        ground_y = heights[(x, z)]
        if blocks.get((x, ground_y + 1, z)) == "water":
            continue
        if blocks.get((x, ground_y + 2, z)) is not None:
            continue
        mobs.append(
            {
                "kind": rng.choices(
                    ("zombie", "skeleton", "slime"), weights=(4, 4, 2), k=1
                )[0],
                "x": x + 0.5,
                "y": ground_y + 1.0,
                "z": z + 0.5,
                "health": 12,
                "cooldown": 0.0,
                "shoot_cooldown": rng.uniform(0.2, 1.5),
                "wander": rng.random() * math.tau,
                "wander_time": rng.uniform(0.5, 3.0),
            }
        )
    return mobs


def find_target_mob(mobs, origin, yaw, pitch, max_distance=4.5):
    direction = (
        math.cos(yaw) * math.cos(pitch),
        math.sin(pitch),
        math.sin(yaw) * math.cos(pitch),
    )
    closest = None
    closest_depth = max_distance
    for mob in mobs:
        center = (mob["x"], mob["y"] + 0.7, mob["z"])
        offset = tuple(center[index] - origin[index] for index in range(3))
        depth = sum(offset[index] * direction[index] for index in range(3))
        if not 0 < depth < closest_depth:
            continue
        miss = math.sqrt(
            sum(
                (offset[index] - direction[index] * depth) ** 2
                for index in range(3)
            )
        )
        if miss <= 0.65:
            closest = mob
            closest_depth = depth
    return closest


def update_mobs(mobs, arrows, blocks, heights, player_x, player_y, player_z, delta_time):
    damage = 0
    for mob in mobs:
        mob["cooldown"] = max(0.0, mob["cooldown"] - delta_time)
        mob["shoot_cooldown"] = max(
            0.0, mob["shoot_cooldown"] - delta_time
        )
        dx = player_x - mob["x"]
        dz = player_z - mob["z"]
        distance = math.hypot(dx, dz)
        if (
            mob["kind"] == "skeleton"
            and 3.0 <= distance < 12.0
            and mob["shoot_cooldown"] == 0
        ):
            start = (mob["x"], mob["y"] + 0.85, mob["z"])
            target = (player_x, player_y + 0.9, player_z)
            direction = tuple(target[i] - start[i] for i in range(3))
            direction_length = math.sqrt(sum(value * value for value in direction))
            direction = tuple(value / direction_length for value in direction)
            if raycast(blocks, start, direction, direction_length) is None:
                arrows.append(
                    {
                        "x": start[0],
                        "y": start[1],
                        "z": start[2],
                        "vx": direction[0] * 9.0,
                        "vy": direction[1] * 9.0,
                        "vz": direction[2] * 9.0,
                        "life": 2.0,
                    }
                )
                mob["shoot_cooldown"] = 1.8
        if distance < 1.35:
            if mob["cooldown"] == 0:
                damage += 2
                mob["cooldown"] = 1.1
            continue
        mob["wander_time"] -= delta_time
        if distance < 12:
            direction = math.atan2(dz, dx)
            if mob["kind"] == "skeleton":
                speed = 0.55
            else:
                speed = 1.0 if mob["kind"] == "zombie" else 1.35
        else:
            if mob["wander_time"] <= 0:
                mob["wander"] += random.uniform(-1.5, 1.5)
                mob["wander_time"] = random.uniform(1.0, 3.0)
            direction = mob["wander"]
            speed = 0.45
        next_x = mob["x"] + math.cos(direction) * speed * delta_time
        next_z = mob["z"] + math.sin(direction) * speed * delta_time
        cell_x, cell_z = math.floor(next_x), math.floor(next_z)
        if not 0 <= cell_x < WORLD_SIZE or not 0 <= cell_z < WORLD_SIZE:
            continue
        ground_y = heights[(cell_x, cell_z)]
        if (
            blocks.get((cell_x, ground_y + 1, cell_z)) == "water"
            or blocks.get((cell_x, ground_y + 2, cell_z)) is not None
            or abs(ground_y - math.floor(mob["y"] - 1)) > 1
        ):
            continue
        mob["x"] = next_x
        mob["z"] = next_z
        mob["y"] = ground_y + 1.0

    player_target = (player_x, player_y + 0.9, player_z)
    for arrow in arrows[:]:
        arrow["life"] -= delta_time
        next_position = (
            arrow["x"] + arrow["vx"] * delta_time,
            arrow["y"] + arrow["vy"] * delta_time,
            arrow["z"] + arrow["vz"] * delta_time,
        )
        velocity = (arrow["vx"], arrow["vy"], arrow["vz"])
        speed = math.sqrt(sum(value * value for value in velocity))
        if raycast(blocks, (arrow["x"], arrow["y"], arrow["z"]), velocity, speed * delta_time):
            arrows.remove(arrow)
            continue
        arrow["x"], arrow["y"], arrow["z"] = next_position
        if math.dist(next_position, player_target) < 0.55:
            damage += 3
            arrows.remove(arrow)
        elif arrow["life"] <= 0:
            arrows.remove(arrow)
    return damage


def project_camera_point(dx, dy, dz, yaw, pitch, focal_length):
    forward_x, forward_z = math.cos(yaw), math.sin(yaw)
    right_x, right_z = -forward_z, forward_x
    horizontal_depth = dx * forward_x + dz * forward_z
    side = dx * right_x + dz * right_z
    sin_pitch = math.sin(pitch)
    cos_pitch = math.cos(pitch)
    depth = horizontal_depth * cos_pitch + dy * sin_pitch
    vertical = dy * cos_pitch - horizontal_depth * sin_pitch
    if depth <= 0.1:
        return None
    return (
        round(SCREEN_WIDTH / 2 + side * focal_length / depth),
        round(SCREEN_HEIGHT / 2 - vertical * focal_length / depth),
        depth,
    )


def draw_mob_cuboid(screen, mob, origin, facing, part, focal_length, yaw, pitch):
    local_x, bottom, local_z, width, height, depth_size, color = part
    right_x, right_z = -facing[1], facing[0]

    def project(x, y, z):
        world_x = mob["x"] + x * right_x + z * facing[0]
        world_z = mob["z"] + x * right_z + z * facing[1]
        return project_camera_point(
            world_x - origin[0],
            mob["y"] + y - origin[1],
            world_z - origin[2],
            yaw,
            pitch,
            focal_length,
        )

    half_width = width / 2
    half_depth = depth_size / 2
    corners = (
        (-half_width, bottom, -half_depth),
        (half_width, bottom, -half_depth),
        (half_width, bottom + height, -half_depth),
        (-half_width, bottom + height, -half_depth),
        (-half_width, bottom, half_depth),
        (half_width, bottom, half_depth),
        (half_width, bottom + height, half_depth),
        (-half_width, bottom + height, half_depth),
    )
    projected_corners = [
        project(local_x + x, y, local_z + z) for x, y, z in corners
    ]
    point_0, point_1, point_2, point_3, point_4, point_5, point_6, point_7 = (
        projected_corners
    )
    if (
        point_0 is None
        or point_1 is None
        or point_2 is None
        or point_3 is None
        or point_4 is None
        or point_5 is None
        or point_6 is None
        or point_7 is None
    ):
        return
    projected = (
        point_0, point_1, point_2, point_3,
        point_4, point_5, point_6, point_7,
    )

    faces = (
        ((4, 5, 6, 7), 1.0),
        ((0, 3, 2, 1), 0.54),
        ((0, 4, 7, 3), 0.72),
        ((1, 2, 6, 5), 0.82),
        ((3, 7, 6, 2), 1.14),
        ((0, 1, 5, 4), 0.48),
    )
    for indices, shade in sorted(
        faces,
        key=lambda face: sum(projected[index][2] for index in face[0]) / 4,
        reverse=True,
    ):
        points = [projected[index] for index in indices]
        face_color = tuple(min(255, round(channel * shade)) for channel in color)
        pygame.draw.polygon(screen, face_color, [(x, y) for x, y, _ in points])
        pygame.draw.polygon(
            screen,
            tuple(max(0, channel - 18) for channel in face_color),
            [(x, y) for x, y, _ in points],
            1,
        )


def draw_mobs(screen, mobs, origin, yaw, pitch, render_distance):
    focal_length = SCREEN_WIDTH / (2 * math.tan(FIELD_OF_VIEW / 2))
    for mob in mobs:
        dx, dz = mob["x"] - origin[0], mob["z"] - origin[2]
        center_projection = project_camera_point(
            dx, mob["y"] + 0.8 - origin[1], dz, yaw, pitch, focal_length
        )
        if center_projection is None:
            continue
        center_x, center_y, depth = center_projection
        if depth <= 0.3 or depth > render_distance:
            continue
        mob_height = max(5, min(90, round(focal_length * 1.4 / depth)))
        mob_width = max(4, mob_height // 2)
        body = pygame.Rect(
            center_x - mob_width // 2,
            center_y - mob_height // 2,
            mob_width,
            mob_height,
        )
        if not screen.get_rect().colliderect(body):
            continue
        if mob["kind"] == "slime":
            color = (73, 220, 125)
            pygame.draw.rect(screen, color, body, border_radius=max(2, mob_width // 5))
            eye_y = body.y + body.height // 3
            pygame.draw.rect(screen, (22, 45, 36), (body.x + 2, eye_y, 2, 2))
            pygame.draw.rect(screen, (22, 45, 36), (body.right - 4, eye_y, 2, 2))
        else:
            to_player = (origin[0] - mob["x"], origin[2] - mob["z"])
            facing_length = math.hypot(*to_player)
            facing = (
                (to_player[0] / facing_length, to_player[1] / facing_length)
                if facing_length
                else (1.0, 0.0)
            )
            if mob["kind"] == "skeleton":
                bone = (218, 215, 194)
                parts = [
                    (0, 1.48, 0, 0.42, 0.42, 0.42, bone),
                    (0, 0.72, 0, 0.11, 0.68, 0.12, bone),
                    (0, 1.12, 0, 0.42, 0.09, 0.18, bone),
                    (0, 0.91, 0, 0.38, 0.08, 0.17, bone),
                    (0, 0.70, 0, 0.34, 0.08, 0.16, bone),
                    (-0.28, 0.72, 0, 0.11, 0.68, 0.12, bone),
                    (0.28, 0.72, 0, 0.11, 0.68, 0.12, bone),
                    (-0.14, 0, 0, 0.12, 0.72, 0.14, bone),
                    (0.14, 0, 0, 0.12, 0.72, 0.14, bone),
                ]
            else:
                skin = (75, 152, 102)
                shirt = (47, 112, 76)
                pants = (48, 66, 112)
                parts = [
                    (0, 1.43, 0, 0.54, 0.48, 0.48, skin),
                    (0, 0.72, 0, 0.56, 0.72, 0.32, shirt),
                    (-0.39, 0.72, 0, 0.22, 0.70, 0.25, shirt),
                    (0.39, 0.72, 0, 0.22, 0.70, 0.25, shirt),
                    (-0.15, 0, 0, 0.25, 0.72, 0.30, pants),
                    (0.15, 0, 0, 0.25, 0.72, 0.30, pants),
                ]
            for part in parts:
                draw_mob_cuboid(
                    screen, mob, origin, facing, part, focal_length, yaw, pitch
                )

            def project_detail(local_x, y, local_z):
                world_x = mob["x"] - facing[1] * local_x + facing[0] * local_z
                world_z = mob["z"] + facing[0] * local_x + facing[1] * local_z
                projection = project_camera_point(
                    world_x - origin[0],
                    mob["y"] + y - origin[1],
                    world_z - origin[2],
                    yaw,
                    pitch,
                    focal_length,
                )
                return projection[:2] if projection is not None else None

            if mob["kind"] == "skeleton":
                eye_color = (36, 34, 31)
                for eye_x in (-0.12, 0.12):
                    eye = project_detail(eye_x, 1.70, 0.225)
                    if eye is not None:
                        pygame.draw.rect(screen, eye_color, (*eye, 3, 3))
                bow_top = project_detail(0.48, 1.42, 0.18)
                bow_mid = project_detail(0.60, 1.21, 0.18)
                bow_bottom = project_detail(0.48, 1.00, 0.18)
                string_top = project_detail(0.48, 1.42, 0.18)
                string_bottom = project_detail(0.48, 1.00, 0.18)
                if (
                    bow_top is not None
                    and bow_mid is not None
                    and bow_bottom is not None
                    and string_top is not None
                    and string_bottom is not None
                ):
                    pygame.draw.lines(
                        screen, (125, 78, 42), False,
                        (bow_top, bow_mid, bow_bottom), 3,
                    )
                    pygame.draw.line(
                        screen, (225, 215, 190), string_top, string_bottom, 1
                    )
            else:
                for eye_x in (-0.15, 0.15):
                    eye = project_detail(eye_x, 1.69, 0.245)
                    if eye is not None:
                        pygame.draw.rect(screen, (225, 50, 45), (*eye, 3, 3))

        if mob["kind"] == "slime":
            bar_rect = (body.x, body.y - 5, body.width, 3)
        else:
            bar_projection = project_camera_point(
                dx, mob["y"] + 2.02 - origin[1], dz, yaw, pitch, focal_length
            )
            if bar_projection is None:
                continue
            bar_x, bar_y, bar_depth = bar_projection
            if bar_depth <= 0.3 or bar_depth > render_distance:
                continue
            bar_width = max(4, round(focal_length * 0.55 / bar_depth))
            bar_rect = (bar_x - bar_width // 2, bar_y, bar_width, 3)
        pygame.draw.rect(screen, (50, 30, 30), bar_rect)
        pygame.draw.rect(
            screen,
            (230, 55, 65),
            (bar_rect[0], bar_rect[1], round(bar_rect[2] * mob["health"] / 12), 3),
        )


def draw_arrows(screen, arrows, origin, yaw, pitch, render_distance):
    focal_length = SCREEN_WIDTH / (2 * math.tan(FIELD_OF_VIEW / 2))
    for arrow in arrows:
        dx, dz = arrow["x"] - origin[0], arrow["z"] - origin[2]
        projection = project_camera_point(
            dx, arrow["y"] - origin[1], dz, yaw, pitch, focal_length
        )
        if projection is None:
            continue
        center_x, center_y, depth = projection
        if depth <= 0.3 or depth > render_distance:
            continue
        if screen.get_rect().collidepoint(center_x, center_y):
            pygame.draw.line(
                screen, (105, 75, 45), (center_x - 3, center_y + 1),
                (center_x + 3, center_y - 1), 2,
            )


def draw_item_icon(screen, item, rect):
    family = tool_family(item)
    if item in BLOCK_COLORS:
        pygame.draw.rect(
            screen, BLOCK_COLORS[item],
            (rect.centerx - 11, rect.centery - 10, 22, 20),
        )
    elif family == "sword":
        blade_color = ITEM_COLORS.get(item, (220, 230, 245))
        pygame.draw.line(
            screen, blade_color,
            (rect.centerx - 8, rect.centery + 9),
            (rect.centerx + 8, rect.centery - 9), 4,
        )
        pygame.draw.line(
            screen, (122, 76, 45),
            (rect.centerx - 9, rect.centery + 7),
            (rect.centerx - 3, rect.centery + 13), 4,
        )
        pygame.draw.line(
            screen, (220, 180, 92),
            (rect.centerx - 5, rect.centery + 3),
            (rect.centerx + 1, rect.centery + 9), 3,
        )
    elif item == "apple":
        pygame.draw.circle(screen, ITEM_COLORS[item], rect.center, 10)
        pygame.draw.line(
            screen, (92, 190, 84),
            (rect.centerx, rect.centery - 8),
            (rect.centerx + 4, rect.centery - 13), 3,
        )
    elif family in ("pickaxe", "axe"):
        tool_color = ITEM_COLORS.get(item, (190, 195, 205))
        if family == "pickaxe":
            pygame.draw.line(
                screen, (125, 82, 48),
                (rect.centerx - 7, rect.centery + 11),
                (rect.centerx + 7, rect.centery - 10), 4,
            )
            pygame.draw.line(
                screen, tool_color,
                (rect.centerx - 10, rect.centery - 8),
                (rect.centerx + 10, rect.centery - 8), 4,
            )
        else:
            pygame.draw.line(
                screen, (125, 82, 48),
                (rect.centerx - 6, rect.centery + 11),
                (rect.centerx + 5, rect.centery - 10), 4,
            )
            pygame.draw.polygon(
                screen, tool_color,
                (
                    (rect.centerx + 2, rect.centery - 12),
                    (rect.centerx + 12, rect.centery - 9),
                    (rect.centerx + 8, rect.centery - 2),
                    (rect.centerx, rect.centery - 4),
                ),
            )
    elif item == "stick":
        pygame.draw.line(
            screen, ITEM_COLORS[item],
            (rect.centerx - 6, rect.centery + 10),
            (rect.centerx + 6, rect.centery - 10), 4,
        )
    else:
        pygame.draw.ellipse(
            screen, ITEM_COLORS.get(item, (180, 180, 180)),
            (rect.centerx - 11, rect.centery - 7, 22, 14),
        )


def draw_hotbar_item_icon(screen, item, rect, inventory, creative_mode):
    if creative_mode or inventory.get(item, 0) > 0:
        draw_item_icon(screen, item, rect)


def draw_dropped_items(screen, dropped_items, origin, yaw, pitch, render_distance):
    focal_length = SCREEN_WIDTH / (2 * math.tan(FIELD_OF_VIEW / 2))
    for dropped in dropped_items:
        projection = project_camera_point(
            dropped["x"] - origin[0],
            dropped["y"] - origin[1],
            dropped["z"] - origin[2],
            yaw,
            pitch,
            focal_length,
        )
        if projection is None:
            continue
        center_x, center_y, depth = projection
        if depth > render_distance or not screen.get_rect().collidepoint(center_x, center_y):
            continue
        size = max(5, min(18, round(focal_length * 0.12 / depth)))
        rect = pygame.Rect(center_x - size // 2, center_y - size // 2, size, size)
        draw_item_icon(screen, dropped["item"], rect)


def drop_inventory_item(inventory, dropped_items, item, x, y, z, yaw, creative_mode):
    if not creative_mode and inventory.get(item, 0) <= 0:
        return False
    if not creative_mode:
        inventory[item] -= 1
    dropped_items.append(
        {
            "item": item,
            "x": x + math.cos(yaw) * 0.8,
            "y": y + 0.85,
            "z": z + math.sin(yaw) * 0.8,
            "vx": math.cos(yaw) * 1.5,
            "vy": 1.8,
            "vz": math.sin(yaw) * 1.5,
            "age": 0.0,
        }
    )
    return True


def tool_family(item):
    if item is None:
        return None
    for family in ("sword", "pickaxe", "axe"):
        if item == family or item.endswith(f"_{family}"):
            return family
    return None


def new_inventory():
    inventory = {item: 0 for item in (*BLOCK_COLORS, *ITEM_COLORS)}
    inventory["sword"] = 1
    inventory["apple"] = 3
    inventory["pickaxe"] = 1
    inventory["axe"] = 1
    return inventory


def crafting_result(grid):
    occupied = {
        (index % 3, index // 3): item
        for index, item in enumerate(grid)
        if item is not None
    }
    for recipe in RECIPE_BOOK:
        pattern = dict(recipe[5])
        min_x = min(index % 3 for index in pattern)
        min_y = min(index // 3 for index in pattern)
        width = max(index % 3 for index in pattern) - min_x + 1
        height = max(index // 3 for index in pattern) - min_y + 1
        for offset_y in range(4 - height):
            for offset_x in range(4 - width):
                required = {
                    (
                        offset_x + index % 3 - min_x,
                        offset_y + index // 3 - min_y,
                    ): item
                    for index, item in pattern.items()
                }
                if occupied == required:
                    consumed_slots = tuple(
                        y * 3 + x for x, y in required
                    )
                    return recipe[3], recipe[4], consumed_slots
    return None


RECIPE_BOOK = (
    ("planks", "Planks", "1 wood -> 4 planks", "planks", 4, ((4, "wood"),)),
    ("sticks", "Sticks", "2 planks -> 4 sticks", "stick", 4, ((1, "planks"), (4, "planks"))),
    (
        "crafting_table", "Crafting table", "4 planks -> 1 crafting table",
        "crafting_table", 1,
        ((1, "planks"), (2, "planks"), (4, "planks"), (5, "planks")),
    ),
    ("wood_sword", "Wooden sword", "2 planks + 1 stick", "wood_sword", 1,
     ((1, "planks"), (4, "planks"), (7, "stick"))),
    ("stone_sword", "Stone sword", "2 stone + 1 stick", "stone_sword", 1,
     ((1, "stone"), (4, "stone"), (7, "stick"))),
    ("wood_pickaxe", "Wooden pickaxe", "3 planks + 2 sticks", "wood_pickaxe", 1,
     ((0, "planks"), (1, "planks"), (2, "planks"), (4, "stick"), (7, "stick"))),
    ("stone_pickaxe", "Stone pickaxe", "3 stone + 2 sticks", "stone_pickaxe", 1,
     ((0, "stone"), (1, "stone"), (2, "stone"), (4, "stick"), (7, "stick"))),
    ("wood_axe", "Wooden axe", "3 planks + 2 sticks", "wood_axe", 1,
     ((1, "planks"), (2, "planks"), (4, "stick"), (5, "planks"), (7, "stick"))),
    ("stone_axe", "Stone axe", "3 stone + 2 sticks", "stone_axe", 1,
     ((1, "stone"), (2, "stone"), (4, "stick"), (5, "stone"), (7, "stick"))),
)


def prepare_recipe(recipe_key, grid, inventory, creative_mode):
    recipe = next((entry for entry in RECIPE_BOOK if entry[0] == recipe_key), None)
    if recipe is None:
        return False
    required = {}
    for ingredient in recipe[5]:
        item = ingredient[1]
        required[item] = required.get(item, 0) + 1
    available = dict(inventory)
    for item in grid:
        if item is not None:
            available[item] = available.get(item, 0) + 1
    if not creative_mode and any(
        available.get(item, 0) < count for item, count in required.items()
    ):
        return False
    if not creative_mode:
        for item in grid:
            if item is not None:
                inventory[item] = inventory.get(item, 0) + 1
        for item, count in required.items():
            inventory[item] -= count
    grid[:] = [None] * 9
    for index, item in recipe[5]:
        grid[index] = item
    return True


def craft_item(grid, inventory):
    result = crafting_result(grid)
    if result is None:
        return False
    item, count, consumed_slots = result
    for index in consumed_slots:
        grid[index] = None
    inventory[item] = inventory.get(item, 0) + count
    return True


def draw_crafting_menu(
    screen, font, small_font, inventory, grid, selected_slot, selected_cell,
    creative_mode, recipe_book_open,
):
    screen.fill((12, 12, 14))
    panel = pygame.Rect(28, 45, SCREEN_WIDTH - 56, SCREEN_HEIGHT - 90)
    pygame.draw.rect(screen, (22, 22, 27), panel, border_radius=10)
    pygame.draw.rect(screen, (110, 110, 122), panel, 2, border_radius=10)
    title = render_text(font, "Inventory & Crafting", (255, 255, 255))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 75)))
    buttons = {}
    buttons["recipe_book"] = pygame.Rect(48, 101, 160, 30)
    draw_rounded_button(
        screen, buttons["recipe_book"],
        hovered=buttons["recipe_book"].collidepoint(pygame.mouse.get_pos()),
        active=recipe_book_open,
    )
    book_label = render_text(small_font, "Recipe book" if not recipe_book_open else "Inventory", (245, 245, 248))
    screen.blit(book_label, book_label.get_rect(center=buttons["recipe_book"].center))
    if recipe_book_open:
        for index, (key, name, description, result_item, count, _pattern) in enumerate(RECIPE_BOOK):
            rect = pygame.Rect(48, 143 + index * 44, 430, 40)
            buttons[f"recipe_{key}"] = rect
            enough = creative_mode or all(
                inventory.get(item, 0) >= sum(
                    1 for ingredient in _pattern if ingredient[1] == item
                )
                for item in {ingredient[1] for ingredient in _pattern}
            )
            draw_rounded_button(
                screen, rect,
                hovered=rect.collidepoint(pygame.mouse.get_pos()),
                active=enough,
            )
            draw_item_icon(screen, result_item, pygame.Rect(rect.x + 9, rect.y + 4, 32, 32))
            label = render_text(small_font, name, (240, 240, 245))
            description_text = render_text(small_font, description, (190, 190, 200))
            screen.blit(label, (rect.x + 52, rect.y + 2))
            screen.blit(description_text, (rect.x + 52, rect.y + 20))
    else:
        screen.blit(
            render_text(small_font, "Click an item to place one in the selected crafting slot.", (190, 190, 200)),
            (48, 105),
        )
        item_names = tuple((*BLOCK_COLORS, *ITEM_COLORS)) if creative_mode else tuple(
            item for item, count in inventory.items() if count > 0
        )
        for index, item in enumerate(item_names):
            column, row = index % 5, index // 5
            rect = pygame.Rect(48 + column * 88, 138 + row * 69, 78, 60)
            buttons[f"item_{item}"] = rect
            draw_rounded_button(
                screen, rect, hovered=rect.collidepoint(pygame.mouse.get_pos()),
            )
            draw_item_icon(screen, item, pygame.Rect(rect.x + 23, rect.y + 3, 32, 30))
            label = render_text(small_font, item.replace("_", " ")[:10], (240, 240, 245))
            screen.blit(label, label.get_rect(center=(rect.centerx, rect.y + 40)))
            count = "INF" if creative_mode else str(inventory.get(item, 0))
            count_text = render_text(small_font, count, (190, 190, 200))
            screen.blit(count_text, count_text.get_rect(center=(rect.centerx, rect.y + 54)))

    screen.blit(
        render_text(small_font, "3 x 3 crafting grid", (230, 230, 235)), (530, 127)
    )
    grid_left, grid_top, cell_size, gap = 530, 154, 50, 5
    for index, item in enumerate(grid):
        column, row = index % 3, index // 3
        rect = pygame.Rect(
            grid_left + column * (cell_size + gap),
            grid_top + row * (cell_size + gap),
            cell_size, cell_size,
        )
        buttons[f"craft_{index}"] = rect
        draw_rounded_button(
            screen, rect,
            hovered=rect.collidepoint(pygame.mouse.get_pos()),
            active=index == selected_cell,
        )
        if item is not None:
            draw_item_icon(screen, item, rect.inflate(-12, -12))

    buttons["craft_result"] = pygame.Rect(760, 199, 90, 60)
    result = crafting_result(grid)
    draw_rounded_button(
        screen, buttons["craft_result"],
        hovered=buttons["craft_result"].collidepoint(pygame.mouse.get_pos()),
        active=result is not None,
    )
    if result is not None:
        draw_item_icon(
            screen, result[0], buttons["craft_result"].inflate(-25, -25)
        )
        result_count = render_text(small_font, f"x{result[1]}", (255, 255, 255))
        screen.blit(result_count, (buttons["craft_result"].right - 28, buttons["craft_result"].bottom - 18))
    pygame.draw.line(
        screen, (210, 210, 215), (buttons["craft_result"].left - 13, 229),
        (buttons["craft_result"].left - 3, 229), 2,
    )
    pygame.draw.polygon(
        screen, (210, 210, 215),
        (
            (buttons["craft_result"].left - 3, 224),
            (buttons["craft_result"].left + 4, 229),
            (buttons["craft_result"].left - 3, 234),
        ),
    )
    screen.blit(
        render_text(small_font, "Wood -> 4 planks", (200, 200, 205)), (530, 327)
    )
    screen.blit(
        render_text(small_font, "2 planks -> 4 sticks", (200, 200, 205)), (530, 348)
    )
    screen.blit(
        render_text(small_font, "4 planks -> crafting table", (200, 200, 205)), (530, 369)
    )

    slot_size, slot_gap = 38, 3
    slots_width = len(HOTBAR) * (slot_size + slot_gap) - slot_gap
    slots_x = SCREEN_WIDTH // 2 - slots_width // 2
    for index, item in enumerate(HOTBAR):
        rect = pygame.Rect(
            slots_x + index * (slot_size + slot_gap), panel.bottom - 47,
            slot_size, slot_size,
        )
        buttons[f"hotbar_{index}"] = rect
        draw_rounded_button(screen, rect, active=index == selected_slot)
        draw_hotbar_item_icon(
            screen, item, rect.inflate(-8, -8), inventory, creative_mode
        )
    return buttons


def block_break_time(block, tool):
    family = tool_family(tool)
    if block == "stone":
        if family == "pickaxe" and not tool.startswith("wood_"):
            return BLOCK_BREAK_SECONDS["stone_pickaxe"]
        return None
    if block in ("wood", "leaves"):
        if family == "axe":
            return BLOCK_BREAK_SECONDS["wood_axe"]
        if family in ("pickaxe", "sword"):
            return BLOCK_BREAK_SECONDS["wood_hand"]
        return BLOCK_BREAK_SECONDS["wood_hand"]
    return BLOCK_BREAK_SECONDS["default"]


def draw_breaking_cracks(screen, progress):
    if progress <= 0:
        return
    center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    crack_color = (25, 25, 25)
    pygame.draw.lines(
        screen, crack_color, False,
        (
            (center_x - 8, center_y - 9),
            (center_x - 2, center_y - 3),
            (center_x - 5, center_y + 2),
            (center_x + 1, center_y + 5),
            (center_x - 1, center_y + 10),
        ), 2,
    )
    if progress >= 0.25:
        pygame.draw.lines(
            screen, crack_color, False,
            (
                (center_x + 8, center_y - 10),
                (center_x + 3, center_y - 4),
                (center_x + 7, center_y),
                (center_x + 2, center_y + 6),
            ), 2,
        )
    if progress >= 0.55:
        pygame.draw.lines(
            screen, crack_color, False,
            (
                (center_x - 10, center_y + 1),
                (center_x - 4, center_y - 2),
                (center_x + 2, center_y + 1),
                (center_x + 9, center_y - 3),
            ), 2,
        )
    if progress >= 0.8:
        pygame.draw.lines(
            screen, crack_color, False,
            (
                (center_x + 1, center_y - 9),
                (center_x - 2, center_y - 2),
                (center_x + 2, center_y + 3),
                (center_x - 4, center_y + 9),
            ), 2,
        )


def consume_food(inventory, hunger, health, item):
    if item not in FOOD_ITEMS or inventory.get(item, 0) <= 0:
        return hunger, health, False
    nutrition = FOOD_ITEMS[item]
    inventory[item] -= 1
    health = min(20, health + FOOD_HEAL[item])
    return min(20.0, hunger + nutrition), health, True


def advance_hunger(hunger, hunger_clock, starvation_clock, health, delta_time, creative):
    if creative:
        return hunger, hunger_clock, starvation_clock, health
    hunger_clock += delta_time
    if hunger_clock >= 24:
        hunger_clock %= 24
        hunger = max(0.0, hunger - 1.0)
    if hunger <= 0:
        starvation_clock += delta_time
        if starvation_clock >= 4:
            starvation_clock %= 4
            health = max(0, health - 1)
    else:
        starvation_clock = 0.0
    return hunger, hunger_clock, starvation_clock, health


def player_intersects_blocks(blocks, player_x, feet_y, player_z, leaves_only=False):
    for block_x in (
        math.floor(player_x - PLAYER_RADIUS),
        math.floor(player_x + PLAYER_RADIUS),
    ):
        for block_y in range(
            math.floor(feet_y + 0.05),
            math.floor(feet_y + PLAYER_HEIGHT - 0.05) + 1,
        ):
            for block_z in (
                math.floor(player_z - PLAYER_RADIUS),
                math.floor(player_z + PLAYER_RADIUS),
            ):
                block = blocks.get((block_x, block_y, block_z))
                if leaves_only:
                    if block == "leaves":
                        return True
                elif block not in (None, "water"):
                    return True
    return False


def hit_mob(mobs, mob, inventory, damage=5):
    if mob not in mobs:
        return False
    mob["health"] -= damage
    if mob["health"] > 0:
        return False
    mobs.remove(mob)
    inventory["steak"] = inventory.get("steak", 0) + 1
    return True


def draw_sword_swing(screen, swing_timer):
    progress = 1 - swing_timer / 0.24
    angle = -1.9 + max(0.0, min(1.0, progress)) * 2.7
    pivot = (SCREEN_WIDTH - 110, SCREEN_HEIGHT - 145)
    length = 100
    tip = (
        round(pivot[0] + math.cos(angle) * length),
        round(pivot[1] + math.sin(angle) * length),
    )
    guard = (
        round(pivot[0] + math.cos(angle + math.pi / 2) * 12),
        round(pivot[1] + math.sin(angle + math.pi / 2) * 12),
    )
    pygame.draw.line(screen, (119, 78, 48), pivot, guard, 9)
    pygame.draw.line(screen, (232, 194, 104), guard, (pivot[0] - 7, pivot[1] + 13), 7)
    pygame.draw.line(screen, (225, 232, 242), guard, tip, 10)
    pygame.draw.line(screen, (255, 255, 255), guard, tip, 3)


def draw_first_person_hand(screen, hand_rect, skin=(193, 133, 91)):
    pygame.draw.rect(
        screen, (105, 68, 48),
        (hand_rect.x - 2, hand_rect.y - 2, hand_rect.width + 4, hand_rect.height + 4),
        border_radius=9,
    )
    pygame.draw.rect(screen, skin, hand_rect, border_radius=8)
    pygame.draw.line(
        screen, (222, 167, 120),
        (hand_rect.x + 7, hand_rect.y + 6),
        (hand_rect.right - 7, hand_rect.y + 6), 3,
    )


def draw_first_person_item(screen, item, swing_timer=0.0):
    family = tool_family(item)
    base_x = SCREEN_WIDTH - 112
    base_y = SCREEN_HEIGHT - 58
    swing_offset = round(math.sin((0.24 - swing_timer) / 0.24 * math.pi) * 18) if swing_timer else 0
    hand = pygame.Rect(base_x + 34, base_y - swing_offset, 48, 54)

    if item in BLOCK_COLORS:
        pygame.draw.polygon(
            screen, BLOCK_COLORS[item],
            (
                (base_x + 12, base_y - 42 - swing_offset),
                (base_x + 56, base_y - 42 - swing_offset),
                (base_x + 56, base_y + 2 - swing_offset),
                (base_x + 12, base_y + 2 - swing_offset),
            ),
        )
        pygame.draw.polygon(
            screen, tuple(max(0, channel - 35) for channel in BLOCK_COLORS[item]),
            (
                (base_x + 56, base_y - 42 - swing_offset),
                (base_x + 72, base_y - 30 - swing_offset),
                (base_x + 72, base_y + 14 - swing_offset),
                (base_x + 56, base_y + 2 - swing_offset),
            ),
        )
        draw_first_person_hand(screen, hand)
        return

    draw_first_person_hand(screen, hand)
    if family == "sword":
        blade_color = ITEM_COLORS.get(item, (225, 232, 242))
        pygame.draw.line(
            screen, (122, 76, 45),
            (base_x + 45, base_y - 20 - swing_offset),
            (base_x + 67, base_y - 2 - swing_offset), 9,
        )
        pygame.draw.line(
            screen, blade_color,
            (base_x + 12, base_y - 91 - swing_offset),
            (base_x + 49, base_y - 16 - swing_offset), 12,
        )
        pygame.draw.line(
            screen, (255, 255, 255),
            (base_x + 12, base_y - 91 - swing_offset),
            (base_x + 49, base_y - 16 - swing_offset), 3,
        )
    elif family == "pickaxe":
        pygame.draw.line(
            screen, (125, 82, 48),
            (base_x + 53, base_y - 9 - swing_offset),
            (base_x + 22, base_y - 88 - swing_offset), 9,
        )
        pygame.draw.line(
            screen, ITEM_COLORS.get(item, (190, 195, 205)),
            (base_x + 8, base_y - 79 - swing_offset),
            (base_x + 64, base_y - 79 - swing_offset), 11,
        )
    elif family == "axe":
        pygame.draw.line(
            screen, (125, 82, 48),
            (base_x + 52, base_y - 10 - swing_offset),
            (base_x + 22, base_y - 87 - swing_offset), 9,
        )
        pygame.draw.polygon(
            screen, ITEM_COLORS.get(item, (190, 195, 205)),
            (
                (base_x + 18, base_y - 94 - swing_offset),
                (base_x + 67, base_y - 86 - swing_offset),
                (base_x + 53, base_y - 56 - swing_offset),
                (base_x + 29, base_y - 62 - swing_offset),
            ),
        )
    elif item == "apple":
        pygame.draw.circle(
            screen, ITEM_COLORS[item],
            (base_x + 57, base_y - 27 - swing_offset), 20,
        )
        pygame.draw.line(
            screen, (92, 190, 84),
            (base_x + 56, base_y - 45 - swing_offset),
            (base_x + 62, base_y - 55 - swing_offset), 4,
        )


def world_save_path(world_name):
    return SAVE_DIRECTORY / f"{world_name.lower()}.json"


def load_game_save(path):
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as save_file:
            return json.load(save_file)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Save file is corrupted: {path}") from error


def write_game_save(path, save_data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.stem}_",
            suffix=".tmp",
            delete=False,
        ) as save_file:
            temporary_path = Path(save_file.name)
            json.dump(save_data, save_file, separators=(",", ":"))
            save_file.flush()
            os.fsync(save_file.fileno())
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise


def raycast(blocks, origin, direction, max_distance):
    origin_x, origin_y, origin_z = origin
    direction_x, direction_y, direction_z = direction
    direction_length = math.sqrt(
        direction_x * direction_x
        + direction_y * direction_y
        + direction_z * direction_z
    )
    direction_x /= direction_length
    direction_y /= direction_length
    direction_z /= direction_length

    cell_x = math.floor(origin_x)
    cell_y = math.floor(origin_y)
    cell_z = math.floor(origin_z)
    step_x = 1 if direction_x >= 0 else -1
    step_y = 1 if direction_y >= 0 else -1
    step_z = 1 if direction_z >= 0 else -1
    delta_x = abs(1.0 / direction_x) if abs(direction_x) > 1e-10 else float("inf")
    delta_y = abs(1.0 / direction_y) if abs(direction_y) > 1e-10 else float("inf")
    delta_z = abs(1.0 / direction_z) if abs(direction_z) > 1e-10 else float("inf")
    max_x = (
        (cell_x + (1 if step_x > 0 else 0) - origin_x) / direction_x
        if delta_x != float("inf") else float("inf")
    )
    max_y = (
        (cell_y + (1 if step_y > 0 else 0) - origin_y) / direction_y
        if delta_y != float("inf") else float("inf")
    )
    max_z = (
        (cell_z + (1 if step_z > 0 else 0) - origin_z) / direction_z
        if delta_z != float("inf") else float("inf")
    )

    distance = 0.0
    normal = (0, 0, 0)
    while distance <= max_distance:
        position = (cell_x, cell_y, cell_z)
        block = blocks.get(position)
        if block is not None:
            return position, block, normal, distance

        if max_x <= max_y and max_x <= max_z:
            distance = max_x
            cell_x += step_x
            max_x += delta_x
            normal = (-step_x, 0, 0)
        elif max_y <= max_z:
            distance = max_y
            cell_y += step_y
            max_y += delta_y
            normal = (0, -step_y, 0)
        else:
            distance = max_z
            cell_z += step_z
            max_z += delta_z
            normal = (0, 0, -step_z)
        if distance > max_distance:
            break
        if cell_y < 0 or cell_y >= WORLD_HEIGHT:
            break
        if cell_x < -1 or cell_x > WORLD_SIZE or cell_z < -1 or cell_z > WORLD_SIZE:
            break
    return None


def render_grid_index(x, y, z):
    return (x + 1) * RENDER_GRID_X_STRIDE + y * RENDER_GRID_Y_STRIDE + z + 1


def set_render_grid_block(render_grid, position, block):
    x, y, z = position
    if (
        -1 <= x <= WORLD_SIZE
        and 0 <= y < WORLD_HEIGHT
        and -1 <= z <= WORLD_SIZE
    ):
        render_grid[render_grid_index(x, y, z)] = (
            RENDER_BLOCK_IDS[block] if block is not None else 0
        )


def build_render_grid(blocks):
    render_grid = bytearray((WORLD_SIZE + 2) ** 2 * WORLD_HEIGHT)
    for (x, y, z), block in blocks.items():
        set_render_grid_block(render_grid, (x, y, z), block)
    return render_grid


def raycast_render_grid(
    render_grid, origin, direction_x, direction_y, direction_z, max_distance,
):
    origin_x, origin_y, origin_z = origin
    direction_length = math.sqrt(
        direction_x * direction_x
        + direction_y * direction_y
        + direction_z * direction_z
    )
    direction_x /= direction_length
    direction_y /= direction_length
    direction_z /= direction_length

    cell_x = math.floor(origin_x)
    cell_y = math.floor(origin_y)
    cell_z = math.floor(origin_z)
    if (
        cell_y < 0 or cell_y >= WORLD_HEIGHT
        or cell_x < -1 or cell_x > WORLD_SIZE
        or cell_z < -1 or cell_z > WORLD_SIZE
    ):
        return None

    step_x = 1 if direction_x >= 0 else -1
    step_y = 1 if direction_y >= 0 else -1
    step_z = 1 if direction_z >= 0 else -1
    delta_x = abs(1.0 / direction_x) if abs(direction_x) > 1e-10 else float("inf")
    delta_y = abs(1.0 / direction_y) if abs(direction_y) > 1e-10 else float("inf")
    delta_z = abs(1.0 / direction_z) if abs(direction_z) > 1e-10 else float("inf")
    max_x = (
        (cell_x + (1 if step_x > 0 else 0) - origin_x) / direction_x
        if delta_x != float("inf") else float("inf")
    )
    max_y = (
        (cell_y + (1 if step_y > 0 else 0) - origin_y) / direction_y
        if delta_y != float("inf") else float("inf")
    )
    max_z = (
        (cell_z + (1 if step_z > 0 else 0) - origin_z) / direction_z
        if delta_z != float("inf") else float("inf")
    )

    distance = 0.0
    normal = (0, 0, 0)
    grid_index = render_grid_index(cell_x, cell_y, cell_z)
    while distance <= max_distance:
        block_id = render_grid[grid_index]
        if block_id:
            return (
                (cell_x, cell_y, cell_z),
                RENDER_BLOCK_TYPES[block_id],
                normal,
                distance,
            )

        if max_x <= max_y and max_x <= max_z:
            distance = max_x
            cell_x += step_x
            grid_index += step_x * RENDER_GRID_X_STRIDE
            max_x += delta_x
            normal = (-step_x, 0, 0)
        elif max_y <= max_z:
            distance = max_y
            cell_y += step_y
            grid_index += step_y * RENDER_GRID_Y_STRIDE
            max_y += delta_y
            normal = (0, -step_y, 0)
        else:
            distance = max_z
            cell_z += step_z
            grid_index += step_z
            max_z += delta_z
            normal = (0, 0, -step_z)
        if distance > max_distance:
            break
        if cell_y < 0 or cell_y >= WORLD_HEIGHT:
            break
        if cell_x < -1 or cell_x > WORLD_SIZE or cell_z < -1 or cell_z > WORLD_SIZE:
            break
    return None


def find_aim_assist_target(blocks, origin, yaw, pitch):
    best_target = None
    best_score = float("inf")
    best_angles = (yaw, pitch)
    for yaw_step in range(-3, 4):
        candidate_yaw = yaw + yaw_step * 0.045
        for pitch_step in range(-3, 4):
            candidate_pitch = max(
                -1.55, min(1.55, pitch + pitch_step * 0.045)
            )
            direction = (
                math.cos(candidate_yaw) * math.cos(candidate_pitch),
                math.sin(candidate_pitch),
                math.sin(candidate_yaw) * math.cos(candidate_pitch),
            )
            hit = raycast(blocks, origin, direction, MAX_REACH)
            if hit is None:
                continue
            score = yaw_step * yaw_step + pitch_step * pitch_step
            if score < best_score:
                best_target = hit
                best_score = score
                best_angles = (candidate_yaw, candidate_pitch)
    return best_target, best_angles


def suspicious_chunks(blocks):
    return {
        (x // CHUNK_SIZE, z // CHUNK_SIZE)
        for (x, _y, z), block in blocks.items()
        if block in SPECIAL_BLOCKS
    }


def empty_container():
    return [{"block": None, "count": 0} for _ in range(CONTAINER_SLOT_COUNT)]


def store_inventory_item(slots, block, inventory, creative_mode):
    count = inventory.get(block, 0)
    if count <= 0 and not creative_mode:
        return False

    slot = next(
        (item for item in slots if item["block"] == block),
        next((item for item in slots if item["block"] is None), None),
    )
    if slot is None:
        return False

    slot["block"] = block
    slot["count"] += 1 if creative_mode else count
    if not creative_mode:
        inventory[block] = 0
    return True


def take_container_item(slot, inventory):
    block = slot["block"]
    if block is None or slot["count"] <= 0:
        return False
    inventory[block] = inventory.get(block, 0) + slot["count"]
    slot["block"] = None
    slot["count"] = 0
    return True


def draw_container_menu(
    screen, font, small_font, block, slots, inventory, selected,
    button_theme=BUTTON_THEMES[0], creative_mode=False,
):
    screen.fill((12, 12, 14))
    title = render_text(font, f"{SPECIAL_BLOCK_LABELS[block]} Inventory", (255, 255, 255))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 105)))
    hint = render_text(
        small_font,
        "Click a stored item to take it. Click a hotbar slot to store its selected item.",
        (190, 190, 200),
    )
    screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 140)))

    buttons = {}
    start_x = SCREEN_WIDTH // 2 - 108
    start_y = 175
    for index, slot in enumerate(slots):
        x = start_x + (index % 3) * 76
        y = start_y + (index // 3) * 68
        rect = pygame.Rect(x, y, 64, 56)
        buttons[f"container_{index}"] = rect
        draw_rounded_button(screen, rect, button_theme)
        if slot["block"] is not None:
            pygame.draw.rect(screen, BLOCK_COLORS[slot["block"]], (x + 19, y + 7, 26, 26))
            count = render_text(small_font, str(slot["count"]), (255, 255, 255))
            screen.blit(count, count.get_rect(bottomright=(rect.right - 4, rect.bottom - 3)))

    hotbar_x = SCREEN_WIDTH // 2 - len(HOTBAR) * 36
    hotbar_y = 420
    for index, item in enumerate(HOTBAR):
        x = hotbar_x + index * 72
        rect = pygame.Rect(x, hotbar_y, 64, 62)
        buttons[f"hotbar_{index}"] = rect
        draw_rounded_button(
            screen, rect, button_theme, active=index == selected
        )
        draw_hotbar_item_icon(
            screen, item, pygame.Rect(x + 18, hotbar_y + 6, 28, 28),
            inventory, creative_mode,
        )
        name = render_text(small_font, item.replace("_", " ")[:9], (235, 235, 240))
        screen.blit(name, name.get_rect(center=(rect.centerx, hotbar_y + 43)))
        count_text = "INF" if inventory.get(item, 0) < 0 else str(inventory.get(item, 0))
        count_surface = render_text(small_font, count_text, (200, 200, 205))
        screen.blit(count_surface, count_surface.get_rect(midbottom=(rect.centerx, rect.bottom - 2)))

    close_hint = render_text(small_font, "Esc: close", (190, 190, 200))
    screen.blit(close_hint, close_hint.get_rect(center=(SCREEN_WIDTH // 2, 525)))
    return buttons


def _block_color_uncached(
    block, normal, distance, esp=False, chest_esp=False, suspicious=False,
    texture_color=None, fog_color=None, fog_strength=0.0, neon_city=False,
):
    if block in CONTAINER_BLOCKS and chest_esp:
        return ESP_BLOCK_COLORS["chest"]
    if suspicious:
        return (235, 35, 45)
    if esp:
        if block in ESP_BLOCK_COLORS:
            return ESP_BLOCK_COLORS[block]
        red, green, blue = BLOCK_COLORS[block]
        return (min(255, red + 80), min(255, green + 80), min(255, blue + 80))
    red, green, blue = texture_color or BLOCK_COLORS[block]
    if normal[1] == 0:
        if normal[0] != 0:
            light = 0.78
        else:
            light = 0.64
    else:
        light = 1.0 if normal[1] > 0 else 0.48
    light *= max(0.55, 1.0 - distance * 0.004)
    color = (
        int(red * light),
        int(green * light),
        int(blue * light),
    )
    if neon_city:
        color = (
            min(255, int(color[0] * 0.48 + color[2] * 0.18)),
            min(255, int(color[1] * 0.62 + color[2] * 0.35)),
            min(255, int(color[2] * 0.82 + color[0] * 0.28)),
        )
    if fog_color is not None and fog_strength > 0:
        return tuple(
            int(channel + (fog_channel - channel) * fog_strength)
            for channel, fog_channel in zip(color, fog_color)
        )
    return color


@lru_cache(maxsize=32768)
def _cached_block_color(
    block, normal, distance_step, esp, chest_esp, suspicious, fog_color,
    fog_step, neon_city,
):
    return _block_color_uncached(
        block,
        normal,
        distance_step / 4,
        esp,
        chest_esp,
        suspicious,
        fog_color=fog_color,
        fog_strength=fog_step / 100,
        neon_city=neon_city,
    )


def block_color(
    block, normal, distance, esp=False, chest_esp=False, suspicious=False,
    texture_color=None, fog_color=None, fog_strength=0.0, neon_city=False,
):
    if texture_color is not None:
        fog_color = tuple(fog_color) if fog_color is not None else None
        return _cached_textured_block_color(
            block, normal, round(distance * 4), esp, chest_esp, suspicious,
            tuple(texture_color), fog_color, round(fog_strength * 100), neon_city,
        )
    fog_color = tuple(fog_color) if fog_color is not None else None
    return _cached_block_color(
        block,
        normal,
        round(distance * 4),
        esp,
        chest_esp,
        suspicious,
        fog_color,
        round(fog_strength * 100),
        neon_city,
    )


@lru_cache(maxsize=65536)
def _cached_textured_block_color(
    block, normal, distance_step, esp, chest_esp, suspicious, texture_color,
    fog_color, fog_step, neon_city,
):
    return _block_color_uncached(
        block,
        normal,
        distance_step / 4,
        esp,
        chest_esp,
        suspicious,
        texture_color,
        fog_color,
        fog_step / 100,
        neon_city,
    )


@lru_cache(maxsize=65536)
def block_texture_color(block, position, normal, texture_u, texture_v):
    base = BLOCK_COLORS[block]
    x, y, z = position
    u, v = texture_u, texture_v
    if block == "grass" and normal[1] <= 0:
        base = BLOCK_COLORS["dirt"]

    if block in ("stone", "dirt", "grass"):
        pattern_x, pattern_y = u // 2, v // 2
    elif block == "wood":
        pattern_x, pattern_y = u // 2, (v + x + z) // 2
    elif block == "planks":
        pattern_x, pattern_y = u // 2, (v + y) // 2
    else:
        pattern_x, pattern_y = u, v

    value = (
        x * 374761393 + y * 668265263 + z * 69069
        + pattern_x * 1274126177 + pattern_y * 42595009
        + (normal[0] + 2 * normal[1] + 3 * normal[2]) * 1013904223
    ) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    shade = ((value >> 28) & 0x0F) // 2 - 3

    if block == "wood" and u % 4 == 0:
        shade -= 7
    elif block == "planks" and v % 4 == 0:
        shade -= 6
    elif block == "leaves":
        shade += 3 if value & 3 else -4
    elif block in ("chest", "ender_chest") and v in (0, 1, 6, 7):
        shade -= 8
    elif block == "crafting_table" and normal[1] > 0:
        shade += 3 if (u + v) % 4 < 2 else -3
    elif block == "water":
        shade += 3 if (u + v + y) % 5 == 0 else -1

    return tuple(max(0, min(255, channel + shade)) for channel in base)


def draw_neon_skyline(screen, horizon_row):
    width, height = screen.get_size()
    baseline = max(0, min(height, horizon_row))
    if baseline <= 0 or width <= 0:
        return

    step = max(5, width // 24)
    for index, left in enumerate(range(0, width, step)):
        building_width = step + (index * 7 % max(1, step // 2))
        building_height = max(
            2,
            int(height * (0.08 + (index * 13 % 15) / 100)),
        )
        top = max(0, baseline - building_height)
        rect = pygame.Rect(left, top, min(building_width, width - left), baseline - top)
        pygame.draw.rect(screen, (14, 10, 30), rect)
        if index % 3 == 0:
            glow = (239, 47, 194)
        elif index % 3 == 1:
            glow = (45, 225, 255)
        else:
            glow = (143, 82, 255)
        pygame.draw.line(screen, glow, (rect.left, rect.top), (rect.right - 1, rect.top))

        window_step = max(2, step // 4)
        for window_x in range(rect.left + 2, rect.right - 1, window_step):
            for window_y in range(rect.top + 3, rect.bottom - 1, 5):
                if (window_x + window_y + index) % 3:
                    pygame.draw.rect(
                        screen, glow, (window_x, window_y, 1, 2)
                    )


def draw_world(
    screen, render_grid, origin, yaw, pitch, column_offsets, row_offsets,
    render_distance, render_width, render_height, esp=False, chest_esp=False,
    sus_chunk_finder=False, sus_chunks=None, world_color=(92, 110, 72),
    skybox_color=(86, 155, 221), neon_city=False,
):
    horizon = render_height / 2 + pitch * render_height
    horizon_row = max(0, min(render_height, int(horizon)))
    sky_glow = (110, 22, 112) if neon_city else (49, 67, 18)
    for screen_y in range(horizon_row):
        sky = max(0.0, min(1.0, screen_y / max(1.0, horizon)))
        color = tuple(
            min(255, int(channel + amount * sky))
            for channel, amount in zip(skybox_color, sky_glow)
        )
        pygame.draw.line(screen, color, (0, screen_y), (render_width - 1, screen_y))
    if neon_city:
        draw_neon_skyline(screen, horizon_row)
    screen.fill(
        world_color,
        (0, horizon_row, render_width, render_height - horizon_row),
    )

    sin_pitch = math.sin(pitch)
    cos_pitch = math.cos(pitch)
    sin_yaw = math.sin(yaw)
    cos_yaw = math.cos(yaw)
    max_fog_distance = max(1.0, render_distance)
    vertical_directions = [
        sin_pitch + camera_y * cos_pitch for camera_y in row_offsets
    ]
    for screen_x, camera_x in enumerate(column_offsets):
        horizontal_x = cos_yaw - camera_x * sin_yaw
        horizontal_z = sin_yaw + camera_x * cos_yaw

        for screen_y, vertical_direction in enumerate(vertical_directions):
            hit = raycast_render_grid(
                render_grid,
                origin,
                horizontal_x,
                vertical_direction,
                horizontal_z,
                render_distance,
            )
            if hit is not None:
                position, block, normal, distance = hit
                direction = (
                    horizontal_x,
                    vertical_direction,
                    horizontal_z,
                )
                suspicious = (
                    sus_chunk_finder
                    and sus_chunks is not None
                    and (position[0] // CHUNK_SIZE, position[2] // CHUNK_SIZE)
                    in sus_chunks
                )
                if block == "grass" and normal[1] == 0:
                    hit_height = origin[1] + direction[1] * distance
                    if hit_height - math.floor(hit_height) < 0.75:
                        block = "dirt"
                hit_x = origin[0] + direction[0] * distance
                hit_y = origin[1] + direction[1] * distance
                hit_z = origin[2] + direction[2] * distance
                if normal[1] != 0:
                    texture_u, texture_v = (
                        math.floor((hit_x - position[0]) * 8),
                        math.floor((hit_z - position[2]) * 8),
                    )
                elif normal[0] != 0:
                    texture_u, texture_v = (
                        math.floor((hit_z - position[2]) * 8),
                        math.floor((hit_y - position[1]) * 8),
                    )
                else:
                    texture_u, texture_v = (
                        math.floor((hit_x - position[0]) * 8),
                        math.floor((hit_y - position[1]) * 8),
                    )
                texture_color = block_texture_color(
                    block,
                    position,
                    normal,
                    max(0, min(7, texture_u)),
                    max(0, min(7, texture_v)),
                )
                fog_strength = max(
                    0.0,
                    min(0.45, (distance / max_fog_distance - 0.55) * 0.8),
                )
                screen.set_at(
                    (screen_x, screen_y),
                    block_color(
                        block,
                        normal,
                        distance,
                        esp,
                        chest_esp,
                        suspicious,
                        texture_color=texture_color,
                        fog_color=world_color,
                        fog_strength=fog_strength,
                        neon_city=neon_city,
                    ),
                )


def draw_through_wall_chest_esp(
    screen, blocks, origin, yaw, pitch, render_distance, small_font,
    marker_color=ESP_BLOCK_COLORS["chest"], box_scale=1.0, tracer=True,
    label_prefix="",
):
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    focal_y = SCREEN_HEIGHT / (2 * math.tan(FIELD_OF_VIEW / 2))
    focal_x = focal_y
    forward_x = math.cos(yaw)
    forward_z = math.sin(yaw)
    right_x = -forward_z
    right_z = forward_x

    for (block_x, block_y, block_z), block in blocks.items():
        if block not in CONTAINER_BLOCKS:
            continue

        dx = block_x + 0.5 - origin[0]
        dy = block_y + 0.5 - origin[1]
        dz = block_z + 0.5 - origin[2]
        depth = dx * forward_x + dz * forward_z
        if depth <= 0.25 or depth > render_distance:
            continue

        horizontal = dx * right_x + dz * right_z
        screen_x = SCREEN_WIDTH / 2 + focal_x * horizontal / depth
        vertical = (dy / depth - math.sin(pitch)) / math.cos(pitch)
        screen_y = SCREEN_HEIGHT / 2 - focal_y * vertical
        box_width = max(12, round(focal_x / depth * box_scale))
        box_height = max(12, round(focal_y / depth * box_scale))
        box_width = min(SCREEN_WIDTH // 2, box_width)
        box_height = min(SCREEN_HEIGHT // 2, box_height)
        rect = pygame.Rect(0, 0, box_width, box_height)
        rect.center = (round(screen_x), round(screen_y))
        if not screen.get_rect().colliderect(rect):
            continue

        glow_color = marker_color
        glow_rect = rect.inflate(16, 16)
        if tracer:
            pygame.draw.line(
                overlay,
                (*glow_color, 135),
                (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18),
                rect.center,
                2,
            )
        pygame.draw.rect(overlay, (*glow_color, 42), glow_rect, border_radius=7)
        pygame.draw.rect(
            overlay, (*glow_color, 145), rect.inflate(7, 7), 6, border_radius=5
        )
        pygame.draw.rect(overlay, (*glow_color, 245), rect, 4, border_radius=3)
        label = render_text(
            small_font,
            f"{label_prefix}{SPECIAL_BLOCK_LABELS[block].upper()}",
            (255, 255, 255),
        )
        label_rect = label.get_rect(midbottom=(rect.centerx, rect.top - 3))
        label_bg = label_rect.inflate(10, 6)
        pygame.draw.rect(
            overlay, (*glow_color, 200), label_bg, border_radius=5
        )
        overlay.blit(label, label_rect)

    screen.blit(overlay, (0, 0))


def draw_player_avatar(screen):
    center_x = SCREEN_WIDTH // 2
    feet_y = SCREEN_HEIGHT - 78
    pygame.draw.ellipse(
        screen, (45, 55, 58), (center_x - 34, feet_y - 5, 68, 14)
    )
    pygame.draw.rect(screen, (48, 83, 154), (center_x - 24, feet_y - 43, 19, 39))
    pygame.draw.rect(screen, (37, 68, 133), (center_x + 5, feet_y - 43, 19, 39))
    pygame.draw.rect(screen, (52, 101, 190), (center_x - 27, feet_y - 91, 54, 49))
    pygame.draw.rect(screen, (193, 133, 91), (center_x - 40, feet_y - 88, 13, 43))
    pygame.draw.rect(screen, (193, 133, 91), (center_x + 27, feet_y - 88, 13, 43))
    pygame.draw.rect(screen, (193, 133, 91), (center_x - 19, feet_y - 127, 38, 36))
    pygame.draw.rect(screen, (105, 68, 44), (center_x - 19, feet_y - 130, 38, 10))
    pygame.draw.rect(screen, (55, 43, 35), (center_x - 10, feet_y - 113, 4, 4))
    pygame.draw.rect(screen, (55, 43, 35), (center_x + 6, feet_y - 113, 4, 4))


def draw_hud(
    screen, font, small_font, inventory, selected, target, third_person, health,
    creative_mode=False, hunger=20.0, mining_progress=0.0,
):
    global HUD_PANEL
    if HUD_PANEL is None:
        HUD_PANEL = pygame.Surface((435, 62), pygame.SRCALPHA)
        HUD_PANEL.fill((20, 30, 40, 205))
    screen.blit(HUD_PANEL, (10, 10))
    screen.blit(
        render_text(
            font,
            "WASD: move    Mouse: look    Space: jump    F5: camera",
            (255, 255, 255),
        ),
        (22, 16),
    )
    screen.blit(
        render_text(
            small_font,
            "Hold click: mine    Right click: place/eat    E: inventory",
            (235, 235, 235),
        ),
        (22, 41),
    )
    pygame.draw.rect(screen, (44, 38, 38), (SCREEN_WIDTH - 170, 16, 150, 18))
    pygame.draw.rect(
        screen, (184, 55, 55), (SCREEN_WIDTH - 168, 18, round(146 * health / 20), 14)
    )
    health_text = render_text(small_font, f"Health {health}/20", (255, 255, 255))
    screen.blit(health_text, health_text.get_rect(midright=(SCREEN_WIDTH - 178, 25)))
    hunger_x = SCREEN_WIDTH - 168
    pygame.draw.rect(screen, (45, 38, 32), (hunger_x, 43, 146, 13))
    pygame.draw.rect(
        screen, (224, 151, 55),
        (hunger_x + 2, 45, round(142 * max(0, hunger) / 20), 9),
    )
    hunger_text = render_text(small_font, f"Hunger {round(hunger)}/20", (255, 255, 255))
    screen.blit(hunger_text, hunger_text.get_rect(midright=(hunger_x - 8, 50)))

    pygame.draw.line(
        screen, (255, 255, 255), (SCREEN_WIDTH // 2 - 7, SCREEN_HEIGHT // 2),
        (SCREEN_WIDTH // 2 + 7, SCREEN_HEIGHT // 2), 2,
    )
    pygame.draw.line(
        screen, (255, 255, 255), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 7),
        (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 7), 2,
    )
    if target is not None:
        pygame.draw.rect(
            screen, (255, 241, 118),
            (SCREEN_WIDTH // 2 - 10, SCREEN_HEIGHT // 2 - 10, 20, 20), 1,
        )
        draw_breaking_cracks(screen, mining_progress)
    if third_person:
        draw_player_avatar(screen)

    start_x = SCREEN_WIDTH // 2 - len(HOTBAR) * 28
    for index, item in enumerate(HOTBAR):
        x = start_x + index * 56
        y = SCREEN_HEIGHT - 62
        outline = (255, 241, 118) if index == selected else (35, 35, 35)
        pygame.draw.rect(screen, (48, 48, 48), (x, y, 48, 48))
        pygame.draw.rect(screen, outline, (x, y, 48, 48), 3 if index == selected else 2)
        item_count = inventory.get(item, 0)
        draw_hotbar_item_icon(
            screen, item, pygame.Rect(x + 7, y + 5, 34, 28),
            inventory, creative_mode,
        )
        if creative_mode:
            count_text = "INF"
        elif item_count > 0:
            count_text = str(item_count)
        else:
            count_text = ""
        if count_text:
            count = render_text(small_font, count_text, (255, 255, 255))
            screen.blit(count, count.get_rect(center=(x + 24, y + 39)))


def draw_rounded_button(
    screen, rect, theme=BUTTON_THEMES[0], hovered=False, active=False
):
    _name, base_color, hover_color, border_color = theme
    fill_color = hover_color if hovered else base_color
    if active:
        fill_color = hover_color
        border_color = (255, 235, 100)
    radius = min(26, rect.height // 2)
    pygame.draw.rect(screen, fill_color, rect, border_radius=radius)
    pygame.draw.rect(
        screen, border_color, rect, 2 if active else 1, border_radius=radius
    )


def draw_menu_button(
    screen, font, label, rect, mouse_position, dark=False, theme=BUTTON_THEMES[0]
):
    draw_rounded_button(
        screen, rect, theme, hovered=rect.collidepoint(mouse_position)
    )
    text = render_text(font, label, (255, 255, 255))
    screen.blit(text, text.get_rect(center=rect.center))


def draw_menu(
    screen, font, small_font, mode, render_distance, quality,
    skybox_name="Blue", button_theme=BUTTON_THEMES[0], fullscreen=False,
    display_resolution="960x600",
    resolution_status="",
):
    screen.fill((12, 12, 14))

    mouse_position = pygame.mouse.get_pos()
    center_x = SCREEN_WIDTH // 2
    buttons = {}

    if mode == "main":
        title = render_text(font, "BLACK CLIENT BETA", (255, 255, 255))
        screen.blit(title, title.get_rect(center=(center_x, 150)))
        subtitle = render_text(small_font, "A little 3D block-building game", (235, 240, 235))
        screen.blit(subtitle, subtitle.get_rect(center=(center_x, 185)))
        welcome = render_text(font, "Welcome back", (225, 225, 230))
        screen.blit(welcome, (42, 42))
        for name, label, y in (
            ("single_player", "Single Player", 235),
            ("options", "Options", 297),
            ("quit", "Quit", 359),
        ):
            buttons[name] = pygame.Rect(center_x - 205, y, 410, 56)
            draw_menu_button(
                screen, font, label, buttons[name], mouse_position,
                dark=True, theme=button_theme,
            )
    elif mode == "worlds":
        title = render_text(font, "Select World", (255, 255, 255))
        screen.blit(title, title.get_rect(center=(center_x, 150)))
        for index, world_name in enumerate(WORLD_PRESETS):
            key = f"world_{world_name.lower()}"
            buttons[key] = pygame.Rect(center_x - 205, 190 + index * 54, 410, 50)
            draw_menu_button(
                screen, font, world_name, buttons[key], mouse_position,
                dark=True, theme=button_theme,
            )
        buttons["back"] = pygame.Rect(center_x - 205, 416, 410, 50)
        draw_menu_button(
            screen, font, "Back to Main Menu", buttons["back"], mouse_position,
            dark=True, theme=button_theme,
        )
    elif mode == "options":
        title = render_text(font, "Options", (255, 255, 255))
        screen.blit(title, title.get_rect(center=(center_x, 44)))
        distance_text = render_text(
            small_font, f"Render Distance: {render_distance}", (255, 255, 255)
        )
        screen.blit(distance_text, distance_text.get_rect(center=(center_x, 82)))
        buttons["distance"] = pygame.Rect(center_x - 175, 96, 350, 16)
        pygame.draw.rect(screen, (48, 58, 64), buttons["distance"], border_radius=8)
        pygame.draw.rect(screen, (190, 205, 190), buttons["distance"], 2, border_radius=8)
        knob_x = buttons["distance"].left + round(
            (render_distance - 1) / 99 * (buttons["distance"].width - 1)
        )
        pygame.draw.circle(screen, (255, 241, 118), (knob_x, buttons["distance"].centery), 10)

        quality_width, quality_height = quality_dimensions(quality)
        quality_text = render_text(
            small_font,
            f"Render Quality: {quality} ({quality_width}x{quality_height})",
            (255, 255, 255),
        )
        screen.blit(quality_text, quality_text.get_rect(center=(center_x, 135)))
        buttons["quality"] = pygame.Rect(center_x - 180, 151, 360, 38)
        draw_menu_button(
            screen, font, "Next Quality (Poop to Ultra)", buttons["quality"], mouse_position,
            theme=button_theme,
        )
        resolution_text = render_text(
            small_font,
            f"Display Resolution: {display_resolution}",
            (255, 255, 255),
        )
        screen.blit(
            resolution_text, resolution_text.get_rect(center=(center_x, 205))
        )
        buttons["resolution"] = pygame.Rect(center_x - 180, 221, 360, 38)
        draw_menu_button(
            screen,
            font,
            "Change Resolution",
            buttons["resolution"],
            mouse_position,
            theme=button_theme,
        )
        skybox_text = render_text(small_font, f"Skybox: {skybox_name}", (255, 255, 255))
        screen.blit(skybox_text, skybox_text.get_rect(center=(center_x, 275)))
        buttons["skybox"] = pygame.Rect(center_x - 180, 291, 360, 38)
        draw_menu_button(
            screen, font, "Change Skybox", buttons["skybox"], mouse_position,
            theme=button_theme,
        )
        button_theme_text = render_text(
            small_font, f"Button Style: {button_theme[0]}", (255, 255, 255)
        )
        screen.blit(
            button_theme_text, button_theme_text.get_rect(center=(center_x, 345))
        )
        buttons["button_theme"] = pygame.Rect(center_x - 180, 361, 360, 38)
        draw_menu_button(
            screen, font, "Change Button Style", buttons["button_theme"],
            mouse_position, theme=button_theme,
        )
        buttons["fullscreen"] = pygame.Rect(center_x - 180, 411, 360, 38)
        draw_menu_button(
            screen,
            font,
            f"Fullscreen: {'On' if fullscreen else 'Off'} (F11)",
            buttons["fullscreen"],
            mouse_position,
            theme=button_theme,
        )
        buttons["apply_resolution"] = pygame.Rect(center_x - 180, 459, 360, 42)
        draw_menu_button(
            screen,
            font,
            f"Apply {display_resolution}",
            buttons["apply_resolution"],
            mouse_position,
            theme=button_theme,
        )
        if resolution_status:
            status_text = render_text(small_font, resolution_status, (190, 220, 190))
            screen.blit(
                status_text, status_text.get_rect(center=(center_x, 512))
            )
        buttons["back"] = pygame.Rect(center_x - 180, 531, 360, 42)
        draw_menu_button(
            screen, font, "Back", buttons["back"], mouse_position,
            theme=button_theme,
        )
    elif mode == "pause":
        title = render_text(font, "Paused", (255, 255, 255))
        screen.blit(title, title.get_rect(center=(center_x, 175)))
        for name, label, y in (
            ("resume", "Resume", 220),
            ("options", "Options", 280),
            ("main_menu", "Main Menu", 340),
            ("quit", "Quit", 400),
        ):
            buttons[name] = pygame.Rect(center_x - 190, y, 380, 54)
            draw_menu_button(
                screen, font, label, buttons[name], mouse_position, theme=button_theme
            )

    return buttons


def draw_mod_menu(
    screen, font, small_font, enabled, world_color_name="Natural",
    button_theme=BUTTON_THEMES[0],
):
    screen.fill((12, 12, 14))

    panel = pygame.Rect(24, 20, 460, 580)
    pygame.draw.rect(screen, (20, 20, 24), panel, border_radius=10)
    pygame.draw.rect(screen, (95, 95, 105), panel, 2, border_radius=10)
    title = render_text(font, "BLACK CLIENT", (255, 255, 255))
    screen.blit(title, (panel.x + 22, panel.y + 18))
    hint = render_text(small_font, "Shift or Esc to close", (180, 180, 188))
    screen.blit(hint, (panel.x + 22, panel.y + 48))

    buttons = {}
    mouse_position = pygame.mouse.get_pos()
    for index, (key, label) in enumerate(MOD_MENU_OPTIONS):
        rect = pygame.Rect(panel.x + 20, panel.y + 88 + index * 52, panel.width - 40, 46)
        buttons[key] = rect
        active = enabled[key]
        draw_rounded_button(
            screen, rect, button_theme, hovered=rect.collidepoint(mouse_position),
            active=active,
        )
        label_surface = render_text(small_font, label, (245, 245, 248))
        screen.blit(label_surface, (rect.x + 14, rect.y + 12))
        if key == "world_color":
            status = world_color_name
            status_color = (190, 190, 195)
        else:
            status = "ON" if active else "OFF"
            status_color = (155, 235, 170) if active else (190, 190, 195)
        status_surface = render_text(small_font, status, status_color)
        screen.blit(status_surface, status_surface.get_rect(midright=(rect.right - 12, rect.centery)))

    return buttons


def draw_command_box(screen, font, small_font, command_text, status):
    screen.fill((12, 12, 14))
    box = pygame.Rect(24, SCREEN_HEIGHT - 148, SCREEN_WIDTH - 48, 124)
    pygame.draw.rect(screen, (14, 14, 18), box, border_radius=8)
    pygame.draw.rect(screen, (125, 125, 135), box, 2, border_radius=8)
    screen.blit(
        render_text(font, "Command", (255, 255, 255)),
        (box.x + 16, box.y + 10),
    )
    pygame.draw.rect(
        screen, (34, 34, 40), (box.x + 14, box.y + 40, box.width - 28, 32),
        border_radius=4,
    )
    visible_text = command_text or "/"
    screen.blit(
        render_text(small_font, visible_text, (245, 245, 248)),
        (box.x + 22, box.y + 48),
    )
    screen.blit(
        render_text(
            small_font,
            "Suggestions: /gamemode creative    /gamemode survival    /help",
            (185, 185, 195),
        ),
        (box.x + 16, box.y + 80),
    )
    if status:
        screen.blit(
            render_text(small_font, status, (235, 220, 135)),
            (box.x + 16, box.y + 101),
        )


def draw_death_screen(screen, font, small_font, button_theme=BUTTON_THEMES[0]):
    screen.fill((24, 8, 11))
    title_font = pygame.font.SysFont("segoeui", 48, bold=True)
    title = render_text(title_font, "YOU DIED", (235, 72, 72))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 65)))
    subtitle = render_text(small_font, "Your adventure is not over yet.", (220, 205, 205))
    screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 22)))
    buttons = {
        "respawn": pygame.Rect(SCREEN_WIDTH // 2 - 145, SCREEN_HEIGHT // 2 + 20, 290, 50),
        "main_menu": pygame.Rect(SCREEN_WIDTH // 2 - 145, SCREEN_HEIGHT // 2 + 82, 290, 50),
    }
    mouse_position = pygame.mouse.get_pos()
    for key, label in (("respawn", "Respawn"), ("main_menu", "Main Menu")):
        draw_menu_button(
            screen, font, label, buttons[key], mouse_position, theme=button_theme
        )
    return buttons


def draw_inventory_menu(
    screen, font, small_font, inventory, creative_mode, inventory_tab, selected_block,
    selected_slot, button_theme=BUTTON_THEMES[0],
):
    screen.fill((12, 12, 14))
    panel = pygame.Rect(SCREEN_WIDTH // 2 - 270, 70, 540, 460)
    pygame.draw.rect(screen, (22, 22, 27), panel, border_radius=10)
    pygame.draw.rect(screen, (110, 110, 122), panel, 2, border_radius=10)
    title = "Creative Inventory" if creative_mode else "Inventory"
    title_surface = render_text(font, title, (255, 255, 255))
    screen.blit(title_surface, title_surface.get_rect(center=(SCREEN_WIDTH // 2, 105)))

    buttons = {}
    if creative_mode:
        for tab, label, x in (
            ("storage", "Storage", SCREEN_WIDTH // 2 - 165),
            ("blocks", "Blocks", SCREEN_WIDTH // 2 - 50),
            ("items", "Items", SCREEN_WIDTH // 2 + 65),
        ):
            rect = pygame.Rect(x, 130, 130, 36)
            buttons[f"tab_{tab}"] = rect
            draw_rounded_button(
                screen, rect, button_theme,
                hovered=rect.collidepoint(pygame.mouse.get_pos()),
                active=inventory_tab == tab,
            )
            tab_text = render_text(small_font, label, (245, 245, 248))
            screen.blit(tab_text, tab_text.get_rect(center=rect.center))

    showing_blocks = creative_mode and inventory_tab == "blocks"
    showing_items = creative_mode and inventory_tab == "items"
    item_names = (
        tuple(ITEM_COLORS)
        if showing_items
        else tuple(BLOCK_COLORS)
        if showing_blocks or creative_mode
        else (*BLOCK_COLORS, *ITEM_COLORS)
    )
    hint_text = (
        "Choose a block to add it to storage and select it."
        if showing_blocks
        else "Choose an item to add it to storage and select it."
        if showing_items
        else "Choose an item to select it. Esc: close"
    )
    hint = render_text(small_font, hint_text, (190, 190, 200))
    screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 182)))

    for index, item in enumerate(item_names):
        column = index % 5
        row = index // 5
        rect = pygame.Rect(panel.x + 20 + column * 102, panel.y + 145 + row * 104, 92, 90)
        buttons[f"item_{item}"] = rect
        active = item == selected_block
        draw_rounded_button(
            screen, rect, button_theme,
            hovered=rect.collidepoint(pygame.mouse.get_pos()), active=active,
        )
        draw_item_icon(
            screen, item, pygame.Rect(rect.x + 31, rect.y + 10, 30, 30)
        )
        name = render_text(small_font, item.replace("_", " ")[:13], (240, 240, 245))
        screen.blit(name, name.get_rect(center=(rect.centerx, rect.y + 52)))
        count = "64+" if showing_blocks or showing_items else str(inventory.get(item, 0))
        if count != "0":
            count_text = render_text(small_font, count, (190, 190, 200))
            screen.blit(count_text, count_text.get_rect(center=(rect.centerx, rect.y + 72)))
    slot_size = 38
    slot_gap = 3
    slots_width = len(HOTBAR) * (slot_size + slot_gap) - slot_gap
    slots_x = SCREEN_WIDTH // 2 - slots_width // 2
    for index, item in enumerate(HOTBAR):
        rect = pygame.Rect(
            slots_x + index * (slot_size + slot_gap), panel.bottom - 48,
            slot_size, slot_size,
        )
        buttons[f"hotbar_{index}"] = rect
        draw_rounded_button(
            screen, rect, button_theme,
            hovered=rect.collidepoint(pygame.mouse.get_pos()),
            active=index == selected_slot,
        )
        draw_hotbar_item_icon(
            screen, item, rect.inflate(-7, -7), inventory, creative_mode
        )
    return buttons


def build_render_rays(render_width, render_height):
    column_offsets = [
        (2.0 * (x + 0.5) / render_width - 1.0)
        * (SCREEN_WIDTH / SCREEN_HEIGHT)
        * math.tan(FIELD_OF_VIEW / 2)
        for x in range(render_width)
    ]
    row_offsets = [
        (1.0 - 2.0 * (y + 0.5) / render_height)
        * math.tan(FIELD_OF_VIEW / 2)
        for y in range(render_height)
    ]
    return column_offsets, row_offsets


def quality_dimensions(quality):
    scale = QUALITY_LEVELS[quality]
    width = max(1, round(SCREEN_WIDTH * scale))
    height = max(1, round(SCREEN_HEIGHT * scale))
    return width, height


def build_render_state(quality, scale=1.0):
    base_width, base_height = quality_dimensions(quality)
    render_width = max(1, round(base_width * scale))
    render_height = max(1, round(base_height * scale))
    render_surface = pygame.Surface((render_width, render_height))
    column_offsets, row_offsets = build_render_rays(render_width, render_height)
    return render_width, render_height, render_surface, column_offsets, row_offsets


def run_game():
    global SCREEN_WIDTH, SCREEN_HEIGHT

    pygame.init()
    SCREEN_WIDTH, SCREEN_HEIGHT = DISPLAY_RESOLUTIONS["1920x1080"]
    fullscreen = True
    display_resolution = "1920x1080"
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN
    )
    SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
    resolution_status = f"Current display: {SCREEN_WIDTH}x{SCREEN_HEIGHT}"
    windowed_resolution = (WINDOWED_WIDTH, WINDOWED_HEIGHT)
    pygame.display.set_caption("Black Client")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("segoeui", 17)
    small_font = pygame.font.SysFont("segoeui", 14)
    blocks, heights = make_world()
    render_grid = build_render_grid(blocks)
    container_blocks = {
        position: block
        for position, block in blocks.items()
        if block in CONTAINER_BLOCKS
    }
    sus_chunks = suspicious_chunks(blocks)
    inventory = new_inventory()
    container_contents = {}
    ender_chest_contents = empty_container()
    carried_contents = {"chest": [], "shulker": []}
    mobs = spawn_mobs(heights, blocks, WORLD_PRESETS["Test"]["seed"])
    arrows = []
    dropped_items = []
    crafting_grid: list[str | None] = [None] * 9
    selected_craft_cell = 0
    recipe_book_open = False
    current_world = "Test"
    selected = 0
    render_distance = 16
    quality = "High"
    active_quality = quality
    render_scale = 0.5
    (
        render_width, render_height, render_surface, column_offsets, row_offsets,
    ) = build_render_state(quality, render_scale)
    menu_mode = "main"
    options_return = "main"
    slider_dragging = False
    mods = {key: False for key, _label in MOD_MENU_OPTIONS}
    mods["world_color"] = False
    world_color_index = len(WORLD_COLORS) - 1
    skybox_index = len(SKYBOXES) - 1
    button_theme_index = 0
    creative_mode = True
    creative_selected_block = "dirt"
    inventory_tab = "blocks"
    inventory_drag_item = None
    inventory_drag_source = None
    command_text = ""
    command_status = ""
    opened_container = None
    last_space_tap = -1000
    creative_flight = False

    player_x, player_z, feet_y = world_spawn(heights)
    velocity_y = 0.0
    on_ground = True
    yaw = 0.8
    pitch = 0.0
    third_person = False
    health = 20
    hunger = 20.0
    hunger_clock = 0.0
    starvation_clock = 0.0
    swing_timer = 0.0
    highest_fall_y = feet_y
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    running = True
    mine_button_held = False
    mining_position = None
    mining_progress = 0.0

    def toggle_fullscreen():
        nonlocal screen, fullscreen, render_width, render_height
        nonlocal render_surface, column_offsets, row_offsets
        global SCREEN_WIDTH, SCREEN_HEIGHT

        fullscreen = not fullscreen
        if fullscreen:
            display_info = pygame.display.Info()
            screen = pygame.display.set_mode(
                (display_info.current_w, display_info.current_h),
                pygame.FULLSCREEN,
            )
        else:
            screen = pygame.display.set_mode(windowed_resolution)
        SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
        (
            render_width, render_height, render_surface, column_offsets, row_offsets,
        ) = build_render_state(quality, render_scale)
        pygame.event.set_grab(menu_mode == "game")
        pygame.mouse.set_visible(menu_mode != "game")

    def apply_display_resolution():
        nonlocal resolution_status
        nonlocal screen, windowed_resolution
        nonlocal render_width, render_height, render_surface, column_offsets, row_offsets
        global SCREEN_WIDTH, SCREEN_HEIGHT

        requested_resolution = DISPLAY_RESOLUTIONS[display_resolution]
        flags = pygame.FULLSCREEN if fullscreen else 0
        screen = pygame.display.set_mode(requested_resolution, flags)
        if not fullscreen:
            windowed_resolution = screen.get_size()
        SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
        if SCREEN_WIDTH == requested_resolution[0] and SCREEN_HEIGHT == requested_resolution[1]:
            resolution_status = f"Applied: {SCREEN_WIDTH}x{SCREEN_HEIGHT}"
        else:
            resolution_status = (
                f"Display set to {SCREEN_WIDTH}x{SCREEN_HEIGHT} "
                f"(requested {requested_resolution[0]}x{requested_resolution[1]})"
            )
        (
            render_width, render_height, render_surface, column_offsets, row_offsets,
        ) = build_render_state(quality, render_scale)

    while running:
        delta_time = min(clock.tick(60) / 1000.0, 0.05)
        place_requested = False
        interact_requested = False
        attack_requested = False
        eat_requested = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                elif menu_mode == "command":
                    if event.key == pygame.K_ESCAPE:
                        menu_mode = "game"
                        pygame.key.stop_text_input()
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                    elif event.key == pygame.K_BACKSPACE:
                        command_text = command_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        command = command_text.strip().lower()
                        if command in ("/gamemode creative", "/gamemode crative"):
                            creative_mode = True
                            health = 20
                            command_status = "Creative mode enabled. Press E for inventory."
                            menu_mode = "game"
                            pygame.key.stop_text_input()
                            pygame.event.set_grab(True)
                            pygame.mouse.set_visible(False)
                        elif command == "/gamemode survival":
                            if current_world == "Test":
                                command_status = "The Test world is always in Creative mode."
                            else:
                                creative_mode = False
                                creative_flight = False
                                inventory = new_inventory()
                                hunger = 20.0
                                creative_selected_block = HOTBAR[0]
                                command_status = "Survival mode enabled."
                            menu_mode = "game"
                            pygame.key.stop_text_input()
                            pygame.event.set_grab(True)
                            pygame.mouse.set_visible(False)
                        elif command == "/help":
                            command_status = "Try /gamemode creative or /gamemode survival."
                            command_text = "/"
                        else:
                            command_status = "Unknown command. Try /help."
                            command_text = "/"
                    elif event.key == pygame.K_SLASH and not command_text:
                        command_text = "/"
                elif event.key == pygame.K_ESCAPE:
                    if menu_mode == "game":
                        menu_mode = "pause"
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                    elif menu_mode == "modmenu":
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                    elif menu_mode == "pause":
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                    elif menu_mode == "options":
                        menu_mode = options_return
                    elif menu_mode == "worlds":
                        menu_mode = "main"
                    elif menu_mode in ("inventory_menu", "crafting"):
                        if menu_mode == "crafting":
                            for ingredient in crafting_grid:
                                if ingredient is not None and not creative_mode:
                                    inventory[ingredient] = inventory.get(ingredient, 0) + 1
                            crafting_grid = [None] * 9
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                    elif menu_mode == "container":
                        menu_mode = "game"
                        opened_container = None
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                elif menu_mode == "game" and event.key == pygame.K_SLASH:
                    menu_mode = "command"
                    command_text = "/"
                    command_status = ""
                    pygame.key.start_text_input()
                    pygame.event.set_grab(False)
                    pygame.mouse.set_visible(True)
                elif menu_mode == "game" and event.key == pygame.K_e:
                    menu_mode = "crafting"
                    pygame.event.set_grab(False)
                    pygame.mouse.set_visible(True)
                elif menu_mode == "game" and event.key == pygame.K_q:
                    drop_inventory_item(
                        inventory, dropped_items, HOTBAR[selected],
                        player_x, feet_y, player_z, yaw, creative_mode,
                    )
                elif event.key == pygame.K_RSHIFT:
                    if menu_mode == "game":
                        menu_mode = "modmenu"
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                    elif menu_mode == "modmenu":
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                elif menu_mode == "game" and event.key in (
                    pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
                    pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0,
                ):
                    hotbar_keys = (
                        pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                        pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8,
                        pygame.K_9, pygame.K_0,
                    )
                    selected = hotbar_keys.index(event.key)
                    if creative_mode and HOTBAR[selected] in BLOCK_COLORS:
                        creative_selected_block = HOTBAR[selected]
                elif menu_mode == "game" and event.key == pygame.K_F5:
                    third_person = not third_person
                elif menu_mode == "game" and event.key == pygame.K_SPACE:
                    now = pygame.time.get_ticks()
                    if creative_mode and now - last_space_tap <= 350:
                        creative_flight = not creative_flight
                        velocity_y = 0
                        last_space_tap = -1000
                    else:
                        last_space_tap = now
                        if not mods["fly"] and not creative_flight and on_ground:
                            velocity_y = JUMP_SPEED
                            on_ground = False
            elif event.type == pygame.TEXTINPUT and menu_mode == "command":
                if event.text == "/" and command_text == "/":
                    continue
                command_text += event.text
            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button in (1, 3)
                and menu_mode != "game"
            ):
                buttons = {}
                if menu_mode == "death":
                    buttons = draw_death_screen(
                        screen, font, small_font, BUTTON_THEMES[button_theme_index]
                    )
                    if event.button == 1 and buttons["respawn"].collidepoint(event.pos):
                        player_x, player_z, feet_y = world_spawn(heights)
                        highest_fall_y = feet_y
                        velocity_y = 0.0
                        on_ground = True
                        health = 20
                        hunger = max(hunger, 6.0)
                        arrows.clear()
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                    elif event.button == 1 and buttons["main_menu"].collidepoint(event.pos):
                        menu_mode = "main"
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                elif menu_mode == "crafting":
                    buttons = draw_crafting_menu(
                        screen, font, small_font, inventory, crafting_grid,
                        selected, selected_craft_cell, creative_mode,
                        recipe_book_open,
                    )
                    if buttons["recipe_book"].collidepoint(event.pos):
                        recipe_book_open = not recipe_book_open
                        continue
                    for index in range(len(HOTBAR)):
                        if buttons[f"hotbar_{index}"].collidepoint(event.pos):
                            selected = index
                            break
                    if event.button == 1:
                        for index in range(9):
                            if buttons[f"craft_{index}"].collidepoint(event.pos):
                                selected_craft_cell = index
                                break
                        if recipe_book_open:
                            for recipe in RECIPE_BOOK:
                                recipe_key = recipe[0]
                                recipe_button = buttons.get(f"recipe_{recipe_key}")
                                if recipe_button is not None and recipe_button.collidepoint(event.pos):
                                    prepare_recipe(
                                        recipe_key, crafting_grid, inventory, creative_mode
                                    )
                                    break
                        else:
                            if buttons["craft_result"].collidepoint(event.pos):
                                craft_item(crafting_grid, inventory)
                            for item in (*BLOCK_COLORS, *ITEM_COLORS):
                                item_button = buttons.get(f"item_{item}")
                                if item_button is None or not item_button.collidepoint(event.pos):
                                    continue
                                if creative_mode or inventory.get(item, 0) > 0:
                                    previous = crafting_grid[selected_craft_cell]
                                    if previous is not None and not creative_mode:
                                        inventory[previous] = inventory.get(previous, 0) + 1
                                    if not creative_mode:
                                        inventory[item] -= 1
                                    crafting_grid[selected_craft_cell] = item
                                break
                    else:
                        if not recipe_book_open:
                            for index in range(9):
                                if buttons[f"craft_{index}"].collidepoint(event.pos):
                                    ingredient = crafting_grid[index]
                                    if ingredient is not None:
                                        if not creative_mode:
                                            inventory[ingredient] = inventory.get(ingredient, 0) + 1
                                        crafting_grid[index] = None
                                    break
                            for item in (*BLOCK_COLORS, *ITEM_COLORS):
                                item_button = buttons.get(f"item_{item}")
                                if item_button is not None and item_button.collidepoint(event.pos):
                                    if creative_mode or inventory.get(item, 0) > 0:
                                        HOTBAR[selected] = item
                                    break
                elif menu_mode == "modmenu":
                    buttons = draw_mod_menu(
                        screen, font, small_font, mods,
                        WORLD_COLORS[world_color_index][0],
                        BUTTON_THEMES[button_theme_index],
                    )
                    for key, rect in buttons.items():
                        if rect.collidepoint(event.pos):
                            if key == "world_color":
                                world_color_index = (world_color_index + 1) % len(WORLD_COLORS)
                            else:
                                mods[key] = not mods[key]
                            break
                elif menu_mode == "crafting":
                    draw_crafting_menu(
                        screen, font, small_font, inventory, crafting_grid,
                        selected, selected_craft_cell, creative_mode,
                        recipe_book_open,
                    )
                elif menu_mode == "inventory_menu":
                    if event.button != 1:
                        continue
                    buttons = draw_inventory_menu(
                        screen, font, small_font, inventory, creative_mode,
                        inventory_tab, creative_selected_block,
                        selected, BUTTON_THEMES[button_theme_index],
                    )
                    if creative_mode:
                        if buttons["tab_storage"].collidepoint(event.pos):
                            inventory_tab = "storage"
                            continue
                        elif buttons["tab_blocks"].collidepoint(event.pos):
                            inventory_tab = "blocks"
                            continue
                        elif buttons["tab_items"].collidepoint(event.pos):
                            inventory_tab = "items"
                            continue
                    inventory_drag_item = None
                    inventory_drag_source = None
                    for index in range(len(HOTBAR)):
                        if buttons[f"hotbar_{index}"].collidepoint(event.pos):
                            inventory_drag_source = index
                            break
                    for item in (*BLOCK_COLORS, *ITEM_COLORS):
                        item_button = buttons.get(f"item_{item}")
                        if item_button is not None and item_button.collidepoint(event.pos):
                            if creative_mode or inventory.get(item, 0) > 0:
                                inventory_drag_item = item
                            break
                elif menu_mode == "container":
                    if opened_container is not None:
                        container_block, container_position = opened_container
                        slots = (
                            ender_chest_contents
                            if container_block == "ender_chest"
                            else container_contents.setdefault(
                                container_position, empty_container()
                            )
                        )
                        buttons = draw_container_menu(
                            screen, font, small_font, container_block, slots,
                            inventory, selected, BUTTON_THEMES[button_theme_index],
                            creative_mode,
                        )
                        for index in range(CONTAINER_SLOT_COUNT):
                            if buttons[f"container_{index}"].collidepoint(event.pos):
                                take_container_item(slots[index], inventory)
                                break
                        else:
                            for index in range(len(HOTBAR)):
                                if buttons[f"hotbar_{index}"].collidepoint(event.pos):
                                    selected = index
                                    store_inventory_item(
                                        slots, HOTBAR[index], inventory, creative_mode
                                    )
                                    break
                else:
                    buttons = draw_menu(
                        screen, font, small_font, menu_mode, render_distance, quality,
                        SKYBOXES[skybox_index][0],
                        BUTTON_THEMES[button_theme_index],
                        fullscreen,
                        display_resolution,
                        resolution_status,
                    )
                if menu_mode == "main":
                    if buttons["single_player"].collidepoint(event.pos):
                        menu_mode = "worlds"
                    elif buttons["options"].collidepoint(event.pos):
                        options_return = "main"
                        menu_mode = "options"
                    elif buttons["quit"].collidepoint(event.pos):
                        running = False
                elif menu_mode == "worlds":
                    selected_world = next(
                        (
                            world_name
                            for world_name in WORLD_PRESETS
                            if buttons[f"world_{world_name.lower()}"].collidepoint(event.pos)
                        ),
                        None,
                    )
                    if selected_world is not None:
                        current_world = selected_world
                        creative_mode = current_world == "Test"
                        if creative_mode:
                            creative_flight = False
                        creative_selected_block = HOTBAR[0]
                        preset = WORLD_PRESETS[selected_world]
                        blocks, heights = make_world(
                            seed=preset["seed"],
                            roughness=preset["roughness"],
                            max_height=preset["max_height"],
                            tree_chance=preset["tree_chance"],
                        )
                        render_grid = build_render_grid(blocks)
                        container_blocks = {
                            position: block
                            for position, block in blocks.items()
                            if block in CONTAINER_BLOCKS
                        }
                        sus_chunks = suspicious_chunks(blocks)
                        mobs = spawn_mobs(heights, blocks, preset["seed"])
                        arrows.clear()
                        dropped_items.clear()
                        crafting_grid = [None] * 9
                        recipe_book_open = False
                        player_x, player_z, feet_y = world_spawn(heights)
                        highest_fall_y = feet_y
                        velocity_y = 0.0
                        health = 20
                        hunger = 20.0
                        hunger_clock = 0.0
                        starvation_clock = 0.0
                        swing_timer = 0.0
                        inventory = new_inventory()
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                    elif buttons["back"].collidepoint(event.pos):
                        menu_mode = "main"
                elif menu_mode == "options":
                    if buttons["distance"].inflate(0, 18).collidepoint(event.pos):
                        slider_dragging = True
                        slider_x = max(
                            buttons["distance"].left,
                            min(buttons["distance"].right - 1, event.pos[0]),
                        )
                        render_distance = 1 + round(
                            (slider_x - buttons["distance"].left)
                            / (buttons["distance"].width - 1) * 99
                        )
                    elif buttons["fullscreen"].collidepoint(event.pos):
                        toggle_fullscreen()
                    elif buttons["quality"].collidepoint(event.pos):
                        quality_names = tuple(QUALITY_LEVELS)
                        quality = quality_names[
                            (quality_names.index(quality) + 1) % len(quality_names)
                        ]
                    elif buttons["resolution"].collidepoint(event.pos):
                        resolution_names = tuple(DISPLAY_RESOLUTIONS)
                        display_resolution = resolution_names[
                            (resolution_names.index(display_resolution) + 1)
                            % len(resolution_names)
                        ]
                        resolution_status = f"Selected: {display_resolution}"
                    elif buttons["skybox"].collidepoint(event.pos):
                        skybox_index = (skybox_index + 1) % len(SKYBOXES)
                    elif buttons["button_theme"].collidepoint(event.pos):
                        button_theme_index = (
                            button_theme_index + 1
                        ) % len(BUTTON_THEMES)
                    elif buttons["apply_resolution"].collidepoint(event.pos):
                        apply_display_resolution()
                    elif buttons["back"].collidepoint(event.pos):
                        menu_mode = options_return
                elif menu_mode == "pause":
                    if buttons["resume"].collidepoint(event.pos):
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                    elif buttons["options"].collidepoint(event.pos):
                        options_return = "pause"
                        menu_mode = "options"
                    elif buttons["main_menu"].collidepoint(event.pos):
                        menu_mode = "main"
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                    elif buttons["quit"].collidepoint(event.pos):
                        running = False
            elif (
                event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
                and menu_mode == "inventory_menu"
            ):
                buttons = draw_inventory_menu(
                    screen, font, small_font, inventory, creative_mode,
                    inventory_tab, creative_selected_block,
                    selected, BUTTON_THEMES[button_theme_index],
                )
                destination = next(
                    (
                        index for index in range(len(HOTBAR))
                        if buttons[f"hotbar_{index}"].collidepoint(event.pos)
                    ),
                    None,
                )
                if inventory_drag_source is not None:
                    if destination is not None:
                        if destination != inventory_drag_source:
                            HOTBAR[inventory_drag_source], HOTBAR[destination] = (
                                HOTBAR[destination], HOTBAR[inventory_drag_source]
                            )
                        selected = destination
                elif inventory_drag_item is not None:
                    item_button = buttons.get(f"item_{inventory_drag_item}")
                    if destination is not None:
                        selected = destination
                        HOTBAR[destination] = inventory_drag_item
                        if creative_mode:
                            inventory[inventory_drag_item] = max(
                                inventory.get(inventory_drag_item, 0), 64
                            )
                            if inventory_drag_item in BLOCK_COLORS:
                                creative_selected_block = inventory_drag_item
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                    elif item_button is not None and item_button.collidepoint(event.pos):
                        HOTBAR[selected] = inventory_drag_item
                        if creative_mode:
                            inventory[inventory_drag_item] = max(
                                inventory.get(inventory_drag_item, 0), 64
                            )
                            if inventory_drag_item in BLOCK_COLORS:
                                creative_selected_block = inventory_drag_item
                        menu_mode = "game"
                        pygame.event.set_grab(True)
                        pygame.mouse.set_visible(False)
                inventory_drag_item = None
                inventory_drag_source = None
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                slider_dragging = False
                mine_button_held = False
            elif (
                event.type == pygame.MOUSEMOTION
                and menu_mode == "options"
                and slider_dragging
            ):
                buttons = draw_menu(
                    screen, font, small_font, menu_mode, render_distance, quality,
                    SKYBOXES[skybox_index][0],
                    BUTTON_THEMES[button_theme_index],
                    fullscreen,
                    display_resolution,
                    resolution_status,
                )
                slider_x = max(
                    buttons["distance"].left,
                    min(buttons["distance"].right - 1, event.pos[0]),
                )
                render_distance = 1 + round(
                    (slider_x - buttons["distance"].left)
                    / (buttons["distance"].width - 1) * 99
                )
            elif event.type == pygame.MOUSEWHEEL and menu_mode == "game":
                selected = (selected - event.y) % len(HOTBAR)
                if creative_mode and HOTBAR[selected] in BLOCK_COLORS:
                    creative_selected_block = HOTBAR[selected]
            elif event.type == pygame.MOUSEMOTION and menu_mode == "game":
                yaw += event.rel[0] * 0.0025
                pitch = max(-1.55, min(1.55, pitch - event.rel[1] * 0.0025))
            elif event.type == pygame.MOUSEBUTTONDOWN and menu_mode == "game":
                if event.button in (4, 5):
                    selected = (selected + (1 if event.button == 5 else -1)) % len(HOTBAR)
                    if creative_mode and HOTBAR[selected] in BLOCK_COLORS:
                        creative_selected_block = HOTBAR[selected]
                elif event.button == 1:
                    has_selected_item = (
                        creative_mode
                        or inventory.get(HOTBAR[selected], 0) > 0
                    )
                    if has_selected_item and tool_family(HOTBAR[selected]) == "sword":
                        attack_requested = True
                    else:
                        mine_button_held = True
                elif event.button == 3:
                    if HOTBAR[selected] in FOOD_ITEMS:
                        eat_requested = True
                    else:
                        interact_requested = True

        if menu_mode != "game":
            if menu_mode == "modmenu":
                draw_mod_menu(
                    screen, font, small_font, mods,
                    WORLD_COLORS[world_color_index][0],
                    BUTTON_THEMES[button_theme_index],
                )
            elif menu_mode == "command":
                draw_command_box(screen, font, small_font, command_text, command_status)
            elif menu_mode == "inventory_menu":
                draw_inventory_menu(
                    screen, font, small_font, inventory, creative_mode,
                    inventory_tab, creative_selected_block,
                    selected, BUTTON_THEMES[button_theme_index],
                )
            elif menu_mode == "crafting":
                draw_crafting_menu(
                    screen, font, small_font, inventory, crafting_grid,
                    selected, selected_craft_cell, creative_mode,
                    recipe_book_open,
                )
            elif menu_mode == "death":
                draw_death_screen(
                    screen, font, small_font, BUTTON_THEMES[button_theme_index]
                )
            elif menu_mode == "container" and opened_container is not None:
                container_block, container_position = opened_container
                slots = (
                    ender_chest_contents
                    if container_block == "ender_chest"
                    else container_contents.setdefault(
                        container_position, empty_container()
                    )
                )
                draw_container_menu(
                    screen, font, small_font, container_block,
                    slots, inventory, selected, BUTTON_THEMES[button_theme_index],
                    creative_mode,
                )
            else:
                draw_menu(
                    screen, font, small_font, menu_mode, render_distance, quality,
                    SKYBOXES[skybox_index][0],
                    BUTTON_THEMES[button_theme_index],
                    fullscreen,
                    display_resolution,
                    resolution_status,
                )
            pygame.display.flip()
            continue

        if quality != active_quality:
            active_quality = quality
            render_scale = 0.5
            (
                render_width, render_height, render_surface, column_offsets,
                row_offsets,
            ) = build_render_state(quality, render_scale)

        keys = pygame.key.get_pressed()
        move_speed = MOVE_SPEED * (2.0 if mods["speed_boost"] else 1.0)
        is_flying = mods["fly"] or creative_flight
        in_water = blocks.get(
            (math.floor(player_x), math.floor(feet_y + 0.1), math.floor(player_z))
        ) == "water"
        if in_water and not is_flying:
            move_speed *= 0.65
        if keys[pygame.K_LSHIFT] and not is_flying:
            move_speed *= 0.3
        if eat_requested and HOTBAR[selected] in FOOD_ITEMS:
            hunger, health, _ate = consume_food(
                inventory, hunger, health, HOTBAR[selected]
            )
        hunger, hunger_clock, starvation_clock, health = advance_hunger(
            hunger, hunger_clock, starvation_clock, health, delta_time, creative_mode
        )
        swing_timer = max(0.0, swing_timer - delta_time)
        forward = float(keys[pygame.K_w] or keys[pygame.K_UP]) - float(
            keys[pygame.K_s] or keys[pygame.K_DOWN]
        )
        strafe = float(keys[pygame.K_d]) - float(keys[pygame.K_a])
        magnitude = math.hypot(forward, strafe)
        if magnitude:
            forward /= magnitude
            strafe /= magnitude
            move_x = (
                math.cos(yaw) * forward - math.sin(yaw) * strafe
            ) * move_speed * delta_time
            move_z = (
                math.sin(yaw) * forward + math.cos(yaw) * strafe
            ) * move_speed * delta_time
            for delta_x, delta_z in ((move_x, 0), (0, move_z)):
                next_x = player_x + delta_x
                next_z = player_z + delta_z
                blocked = player_intersects_blocks(
                    blocks, next_x, feet_y, next_z
                )
                if not blocked:
                    player_x, player_z = next_x, next_z

        if is_flying:
            velocity_y = 0
            vertical_input = float(keys[pygame.K_SPACE]) - float(
                keys[pygame.K_LCTRL]
                or keys[pygame.K_RCTRL]
                or keys[pygame.K_LSHIFT]
            )
            next_feet_y = feet_y + vertical_input * move_speed * delta_time
            if not player_intersects_blocks(
                blocks, player_x, next_feet_y, player_z, leaves_only=True
            ):
                feet_y = next_feet_y
            on_ground = False
        else:
            if in_water and keys[pygame.K_SPACE] and not on_ground:
                velocity_y = max(velocity_y, 2.8)
            if keys[pygame.K_SPACE] and on_ground:
                velocity_y = JUMP_SPEED
                on_ground = False
            velocity_y -= GRAVITY * delta_time * (0.22 if in_water else 1.0)
            next_feet_y = feet_y + velocity_y * delta_time
            if velocity_y > 0 and player_intersects_blocks(
                blocks, player_x, next_feet_y, player_z
            ):
                next_feet_y = feet_y
                velocity_y = 0
            ground_x = math.floor(player_x)
            ground_z = math.floor(player_z)
            ground_block = blocks.get((ground_x, math.floor(next_feet_y), ground_z))
            if velocity_y <= 0 and ground_block is not None and ground_block != "water":
                feet_y = math.floor(next_feet_y) + 1.0
                velocity_y = 0
                on_ground = True
                if (
                    highest_fall_y - feet_y > 4
                    and not mods["god_mode"]
                    and not creative_mode
                ):
                    health = max(0, health - int((highest_fall_y - feet_y - 3) * 2))
                highest_fall_y = feet_y
            else:
                feet_y = next_feet_y
                on_ground = False
                highest_fall_y = max(highest_fall_y, feet_y)
            if feet_y < 1.0:
                feet_y = 1.0
                velocity_y = 0
                on_ground = True
                if not mods["god_mode"] and not creative_mode:
                    health = 0
                highest_fall_y = feet_y
        health = max(
            0,
            health
            - update_mobs(
                mobs, arrows, blocks, heights, player_x, feet_y, player_z,
                delta_time,
            ),
        )
        if health <= 0:
            health = 0
            menu_mode = "death"
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            continue

        for dropped in dropped_items[:]:
            dropped["age"] += delta_time
            dropped["x"] += dropped["vx"] * delta_time
            dropped["z"] += dropped["vz"] * delta_time
            dropped["vx"] *= max(0.0, 1.0 - delta_time * 3.0)
            dropped["vz"] *= max(0.0, 1.0 - delta_time * 3.0)
            dropped["vy"] -= GRAVITY * delta_time
            dropped["y"] += dropped["vy"] * delta_time
            cell_x = max(0, min(WORLD_SIZE - 1, math.floor(dropped["x"])))
            cell_z = max(0, min(WORLD_SIZE - 1, math.floor(dropped["z"])))
            ground_y = heights[(cell_x, cell_z)] + 1.05
            if dropped["y"] <= ground_y:
                dropped["y"] = ground_y
                dropped["vy"] = 0.0
            if (
                dropped["age"] >= 1.0
                and math.dist(
                    (player_x, feet_y + 0.8, player_z),
                    (dropped["x"], dropped["y"], dropped["z"]),
                ) < 1.0
            ):
                inventory[dropped["item"]] = (
                    inventory.get(dropped["item"], 0) + 1
                )
                dropped_items.remove(dropped)

        eye = (player_x, feet_y + PLAYER_HEIGHT, player_z)
        forward_x = math.cos(yaw) * math.cos(pitch)
        forward_z = math.sin(yaw) * math.cos(pitch)
        center_direction = (forward_x, math.sin(pitch), forward_z)
        target = raycast(blocks, eye, center_direction, MAX_REACH)
        if mods["aimbot"]:
            assisted_target, assisted_angles = find_aim_assist_target(
                blocks, eye, yaw, pitch
            )
            if assisted_target is not None:
                target = assisted_target
                yaw, pitch = assisted_angles
        if target is not None and (mine_button_held or mods["auto_mine"]):
            target_position = target[0]
            selected_tool = (
                HOTBAR[selected]
                if creative_mode or inventory.get(HOTBAR[selected], 0) > 0
                else None
            )
            break_time = block_break_time(target[1], selected_tool)
            if break_time is None:
                mining_position = None
                mining_progress = 0.0
            else:
                if mining_position != target_position:
                    mining_position = target_position
                    mining_progress = 0.0
                mining_progress = min(1.0, mining_progress + delta_time / break_time)
        else:
            mining_position = None
            mining_progress = 0.0
        if target is not None:
            target_position, _block, normal, _distance = target
        mob_target = find_target_mob(mobs, eye, yaw, pitch)
        if mob_target is not None and target is not None:
            mob_distance = math.dist(
                eye, (mob_target["x"], mob_target["y"] + 0.7, mob_target["z"])
            )
            if target[3] + 0.25 < mob_distance:
                mob_target = None
        if (
            attack_requested
            and (creative_mode or inventory.get(HOTBAR[selected], 0) > 0)
            and tool_family(HOTBAR[selected]) == "sword"
        ):
            swing_timer = 0.24
            if mob_target is not None:
                damage = 7 if HOTBAR[selected] == "stone_sword" else 5
                hit_mob(mobs, mob_target, inventory, damage)
        if interact_requested and target is not None:
            target_position, target_block, _normal, _distance = target
            if target_block in CONTAINER_BLOCKS:
                opened_container = (target_block, target_position)
                if target_block != "ender_chest":
                    container_contents.setdefault(target_position, empty_container())
                menu_mode = "container"
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)
                draw_container_menu(
                    screen,
                    font,
                    small_font,
                    target_block,
                    ender_chest_contents
                    if target_block == "ender_chest"
                    else container_contents[target_position],
                    inventory,
                    selected,
                    BUTTON_THEMES[button_theme_index],
                    creative_mode,
                )
                pygame.display.flip()
                continue
            place_requested = True

        camera_origin = eye
        if third_person:
            camera_distance = 3.5
            camera_origin = (
                player_x - math.cos(yaw) * camera_distance,
                feet_y + PLAYER_HEIGHT * 0.85,
                player_z - math.sin(yaw) * camera_distance,
            )
            camera_delta = tuple(
                camera_origin[index] - eye[index] for index in range(3)
            )
            camera_length = math.sqrt(sum(value * value for value in camera_delta))
            camera_hit = raycast(
                blocks,
                eye,
                tuple(value / camera_length for value in camera_delta),
                camera_length,
            )
            if camera_hit is not None:
                safe_distance = max(0.15, camera_hit[3] - 0.2)
                camera_origin = tuple(
                    eye[index] + camera_delta[index] / camera_length * safe_distance
                    for index in range(3)
                )

        render_started = time.perf_counter()
        draw_world(
            render_surface,
            render_grid,
            camera_origin,
            yaw,
            pitch,
            column_offsets,
            row_offsets,
            render_distance,
            render_width,
            render_height,
            esp=mods["esp"],
            chest_esp=mods["chest_esp"],
            sus_chunk_finder=mods["sus_chunk_finder"],
            sus_chunks=sus_chunks,
            world_color=WORLD_COLORS[world_color_index][1],
            skybox_color=SKYBOXES[skybox_index][1],
            neon_city=quality == "Ultra" or skybox_index == len(SKYBOXES) - 1,
        )
        render_seconds = time.perf_counter() - render_started
        pygame.transform.smoothscale(
            render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT), screen
        )
        draw_mobs(screen, mobs, camera_origin, yaw, pitch, render_distance)
        draw_arrows(screen, arrows, camera_origin, yaw, pitch, render_distance)
        draw_dropped_items(
            screen, dropped_items, camera_origin, yaw, pitch, render_distance
        )
        if not third_person:
            draw_first_person_item(
                screen,
                HOTBAR[selected]
                if creative_mode or inventory.get(HOTBAR[selected], 0) > 0
                else None,
                swing_timer if tool_family(HOTBAR[selected]) == "sword" else 0.0,
            )
        next_render_scale = render_scale
        if render_seconds > 0.040:
            next_render_scale = max(
                0.25,
                render_scale * math.sqrt(0.025 / render_seconds),
            )
        elif render_seconds < 0.025 and render_scale < 1.0:
            next_render_scale = min(1.0, render_scale * 1.03)
        if abs(next_render_scale - render_scale) >= 0.005:
            render_scale = next_render_scale
            (
                render_width, render_height, render_surface, column_offsets,
                row_offsets,
            ) = build_render_state(quality, render_scale)
        if mods["chest_esp"]:
            draw_through_wall_chest_esp(
                screen, container_blocks, camera_origin, yaw, pitch,
                render_distance, small_font,
            )
        if mods["sus_chunk_finder"]:
            draw_through_wall_chest_esp(
                screen,
                container_blocks,
                camera_origin,
                yaw,
                pitch,
                render_distance,
                small_font,
                marker_color=(255, 25, 25),
                box_scale=1.8,
                tracer=False,
                label_prefix="SUS ",
            )
        draw_hud(
            screen, font, small_font, inventory, selected, target, third_person, health,
            creative_mode, hunger, mining_progress,
        )
        pygame.display.flip()

        if target is not None:
            target_position, block, normal, _distance = target
            if mining_progress >= 1.0 and mining_position == target_position:
                blocks.pop(target_position, None)
                set_render_grid_block(render_grid, target_position, None)
                container_blocks.pop(target_position, None)
                item = "dirt" if block == "grass" else block
                inventory[item] = inventory.get(item, 0) + 1
                mining_position = None
                mining_progress = 0.0
                if block in ("chest", "shulker"):
                    contents = container_contents.pop(
                        target_position, empty_container()
                    )
                    carried_contents[block].append(contents)
                if block in SPECIAL_BLOCKS:
                    sus_chunks = suspicious_chunks(blocks)
            elif place_requested:
                place_position = tuple(
                    target_position[index] + normal[index] for index in range(3)
                )
                chosen = HOTBAR[selected]
                overlaps_player = (
                    player_x - PLAYER_RADIUS < place_position[0] + 1
                    and player_x + PLAYER_RADIUS > place_position[0]
                    and player_z - PLAYER_RADIUS < place_position[2] + 1
                    and player_z + PLAYER_RADIUS > place_position[2]
                    and feet_y < place_position[1] + 1
                    and feet_y + PLAYER_HEIGHT > place_position[1]
                )
                if (
                    chosen in BLOCK_COLORS
                    and place_position not in blocks
                    and (creative_mode or inventory[chosen] > 0)
                    and place_position[1] >= 0
                    and place_position[1] < WORLD_HEIGHT
                    and not overlaps_player
                ):
                    blocks[place_position] = chosen
                    set_render_grid_block(render_grid, place_position, chosen)
                    if chosen in CONTAINER_BLOCKS:
                        container_blocks[place_position] = chosen
                    if not creative_mode:
                        inventory[chosen] -= 1
                    if chosen in ("chest", "shulker"):
                        container_contents[place_position] = (
                            carried_contents[chosen].pop(0)
                            if carried_contents[chosen]
                            else empty_container()
                        )
                    if chosen in SPECIAL_BLOCKS:
                        sus_chunks = suspicious_chunks(blocks)

    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(run_game())
