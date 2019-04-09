import json
from thing_registry import MqttProxy, ThingRegistry
from things import Thing, BatteryPoweredThing, Lamp, DimmableLamp, Button

class MyIkeaButton(Button):
    def __init__(self, pretty_name, btn1, btn2):
        super().__init__(pretty_name)
        self.btn1 = btn1
        self.btn2 = btn2

    def handle_action(self, action, msg):
        if action == 'arrow_right_click':
            self.btn1.brightness_up()
        if action == 'arrow_left_click':
            self.btn1.brightness_down()
        if action == 'brightness_up_click':
            self.btn2.brightness_up()
        if action == 'brightness_down_click':
            self.btn2.brightness_down()
        if action == 'toggle':
            if self.btn1.is_on or self.btn2.is_on:
                self.btn1.turn_off()
                self.btn2.turn_off()
            else:
                self.btn2.set_brightness(20)

mqtt = MqttProxy('192.168.2.100', 1883, 'zigbee2mqtt/')
thing_registry = ThingRegistry(mqtt)
ll = DimmableLamp('Kitchen - Left', thing_registry)
lr = DimmableLamp('Kitchen - Right', thing_registry)

thing_registry.register_thing('0xd0cf5efffe30c9bd', DimmableLamp('DeskLamp', thing_registry))
thing_registry.register_thing('0x000d6ffffef34561', ll)
thing_registry.register_thing('0x0017880104b8c734', lr)
thing_registry.register_thing('0xd0cf5efffe7b6279', DimmableLamp('FloorLamp', thing_registry))
thing_registry.register_thing('0x0017880104efbfdd', Button('HueButton'))
thing_registry.register_thing('0xd0cf5efffeffac46', MyIkeaButton('IkeaButton', ll, lr))

mqtt.bg_run()


from flask import Flask, send_from_directory
flask_app = Flask(__name__)


@flask_app.route('/webapp/<path:path>')
def flask_endpoint_webapp_root(path):
    return send_from_directory('webapp', path)


# Registry status actions

@flask_app.route('/things/all_known_things')
def flask_endpoint_known_things():
    return json.dumps(thing_registry.get_known_things_names())

@flask_app.route('/things/unknown_things')
def flask_endpoint_things_unknown_ids():
    return json.dumps(thing_registry.get_unknown_ids())

@flask_app.route('/things/get_world_status')
def flask_endpoint_get_world_status():
    actions = {}
    for thing in thing_registry.get_known_things_names():
        obj = thing_registry.get_by_name_or_id(thing)
        actions[thing] = {'status': obj.json_status()}
        actions[thing].update(obj.describe_capabilities())

    return json.dumps(actions)


# Thing actions

@flask_app.route('/things/<name_or_id>/turn_on')
def flask_endpoint_things_turn_on(name_or_id):
    obj = thing_registry.get_by_name_or_id(name_or_id)
    obj.turn_on()
    return json.dumps(obj.json_status())

@flask_app.route('/things/<name_or_id>/turn_off')
def flask_endpoint_things_turn_off(name_or_id):
    obj = thing_registry.get_by_name_or_id(name_or_id)
    obj.turn_off()
    return json.dumps(obj.json_status())

@flask_app.route('/things/<name_or_id>/set_brightness/<brightness>')
def flask_endpoint_things_set_brightness(name_or_id, brightness):
    obj = thing_registry.get_by_name_or_id(name_or_id)
    obj.set_brightness(int(brightness))
    return json.dumps(obj.json_status())

@flask_app.route('/things/<name_or_id>/status')
def flask_endpoint_things_status(name_or_id):
    return json.dumps(thing_registry.get_by_name_or_id(name_or_id).json_status())



 
# @flask_app.route('/things/<name_or_id>/toggle')
# def flask_endpoint_things_toggle(name_or_id):
#     obj = thing_registry.get_by_name_or_id(name_or_id)
#     obj.toggle()
#     return json.dumps(obj.json_status())
# 
# @flask_app.route('/things/<name_or_id>/brightness_down')
# def flask_endpoint_things_brightness_down(name_or_id):
#     obj = thing_registry.get_by_name_or_id(name_or_id)
#     obj.brightness_down()
#     return json.dumps(obj.json_status())
# 
# @flask_app.route('/things/<name_or_id>/brightness_up')
# def flask_endpoint_things_brightness_up(name_or_id):
#     obj = thing_registry.get_by_name_or_id(name_or_id)
#     obj.brightness_up()
#     return json.dumps(obj.json_status())

flask_app.run(host='0.0.0.0', port=2000, debug=True)

print("STOPPING")
mqtt.stop()
print("EXIT")

