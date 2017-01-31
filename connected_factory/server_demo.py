import sys
import time
from opcua import ua, Server, uamethod
from opcua.server.history_sql import HistorySQLite

sys.path.insert(0, "..")


@uamethod
def move_arm_v(parent, coord):
    return _move_arm(coord)


@uamethod
def move_arm(parent, x, y):
    return _move_arm([x, y])


def estimate_arm_travel_time(coord):
    x0 = robot.get_child(["2:Arm X coordinate"]).get_value()
    y0 = robot.get_child(["2:Arm Y coordinate"]).get_value()
    dist = (abs(coord[0]-x0)**2+(abs(coord[1]-y0)**2)**0.5)
    return dist/arm_speed.get_value()


def _move_arm(coord):
    print("\nMoving arm to coordinates ({0},{1})...".format(coord[0], coord[1]), end='')
    x_coord = robot.get_child(["2:Arm X coordinate"])
    y_coord = robot.get_child(["2:Arm Y coordinate"])
    time.sleep(estimate_arm_travel_time(coord))
    x_coord.set_value(coord[0])
    y_coord.set_value(coord[1])
    print("Done!")
    return True


@uamethod
def use_clamp(parent):
    return _use_clamp()


def _use_clamp():
    x = robot.get_child(["2:Arm X coordinate"]).get_value()
    y = robot.get_child(["2:Arm Y coordinate"]).get_value()
    print("Attempting to catch an object at coordinates ({0},{1}).".format(x, y))

    # Simulating an object at coordinate (15.2, 13.0)
    if x == 15.2 and y == 13.0:
        clamp_resitance_sensor.set_value(100)

    if clamp_resitance_sensor.get_value() >= 100:
        arm_clamp.set_value(True)
        print("An object has been catched by the clamp!")
        return True
    else:
        print("Nothing is in the clamp!")
        move_arm(arm_idle_position.get_value)
        return False


@uamethod
def open_clamp(parent):
    _open_clamp()


def _open_clamp():
    arm_clamp.set_value(False)
    print("Oppening clamp!")


@uamethod
def grab_object(parent, source_coord, target_coord):
    print("The grab_object function has been called!")
    if _move_arm(source_coord) is not True:
        return False
    if _use_clamp() is not True:
        _move_arm(arm_idle_position)
        return False
    if _move_arm(target_coord) is not True:
        return False
    _open_clamp()
    return _move_arm(arm_idle_position.get_value())


def test_event():
    power_event_generator.event.Message = "Power is low!"
    power_event_generator.event.IsInUse = True
    power_event_generator.event.PowerLevel = 20
    power_event_generator.trigger()
    print("\nPower Event triggered!")


if __name__ == "__main__":

    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/connected-factory/server/")

    uri = "https://github.com/thegazou/connected-factory"
    idx = server.register_namespace(uri)
    objects = server.get_objects_node()
    robot = objects.add_object(idx, "Robot1")

    temp_sensor = robot.add_variable(idx, "TempSensor", 6.7)

    arm_x_coord = robot.add_variable(idx, "Arm X coordinate", 30.2)
    arm_x_coord.set_writable()
    arm_y_coord = robot.add_variable(idx, "Arm Y coordinate", 15.4)
    arm_y_coord.set_writable()
    arm_speed = robot.add_variable(idx, "Arm speed", 45)
    arm_speed.set_writable()
    arm_model = robot.add_variable(idx, "Arm model", "Mikron 3")
    arm_clamp = robot.add_variable(idx, "Arm Clamp", False)
    clamp_resitance_sensor = arm_clamp.add_property(idx, "Resistance sensor", 0)
    robot.add_method(idx, "use_clamp", use_clamp, [], [ua.VariantType.Boolean])
    robot.add_method(idx, "open_clamp", open_clamp, [], [])
    arm_idle_position = robot.add_property(idx, "Arm idle position", [10, 10])

    inargx = ua.Argument()
    inargx.Name = "vec2"
    inargx.DataType = ua.NodeId(ua.ObjectIds.Double)
    inargx.ValueRank = -1
    inargx.ArrayDimensions = []
    inargx.Description = ua.LocalizedText("List contenant les coordonnées de la cible")
    robot.add_method(idx, "move_arm_v", move_arm_v,
                     [inargx], [ua.VariantType.Boolean])
    robot.add_method(idx, "move_arm", move_arm,
                     [ua.VariantType.Double, ua.VariantType.Double], [ua.VariantType.Boolean])

    robot.add_method(idx, "grab_object", grab_object,
                     [ua.VariantType.Double, ua.VariantType.Double], [ua.VariantType.Boolean])

    power_event = server.create_custom_event_type(2, 'Low Power Event', ua.ObjectIds.BaseEventType)
    power_event.add_property(1, 'Message', ua.Variant("Power is low!", ua.VariantType.String))
    power_event.add_property(2, 'PowerLevel', ua.Variant(15, ua.VariantType.Int32))
    power_event.add_property(3, 'IsInUse', ua.Variant(True, ua.VariantType.Boolean))
    power_event_generator = server.get_event_generator(power_event, robot)
    trigger_event = robot.add_variable(idx, "Trigger Event", False)
    trigger_event.set_writable()

    server.iserver.history_manager.set_storage(HistorySQLite("temp_sensor_history.sql"))

    server.start()
    server.historize_node_data_change(temp_sensor, period=None, count=100)
    try:
        count = 0
        while True:
            time.sleep(1)
            count += 0.1
            temp_sensor.set_value(count)

            if trigger_event.get_value():
                test_event()
                trigger_event.set_value(False)

    finally:
        server.stop()
