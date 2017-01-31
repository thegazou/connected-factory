import sys
import logging
import time
from opcua import Client
from opcua import ua

sys.path.insert(0, "..")

try:
    from IPython import embed
except ImportError:
    import code


    def embed():
        vars = globals()
        vars.update(locals())
        shell = code.InteractiveConsole(vars)
        shell.interact()


class TemperatureSubHandler(object):
    @staticmethod
    def datachange_notification(node, val, data):
        print("The Temperature of the robot is now {0:3.1f}°.".format(val))


class ServerEventSubHandler(object):
    @staticmethod
    def event_notification(event):
        if event.IsInUse:
            print("Event received from {0}: {1} Current power level is {2}% and is being used."
                  .format(event.SourceName, event.Message, event.PowerLevel))
        else:
            print("Event received from {0}: {1} Current power level is {2}% and is not being used."
                  .format(event.SourceName, event.Message, event.PowerLevel))


def test_write_variable():
    print("\nTest of the updating variable feature:###################\n")
    arm_speed = robot.get_child(["2:Arm speed"])
    print("The speed of the robot's arm is {0}m/s.".format(arm_speed.get_value()))
    new_speed = 15
    print("Attempting to modify the speed to {0}m/s.".format(new_speed))
    arm_speed.set_value(new_speed)
    print("The speed of the robot's arm is now {0}m/s.".format(arm_speed.get_value()))


def test_write_unwritable_variable():
    print("\nTest of the protection variable feature:###################\n")
    arm_model = robot.get_child(["2:Arm model"])
    print("The robot's arm is a {0}.".format(arm_model.get_value()))
    new_model = "Mikron 2017"
    print("Attempting to modify the model of the arm to {0}.".format(new_model))
    try:
        arm_model.set_value(new_model)
        print("The robot's arm is a {0}.".format(arm_model.get_value()))
    except ua.uaerrors._auto.BadUserAccessDenied as error:
        print("ERROR:", error)


def test_subscription():
    print("\nTest of the subscription feature:###################\n")
    print("The Temperature of the robot is {0:3.1f}°.".format(robot.get_child(["2:TempSensor"]).get_value()))
    time.sleep(1)
    print("Start listening for Temperature changes!")
    handler = TemperatureSubHandler()
    sub = client.create_subscription(1, handler)
    handle = sub.subscribe_data_change(root.get_child(["0:Objects", "2:Robot1", "2:TempSensor"]))
    i = 0
    while i < 3:
        time.sleep(1)
        i += 1
    sub.unsubscribe(handle)
    print("Stop listening for Temperature changes!")
    time.sleep(1)


def test_get_history():
    print("\nTest of the historical access feature:###################\n")
    temp_sensor = robot.get_child(["2:TempSensor"])

    print("Pulling the last 5 records of the robot's temperature sensor:")
    history = temp_sensor.read_raw_history(numvalues=5)
    print(dir(history[0]))
    for temp in reversed(history):
        print("Temperature at {0} was {1:3.1f}°.".format(str(temp.SourceTimestamp)
                                                         .split(' ')[1].split('.')[0], temp.Value.Value))


def test_function():
    print("\nTest of the call function feature:###################\n")
    robot_arm_x = robot.get_child(["2:Arm X coordinate"])
    robot_arm_y = robot.get_child(["2:Arm Y coordinate"])
    print("The x coordinate of the robot's arm is {0:3.1f}".format(robot_arm_x.get_value()))
    print("The y coordinate of the robot's arm is {0:3.1f}".format(robot_arm_y.get_value()))
    x = 40.0
    y = 55.1
    print("Attempting to move the arm to coordinates({0}, {1}).".format(x, y))
    robot.call_method("2:move_arm", x, y)
    print("The x coordinate of the robot's arm is now {0:3.1f}".format(robot_arm_x.get_value()))
    print("The y coordinate of the robot's arm is now {0:3.1f}".format(robot_arm_y.get_value()))


def test_server_event():
    print("\nTest of the server event feature:###################\n")
    low_power_event = root.get_child(["0:Types", "0:EventTypes", "0:BaseEventType", "2:Low Power Event"])
    handler = ServerEventSubHandler()
    sub = client.create_subscription(500, handler)

    print("Start listening for server events!")
    handle = sub.subscribe_events(robot, low_power_event)
    trigger_server_event = robot.get_child(["2:Trigger Event"])
    trigger_server_event.set_value(True)
    i = 0
    while i < 2:
        time.sleep(1)
        i += 1
    sub.unsubscribe(handle)
    print("Stop listening for Server Event!")
    time.sleep(1)


def test_real_function():
    print("\nTest of a real application function:###################\n")
    target_position = [32.1, 55.8]
    print("Attempting to get an object at position ({0},{1}).".format(target_position[0], target_position[1]))
    robot.call_method("2:move_arm", target_position[0], target_position[1])
    result = robot.call_method("2:use_clamp")
    if result is True:
        print("An object has been caught!")
    else:
        print("Nothing has been found!")
        return
    print("Moving arm to his inital position")
    initial_position = robot.get_child("2:Arm inital position").get_value()
    if robot.call_method("2:move_arm", initial_position[0], initial_position[1]) is True:
        print("Releasing object from the clamp")
        robot.call_method("2:open_clamp")
        print("The Operation is a succes!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN)
    logger = logging.getLogger("KeepAlive")
    logger.setLevel(logging.DEBUG)
    client = Client("opc.tcp://localhost:4840/connected-factory/server/")
    client.connect()
    root = client.get_root_node()
    robot = root.get_child(["0:Objects", "2:Robot1"])
    print("Connected to my custom Opc Ua Server")

    try:
        test_real_function()
        test_write_variable()
        test_write_unwritable_variable()
        test_subscription()
        test_get_history()
        test_function()
        test_server_event()
        test_real_function()

        # embed()
    finally:
        client.disconnect()
