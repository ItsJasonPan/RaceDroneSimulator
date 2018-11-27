from panda3d.core import WindowProperties
from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionTraverser, CollisionNode, CollisionBox
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import Filename, AmbientLight, DirectionalLight
from panda3d.core import PandaNode, TextNode, Point3
from pandac.PandaModules import*
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
import random
import sys
import math

# Function to put instructions on the screen.
# this function is modified based on an example provided by Panda3d – Roaming Ralph 
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(0, 200, 50, 1), scale=.05,
        parent=base.a2dTopLeft, pos=(0.08, -pos - 0.04), align=TextNode.ALeft)


class RaceDrone(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # initalize the window
        base.disableMouse()
        self.win.setClearColor((0, 0, 0, 1))
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setSize(1700,1000)
        base.win.requestProperties(props)

        # store keys
        self.keyMap = {
            "left": 0, "right": 0, "forward": 0, "backward": 0, 
            "drift-left": 0, "drift-right": 0, "up": 0, "down": 0,
            "restart": 0, "firstPerson": 0, "gravity": 0}

        #instructions
        self.ins2 = addInstructions(0.12, "[Left/Right Arrow]: Rotate Left/Right")
        self.ins3 = addInstructions(0.18, "[Up/Down Arrow]: Fly Forward/Backward")
        self.ins4 = addInstructions(0.24, "[A, D]: Move Camera")
        self.ins5 = addInstructions(0.30, "[W, S]: Lift / Descent")
        self.ins6 = addInstructions(0.36, "[F]: Toggle First Person/ Third Person")
        self.ins7 = addInstructions(0.42, "[G]: Toggle Gravity")
        self.ins8 = addInstructions(0.48, "[R]: Restart")

        # Set up the playground
        # other maps:
        # models/toon/phase_15/hood/toontown_central.bam
        # models/world
        # CS_Map/myCSMAP.egg

        self.environ = loader.loadModel("phase_15/hood/toontown_central.bam")
        self.environ.setScale(1.5)
        self.environ.reparentTo(render)
        self.mapScale = 2
        #self.sky = loader.loadModel("phase_3.5/models/props/BR_sky.bam")
        #self.sky.setScale(1.5)
        #self.sky.reparentTo(render)
        # Create drone and initalize drone position
        self.Drone = Actor("models/mydrone.egg")
        self.Drone.reparentTo(render)

        # resize and reposition the drone
        self.Drone.setScale(.1)
        self.Drone.setPos(5,5,8)
        self.Drone.setH(180)
        # initial position is saved for restarting the game
        self.DroneStartPos = self.Drone.getPos()


        # User Controls
        self.accept('escape', __import__('sys').exit, [0])
        self.accept("arrow_left", self.setKey, ["left", True])
        self.accept("arrow_right", self.setKey, ["right", True])
        self.accept("arrow_up", self.setKey, ["forward", True])
        self.accept("arrow_down", self.setKey, ["backward", True])
        self.accept("a", self.setKey, ["drift-left", True])
        self.accept("d", self.setKey, ["drift-right", True])
        self.accept("arrow_left-up", self.setKey, ["left", False])
        self.accept("arrow_right-up", self.setKey, ["right", False])
        self.accept("arrow_up-up", self.setKey, ["forward", False])
        self.accept("arrow_down-up", self.setKey, ["backward", False])
        self.accept("a-up", self.setKey, ["drift-left", False])
        self.accept("d-up", self.setKey, ["drift-right", False])
        self.accept("w", self.setKey, ["up", True])
        self.accept("w-up", self.setKey, ["up", False])
        self.accept("s", self.setKey, ["down", True])
        self.accept("s-up", self.setKey, ["down", False])
        self.accept("r", self.setKey, ["restart", True])
        self.accept("r-up", self.setKey, ["restart", False])
        self.accept("f", self.setKey, ["firstPerson", True])
        self.accept("f-up", self.setKey, ["firstPerson", False])
        self.accept("g", self.setKey, ["gravity", True])
        self.accept("g-up", self.setKey, ["gravity", False])

        taskMgr.add(self.move, "moveTask")

        # Disable Mouse
        self.disableMouse()

        # Camera settings
        self.cameraDistance = 5
        self.cameraPitch = -10

        # create the collision box for the drone 
        # this collision box will be used for collision detection
        self.droneBox = CollisionBox((0,0,2.5), 3, 3, 0.7)
        self.cnodePath = self.Drone.attachNewNode(CollisionNode('cnode'))
        self.cnodePath.node().addSolid(self.droneBox)

        # collision detection set up
        self.cTrav = CollisionTraverser()
        self.queue = CollisionHandlerQueue()
        self.cTrav.addCollider(self.cnodePath, self.queue)
        self.cTrav.traverse(render)


        # Lighting portion are modified from an example provided by Panda3d – Roaming Ralph 
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((1, 1, 1, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection((-5, -5, -5))
        directionalLight.setColor((1, 1, 1, 1))
        directionalLight.setSpecularColor((1, 1, 1, 1))
        render.setLight(render.attachNewNode(ambientLight))
        render.setLight(render.attachNewNode(directionalLight))

        # Crashed Text
        self.crashed = OnscreenText()
        self.firstPerson = False

        # HPR setting
        self.angle = 0
        self.angleChange = 0.5
        self.maxAngle = 15

        # Speed Control
        self.FBSpeed = self.mapScale * 6
        self.LRSpeed = self.mapScale * 4
        self.turnSpeed = 80
        self.liftSpeed = self.mapScale * 80
        self.downSpeed = self.mapScale * 80


        # AI set up
        self.AI = False
        if self.AI:
            self.droneAI = Actor("models/mydrone.egg")
            self.droneAI.reparentTo(render)
            self.droneAI.setScale(.1)
            self.droneAI.setPos(5,5,5)
            self.AI_actions = open("AI/RoamingRalph/AI_easy.txt", "r").readlines()

        #######################
        # additional features #
        #######################

        # acceleration
        self.FBacceleration = 0
        self.LRacceleration = 0
        self.accelMax = 40
        self.accelIncrement = 2

        # gravity 
        self.gravity = True
        self.gravity_value = 15


    # Record user inputs
    def setKey(self, key, value):
        self.keyMap[key] = value


    # Main Function (Deal with user interface and collision detection)
    def move(self, task):

        #debug
        #print(self.drone.getPos())
        #print(self.FBacceleration, self.LRacceleration)

        # crash message
        self.crashed.destroy()
        self.crashed = OnscreenText(text="Crashed!!!" if len(self.queue.getEntries()) != 0 else "", pos = (-0.5, 0.02), 
                                scale = 0.07, mayChange = True, fg = (255,255,255,1))

        # Get the time that elapsed since last frame.  
        dt = globalClock.getDt()


        # control the movement of AI
        if self.AI:
            if self.AI_actions != []:
                curAction = self.AI_actions[0].split(" ")
                self.droneAI.setX(float(curAction[0]))
                self.droneAI.setY(float(curAction[1]))
                self.droneAI.setZ(float(curAction[2]))
                self.droneAI.setH(float(curAction[3]))
                self.droneAI.setP(float(curAction[4]))
                self.droneAI.setR(float(curAction[5]))
                self.AI_actions.pop(0)

        # Drone is movable only when it's not crashed
        if len(self.queue.getEntries()) == 0:

            # initial height
            curHeight = self.Drone.getZ()

            # move by acceleration
            if self.FBacceleration != 0:
                self.Drone.setX(self.Drone, self.FBSpeed * self.FBacceleration * dt)
                self.FBacceleration += 1 if self.FBacceleration < 0 else -1
            if self.LRacceleration != 0:
                self.Drone.setY(self.Drone, self.LRSpeed * self.LRacceleration * dt)
                self.LRacceleration += 1 if self.LRacceleration < 0 else -1
                self.Drone.setZ(curHeight)

            # tilting while drift left and right
            if self.keyMap["drift-left"]:
                #self.Drone.setY(self.Drone, self.LRSpeed * dt)
                # tilt left when drift left
                if self. angle > -self.maxAngle:
                    self.angle -= self.angleChange
                self.Drone.setP(self.angle)
                if self.LRacceleration < self.accelMax:
                    self.LRacceleration += self.accelIncrement
            elif self.keyMap["drift-right"]:
                #self.Drone.setY(self.Drone, -self.LRSpeed * dt)
                # tilt right when drift right
                if self. angle < self.maxAngle:
                    self.angle += self.angleChange
                self.Drone.setP(self.angle)
                if self.LRacceleration > -self.accelMax:
                    self.LRacceleration -= self.accelIncrement
            # gradually stablize itself while drift-keys are not pressed
            else:
                if self.angle >=self.angleChange:
                    self.angle -= self.angleChange
                elif self.angle <=-self.angleChange:
                    self.angle +=self.angleChange
                self.Drone.setP(self.angle)

            # turn left
            if self.keyMap["left"]:
                self.Drone.setH(self.Drone.getH() + self.turnSpeed * dt)
            # turn right
            if self.keyMap["right"]:
                self.Drone.setH(self.Drone.getH() - self.turnSpeed * dt)

            # go forward
            if self.keyMap["forward"]:
                #self.Drone.setX(self.Drone, self.FBSpeed * dt)
                if self.FBacceleration < self.accelMax:
                    self.FBacceleration += self.accelIncrement
            elif self.keyMap["backward"]:
                #self.Drone.setX(self.Drone, -self.FBSpeed * dt)
                if self.FBacceleration > -self.accelMax:
                    self.FBacceleration -= self.accelIncrement

            # lift up
            if self.keyMap["up"]:
                self.Drone.setZ(self.Drone, self.liftSpeed * dt)
            # go down
            if self.keyMap["down"]:
                self.Drone.setZ(self.Drone, -self.downSpeed * dt)

            # gravity
            if self.gravity:
                self.Drone.setZ(self.Drone, -self.gravity_value * dt)


        # restart game / reset position
        if self.keyMap["restart"]:
            self.Drone.setPos(self.DroneStartPos + (0, 0, 5))
            self.collisionCount = False
            self.crashed.destroy()
            self.Drone.setH(180)

        # First Person View / Third Person View Toggle 
        if self.keyMap["firstPerson"]:
            self.firstPerson = not self.firstPerson

        # Gravity Toggle
        if self.keyMap["gravity"]:
            self.gravity = not self.gravity

        # uncomment the following code to see the collision box
        ########################
        #self.cnodePath.show() #
        ########################


        # set the position and HPR of the camera according to the position of the drone
        # First Person View
        if self.firstPerson:
            base.camera.setH(self.Drone.getH()-90)
            base.camera.setP(self.Drone.getR())
            base.camera.setR(self.Drone.getP())
            base.camera.setPos(self.Drone.getPos())
        # Third Person View
        else:
            base.camera.setHpr(self.Drone.getHpr()+(180,0,0))
            h,p,r = self.Drone.getHpr()
            base.camera.setPos(self.Drone.getPos() + (math.cos(math.pi * h / 180) * -self.cameraDistance, \
                math.sin(math.pi * h / 180) * -self.cameraDistance, 0.5))

            viewTarget = Point3(self.Drone.getPos() + (0,0,0)) # the look-at point can be changed

            base.camera.lookAt(viewTarget)

        return task.cont



base = RaceDrone()
base.run()
