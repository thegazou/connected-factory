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


def fail():
    print("The operation has failed!")
    return False


def test_write_variable():
    print("\nTest of the updating variable feature:##################\n")
    arm_speed = robot.get_child(["2:Arm speed"])
    print("The speed of the robot's arm is {0}m/s.\n".format(arm_speed.get_value()))
    new_speed = 50
    print("Modifying the speed to {0}m/s.\n".format(new_speed))
    arm_speed.set_value(new_speed)
    time.sleep(1)
    print("Reading the new value of the node:")
    print("The speed of the robot's arm is now {0}m/s.".format(arm_speed.get_value()))
    print("\n######################Fin du test#######################\n")


def test_write_unwritable_variable():
    print("\nTest of the protection variable feature:################\n")
    arm_model = robot.get_child(["2:Arm model"])
    print("The robot's arm is a {0}.\n".format(arm_model.get_value()))
    new_model = "Mikron 2017"
    print("Attempting to modify the model of the arm to {0}.\n".format(new_model))
    time.sleep(1)
    try:
        arm_model.set_value(new_model)
        print("The robot's arm is a {0}.".format(arm_model.get_value()))
    except ua.uaerrors._auto.BadUserAccessDenied as error:
        print("ERROR:", error)
    print("\n######################Fin du test#######################\n")


def test_subscription():
    print("\nTest of the subscription feature:#######################\n")
    print("The Temperature of the robot is {0:3.1f}°.\n".format(robot.get_child(["2:TempSensor"]).get_value()))
    time.sleep(1)
    print("Start listening for Temperature changes!\n")
    handler = TemperatureSubHandler()
    sub = client.create_subscription(1, handler)
    handle = sub.subscribe_data_change(root.get_child(["0:Objects", "2:Robot1", "2:TempSensor"]))
    i = 0
    while i < 3:
        time.sleep(1)
        i += 1
    sub.unsubscribe(handle)
    print("\nStop listening for Temperature changes!")
    time.sleep(1)
    print("\n######################Fin du test#######################\n")


def test_get_history():
    print("\nTest of the historical access feature:##################\n")
    temp_sensor = robot.get_child(["2:TempSensor"])

    print("Pulling the last 5 records of the robot's temperature sensor:\n")
    history = temp_sensor.read_raw_history(numvalues=5)
    for temp in reversed(history):
        print("Temperature at {0} was {1:3.1f}°.".format(str(temp.SourceTimestamp)
                                                         .split(' ')[1].split('.')[0], temp.Value.Value))
    print("\n######################Fin du test########################\n")


def test_function():
    print("\nTest of the call function feature:#######################\n")
    robot_arm_x = robot.get_child(["2:Arm X coordinate"])
    robot_arm_y = robot.get_child(["2:Arm Y coordinate"])
    print("The x coordinate of the robot's arm is {0:3.1f}".format(robot_arm_x.get_value()))
    print("The y coordinate of the robot's arm is {0:3.1f}\n".format(robot_arm_y.get_value()))
    x = 20.0
    y = 12.1
    print("Attempting to move the arm to coordinates({0}, {1}) by calling function the move_arm(x,y)...".format(x, y), end='')
    robot.call_method("2:move_arm", x, y)
    print("Done!")
    print("\nThe new x coordinate of the robot's arm is {0:3.1f}".format(robot_arm_x.get_value()))
    print("The new y coordinate of the robot's arm is {0:3.1f}".format(robot_arm_y.get_value()))
    print("\n######################Fin du test########################\n")


def test_server_event():
    print("\nTest of the server event feature:########################\n")
    low_power_event = root.get_child(["0:Types", "0:EventTypes", "0:BaseEventType", "2:Low Power Event"])
    handler = ServerEventSubHandler()
    sub = client.create_subscription(500, handler)

    print("Start listening for server events!\n")
    handle = sub.subscribe_events(robot, low_power_event)
    trigger_server_event = robot.get_child(["2:Trigger Event"])
    trigger_server_event.set_value(True)
    time.sleep(1)
    i = 0
    while i < 2:
        time.sleep(1)
        i += 1
    sub.unsubscribe(handle)
    print("\nStop listening for Server Event!")
    time.sleep(1)
    print("\n######################Fin du test########################\n")


def grab_object(source_coord, target_coord):
    print("Moving the arm to the object...", end='')
    if robot.call_method("2:move_arm_v", source_coord) is not True:
        return fail()
    print("Done.")
    print("Attempting to catch an object...", end='')
    if robot.call_method("2:use_clamp") is not True:
        print("Nothing has been found!")
        return fail()
    print("An object has been caught!")
    print("Moving to the arm to the bin...", end='')
    if robot.call_method("2:move_arm_v", target_coord) is not True:
        return fail()
    print("Done.")
    print("Releasing object into the bin...", end='')
    robot.call_method("2:open_clamp")
    print("Done.")
    print("Moving the arm to his idle position...", end='')
    if robot.call_method("2:move_arm_v", robot.get_child("2:Arm idle position").get_value()) is not True:
        return fail()
    print("Done.")
    return True


def test_grab_function_client_side():
    print("\nTest of the grab function client side:###################\n")
    source_coord = [12, 13]
    target_coord = [6.0, 8.0]
    print("Attempting to get an object at position ({0},{1}).".format(source_coord[0], source_coord[1]), end='')
    print("and put it in the bin at position ({0},{1}).\n".format(target_coord[0], target_coord[1]))
    if grab_object(source_coord, target_coord) is not True:
        print("\nThe operation has failed!")
        return
    print("\nThe operation is a success!")
    print("\n######################Fin du test########################\n")


def test_grab_function_server_side():
    print("\nTest of the grab function server side:###################\n")
    source_coord = [12.0, 13.0]
    target_coord = [6.0, 8.0]
    print("Attempting to get an object at position ({0},{1}) ".format(source_coord[0], source_coord[1]), end='')
    print("and put it in the bin at position ({0},{1}).\n".format(target_coord[0], target_coord[1]))
    if robot.call_method("2:grab_object", source_coord, target_coord) is not True:
        print("The operation has failed!")
        return
    print("The operation is a success!")
    print("\n######################Fin du test########################\n")


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
        embed()
    finally:
        client.disconnect()
