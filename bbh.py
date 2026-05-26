import pygame
import math
import sys
import random

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
WIDTH, HEIGHT = 1280, 720
FPS = 60

# Colors
BG_COLOR = (5, 5, 10)
# More glowy, high-intensity whitish-blue grid color
MESH_COLOR = (180, 220, 255) 
WAVE_COLOR = (40, 80, 120)
# Clear Blue Light Disc Color as requested
ACCRETION_BLUE = (0, 180, 255)  
WHITE = (255, 255, 255)
TEXT_COLOR = (220, 230, 245)      # Brighter off-white for body text readability
BOX_BG = (8, 12, 28, 235)         # Deeper, high-contrast dark blue for lesson box

# Physics & Display Parameters
GRID_SPACING = 30
GRAVITY_STRENGTH = 1500
WAVE_SPEED = 15
WAVE_FREQUENCY = 0.05

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def create_glow_surface(radius, color, max_alpha=150):
    """Creates a surface with a radial gradient for additive blending glows."""
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        # Calculate alpha based on distance from center
        alpha = int(max_alpha * (1 - (r / radius)**1.5))
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), r)
    return surf

# ==========================================
# CLASSES
# ==========================================
class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime, size):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.initial_lifetime = lifetime
        self.lifetime = lifetime
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt

    def draw(self, surface):
        if self.lifetime > 0:
            alpha = max(0, int(255 * (self.lifetime / self.initial_lifetime)))
            # Create a tiny glowing particle
            color_with_alpha = (*self.color, alpha)
            pygame.draw.circle(surface, color_with_alpha, (int(self.x), int(self.y)), self.size)

class SpacetimeMesh:
    def __init__(self, width, height, spacing):
        self.spacing = spacing
        self.cols = (width // spacing) + 4
        self.rows = (height // spacing) + 4
        self.offset_x = -spacing * 2
        self.offset_y = -spacing * 2

    def draw(self, surface, masses, center_of_mass, time_elapsed, is_merged):
        distorted_points = []
        
        # Calculate distorted positions for every grid point
        for r in range(self.rows):
            row_points = []
            for c in range(self.cols):
                basex = self.offset_x + c * self.spacing
                basey = self.offset_y + r * self.spacing
                
                dx, dy = 0, 0
                # Gravitational Lensing / Well Pull
                for mass_x, mass_y, mass_val in masses:
                    dist_x = mass_x - basex
                    dist_y = mass_y - basey
                    dist = math.hypot(dist_x, dist_y)
                    if dist > 5:
                        pull = (mass_val * GRAVITY_STRENGTH) / (dist**2)
                        # Limit maximum pull to avoid messy line overlapping
                        pull = min(pull, self.spacing * 1.2) 
                        dx += (dist_x / dist) * pull
                        dy += (dist_y / dist) * pull

                # Gravitational Ripples (Waves)
                if not is_merged:
                    cm_dist = math.hypot(center_of_mass[0] - basex, center_of_mass[1] - basey)
                    wave_amp = max(0, 15 - cm_dist * 0.01) # Waves decay over distance
                    wave_val = wave_amp * math.sin(cm_dist * WAVE_FREQUENCY - time_elapsed * WAVE_SPEED)
                    if cm_dist > 10:
                        dx += (basex - center_of_mass[0]) / cm_dist * wave_val
                        dy += (basey - center_of_mass[1]) / cm_dist * wave_val
                else:
                    # Post merger, waves radiate outwards and die off
                    cm_dist = math.hypot(center_of_mass[0] - basex, center_of_mass[1] - basey)
                    ring_radius = time_elapsed * WAVE_SPEED * 40
                    dist_to_ring = abs(cm_dist - ring_radius)
                    if dist_to_ring < 150:
                        wave_amp = 20 * (1 - dist_to_ring/150) * max(0, 1 - time_elapsed/5)
                        wave_val = wave_amp * math.sin(cm_dist * WAVE_FREQUENCY * 2)
                        dx += (basex - center_of_mass[0]) / max(cm_dist, 1) * wave_val
                        dy += (basey - center_of_mass[1]) / max(cm_dist, 1) * wave_val

                row_points.append((basex + dx, basey + dy))
            distorted_points.append(row_points)

        # Draw the grid lines
        for r in range(self.rows):
            for c in range(self.cols):
                px, py = distorted_points[r][c]
                # Horizontal lines
                if c < self.cols - 1:
                    pygame.draw.line(surface, MESH_COLOR, (px, py), distorted_points[r][c+1])
                # Vertical lines
                if r < self.rows - 1:
                    pygame.draw.line(surface, MESH_COLOR, (px, py), distorted_points[r+1][c])


class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Binary Black Hole Merger Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier New", 18, bold=True)
        # Dedicated fonts for educational commentary
        self.lecture_title_font = pygame.font.SysFont("Courier New", 16, bold=True)
        self.lecture_body_font = pygame.font.SysFont("Courier New", 14, bold=True)
        
        # State: INSPIRAL, MERGER, REMNANT, HAWKING
        self.state = "INSPIRAL"
        self.time_scale = 1.0
        self.time_elapsed = 0.0
        self.state_timer = 0.0
        
        self.mesh = SpacetimeMesh(WIDTH, HEIGHT, GRID_SPACING)
        
        # Binary system parameters
        self.center_x = WIDTH // 2
        self.center_y = HEIGHT // 2
        self.orbit_radius = 280.0
        self.angle = 0.0
        self.bh_mass = 20
        self.bh_radius = 35 # Increased from 18 to make them look larger and clearer
        
        # Single Mega BH parameters
        self.mega_bh_pos = [0, 0]
        self.mega_bh_vel = [0, 0]
        self.mega_bh_radius = 0
        self.mega_bh_mass = 0

        # Rendering aids
        self.trail_points = [] # Stores (x1, y1, x2, y2)
        self.particles = []
        self.flash_alpha = 0
        
        # Pre-calculate glows for performance
        self.blue_glow = create_glow_surface(75, ACCRETION_BLUE, 180) # Sized up to match larger bh_radius
        self.mega_glow = None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.time_scale = min(5.0, self.time_scale + 0.2)
                elif event.key == pygame.K_DOWN:
                    self.time_scale = max(0.1, self.time_scale - 0.2)
                elif event.key == pygame.K_SPACE:
                    # Reset simulation
                    self.__init__()

    def update(self, dt):
        scaled_dt = dt * self.time_scale
        self.time_elapsed += scaled_dt
        
        if self.state == "INSPIRAL":
            # Physics of Inspiral (Simplified)
            # As radius decreases, angular velocity increases dramatically
            angular_velocity = 800 / (self.orbit_radius ** 1.5) 
            self.angle += angular_velocity * scaled_dt
            
            # RADIUS DECAY: Calibrated to trigger merger (at orbit_radius <= 52.5)
            # precisely at 25.0 seconds of simulation time.
            shrink_rate = 1512.88 / max(self.orbit_radius, 1.0)
            self.orbit_radius -= shrink_rate * scaled_dt
            
            # Calculate positions
            x1 = self.center_x + math.cos(self.angle) * self.orbit_radius
            y1 = self.center_y + math.sin(self.angle) * self.orbit_radius
            x2 = self.center_x - math.cos(self.angle) * self.orbit_radius
            y2 = self.center_y - math.sin(self.angle) * self.orbit_radius
            
            self.current_masses = [(x1, y1, self.bh_mass), (x2, y2, self.bh_mass)]
            
            # Add to trails
            self.trail_points.append((x1, y1, x2, y2))
            if len(self.trail_points) > 150:
                self.trail_points.pop(0)
                
            # Check for Merger (bh_radius * 1.5 = 52.5)
            if self.orbit_radius <= self.bh_radius * 1.5:
                self.state = "MERGER"
                self.state_timer = 0
                # Setup Remnant
                self.mega_bh_pos = [self.center_x, self.center_y]
                self.mega_bh_radius = self.bh_radius * 1.6 # Scales up proportionally
                self.mega_bh_mass = self.bh_mass * 1.8 # Loss of mass to energy
                self.mega_glow = create_glow_surface(120, ACCRETION_BLUE, 200) # Proportional concentrated glow
                # Recoil Kick
                kick_angle = random.uniform(0, math.pi * 2)
                self.mega_bh_vel = [math.cos(kick_angle) * 15, math.sin(kick_angle) * 15]
                
                # Humongous Light Flash Explosion
                self.flash_alpha = 255
                for _ in range(300):
                    p_angle = random.uniform(0, math.pi * 2)
                    p_speed = random.uniform(100, 800)
                    self.particles.append(Particle(
                        self.center_x, self.center_y, 
                        math.cos(p_angle) * p_speed, math.sin(p_angle) * p_speed,
                        WHITE, random.uniform(0.5, 2.0), random.randint(2, 6)
                    ))
                    
        elif self.state == "MERGER":
            # The Flash and Recoil phase
            self.state_timer += dt # Real time, not scaled, for UI flash
            self.mega_bh_pos[0] += self.mega_bh_vel[0] * scaled_dt
            self.mega_bh_pos[1] += self.mega_bh_vel[1] * scaled_dt
            
            # Slowly decelerate recoil (friction against space for visual sake)
            self.mega_bh_vel[0] *= 0.98
            self.mega_bh_vel[1] *= 0.98
            
            self.current_masses = [(self.mega_bh_pos[0], self.mega_bh_pos[1], self.mega_bh_mass)]
            
            # Fade flash
            if self.flash_alpha > 0:
                self.flash_alpha -= 150 * dt
            
            if self.state_timer > 4.0:
                self.state = "HAWKING"
                
        elif self.state == "HAWKING":
            # Scenery of Hawking Radiation
            self.current_masses = [(self.mega_bh_pos[0], self.mega_bh_pos[1], self.mega_bh_mass)]
            self.mega_bh_pos[0] += self.mega_bh_vel[0] * scaled_dt
            self.mega_bh_pos[1] += self.mega_bh_vel[1] * scaled_dt
            self.mega_bh_vel[0] *= 0.99
            self.mega_bh_vel[1] *= 0.99
            
            # Emit radiation particles from the event horizon (ambient blue particles)
            if self.mega_bh_mass > 0:
                for _ in range(int(2 * self.time_scale) + 1):
                    p_angle = random.uniform(0, math.pi * 2)
                    # Start slightly outside event horizon
                    px = self.mega_bh_pos[0] + math.cos(p_angle) * (self.mega_bh_radius + 2)
                    py = self.mega_bh_pos[1] + math.sin(p_angle) * (self.mega_bh_radius + 2)
                    p_speed = random.uniform(10, 50)
                    self.particles.append(Particle(
                        px, py, 
                        math.cos(p_angle) * p_speed, math.sin(p_angle) * p_speed,
                        ACCRETION_BLUE, random.uniform(1.0, 3.0), random.randint(1, 3)
                    ))
                
                # Emit White Relativistic Jet Particles shooting vertically (Sleeker, narrower alignment)
                for _ in range(int(6 * self.time_scale) + 1):
                    # Upward jet
                    up_x = self.mega_bh_pos[0] + random.uniform(-2, 2)
                    up_y = self.mega_bh_pos[1] - self.mega_bh_radius
                    self.particles.append(Particle(
                        up_x, up_y,
                        random.uniform(-10, 10), random.uniform(-400, -800),
                        (255, 255, 255), random.uniform(0.4, 0.9), random.randint(2, 4)
                    ))
                    # Downward jet
                    down_x = self.mega_bh_pos[0] + random.uniform(-2, 2)
                    down_y = self.mega_bh_pos[1] + self.mega_bh_radius
                    self.particles.append(Particle(
                        down_x, down_y,
                        random.uniform(-10, 10), random.uniform(400, 800),
                        (255, 255, 255), random.uniform(0.4, 0.9), random.randint(2, 4)
                    ))
                
                # Shrink slowly
                shrink_rate = 0.5
                self.mega_bh_mass = max(0, self.mega_bh_mass - shrink_rate * scaled_dt)
                self.mega_bh_radius = max(0, self.mega_bh_radius - (shrink_rate/2) * scaled_dt)
                if self.mega_bh_radius > 0:
                    self.mega_glow = create_glow_surface(int(self.mega_bh_radius * 3), ACCRETION_BLUE, 200)

        # Update all particles
        for p in self.particles[:]:
            p.update(scaled_dt)
            if p.lifetime <= 0:
                self.particles.remove(p)

    def draw_commentary_box(self):
        """Draws a beautiful teacher/classroom commentary overlay with high-attention pulsing text."""
        # Define box position and size
        box_width = 1100
        box_height = 125
        box_x = (WIDTH - box_width) // 2
        box_y = HEIGHT - box_height - 20

        # Generate a high-attention pulsing factor using a sine wave over elapsed time
        # This creates a breathing neon-like glow effect on text titles and borders.
        pulse = (math.sin(self.time_elapsed * 4.0) + 1) / 2  # Cycles smoothly between 0.0 and 1.0
        
        # Striking Attention-Grabbing Colors
        neon_yellow = (255, 220 + int(35 * pulse), 0)        # Bright gold to hot yellow
        neon_orange = (255, 90 + int(60 * pulse), 10)         # Sizzling energetic orange
        neon_cyan = (0, 195 + int(60 * pulse), 255)          # Dynamic high-contrast cyan

        # Determine lesson content based on current simulation state
        if self.state == "INSPIRAL":
            lesson_title = "🔭 COSMIC LESSON: INSPIRAL DANCE & GRAVITATIONAL WAVES"
            title_color = neon_cyan
            lesson_lines = [
                "Two black holes orbit each other in a death spiral. As they churn through spacetime,",
                "they emit ripples called Gravitational Waves, which travel across the cosmos at light speed.",
                "These waves carry away orbital energy, forcing the pair to draw closer and accelerate."
            ]
        elif self.state == "MERGER":
            lesson_title = "💥 COSMIC LESSON: THE COLLISION & MASS-ENERGY CONVERSION"
            title_color = neon_orange
            lesson_lines = [
                "The event horizons touch! This is the violent Merger phase. The physical disruption",
                "is extreme: a massive portion of their starting physical mass is completely disintegrated,",
                "converted directly into pure gravitational energy waves as predicted by Einstein's E=mc²."
            ]
        elif self.state == "HAWKING":
            # If the black hole is still relatively large, describe remnant. If shrinking, describe Hawking.
            if self.mega_bh_mass > 12:
                lesson_title = "🪐 COSMIC LESSON: NEW BLACK HOLE REMNANT & KICK VELOCITY"
                title_color = neon_cyan
                lesson_lines = [
                    "Merger complete! A brand new, larger supermassive black hole has been successfully born.",
                    "Due to asymmetrical energy release during collision, the remnant receives a recoil 'kick' through space.",
                    "The surrounding light disc stabilizes, and hyper-energetic white relativistic jets shoot from its poles."
                ]
            else:
                lesson_title = "🧪 COSMIC LESSON: HAWKING EVAPORATION (QUANTUM VACUUM DECAY)"
                title_color = neon_yellow
                lesson_lines = [
                    f"Notice the event horizon shrinking! (Mass: {self.mega_bh_mass:.1f}/36.0). Quantum virtual particle pairs",
                    "separate near the event horizon: one particle (with negative energy) is sucked into the singularity,",
                    "while its partner escapes as Hawking Radiation. This process slowly drains the black hole's mass-energy."
                ]

        # Draw the main translucent box surface
        box_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, BOX_BG, (0, 0, box_width, box_height), border_radius=10)
        
        # Pulsing glowing border (blends between accretion blue and current title color)
        border_glow = (
            int(ACCRETION_BLUE[0] * (1 - pulse) + title_color[0] * pulse),
            int(ACCRETION_BLUE[1] * (1 - pulse) + title_color[1] * pulse),
            int(ACCRETION_BLUE[2] * (1 - pulse) + title_color[2] * pulse)
        )
        pygame.draw.rect(box_surf, border_glow, (0, 0, box_width, box_height), 2, border_radius=10)
        self.screen.blit(box_surf, (box_x, box_y))

        # Render the pulsing high-attention Title
        title_surf = self.lecture_title_font.render(lesson_title, True, title_color)
        self.screen.blit(title_surf, (box_x + 24, box_y + 14))

        # Render the lesson content
        for idx, line in enumerate(lesson_lines):
            # To highlight key physical concepts, let's render the text in ultra-crisp white/off-white
            line_surf = self.lecture_body_font.render(line, True, TEXT_COLOR)
            self.screen.blit(line_surf, (box_x + 24, box_y + 44 + idx * 22))

    def draw(self):
        self.screen.fill(BG_COLOR)
        
        # 1. Draw Spacetime Mesh
        if self.state == "INSPIRAL":
            self.mesh.draw(self.screen, self.current_masses, (self.center_x, self.center_y), self.time_elapsed, False)
        else:
            self.mesh.draw(self.screen, self.current_masses, self.mega_bh_pos, self.state_timer, True)

        # Additive blending surface for Glows, Jets, and Trails
        blend_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        
        # 2. Draw Trails (The "Dance")
        if self.state == "INSPIRAL" and len(self.trail_points) > 2:
            for i in range(len(self.trail_points) - 1):
                alpha = int(255 * (i / len(self.trail_points)))
                color = (*ACCRETION_BLUE[:2], 255, alpha)
                p1_curr, p2_curr = self.trail_points[i][:2], self.trail_points[i][2:]
                p1_next, p2_next = self.trail_points[i+1][:2], self.trail_points[i+1][2:]
                pygame.draw.line(blend_surface, color, p1_curr, p1_next, 2)
                pygame.draw.line(blend_surface, color, p2_curr, p2_next, 2)

        # 3. Draw Relativistic Jets (Hawking Radiation) on blend surface in HAWKING state
        if self.state == "HAWKING" and self.mega_bh_radius > 0:
            # Render a beautifully sleek, narrow vertical white jet beam
            jet_width = 6 # Set to a sharp, thin, highly focused beam width (reduced from fat radius multiplier)
            for w in range(jet_width, 0, -2):
                alpha = int(120 * (1 - (w / jet_width)**2))
                # Draw vertical column
                pygame.draw.rect(blend_surface, (235, 245, 255, alpha), 
                                 (int(self.mega_bh_pos[0] - w), 0, w * 2, HEIGHT))
                # Stronger central white laser core
                pygame.draw.rect(blend_surface, (255, 255, 255, int(alpha * 1.5)), 
                                 (int(self.mega_bh_pos[0] - w//2), 0, max(1, w), HEIGHT))

        # 4. Draw Accretion Disks (Revolving Blue Light) on blend surface
        if self.state == "INSPIRAL":
            for x, y, m in self.current_masses:
                # Clear blue base glow
                glow_rect = self.blue_glow.get_rect(center=(x, y))
                blend_surface.blit(self.blue_glow, glow_rect.topleft)
                
                # REVOLVING BLUE LIGHT DISC ELEMENTS
                # Orbiting light streams representing relativistic orbiting light
                num_streaks = 8
                for j in range(num_streaks):
                    angle_offset = (j * (math.pi * 2 / num_streaks)) + (self.time_elapsed * 8.0)
                    dist = self.bh_radius + 4 + (j % 3) * 3
                    lx = x + math.cos(angle_offset) * dist
                    ly = y + math.sin(angle_offset) * dist
                    # Draw bright revolving light blob
                    pygame.draw.circle(blend_surface, (150, 230, 255, 200), (int(lx), int(ly)), 3)
                    # Draw a trailing light line
                    lx_tail = x + math.cos(angle_offset - 0.2) * dist
                    ly_tail = y + math.sin(angle_offset - 0.2) * dist
                    pygame.draw.line(blend_surface, (0, 150, 255, 100), (int(lx), int(ly)), (int(lx_tail), int(ly_tail)), 2)
        
        elif self.state in ["MERGER", "HAWKING"]:
            if self.mega_bh_radius > 0:
                # Mega clear blue glow
                if self.mega_glow:
                    glow_rect = self.mega_glow.get_rect(center=(self.mega_bh_pos[0], self.mega_bh_pos[1]))
                    blend_surface.blit(self.mega_glow, glow_rect.topleft)
                
                # REVOLVING BLUE LIGHT DISC ELEMENTS for the Mega Black Hole
                num_streaks = 12
                for j in range(num_streaks):
                    angle_offset = (j * (math.pi * 2 / num_streaks)) + (self.time_elapsed * 6.0)
                    dist = self.mega_bh_radius + 6 + (j % 4) * 4
                    lx = self.mega_bh_pos[0] + math.cos(angle_offset) * dist
                    ly = self.mega_bh_pos[1] + math.sin(angle_offset) * dist
                    pygame.draw.circle(blend_surface, (150, 230, 255, 220), (int(lx), int(ly)), 4)
                    lx_tail = self.mega_bh_pos[0] + math.cos(angle_offset - 0.15) * dist
                    ly_tail = self.mega_bh_pos[1] + math.sin(angle_offset - 0.15) * dist
                    pygame.draw.line(blend_surface, (0, 150, 255, 120), (int(lx), int(ly)), (int(lx_tail), int(ly_tail)), 3)

        # 5. Draw Particles (Flash & Jet Sparks)
        for p in self.particles:
            p.draw(blend_surface)

        # Blit the additive blending surface onto the main screen
        self.screen.blit(blend_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # 6. DRAW THE EVENT HORIZONS (Solid black circles) AFTER the additive blit.
        # This guarantees they remain completely dark black without blue glow bleed inside.
        if self.state == "INSPIRAL":
            for x, y, m in self.current_masses:
                # Event Horizon (Draw completely black)
                pygame.draw.circle(self.screen, (0, 0, 0), (int(x), int(y)), self.bh_radius)
                # Photon ring (White edge outline)
                pygame.draw.circle(self.screen, WHITE, (int(x), int(y)), self.bh_radius, 1)
        
        elif self.state in ["MERGER", "HAWKING"]:
            if self.mega_bh_radius > 0:
                # Event Horizon (Draw completely black)
                pygame.draw.circle(self.screen, (0, 0, 0), (int(self.mega_bh_pos[0]), int(self.mega_bh_pos[1])), int(self.mega_bh_radius))
                # Photon ring (White edge outline)
                pygame.draw.circle(self.screen, WHITE, (int(self.mega_bh_pos[0]), int(self.mega_bh_pos[1])), int(self.mega_bh_radius), 2)

        # 7. The Humongous Light Flash overlay
        if self.flash_alpha > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT))
            flash_surf.fill(WHITE)
            flash_surf.set_alpha(int(self.flash_alpha))
            self.screen.blit(flash_surf, (0, 0))

        # 8. UI Text
        ui_texts = [
            f"State: {self.state}",
            f"Time Dilator: {self.time_scale:.1f}x",
            "Controls: UP/DOWN arrow to scale time, SPACE to restart"
        ]
        
        for i, text in enumerate(ui_texts):
            txt_surf = self.font.render(text, True, TEXT_COLOR)
            self.screen.blit(txt_surf, (20, 20 + i * 25))

        # 9. Draw Dynamic Commentary Dashboard
        self.draw_commentary_box()

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
            # Cap dt to prevent massive jumps if window is moved
            if dt > 0.1: dt = 0.1 
            
            self.handle_events()
            self.update(dt)
            self.draw()

# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    sim = Simulation()
    sim.run()
