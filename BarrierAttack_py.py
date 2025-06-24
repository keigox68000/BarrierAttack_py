import pyxel
import math
import random


# --- ゲームの状態管理 ---
class GameState:
    TITLE_DEMO = 0
    AUTO_PLAY_DEMO = 1
    PLAYING = 2
    GAME_OVER = 3


# --- エンティティの定義 ---
class Player:
    def __init__(self):
        self.reset()

    def reset(self, is_demo=False):
        self.x = pyxel.width / 2 - 12
        self.y = pyxel.height - 50
        self.w = 24
        self.h = 16
        self.speed = 3
        self.is_alive = True
        self.respawn_timer = 0
        self.invincibility_timer = 9999 if is_demo else 180  # 60fps * 3s

    def draw(self):
        if not self.is_alive:
            return
        if self.invincibility_timer > 0 and pyxel.frame_count % 10 < 5:
            return
        pyxel.rect(self.x, self.y + 8, 24, 8, 11)
        pyxel.rect(self.x + 4, self.y, 16, 8, 11)
        pyxel.rect(self.x + 10, self.y + 4, 4, 4, 7)


class Station:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 10
        self.y = 30
        self.w = 48
        self.h = 24
        self.is_alive = True

    def draw(self):
        if not self.is_alive:
            return
        pyxel.rect(self.x, self.y + 8, self.w, 8, 13)
        pyxel.rect(self.x + 8, self.y, self.w - 16, 24, 13)
        pyxel.rect(self.x + 20, self.y + 4, 8, 16, 12)


class LargeMissile:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = pyxel.width - 50
        self.y = 30
        self.w = 40
        self.h = 16
        self.speed = 0.5
        self.is_alive = True

    def draw(self):
        if not self.is_alive:
            return
        pyxel.rect(self.x, self.y, self.w, self.h, 10)
        pyxel.rect(self.x - 5, self.y + 4, 5, 8, 8)
        pyxel.rect(self.x + self.w, self.y + 4, 5, 8, 8)


class BarrierAlien:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = pyxel.width / 2
        self.y = 130
        self.w = 20
        self.h = 16
        self.speed = 2.5
        self.direction = 1
        self.is_alive = True

    def draw(self):
        if not self.is_alive:
            return
        pyxel.rect(self.x, self.y, self.w, self.h, 11)
        pyxel.rect(self.x + 4, self.y + 4, 4, 4, 7)
        pyxel.rect(self.x + 12, self.y + 4, 4, 4, 7)


class MinorAlien:
    def __init__(self, index):
        self.original_index = index
        self.spawn_y = 180
        self.reset()

    def reset(self):
        self.x = 10 + self.original_index * 38
        self.y = self.spawn_y
        self.w = 16
        self.h = 16
        self.is_falling = False
        self.fall_speed_y = 0
        self.fall_speed_x = 0

    def draw(self):
        colors = [8, 9, 12, 10, 11, 7]
        color = colors[self.original_index % len(colors)]
        pyxel.rect(self.x, self.y, self.w, self.h, color)


class Bullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.w = 3
        self.h = 9
        self.speed = 8

    def draw(self):
        pyxel.rect(self.x, self.y, self.w, self.h, 7)


class Particle:
    def __init__(self, x, y, options):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        velocity = random.uniform(0, options.get("speed", 4))
        self.vx = math.cos(angle) * velocity
        self.vy = math.sin(angle) * velocity
        self.life = options.get("life", 30) + random.uniform(
            0, options.get("life", 30) * 0.5
        )
        self.start_life = self.life
        self.color = options.get("color", 10)
        self.size = options.get("size", 2)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.life -= 1

    def draw(self):
        if self.life < self.start_life / 3:
            pyxel.pset(self.x, self.y, 1)
        elif self.life < self.start_life * 2 / 3:
            pyxel.pset(self.x, self.y, 6)
        else:
            pyxel.pset(self.x, self.y, self.color)


class App:
    def __init__(self):
        pyxel.init(640, 480, title="Barrier Attack", fps=60)

        # --- サウンドの作成 ---
        self.create_sounds()

        # --- ゲームの状態管理 ---
        self.game_state = GameState.TITLE_DEMO
        self.state_timer = 0
        self.game_over_reason = ""
        self.score = 0
        self.lives = 3

        # --- デモ画面用の設定 ---
        self.demo_phase = 0
        self.demo_timer = 120
        self.demo_walker_x = -20
        self.demo_title_reveal_x = 0
        self.demo_ai_direction = 1
        self.demo_ai_shoot_timer = 0
        self.title_line1 = "BARRIER"
        self.title_line2 = "ATTACK"
        self.title_colors = [
            5,
            8,
            11,
            12,
            9,
            10,
            7,
        ]  # Blue, Red, Green, Cyan, Pink, Yellow, White

        # --- エンティティの初期化 ---
        self.player = Player()
        self.station = Station()
        self.large_missile = LargeMissile()
        self.large_missile_respawn_timer = 0
        self.barrier_alien = BarrierAlien()
        self.minor_aliens = []
        self.minor_alien_count = 16
        self.minor_alien_respawn_timer = 0
        self.bullets = []
        self.particles = []

        # --- バリアの設定 ---
        self.barrier_y = 100
        self.barrier_amplitude = 10
        self.barrier_frequency = 0.2  # (★★★ 修正点) 波長をさらに短く
        self.barrier_thickness = 1
        self.is_barrier_disabled = False
        self.barrier_disabled_timer = 0

        # --- 操作系 ---
        self.can_shoot = True

        self.reset_full_demo()

        pyxel.run(self.update, self.draw)

    def create_sounds(self):
        pyxel.sounds[0].set("c4", "n", "7", "f", 5)
        pyxel.sounds[1].set("c1", "n", "3", "f", 20)
        pyxel.sounds[2].set("a1", "n", "5", "f", 15)
        pyxel.sounds[3].set("g2g1g0g0", "p", "7", "f", 25)
        pyxel.sounds[4].set("c1c0", "n", "7", "f", 30)
        pyxel.sounds[5].set("e2", "p", "6", "f", 10)
        pyxel.sounds[6].set("g2", "p", "6", "f", 10)

    def reset_game(self):
        self.score = 0
        self.lives = 3
        self.can_shoot = True
        self.is_barrier_disabled = False
        self.init_entities()
        self.game_state = GameState.PLAYING

    def init_entities(self, is_for_demo=False):
        self.player.reset(is_for_demo)
        self.station.reset()
        self.large_missile.reset()
        self.barrier_alien.reset()
        self.minor_aliens.clear()
        self.spawn_minor_aliens()
        self.bullets.clear()
        self.particles.clear()

    def reset_full_demo(self):
        self.game_state = GameState.TITLE_DEMO
        self.demo_phase = 0
        self.demo_timer = 120
        self.demo_walker_x = -20

    def start_autoplay_demo(self):
        self.game_state = GameState.AUTO_PLAY_DEMO
        self.init_entities(True)
        self.state_timer = 900
        self.demo_ai_shoot_timer = 60

    def spawn_minor_aliens(self):
        existing_indices = {alien.original_index for alien in self.minor_aliens}
        for i in range(self.minor_alien_count):
            if i not in existing_indices:
                self.minor_aliens.append(MinorAlien(i))

    def create_particle_burst(self, x, y, options):
        count = options.get("count", 10)
        for _ in range(count):
            self.particles.append(Particle(x, y, options))

    def is_colliding(self, rect1, rect2):
        return (
            rect1.x < rect2.x + rect2.w
            and rect1.x + rect1.w > rect2.x
            and rect1.y < rect2.y + rect2.h
            and rect1.y + rect1.h > rect2.y
        )

    def update(self):
        if self.game_state == GameState.TITLE_DEMO:
            self.update_title_demo()
        elif self.game_state == GameState.AUTO_PLAY_DEMO:
            self.update_autoplay_demo()
        elif self.game_state == GameState.PLAYING:
            self.update_playing()
        elif self.game_state == GameState.GAME_OVER:
            self.update_game_over()

        if self.game_state in [GameState.TITLE_DEMO, GameState.AUTO_PLAY_DEMO]:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset_game()

    def update_title_demo(self):
        speed = 2.5
        char_width1 = 32
        total_width = len(self.title_line1) * char_width1
        title_x = (pyxel.width - total_width) / 2

        if self.demo_phase == 0:
            self.demo_timer -= 1
            if self.demo_timer <= 0:
                self.demo_phase = 1
        elif self.demo_phase == 1:
            self.demo_walker_x += speed
            if self.demo_walker_x > 30:
                self.demo_phase = 2
        elif self.demo_phase == 2:
            self.demo_walker_x += speed
            self.demo_title_reveal_x = self.demo_walker_x
            if self.demo_walker_x >= title_x + 100:
                self.demo_phase = 3
        elif self.demo_phase == 3:
            self.demo_walker_x -= speed
            self.demo_title_reveal_x = self.demo_walker_x
            if self.demo_walker_x <= title_x - 60:
                self.demo_phase = 4
        elif self.demo_phase == 4:
            self.demo_walker_x += speed
            self.demo_title_reveal_x = self.demo_walker_x
            if self.demo_walker_x >= title_x + total_width + 30:
                self.demo_phase = 5
        elif self.demo_phase == 5:
            self.demo_walker_x += speed
            if self.demo_walker_x > pyxel.width + 20:
                self.demo_phase = 6
                self.demo_timer = 180
        elif self.demo_phase == 6:
            self.demo_timer -= 1
            if self.demo_timer <= 0:
                self.start_autoplay_demo()

    def update_autoplay_demo(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.reset_full_demo()
            return

        if random.random() < 0.01:
            self.demo_ai_direction *= -1

        self.player.x += self.player.speed * self.demo_ai_direction

        self.demo_ai_shoot_timer -= 1
        if self.demo_ai_shoot_timer <= 0:
            self.bullets.append(
                Bullet(self.player.x + self.player.w / 2 - 2, self.player.y)
            )
            pyxel.play(0, 0)
            self.demo_ai_shoot_timer = 30 + random.random() * 60

        self.update_playing_logic()

    def update_playing(self):
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player.x -= self.player.speed
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player.x += self.player.speed

        if pyxel.btn(pyxel.KEY_CTRL) and self.can_shoot and self.player.is_alive:
            self.bullets.append(
                Bullet(self.player.x + self.player.w / 2 - 2, self.player.y)
            )
            pyxel.play(0, 0)
            self.can_shoot = False

        if not pyxel.btn(pyxel.KEY_CTRL):
            self.can_shoot = True

        if not self.player.is_alive:
            self.player.respawn_timer -= 1
            if self.player.respawn_timer <= 0:
                if self.lives > 0:
                    self.player.is_alive = True
                    self.player.x = pyxel.width / 2 - self.player.w / 2
                    self.player.invincibility_timer = 180
                else:
                    self.set_game_over()
        else:
            if self.player.invincibility_timer > 0:
                self.player.invincibility_timer -= 1

        self.update_playing_logic()

    def update_game_over(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.reset_full_demo()
            return
        self.update_playing_logic(in_game_over=True)

    def update_playing_logic(self, in_game_over=False):
        if self.player.is_alive:
            self.player.x = max(0, min(self.player.x, pyxel.width - self.player.w))

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        for bullet in self.bullets[:]:
            bullet.y -= bullet.speed
            if bullet.y < 0:
                self.bullets.remove(bullet)

        if self.is_barrier_disabled:
            self.barrier_disabled_timer -= 1
            if self.barrier_disabled_timer <= 0:
                self.is_barrier_disabled = False
                if not self.barrier_alien.is_alive:
                    self.barrier_alien.reset()

        if not in_game_over:
            self.update_enemies()
        self.check_collisions()

    def update_enemies(self):
        if self.large_missile.is_alive:
            self.large_missile.x -= self.large_missile.speed
        else:
            self.large_missile_respawn_timer -= 1
            if self.large_missile_respawn_timer <= 0:
                self.large_missile.is_alive = True
                self.large_missile.x = pyxel.width
                self.large_missile.speed += 0.2

        if self.barrier_alien.is_alive:
            self.barrier_alien.x += (
                self.barrier_alien.speed * self.barrier_alien.direction
            )
            if random.random() < 0.02:
                self.barrier_alien.speed = 1.5 + random.random() * 3
            if random.random() < 0.01:
                self.barrier_alien.direction *= -1
            if (
                self.barrier_alien.x < 0
                or self.barrier_alien.x + self.barrier_alien.w > pyxel.width
            ):
                self.barrier_alien.direction *= -1

        self.minor_alien_respawn_timer -= 1
        if self.minor_alien_respawn_timer <= 0:
            self.spawn_minor_aliens()
            self.minor_alien_respawn_timer = 600

        is_player_moving = pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_RIGHT)
        is_demo_or_over = self.game_state in [
            GameState.AUTO_PLAY_DEMO,
            GameState.GAME_OVER,
        ]

        if (is_player_moving or is_demo_or_over) and random.random() < 0.03:
            non_falling_aliens = [a for a in self.minor_aliens if not a.is_falling]
            if non_falling_aliens:
                attacker = random.choice(non_falling_aliens)
                attacker.is_falling = True
                attacker.fall_speed_y = 2.5 + random.random() * 2.5
                attacker.fall_speed_x = (random.random() - 0.5) * 2.5

        for alien in self.minor_aliens[:]:
            if alien.is_falling:
                alien.y += alien.fall_speed_y
                alien.x += alien.fall_speed_x
                if alien.x < 0 or alien.x + alien.w > pyxel.width:
                    alien.fall_speed_x *= -1
                if alien.y > pyxel.height:
                    alien.reset()

    def check_collisions(self):
        is_non_interactive = self.game_state in [
            GameState.AUTO_PLAY_DEMO,
            GameState.GAME_OVER,
        ]

        for b in self.bullets[:]:
            if self.station.is_alive and self.is_colliding(b, self.station):
                if not is_non_interactive:
                    self.set_game_over()
                    return
                self.destroy_station(True)
                continue

            if not self.is_barrier_disabled:
                time = pyxel.frame_count
                dynamic_amplitude = self.barrier_amplitude + 2 * math.sin(time / 20)
                barrier_y_at_bullet = (
                    self.barrier_y
                    + math.sin(b.x * self.barrier_frequency - time / 15.0)
                    * dynamic_amplitude
                )
                if abs(b.y - barrier_y_at_bullet) < self.barrier_thickness + 5:
                    self.create_particle_burst(
                        b.x,
                        barrier_y_at_bullet,
                        {"count": 10, "color": 12, "life": 30, "speed": 2, "size": 2},
                    )
                    pyxel.play(1, 1)
                    self.bullets.remove(b)
                    continue

            if (
                self.large_missile.is_alive
                and self.is_barrier_disabled
                and self.is_colliding(b, self.large_missile)
            ):
                self.create_particle_burst(
                    self.large_missile.x + self.large_missile.w / 2,
                    self.large_missile.y + self.large_missile.h / 2,
                    {"count": 50, "color": 10, "life": 60, "speed": 4, "size": 3},
                )
                if not is_non_interactive:
                    self.score += 500
                pyxel.play(2, 4)
                self.bullets.remove(b)
                self.large_missile.is_alive = False
                self.large_missile_respawn_timer = 180
                continue

            if self.barrier_alien.is_alive and self.is_colliding(b, self.barrier_alien):
                self.create_particle_burst(
                    self.barrier_alien.x + self.barrier_alien.w / 2,
                    self.barrier_alien.y + self.barrier_alien.h / 2,
                    {"count": 30, "color": 11, "life": 42, "speed": 3, "size": 2},
                )
                if not is_non_interactive:
                    self.score += 200
                pyxel.play(1, 5)
                self.is_barrier_disabled = True
                self.barrier_disabled_timer = 180
                self.barrier_alien.is_alive = False
                self.bullets.remove(b)
                continue

            bullet_removed = False
            for m in self.minor_aliens[:]:
                if self.is_colliding(b, m):
                    self.create_particle_burst(
                        m.x + m.w / 2,
                        m.y + m.h / 2,
                        {"count": 20, "color": 9, "life": 30, "speed": 2.5, "size": 2},
                    )
                    self.minor_aliens.remove(m)
                    if not is_non_interactive:
                        self.score += 50
                    pyxel.play(1, 6)
                    self.bullets.remove(b)
                    bullet_removed = True
                    break
            if bullet_removed:
                continue

        if self.player.is_alive and self.player.invincibility_timer <= 0:
            for m in self.minor_aliens[:]:
                if self.is_colliding(self.player, m):
                    if self.game_state == GameState.PLAYING:
                        self.player_hit()
                        self.minor_aliens.remove(m)
                        break
                    elif self.game_state == GameState.AUTO_PLAY_DEMO:
                        self.create_particle_burst(
                            self.player.x + self.player.w / 2,
                            self.player.y + self.player.h / 2,
                            {
                                "count": 80,
                                "color": 8,
                                "life": 78,
                                "speed": 5,
                                "size": 3,
                            },
                        )
                        self.player.x = pyxel.width / 2 - self.player.w / 2
                        self.minor_aliens.remove(m)
                        break

        if (
            self.large_missile.is_alive
            and self.station.is_alive
            and self.is_colliding(self.large_missile, self.station)
        ):
            if is_non_interactive:
                self.destroy_station(True)
            else:
                self.set_game_over()

    def destroy_station(self, is_for_demo=False):
        if not self.station.is_alive:
            return
        self.station.is_alive = False
        pyxel.play(2, 4)
        self.create_particle_burst(
            self.station.x + self.station.w / 2,
            self.station.y + self.station.h / 2,
            {"count": 100, "color": 5, "life": 120, "speed": 6, "size": 4},
        )
        if is_for_demo:
            self.station.is_alive = True
            self.large_missile.x = pyxel.width - 50
        else:
            self.set_game_over()

    def player_hit(self):
        if not self.player.is_alive:
            return
        self.create_particle_burst(
            self.player.x + self.player.w / 2,
            self.player.y + self.player.h / 2,
            {"count": 80, "color": 8, "life": 78, "speed": 5, "size": 3},
        )
        pyxel.play(2, 3)
        self.lives -= 1
        self.player.is_alive = False
        self.player.respawn_timer = 120

    def set_game_over(self):
        if self.game_state == GameState.GAME_OVER:
            return
        self.game_state = GameState.GAME_OVER
        self.state_timer = 300

    def draw(self):
        pyxel.cls(0)

        if self.game_state == GameState.TITLE_DEMO:
            self.draw_demo_screen()
        else:
            self.station.draw()
            self.large_missile.draw()
            self.barrier_alien.draw()
            for alien in self.minor_aliens:
                alien.draw()
            self.player.draw()
            for bullet in self.bullets:
                bullet.draw()
            self.draw_barrier()
            for particle in self.particles:
                particle.draw()
            self.draw_ui()

            if self.game_state == GameState.AUTO_PLAY_DEMO:
                pyxel.text(
                    pyxel.width / 2 - 50, 300, 'PUSH "RETURN"', pyxel.frame_count % 16
                )
            elif self.game_state == GameState.GAME_OVER:
                self.draw_game_over_screen()

    def draw_demo_screen(self):
        title_y1 = 200
        title_y2 = 240
        char_width1 = 32
        total_width = len(self.title_line1) * char_width1
        title_x = (pyxel.width - total_width) / 2

        if 1 <= self.demo_phase < 6:
            pyxel.rect(self.demo_walker_x, 350 + 16, 12, 8, 8)
            pyxel.rect(self.demo_walker_x, 350 + 8, 12, 8, 11)
            pyxel.rect(self.demo_walker_x, 350, 12, 8, 7)

        reveal_width = (
            self.demo_title_reveal_x - title_x
            if self.demo_phase > 1
            else total_width + 100
        )
        char_width2 = total_width / len(self.title_line2)

        for i, char in enumerate(self.title_line1):
            char_x = title_x + i * char_width1
            if char_x < title_x + reveal_width:
                pyxel.text(
                    char_x,
                    title_y1,
                    char,
                    self.title_colors[i % len(self.title_colors)],
                )

        for i, char in enumerate(self.title_line2):
            char_x = title_x + i * char_width2
            if char_x < title_x + reveal_width:
                pyxel.text(
                    char_x,
                    title_y2,
                    char,
                    self.title_colors[(i + 2) % len(self.title_colors)],
                )

    def draw_barrier(self):
        if self.is_barrier_disabled:
            return

        time = pyxel.frame_count

        barrier_colors = [10, 11, 12, 5, 9, 8]
        color_change_speed = 45
        current_color = barrier_colors[
            (time // color_change_speed) % len(barrier_colors)
        ]

        for x in range(pyxel.width):
            dynamic_amplitude = self.barrier_amplitude + 2 * math.sin(time / 20.0)
            # (★★★ 修正点) 流れるスピードを速く
            y = (
                self.barrier_y
                + math.sin(x * self.barrier_frequency - time / 2.0) * dynamic_amplitude
            )

            pyxel.line(
                x,
                y - self.barrier_thickness,
                x,
                y + self.barrier_thickness,
                current_color,
            )

    def draw_ui(self):
        pyxel.text(20, pyxel.height - 20, f"LIVES:{self.lives}", 7)
        score_text = f"SCORE:{self.score}"
        score_width = len(score_text) * 4
        pyxel.text(pyxel.width - score_width - 20, pyxel.height - 20, score_text, 7)

    def draw_game_over_screen(self):
        text = "GAME OVER"
        text_width = len(text) * 4
        pyxel.text(pyxel.width / 2 - text_width / 2, pyxel.height / 2, text, 8)


App()
