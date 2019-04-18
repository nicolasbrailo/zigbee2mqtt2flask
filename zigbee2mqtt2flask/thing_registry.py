import json

class ThingRegistry(object):
    """
    Acts as a dictionary of all known things and also as a bridge between
    mqtt and local model objects: the registry knows the id of each thing,
    so it can map an mqtt message to the object which should receive it
    """

    def __init__(self, flask_app, endpoint_prefix):
        self.flask_app = flask_app
        self.known_things = {}
        self.name_to_id = {}
        self.unknown_things = set()

        thing_ep          = endpoint_prefix + '/thing/<thing_name>/<action>'
        known_things_ep   = endpoint_prefix + '/world/known_things'
        unknown_things_ep = endpoint_prefix + '/world/unknown_things'
        world_status_ep   = endpoint_prefix + '/world/status'

        flask_app.add_url_rule('/'+thing_ep,                thing_ep,          self.ws_thing_action_handler)
        flask_app.add_url_rule('/'+thing_ep+'/<path:args>', thing_ep+'+args',  self.ws_thing_action_handler)
        flask_app.add_url_rule('/'+known_things_ep,         known_things_ep,   self.ws_all_known_things)
        flask_app.add_url_rule('/'+unknown_things_ep,       unknown_things_ep, self.ws_all_unknown_things)
        flask_app.add_url_rule('/'+world_status_ep,         world_status_ep,   self.ws_world_status)

        print("Registered endpoint {} for things API".format(thing_ep))
        print("Registered endpoint {}/* for things API with arguments".format(thing_ep))
        print("Registered endpoint {} for known things API".format(known_things_ep))
        print("Registered endpoint {} for unknown things API".format(unknown_things_ep))
        print("Registered endpoint {} for world status API".format(world_status_ep))

    # Flask endpoint handlers

    def ws_all_known_things(self):
        return json.dumps(self.get_known_things_names())

    def ws_all_unknown_things(self):
        return json.dumps(self.get_unknown_ids())

    def ws_world_status(self):
        world = {}
        for thing in self.get_known_things_names():
            obj = self.get_by_name_or_id(thing)
            world[thing] = {'status': obj.json_status(),
                              'supported_actions': obj.supported_actions()}

        return json.dumps(world)

    def ws_thing_action_handler(self, thing_name, action, args=None):
        """ Flask handler: try to find a thing called $thing_name, and invoke
        $action on the found object (if any) """

        try:
            obj = self.get_by_name_or_id(thing_name)
        except KeyError:
            return "No object called {}".format(thing_name), 404

        method = getattr(obj, action, None)
        if method is None:
            return "No method {} on object {}".format(action, thing_name), 405

        parsed_args = []
        if args is not None:
            parsed_args = args.split('/')

        try:
            ret = method(*parsed_args)
            # If the method yielded a value, use it as a return value. Otherwise
            # default to json_status (if json_status itself was called then a
            # direct return is not possible, as json_status returns a dict and not
            # something flask can interpret. In this case, do some magic to return
            # the right thing)
            if ret is not None and action != "json_status":
                return ret

            return json.dumps(obj.json_status())

        except TypeError:
            return "Calling {}.{}({}) yields a type error (are you sure the arguments are correct?)"\
                        .format(thing_name, action, parsed_args), 405



    def register_thing(self, obj):
        if obj.get_pretty_name() in self.name_to_id.keys():
            raise KeyError('Thing {} ({}) already registered'.format(obj.get_pretty_name(), obj.get_id()))

        self.known_things[obj.get_id()] = obj
        self.name_to_id[obj.get_pretty_name()] = obj.get_id()

    def get_by_name_or_id(self, name_or_id):
        if name_or_id in self.name_to_id.keys():
            id = self.name_to_id[name_or_id]
            return self.known_things[id]

        # If it's not a name it must be an id. Else fail
        return self.known_things[name_or_id]

    def get_things_supporting(self, actions):
        def impls_interface(obj, actions):
            for action in actions:
                if action not in obj.supported_actions():
                    return False
            return True

        return [obj for name,obj in self.known_things.items()
                        if impls_interface(obj, actions)]

    def get_known_things_names(self):
        return list(self.name_to_id.keys())

    def get_unknown_ids(self):
        return list(self.unknown_things)

    def on_thing_message(self, thing_id, topic, json_msg):
        if thing_id in self.known_things.keys():
            if not self.known_things[thing_id].consume_message(topic, json_msg):
                self.on_unknown_message(topic, json.dumps(json_msg))
        else:
            if thing_id not in self.unknown_things:
                self.unknown_things.add(thing_id)
                print('Thing {} added to registry of unknown things'.format(thing_id))

    def on_unknown_message(self, topic, payload):
        print('Received message that can\'t be understood:' +\
                    '\t{}\n\t{}'.format(topic, payload))

