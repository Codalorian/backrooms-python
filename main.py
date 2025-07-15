from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import basic_lighting_shader, lit_with_shadows_shader, normals_shader, transition_shader
import random

class InfiniteProceduralTerrain(Entity):
    def __init__(self):
        super().__init__()

        self.player = FirstPersonController()
        self.player.speed = 5
        self.player.gravity = 0.5

        self.back_ent = Entity(model='cube', collider='box', scale=(10, 10, 10), position=(3, 1, 3))

        self.back_ent.parent = self.player

        self.terrain_tiles = {}
        self.walls = {}

        self.player.position = Vec3(1, 1, 1)
        self.generate_initial_terrain()
        
        # NEW: Clear any walls in initial area to make it safer for potential spawns
        for grid_key in list(self.walls.keys()):
            if abs(grid_key[0]) <= 5 and abs(grid_key[1]) <= 5:  # Initial area
                wall = self.walls[grid_key]
                wall.disable()
                del self.walls[grid_key]

        self.spawn_player_randomly()
        self.generate_ceiling()
        
        # Initialize this to prevent errors in update()
        self.player_position = self.player.world_position

    def generate_initial_terrain(self):
        for x in range(-5, 6):
            for z in range(-5, 6):
                self.generate_terrain_tile(x, z)
                if x % 2 and z % 2 == 0:
                    self.generate_wall(x, z)

    def generate_terrain_tile(self, x, z):
        # If your file is actually PNG, change to 'assets/darkeryellow.png'
        tile = Entity(model='plane', position=Vec3(x * 10, 0, z * 10), scale=25, texture='assets/darkeryellow.jpg')
        tile.collider = 'box'
        ceiling = Entity(model='cube', texture='dy.jpg', position=Vec3(x * 10, 10, z * 10), scale=10)
        ceiling.collider = 'box'
        # Don't overwrite dict - store in a list to avoid losing entities
        light = Entity(model='cube', collider='box', position=Vec3(x * 5, 51, z * 5), scale=5)
        self.terrain_tiles[(x, z)] = [tile, ceiling, light]

    def generate_wall(self, x, z):
        scale_x = random.randint(15, 25)
        scale_z = random.randint(15, 25)
        wall_x = x * 10 + random.uniform(-5, 5)  # Reduced range to minimize overlaps with adjacent tiles
        wall_z = z * 10 + random.uniform(-5, 5)
        wall = Entity(model='cube', texture='tex.jpg', position=Vec3(wall_x, 5, wall_z), scale=(scale_x, 10, scale_z), shader=basic_lighting_shader)
        wall.collider = 'box'
        self.walls[(x, z)] = wall

    def generate_ceiling(self):
        pass

    # Commented out (unused and potentially buggy; uncomment and fix if needed)
    # def generate_ceiling_lights(self):
    #     for x in range(-5, 6):
    #         for z in range(-5, 6):
    #             cube = Entity(model='cube', collider='cube', scale=(10, 1, 10), position=self.player.position, color=color.red)
    #             light = PointLight(parent=self.terrain_tiles[(x, z)], color=color.rgb(255, 255, 255), radius=10, position=(0, 5, 0))
    #             # Don't overwrite dict here - assuming this method is for testing; comment out if not needed
    #             # self.terrain_tiles[(x, z)] = light

    def spawn_player_randomly(self):
        max_attempts = 100  # Prevent infinite loop if something goes wrong
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            
            # Limit range to near initial terrain for safety (expand later if needed, e.g., -100 to 100)
            random_grid_x = random.randint(-5, 5)
            random_grid_z = random.randint(-5, 5)
            
            # Generate terrain and walls around this grid FIRST (5-tile radius for buffer)
            for x in range(random_grid_x - 5, random_grid_x + 6):
                for z in range(random_grid_z - 5, random_grid_z + 6):
                    if (x, z) not in self.terrain_tiles:
                        self.generate_terrain_tile(x, z)
                    if x % 2 == 0 and z % 2 == 0 and (x, z) not in self.walls:  # Your wall gen condition
                        self.generate_wall(x, z)
            
            # If there's a wall in this exact grid, remove it to force a safe spawn
            if (random_grid_x, random_grid_z) in self.walls:
                wall = self.walls[(random_grid_x, random_grid_z)]
                wall.disable()
                del self.walls[(random_grid_x, random_grid_z)]
            
            # Pick a safe position WITHIN the tile (center-ish, away from edges to avoid overlaps)
            tile_center_x = random_grid_x * 10
            tile_center_z = random_grid_z * 10
            safe_offset_x = random.uniform(-4, 4)  # Within -4 to 4 units of center (tile is 10 units)
            safe_offset_z = random.uniform(-4, 4)
            spawn_pos = Vec3(tile_center_x + safe_offset_x, 1, tile_center_z + safe_offset_z)  # y=1 to avoid floor clip
            
            # Optional: Simple check for nearby walls (adjust if still issues)
            safe = True
            for wall_grid, wall in self.walls.items():
                if distance_xz(spawn_pos, wall.position) < 10:  # If too close to any wall
                    safe = False
                    break
            
            if safe:
                self.player.position = spawn_pos
                print(f"Spawned player at {spawn_pos} in grid ({random_grid_x}, {random_grid_z})")
                return  # Exit the method (success)
        
        # Fallback if no safe spot after max attempts (rare)
        print("Warning: Could not find safe spawn after max attempts. Spawning at origin.")
        self.player.position = Vec3(0, 1, 0)

    def update(self):
        new_player_position = self.player.world_position
        if new_player_position != self.player_position:
            self.player_position = new_player_position

            player_grid_x = int(self.player_position.x / 10)
            player_grid_z = int(self.player_position.z / 10)

            for x in range(player_grid_x - 5, player_grid_x + 6):
                for z in range(player_grid_z - 5, player_grid_z + 6):
                    if (x, z) not in self.terrain_tiles:
                        self.generate_terrain_tile(x, z)
                    if x % 2 == 0 and z % 2 == 0 and (x, z) not in self.walls:
                        # NEW: Skip wall gen if it's the player's exact grid
                        if x == player_grid_x and z == player_grid_z:
                            continue
                        self.generate_wall(x, z)
            
            tiles_to_remove = [(x, z) for x, z in self.terrain_tiles.keys() if abs(x - player_grid_x) > 5 or abs(z - player_grid_z) > 5]
            walls_to_remove = [(x, z) for x, z in self.walls.keys() if abs(x - player_grid_x) > 5 or abs(z - player_grid_z) > 5]
            for x, z in tiles_to_remove:
                # Handle list of entities (from our fix)
                for ent in self.terrain_tiles[(x, z)]:
                    ent.disable()
                del self.terrain_tiles[(x, z)]
                
            for x, z in walls_to_remove:
                wall = self.walls[(x, z)]
                wall.disable()
                del self.walls[(x, z)]

def input(key):
    if key == "q" or key == "escape":
        app.close()  # Cleanly shut down Ursina to prevent audio errors
        quit()

app = Ursina()
game = InfiniteProceduralTerrain()

window.size = (864, 1536)  # Fix for win-size warning (adjust to your resolution if different)
window.fullscreen = True

app.run()
