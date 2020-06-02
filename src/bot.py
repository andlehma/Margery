import math
import time

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from utils.vec3 import vec3


class Margery(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controller_state = SimpleControllerState()
        self.ball_pos = vec3(0, 0, 0)
        self.defensive_goal = vec3(0, -5120, 0)
        if team == 1:
            self.defensive_goal = vec3(0, 5120, 0)

        self.action = self.kickoff
        self.action_display = "none"

        self.pos = None
        self.yaw = None

        # CONSTANTS
        self.POWERSLIDE_ANGLE = 3

    # Helper Functions
    def aim(self, target: vec3):
        angle_between_bot_and_target = math.atan2(
            target.y - self.pos.y, target.x - self.pos.x)
        angle_front_to_target = angle_between_bot_and_target - self.yaw

        # correct values
        if angle_front_to_target < -math.pi:
            angle_front_to_target += 2 * math.pi
        if angle_front_to_target > math.pi:
            angle_front_to_target -= 2 * math.pi

        self.controller_state.handbrake = abs(
            angle_front_to_target) > self.POWERSLIDE_ANGLE

        # steer
        if angle_front_to_target < math.radians(-10):
            self.controller_state.steer = -1
        elif angle_front_to_target > math.radians(10):
            self.controller_state.steer = 1
        else:
            self.controller_state.steer = 0

    def go_to_location(self, location: vec3, threshold: float, boost: bool):
        distance = self.pos.dist(location)
        if distance > threshold:
            # aim at location
            self.aim(location)

            # drive
            self.controller_state.throttle = 1
            self.controller_state.boost = boost
        else:
            self.controller_state.throttle = 0
            self.controller_state.boost = False

    def check_for_boost_detour(self, location):
        dist_thresh = 100
        distance = self.pos.dist(location)
        for boost_pad in self.field_info.boost_pads:
            dist_to_boost_pad = self.pos.dist(boost_pad.location)
            dist_from_boost_pad_to_location = vec3(
                boost_pad.location).dist(location)
            total_dist = dist_to_boost_pad + dist_from_boost_pad_to_location
            dist_diff = total_dist - distance
            if dist_diff < dist_thresh:
                return boost_pad.location
        return location

    # Actions
    def kickoff(self):
        self.action_display = "kickoff"
        self.go_to_location(vec3(0, 0, 0), 0, True)

    def ballchase(self):
        location = self.check_for_boost_detour(self.ball_pos)
        if location == self.ball_pos:
            self.action_display = "ballchasing"
        else:
            self.action_display = "boost > ball"
        self.go_to_location(location, 0, False)

    def go_to_goal(self):
        location = self.check_for_boost_detour(self.defensive_goal)
        if location == self.defensive_goal:
            self.action_display = "going to goal"
        else:
            self.action_display = "boost > goal"
        self.go_to_location(location, 800, False)

    def boost_detour(self):
        self.action_display = "detouring for boost"

    # Main Loop
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # update information about Margery
        margery = packet.game_cars[self.index]
        self.pos = vec3(margery.physics.location.x,
                        margery.physics.location.y, margery.physics.location.z)
        self.yaw = margery.physics.rotation.yaw

        # update information about the ball
        self.ball_pos = packet.game_ball.physics.location
        ball_is_in_offensive_half = True
        if self.team == 0:  # blue
            if self.ball_pos.y > -10:
                ball_is_in_offensive_half = True
            else:
                ball_is_in_offensive_half = False
        else:  # orange
            if self.ball_pos.y < 10:
                ball_is_in_offensive_half = True
            else:
                ball_is_in_offensive_half = False

        # update information about the field
        self.field_info = self.get_field_info()

        # decision making
        if self.ball_pos.y == 0 and self.ball_pos.x == 0:
            self.action = self.kickoff
        else:
            # go for ball if ball is in offensive half
            # otherwise go to goal
            if ball_is_in_offensive_half:
                self.action = self.ballchase
            else:
                self.action = self.go_to_goal

        # perform the selected action
        self.action()

        # draw debugging information
        draw_debug(self.renderer, margery, self.action_display)

        # output the controller state
        return self.controller_state


def draw_debug(renderer, car, action_display):
    renderer.begin_rendering()
    # print the action that the bot is taking
    renderer.draw_string_3d(car.physics.location, 2, 2,
                            action_display, renderer.white())
    renderer.end_rendering()
