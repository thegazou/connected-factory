import sys
import time
from opcua import ua, Server, uamethod
sys.path.insert(0, "..")


@uamethod
def move_arm(parent, x, y):
    print("\nMoving arm to coordinates ({0},{1}).".format(x, y))
    arm_x_coord=robot.get_child(["2:Arm X coordinate"])
    arm_y_coord=robot.get_child(["2:Arm Y coordinate"])
    arm_x_coord.set_value(x)
    arm_y_coord.set_value(y)
    print("Arm in position!")


def test_event():
    power_event_generator.event.Message = "Power is low!"
    power_event_generator.event.IsInUse = True
    power_event_generator.event.PowerLevel = 20
    power_event_generator.trigger()
    print("\nPower Event triggered!")


if __name__ == "__main__":

    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")

    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)
    objects = server.get_objects_node()
    robot = objects.add_object(idx, "Robot1")

    temp_sensor = robot.add_variable(idx, "TempSensor", 6.7)

    arm_x_coord = robot.add_variable(idx, "Arm X coordinate", 30.2)
    arm_x_coord.set_writable()
    arm_y_coord = robot.add_variable(idx, "Arm Y coordinate", 15.4)
    arm_y_coord.set_writable()
    arm_speed = robot.add_variable(idx, "Arm speed", 10)
    arm_speed.set_writable()
    arm_model = robot.add_variable(idx, "Arm model", "Mikron 3")

    multiply_node = robot.add_method(idx, "move_arm", move_arm,
                                     [ua.VariantType.Int64, ua.VariantType.Int64], [ua.VariantType.Int64])
    power_event = server.create_custom_event_type(2, 'Low Power Event', ua.ObjectIds.BaseEventType)
    power_event.add_property(1, 'Message', ua.Variant("Power is low!", ua.VariantType.String))
    power_event.add_property(2, 'PowerLevel', ua.Variant(15, ua.VariantType.Int32))
    power_event.add_property(3, 'IsInUse', ua.Variant(True, ua.VariantType.Boolean))
    power_event_generator = server.get_event_generator(power_event, robot)
    trigger_event = robot.add_variable(idx, "Trigger Event", False)
    trigger_event.set_writable()

    server.start()
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

