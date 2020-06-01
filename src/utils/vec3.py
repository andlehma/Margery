import math

class vec3:
    def __init__(self, x: float or 'vec3' = 0, y: float = 0, z: float = 0):
        if hasattr(x, 'x'):
            # copy constructor
            self.x = float(x.x)
            self.y = float(x.y) if hasattr(x, 'y') else 0
            self.z = float(x.z) if hasattr(x, 'z') else 0
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    def __add__(self, other: 'vec3'):
        return vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'vec3'):
        return vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __str__(self):
        return "vec3(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ")"

    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def dist(self, other: 'vec3'):
        return (self - other).length()