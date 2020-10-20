import os
import math
import pygame
import numpy as np

from followbot.robot_functions.follower_bot import FollowerBot
from followbot.util.basic_geometry import Line, Circle
from followbot.util.cv_importer import *

BLACK_COLOR = (0, 0, 0)
RED_COLOR = (255, 0, 0)
GREEN_COLOR = (0, 255, 0)
BLUE_COLOR = (0, 0, 255)
YELLOW_COLOR = (150, 150, 0)
CYAN_COLOR = (0, 255, 255)
MAGENTA_COLOR = (255, 0, 255)

DARK_GREEN_COLOR = (0, 128, 0)
NAVY_COLOR = (0, 0, 128)
PINK_COLOR = (255, 20, 147)
KHAKI_COLOR = (240, 230, 140)
ORANGE_COLOR = (255, 69, 0)
OLIVE_COLOR = (128, 128, 0)
BLUE_LIGHT = (120, 120, 255)
WHITE_COLOR = (255, 255, 255)


class Visualizer:
    def __init__(self, world, world_dim, win_size=(960, 960), caption='followbot'):
        """
        :param world:  pointer to world object
        :param world_dim:  [[x0, x1], [y0, y1]]
        :param win_size:
        :param caption:
        """
        pygame.init()
        self.world = world
        self.event = None
        self.win = pygame.display.set_mode(win_size)
        self.win.fill([255, 255, 255])
        self.win_size = win_size
        pygame.display.set_caption(caption)

        margin = 0.1

        world_w = world_dim[0][1] - world_dim[0][0]
        world_h = world_dim[1][1] - world_dim[1][0]

        sx = float(win_size[0]) / (world_w * (1 + 2 * margin))
        sy = -float(win_size[1]) / (world_h * (1 + 2 * margin))

        # make sx == sy
        sx = min(sx, abs(sy)); sy = -sx

        self.scale = np.array([[sx, 0], [0, sy]])
        # self.trans = np.array([margin * win_size[0] - world_dim[0][0] * sx,
        #                        margin * win_size[1] - world_dim[1][1] * sy], dtype=np.float)

        self.trans = np.array(self.win_size, dtype=np.float) / 2.

        self.local_time = 0
        self.grid_map = []

    def transform(self, x):
        return self.trans + np.matmul(x, self.scale)

    def draw_circle(self, center, radius, color, width=0):
        center_uv = self.transform(center)
        pygame.draw.circle(self.win, color, (int(center_uv[0]), int(center_uv[1])), radius, width)

    def draw_line(self, p1, p2, color, width=1):
        p1_uv = self.transform(p1)
        p2_uv = self.transform(p2)
        pygame.draw.line(self.win, color, p1_uv, p2_uv, width)

    def draw_lines(self, points, color, width=1):
        if len(points) < 2: return
        points_uv = self.transform(points)
        pygame.draw.lines(self.win, color, False, points_uv, width)

    def update(self):
        if len(self.world.robots):
            self.trans = np.array(self.win_size, dtype=np.float) / 2. - \
                         np.array(self.world.robots[0].pos) * [self.scale[0, 0], self.scale[1, 1]]
        self.local_time += 1
        self.win.fill(WHITE_COLOR)

        # Draw Obstacles
        for obs in self.world.obstacles:
            if isinstance(obs, Line):
                self.draw_line(obs.line[0], obs.line[1], RED_COLOR, 3)
            elif isinstance(obs, Circle):
                self.draw_circle(obs.center, int(obs.radius * self.scale[0, 0]), RED_COLOR, 0)

        # Draw Pedestrians
        for ii in range(len(self.world.crowds)):
            self.draw_circle(self.world.crowds[ii].pos, 10, self.world.crowds[ii].color)
            self.draw_lines(self.world.crowds[ii].trajectory, DARK_GREEN_COLOR, 3)
            if self.world.crowds[ii].biped:
                ped_geo = self.world.crowds[ii].geometry()
                self.draw_circle(ped_geo.center1, 4, CYAN_COLOR)
                self.draw_circle(ped_geo.center2, 4, CYAN_COLOR)

        # Draw robot
        for robot in self.world.robots:
            self.draw_circle(robot.pos, 7, ORANGE_COLOR)
            self.draw_circle(robot.pos, 9, BLACK_COLOR, 3)
            if isinstance(robot, FollowerBot):
                self.draw_circle(robot.leader_ped.pos, 11, PINK_COLOR, 5)
            # draw a vector showing orientation of the robot
            u, v = math.cos(robot.orien) * 0.5, math.sin(robot.orien) * 0.5
            self.draw_line(robot.pos, robot.pos + [u, v], BLUE_COLOR, 3)

            # draw Lidar output as points
            for pnt in robot.lidar.last_range_pnts:
                if math.isnan(pnt[0]) or math.isnan(pnt[1]):
                    print('Error: Nan Value in Lidar data!')
                    raise ValueError
                else:
                    self.draw_circle(pnt, 2, WHITE_COLOR)

            # for seg in robot.lidar_segments:
            #     self.line(seg[0], seg[-1], BLUE_LIGHT, 3)

            for pos in robot.lidar.last_range_pnts:
                self.draw_circle(pos, 2, GREEN_COLOR, 2)

            for det in robot.detected_peds:
                self.draw_circle(det, 14, RED_COLOR, 2)

            for track in robot.tracks:
                if track.coasted: continue
                self.draw_circle(track.position(), 4, YELLOW_COLOR)
                if len(track.recent_detections) >= 2:
                    self.draw_lines(track.recent_detections, ORANGE_COLOR, 1)

            if len(self.world.POM) > 1:
                self.grid_map = np.rot90(self.world.POM.copy().astype(float))  # + self.world.walkable * 0.5)
                cv2.namedWindow('grid', cv2.WINDOW_NORMAL)
                cv2.imshow('grid', self.grid_map)
                cv2.waitKey(2)
                # plt.imshow(self.grid_map)
                # plt.show()

        # pygame.display.flip()
        pygame.display.update()
        pygame.time.delay(10)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                print('Simulation exited by user')
                exit(1)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                click_pnt = np.matmul(np.linalg.inv(self.scale), (pygame.mouse.get_pos() - self.trans))
                # print('- ped:\n\t\tpos_x: %.3f\n\t\tpos_y: %.3f\n\t\torien: 0' % (click_pnt[0], click_pnt[1]))
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    self.scale *= 1.1
                else:
                    self.scale /= 1.1
            if event.type == pygame.KEYDOWN:
                self.event = event.key
            else:
                self.event = None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.world.pause = not self.world.pause

    def save_screenshot(self, dir):
        pygame.image.save(self.win, os.path.join(dir, 'win-%05d.jpg' % self.local_time))
        if len(self.grid_map) > 1:
            cv2.imwrite(os.path.join(dir, 'grid-%05d.png' % self.local_time), self.grid_map * 255)





