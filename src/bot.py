import math

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from utils.vec3 import vec3


class Margery(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controller_state = SimpleControllerState()

        self.action_display = "none"

        self.pos = None
        self.yaw = None

    def aim(self, target: vec3):
        angle_between_bot_and_target = math.atan2(
            target.y - self.pos.y, target.x - self.pos.x)
        angle_front_to_target = angle_between_bot_and_target - self.yaw

        # correct values
        if angle_front_to_target < -math.pi:
            angle_front_to_target += 2 * math.pi
        if angle_front_to_target > math.pi:
            angle_front_to_target -= 2 * math.pi

        # steer
        if angle_front_to_target < math.radians(-10):
            self.controller_state.steer = -1
        elif angle_front_to_target > math.radians(10):
            self.controller_state.steer = 1
        else:
            self.controller_state.steer = 0

    def go_to_location(self, location: vec3, ball: vec3, threshold: float):
        distance = self.pos.dist(location)
        if distance > threshold:

            # aim at location
            self.aim(location)

            # drive
            self.controller_state.throttle = 1
        else:
            # if we're waiting at location, aim at the ball
            self.controller_state.throttle = 0
            self.aim(ball)

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # update information about Margery
        margery = packet.game_cars[self.index]
        self.pos = vec3(margery.physics.location.x,
                        margery.physics.location.y, margery.physics.location.z)
        self.yaw = margery.physics.rotation.yaw
        self.team = margery.team
        defensive_goal = vec3(0, -5120, 0)
        if self.team == 1:
            defensive_goal = vec3(0, 5120, 0)

        # update information about the ball
        ball_pos = packet.game_ball.physics.location
        ball_is_in_offensive_half = True
        if self.team == 0: # blue
            if ball_pos.y > -10:
                ball_is_in_offensive_half = True
            else:
                ball_is_in_offensive_half = False
        else: # orange
            if ball_pos.y < 10:
                ball_is_in_offensive_half = True
            else:
                ball_is_in_offensive_half = False

        # go for ball if ball is in offensive half
        # otherwise go to goal
        if ball_is_in_offensive_half:
            self.action_display = "going for ball"
            self.go_to_location(ball_pos, ball_pos, 0)
        else:
            self.action_display = "going to goal"
            self.go_to_location(defensive_goal, ball_pos, 800)

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
