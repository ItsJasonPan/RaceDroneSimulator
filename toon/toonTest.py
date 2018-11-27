from panda3d.core import WindowProperties
from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionTraverser, CollisionNode, CollisionBox
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import Filename, AmbientLight, DirectionalLight
from panda3d.core import PandaNode, NodePath, Camera, TextNode
from panda3d.core import CollideMask
from panda3d.core import Point3,Vec3,Vec4
from pandac.PandaModules import*
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
import random
import sys
import os
import math

# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), scale=.05,
                        shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                        pos=(0.08, -pos - 0.04), align=TextNode.ALeft)


class RoamingDroneDemo(ShowBase):
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
            "left": 0, "right": 0, "forward": 0, "drift-left": 0,
             "drift-right": 0, "up": 0, "down": 0, "restart": 0, "firstPerson": 0}
        #instructions
        self.instruction2 = addInstructions(0.12, "[Left Arrow]: Rotate Left")
        self.instruction3 = addInstructions(0.18, "[Right Arrow]: Rotate Right")
        self.instruction4 = addInstructions(0.24, "[Up Arrow]: Fly Forward")
        self.instruction5 = addInstructions(0.30, "[A, D]: Move Camera")
        self.instruction6 = addInstructions(0.36, "[W, S]: Fly Lift/ Descent")
        self.instruction7 = addInstructions(0.42, "[F]: Toggle First Person/ Third Person")
        self.instruction8 = addInstructions(0.48, "[R]: Restart")

        # Set up the playground
        # models/toon/phase_15/hood/toontown_central.bam
        # models/world
        # CS_Map/myCSMAP.egg
        self.environ = loader.loadModel("phase_15/hood/toontown_central.bam")
        self.environ.reparentTo(render)

        # Create drone and initalize drone position
        #print(self.environ.find("**/start_point").getPos())
        #self.DroneStartPos = #self.environ.find("**/start_point").getPos()
        self.Drone = Actor("models/mydrone.egg")
        self.Drone.reparentTo(render)

        # resize and reposition the drone
        self.Drone.setScale(.1)
        self.Drone.setPos(5,5,5)
        self.DroneStartPos = self.Drone.getPos()
        #self.Drone.setPos(self.DroneStartPos + (0, 0, 0.5))

        # Create a floater object for the camera to look at
        self.floater = NodePath(PandaNode("floater"))
        self.floater.reparentTo(self.Drone)
        self.floater.setZ(3.0)

        # User Controls
        self.accept('escape', __import__('sys').exit, [0])
        self.accept("arrow_left", self.setKey, ["left", True])
        self.accept("arrow_right", self.setKey, ["right", True])
        self.accept("arrow_up", self.setKey, ["forward", True])
        self.accept("a", self.setKey, ["drift-left", True])
        self.accept("d", self.setKey, ["drift-right", True])
        self.accept("arrow_left-up", self.setKey, ["left", False])
        self.accept("arrow_right-up", self.setKey, ["right", False])
        self.accept("arrow_up-up", self.setKey, ["forward", False])
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

        self.cTrav = CollisionTraverser()
        self.queue = CollisionHandlerQueue()
        self.cTrav.addCollider(self.cnodePath, self.queue)
        self.cTrav.traverse(render)


        ##################################
        #self.cTrav.showCollisions(render)
        #self.DroneGroundColNp.show()
        #self.camGroundColNp.show()
        ##################################

        # Lighting
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
        self.angleChange = 0.8
        self.maxAngle = 20


    # Records the state of the arrow keys
    def setKey(self, key, value):
        self.keyMap[key] = value

    # Deal with user interface and collision detection

    def move(self, task):
        self.crashed.destroy()
        self.crashed = OnscreenText(text="Crashed!!!" if len(self.queue.getEntries()) != 0 else "", pos = (-0.5, 0.02), 
                                scale = 0.07, mayChange = True, fg = (255,255,255,1))

        # Get the time that elapsed since last frame.  
        dt = globalClock.getDt()

        # Drone is movable only when it's not crashed
        if len(self.queue.getEntries()) == 0:
            if self.keyMap["drift-left"]:
                self.Drone.setY(self.Drone, 40 * dt)
                if self. angle > -self.maxAngle:
                    self.angle -= self.angleChange
                self.Drone.setP(self.angle)
            elif self.keyMap["drift-right"]:
                self.Drone.setY(self.Drone, -40 * dt)
                if self. angle < self.maxAngle:
                    self.angle += self.angleChange
                self.Drone.setP(self.angle)
            else:
                if self.angle >=self.angleChange:
                    self.angle -= self.angleChange
                elif self.angle <=-self.angleChange:
                    self.angle +=self.angleChange
                self.Drone.setP(self.angle)

            if self.keyMap["left"]:
                self.Drone.setH(self.Drone.getH() + 150 * dt)
            if self.keyMap["right"]:
                self.Drone.setH(self.Drone.getH() - 150 * dt)
            if self.keyMap["forward"]:
                self.Drone.setX(self.Drone, 200 * dt)

            if self.keyMap["up"]:
                self.Drone.setZ(self.Drone, 40 * dt)
            if self.keyMap["down"]:
                self.Drone.setZ(self.Drone, -80 * dt)


        # other commands
        if self.keyMap["restart"]:
            self.Drone.setPos(self.DroneStartPos + (0, 0, 5))
            self.collisionCount = False
            self.crashed.destroy()
        if self.keyMap["firstPerson"]:
            self.firstPerson = not self.firstPerson

        ######################
        #self.cnodePath.show()
        ######################


        # set the position and HPR of the camera according to the position of the drone
        if self.firstPerson:
            base.camera.setH(self.Drone.getH()-90)
            base.camera.setP(self.Drone.getR())
            base.camera.setR(self.Drone.getP())
            base.camera.setPos(self.Drone.getPos())

        else:
            base.camera.setHpr(self.Drone.getHpr()+(180,0,0))
            h,p,r = self.Drone.getHpr()
            base.camera.setPos(self.Drone.getPos() + (math.cos(math.pi * h / 180) * -self.cameraDistance, \
                math.sin(math.pi * h / 180) * -self.cameraDistance, 0.5))

            viewTarget = Point3(self.Drone.getPos() + (0,0,0))

            base.camera.lookAt(viewTarget)

        #print(self.camera.getPos())
        return task.cont



base = RoamingDroneDemo()
base.run()
