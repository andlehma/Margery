import math
import time

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from utils.vec3 import vec3

SIN45 = math.sin(0.785398)


class Margery(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controller_state = SimpleControllerState()
        self.ball_pos = vec3(0, 0, 0)
        self.defensive_goal = vec3(0, -5120, 0)
        self.offensive_goal = vec3(0, 5120, 0)
        if team == 1:
            self.defensive_goal = vec3(0, 5120, 0)
            self.offensive_goal = vec3(0, -5120, 0)

        self.action = self.kickoff
        self.action_display = "none"

        self.pos = None
        self.yaw = None

        self.next_dodge_time = 0
        self.on_second_jump = False

        # CONSTANTS
        self.POWERSLIDE_ANGLE = 3  # radians
        self.TURN_THRESHOLD = 5  # degrees
        self.DODGE_THRESHOLD = 300  # unreal units
        self.DODGE_TIME = 0.2  # seconds
        self.BALL_FAR_AWAY_DISTANCE = 1500

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
        if angle_front_to_target < math.radians(-self.TURN_THRESHOLD):
            self.controller_state.steer = -1
        elif angle_front_to_target > math.radians(self.TURN_THRESHOLD):
            self.controller_state.steer = 1
        else:
            self.controller_state.steer = 0

        self.controller_state.pitch = 0

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

    def check_for_boost_detour(self, location: vec3):
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
    
    def normalize_location(self, location: vec3):
        # these values can and should be tweaked
        # walls are at +- 4196 (x) and +- 5120 (y)
        arena_max_x = 4196 - 93 # wall x - ball radius
        arena_min_x = -arena_max_x
        arena_max_y = 5120 - 93 # wall y - ball radius
        arena_min_y = -arena_max_y
        output_location = vec3(location)
        if location.x < arena_min_x:
            output_location.x = arena_min_x
        elif location.x > arena_max_x:
            output_location.x = arena_max_x
        if location.y < arena_min_y:
            output_location.y = arena_min_y
        elif location.y > arena_max_y:
            output_location.y = arena_max_y
        return output_location

    # Actions
    def kickoff(self):
        self.action_display = "kickoff"
        dist_to_ball = self.pos.dist(self.ball_pos)
        if dist_to_ball > 500:
            if self.team == 0:
                self.go_to_location(
                    self.check_for_boost_detour(vec3(0, -300, 0)), 0, True)
            else:
                self.go_to_location(
                    self.check_for_boost_detour(vec3(0, 300, 0)), 0, True)
        else:
            self.ballchase()
        # TODO: implement faster kickoffs

    def dodge(self, direction: vec3):
        if time.time() > self.next_dodge_time:
            # get pitch and yaw values from angle to ball
            angle_between_bot_and_target = math.atan2(
                direction.y - self.pos.y, direction.x - self.pos.x)
            angle_front_to_target = angle_between_bot_and_target - self.yaw
            self.controller_state.pitch = -math.cos(angle_front_to_target)
            self.controller_state.yaw = math.sin(angle_front_to_target)

            # correct pitch values
            if self.controller_state.pitch < -SIN45:
                self.controller_state.pitch = -1
            elif self.controller_state.pitch > SIN45:
                self.controller_state.pitch = 1
            else:
                self.controller_state.pitch = 0

            self.controller_state.jump = True

            if self.on_second_jump:
                self.on_second_jump = False
            else:
                self.on_second_jump = True
                self.next_dodge_time = time.time() + self.DODGE_TIME

    def ballchase(self):
        # check if we are goalside
        goalside = False
        if self.team == 0:
            if self.pos.y < self.ball_pos.y:
                goalside = True
        else:
            if self.pos.y > self.ball_pos.y:
                goalside = True

        # choose next action based on how far away from the ball we are
        dist_to_ball = self.pos.dist(self.ball_pos)
        if dist_to_ball < self.DODGE_THRESHOLD and goalside:
            # dodge into ball
            self.action_display = "shooting"
            self.dodge(self.ball_pos)
        elif dist_to_ball <= self.DODGE_THRESHOLD * 2 and goalside:
            # face ball before dodging
            self.action_display = "setting up to shoot"
            self.aim(self.ball_pos)
            self.controller_state.throttle = 0.5
        else:
            # we are either too far away from the ball or not goalside
            boost = False
            if dist_to_ball > self.BALL_FAR_AWAY_DISTANCE:
                boost = True
            ball_angle_to_goal = math.atan2(
                self.offensive_goal.y - self.ball_pos.y,
                self.offensive_goal.x - self.ball_pos.x)
            ball_distance_to_goal = self.ball_pos.dist(self.offensive_goal)
            dist_plus = ball_distance_to_goal + (self.DODGE_THRESHOLD * 2)
            x = self.offensive_goal.x - \
                (math.cos(ball_angle_to_goal) * dist_plus)
            y = self.offensive_goal.y - \
                (math.sin(ball_angle_to_goal) * dist_plus)
            goalside_position = vec3(x, y, 0)
            location = self.check_for_boost_detour(goalside_position)
            if location == goalside_position:
                self.action_display = "ballchasing"
            else:
                self.action_display = "boost > ball"
            location = self.normalize_location(location)
            self.go_to_location(location, 0, boost)

    def go_to_goal(self):
        location = self.check_for_boost_detour(self.defensive_goal)
        threshold = 800
        if location == self.defensive_goal:
            self.action_display = "going to goal"
        else:
            self.action_display = "boost > goal"
            threshold = 50
        location = self.normalize_location(location)
        self.go_to_location(location, threshold, False)

    # Main Loop
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # update information about Margery
        margery = packet.game_cars[self.index]
        self.pos = vec3(margery.physics.location)
        self.yaw = margery.physics.rotation.yaw
        self.pitch = margery.physics.rotation.pitch

        # update information about the ball
        self.ball_pos = vec3(packet.game_ball.physics.location)
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
                #self.action = self.go_to_goal
                self.action = self.ballchase

        # reset dodge
        self.controller_state.jump = False

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
