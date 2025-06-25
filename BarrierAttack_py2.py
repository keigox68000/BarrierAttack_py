import pyxel
import math
import random
import json


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
        self.x = pyxel.width / 2 - 6  # プレイヤーサイズの半分
        self.y = pyxel.height - 25
        self.w = 12  # 全体的にサイズを半分に
        self.h = 8
        self.speed = 2  # スピードも調整
        self.is_alive = True
        self.respawn_timer = 0
        self.invincibility_timer = 9999 if is_demo else 180  # 60fps * 3s

    def draw(self):
        if not self.is_alive:
            return
        # 無敵時間中の点滅エフェクト
        if self.invincibility_timer > 0 and pyxel.frame_count % 10 < 5:
            return
        pyxel.rect(self.x, self.y + 4, self.w, 4, 11)
        pyxel.rect(self.x + 2, self.y, self.w - 4, 4, 11)
        pyxel.rect(self.x + 5, self.y + 2, 2, 2, 7)


class Station:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 5
        self.y = 15
        self.w = 24
        self.h = 12
        self.is_alive = True

    def draw(self):
        if not self.is_alive:
            return
        pyxel.rect(self.x, self.y + 4, self.w, 4, 13)
        pyxel.rect(self.x + 4, self.y, self.w - 8, 12, 13)
        pyxel.rect(self.x + 10, self.y + 2, 4, 8, 12)


class LargeMissile:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = pyxel.width - 25
        self.y = 15
        self.w = 20
        self.h = 8
        self.speed = 0.25
        self.is_alive = True

    def draw(self):
        if not self.is_alive:
            return
        pyxel.rect(self.x, self.y, self.w, self.h, 10)
        pyxel.rect(self.x - 2, self.y + 2, 2, 4, 8)
        pyxel.rect(self.x + self.w, self.y + 2, 2, 4, 8)


class BarrierAlien:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = pyxel.width / 2
        self.y = 65
        self.w = 10
        self.h = 8
        self.speed = 1.25
        self.direction = 1
        self.is_alive = True

    def draw(self):
        if not self.is_alive:
            return
        pyxel.rect(self.x, self.y, self.w, self.h, 11)
        pyxel.rect(self.x + 2, self.y + 2, 2, 2, 7)
        pyxel.rect(self.x + 6, self.y + 2, 2, 2, 7)


class MinorAlien:
    def __init__(self, index):
        self.original_index = index
        self.spawn_y = 90
        self.reset()

    def reset(self):
        # 解像度に合わせた配置
        self.x = 10 + self.original_index * 19
        self.y = self.spawn_y
        self.w = 8
        self.h = 8
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
        self.w = 2
        self.h = 5
        self.speed = 4

    def draw(self):
        pyxel.rect(self.x, self.y, self.w, self.h, 7)


class Particle:
    def __init__(self, x, y, options):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        velocity = random.uniform(0, options.get("speed", 2))
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
        self.vy += 0.1
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
        # 解像度を320x240に変更
        pyxel.init(320, 240, title="Barrier Attack", fps=60)

        # (★★★ 修正点) BGMと効果音の管理方法を刷新
        self.music_data = None
        self.se_channel = 1  # 効果音はチャンネル2を使用
        self.se_is_playing = False  # SEが再生中かどうかのフラグ

        try:
            with open("musics/bapy.json", "rt") as fin:
                self.music_data = json.loads(fin.read())
        except Exception as e:
            print(f"BGMファイル 'musics/bapy.json' が読み込めませんでした: {e}")

        self.create_sfx()  # 効果音を定義

        self.game_state = GameState.TITLE_DEMO
        self.state_timer = 0
        self.score = 0
        self.lives = 3

        self.demo_phase = 0
        self.demo_timer = 120
        self.demo_walker_x = -20
        self.demo_title_reveal_x = 0
        self.demo_ai_direction = 1
        self.demo_ai_shoot_timer = 0
        self.title_line1 = "BARRIER"
        self.title_line2 = "ATTACK"
        self.title_colors = [5, 8, 11, 12, 9, 10, 7]

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

        # バリアのY座標を調整
        self.barrier_y = 50
        self.barrier_amplitude = 5
        self.barrier_frequency = 0.4
        self.barrier_thickness = 1
        self.is_barrier_disabled = False
        self.barrier_disabled_timer = 0

        self.can_shoot = True
        self.reset_full_demo()
        pyxel.run(self.update, self.draw)

    def create_sfx(self):
        # 効果音をサウンド番号30番以降に定義
        pyxel.sounds[30].set("c4", "n", "7", "f", 5)  # 発射
        pyxel.sounds[31].set("c1", "n", "3", "f", 20)  # バリア衝突
        pyxel.sounds[32].set("g2g1g0g0", "p", "7", "f", 25)  # プレイヤー被弾
        pyxel.sounds[33].set("c1c0", "n", "7", "f", 30)  # 大きい爆発
        pyxel.sounds[34].set("e2", "p", "6", "f", 10)  # 敵ヒット
        pyxel.sounds[35].set("g2", "p", "6", "f", 10)  # 小さいヒット

    def play_bgm(self):
        """BGMを再生する"""
        if self.music_data:
            # チャンネル0,1,3をBGM用に再生
            for ch, sound_data in enumerate(self.music_data):
                pyxel.sounds[ch].set(*sound_data)
                if ch != self.se_channel:
                    pyxel.play(ch, ch, loop=True)
            # SEチャンネルも、対応するBGMサウンドで再生開始
            pyxel.play(self.se_channel, self.se_channel, loop=True)

    def play_se(self, sound_no):
        """効果音を割り込み再生する"""
        pyxel.play(self.se_channel, sound_no, loop=False)
        self.se_is_playing = True

    def update_bgm_resume(self):
        """SE再生後にBGMを復帰させる"""
        # SE再生中フラグが立っており、かつSEチャンネルが再生を終えたら
        if self.se_is_playing and pyxel.play_pos(self.se_channel) is None:
            self.se_is_playing = False
            # BGMの再生位置を取得 (チャンネル0を基準とする)
            tick = pyxel.play_pos(0)[1] if pyxel.play_pos(0) else 0
            # SEチャンネルでBGMをtickの位置から復帰
            pyxel.play(self.se_channel, self.se_channel, tick=tick, loop=True)

    def reset_game(self):
        self.score = 0
        self.lives = 3
        self.can_shoot = True
        self.is_barrier_disabled = False
        self.init_entities()
        self.game_state = GameState.PLAYING
        self.play_bgm()

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
        pyxel.stop()

    def start_autoplay_demo(self):
        self.game_state = GameState.AUTO_PLAY_DEMO
        self.init_entities(True)
        self.state_timer = 900
        self.demo_ai_shoot_timer = 60
        self.play_bgm()  # デモでもBGMを再生

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
        # BGM復帰処理を毎フレーム確認
        if (
            self.game_state == GameState.PLAYING
            or self.game_state == GameState.AUTO_PLAY_DEMO
        ):
            self.update_bgm_resume()

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
        speed = 1.25
        char_width1 = 16
        total_width = len(self.title_line1) * char_width1
        title_x = (pyxel.width - total_width) / 2

        if self.demo_phase == 0:
            self.demo_timer -= 1
            if self.demo_timer <= 0:
                self.demo_phase = 1
        elif self.demo_phase == 1:
            self.demo_walker_x += speed
            if self.demo_walker_x > 15:
                self.demo_phase = 2
        elif self.demo_phase == 2:
            self.demo_walker_x += speed
            self.demo_title_reveal_x = self.demo_walker_x
            if self.demo_walker_x >= title_x + 50:
                self.demo_phase = 3
        elif self.demo_phase == 3:
            self.demo_walker_x -= speed
            self.demo_title_reveal_x = self.demo_walker_x
            if self.demo_walker_x <= title_x - 30:
                self.demo_phase = 4
        elif self.demo_phase == 4:
            self.demo_walker_x += speed
            self.demo_title_reveal_x = self.demo_walker_x
            if self.demo_walker_x >= title_x + total_width + 15:
                self.demo_phase = 5
        elif self.demo_phase == 5:
            self.demo_walker_x += speed
            if self.demo_walker_x > pyxel.width + 10:
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
        self.player.x = max(0, min(self.player.x, pyxel.width - self.player.w))

        self.demo_ai_shoot_timer -= 1
        if self.demo_ai_shoot_timer <= 0:
            self.bullets.append(
                Bullet(self.player.x + self.player.w / 2 - 1, self.player.y)
            )
            self.play_se(30)
            self.demo_ai_shoot_timer = 30 + random.random() * 60

        self.update_world()

    def update_playing(self):
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player.x -= self.player.speed
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player.x += self.player.speed

        self.player.x = max(0, min(self.player.x, pyxel.width - self.player.w))

        if pyxel.btn(pyxel.KEY_CTRL) and self.can_shoot and self.player.is_alive:
            self.bullets.append(
                Bullet(self.player.x + self.player.w / 2 - 1, self.player.y)
            )
            self.play_se(30)
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

        self.update_world()

    def update_game_over(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.reset_full_demo()
            return

        self.update_world()

    def update_world(self):
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
                self.large_missile.speed += 0.1

        if self.barrier_alien.is_alive:
            self.barrier_alien.x += (
                self.barrier_alien.speed * self.barrier_alien.direction
            )
            if random.random() < 0.02:
                self.barrier_alien.speed = 1 + random.random() * 2
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
                attacker.fall_speed_y = 1.25 + random.random() * 1.25
                attacker.fall_speed_x = (random.random() - 0.5) * 1.25

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
                self.destroy_station(is_non_interactive)
                self.bullets.remove(b)
                return
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
                    self.play_se(31)
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
                self.play_se(33)
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
                self.play_se(34)
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
                    self.play_se(35)
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
            self.destroy_station(is_non_interactive)
            return

    def destroy_station(self, is_for_demo=False):
        if not self.station.is_alive:
            return
        self.station.is_alive = False
        self.play_se(33)
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
        self.play_se(32)
        self.lives -= 1
        self.player.is_alive = False
        self.player.respawn_timer = 120

    def set_game_over(self):
        if self.game_state == GameState.GAME_OVER:
            return
        self.game_state = GameState.GAME_OVER
        self.state_timer = 300
        pyxel.stop()

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
                    pyxel.width / 2 - 25, 150, 'PUSH "RETURN"', pyxel.frame_count % 16
                )
            elif self.game_state == GameState.GAME_OVER:
                self.draw_game_over_screen()

    def draw_demo_screen(self):
        title_y1, title_y2 = 100, 120
        char_width1 = 16
        total_width = len(self.title_line1) * char_width1
        title_x = (pyxel.width - total_width) / 2
        if 1 <= self.demo_phase < 6:
            walker_y = 175
            pyxel.rect(self.demo_walker_x, walker_y + 8, 6, 4, 8)
            pyxel.rect(self.demo_walker_x, walker_y + 4, 6, 4, 11)
            pyxel.rect(self.demo_walker_x, walker_y, 6, 4, 7)
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
            y = (
                self.barrier_y
                + math.sin(x * self.barrier_frequency - time / 1.5) * dynamic_amplitude
            )
            pyxel.line(
                x,
                y - self.barrier_thickness,
                x,
                y + self.barrier_thickness,
                current_color,
            )

    def draw_ui(self):
        pyxel.text(10, pyxel.height - 10, f"LIVES:{self.lives}", 7)
        score_text = f"SCORE:{self.score}"
        score_width = len(score_text) * 4
        pyxel.text(pyxel.width - score_width - 10, pyxel.height - 10, score_text, 7)

    def draw_game_over_screen(self):
        text = "GAME OVER"
        text_width = len(text) * 4
        pyxel.text(pyxel.width / 2 - text_width / 2, pyxel.height / 2, text, 8)


App()
