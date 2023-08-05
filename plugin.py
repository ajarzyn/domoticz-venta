# Venta plugin based on sockets
# Author: ajarzyn, 2023
"""
<plugin key="VENTA" name="Venta based on sockets." author="ajarzyn" version="0.0.3">
    <description>
        <h2>Venta based on sockets.</h2><br/>
        Be aware:
         Values greater than 30 seconds will cause a message to be regularly logged about the plugin not responding.
         The plugin will actually function correctly with values greater than 30 though.
    </description>
    <params>
        <param field="Address" label="Venta IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Mode1" label="mac Address" width="150px" required="false" default="ff:ff:ff:ff:ff:ff"/>
        <param field="Port" label="Venta Port" width="30px" required="true" default="48000"/>
        <param field="Mode3" label="Hash" width="150px" required="true"/>
        <param field="Mode4" label="App Name" width="150px" required="false" default="Venta App"/>

        <param field="Mode2" label="Data pull interval in seconds" width="150px" default="25"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0" default="true"/>
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Python" value="18"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import json
import socket
import textwrap
import queue


class VentaAPI:
    METHODS = {
        'get_info': 'GET /Complete',
        'set_opt': 'POST /Action'
    }

    class OnOff:
        def __init__(self, parent_class, method_name, *_):
            self.method_name = method_name
            self.parent_class = parent_class

        def on(self, *_):
            return self.parent_class.set_param(self.method_name, 'true')

        def off(self, *_):
            return self.parent_class.set_param(self.method_name, 'false')

    class ZeroOne:
        def __init__(self, parent_class, method_name, *args):
            self.method_name = method_name
            self.parent_class = parent_class
            if args:
                self._set_methods_names(*args[0])

        def _set_methods_names(self, first_name, second_name):
            setattr(self, first_name, self.zero)
            setattr(self, second_name, self.one)
            setattr(self, "off", self.zero)
            setattr(self, "on", self.one)

        def one(self, *_):
            return self.parent_class.set_param(self.method_name, 1)
            # return self.parent, 1

        def zero(self, *_):
            return self.parent_class.set_param(self.method_name, 0)
            # return self.parent, 0

    class Levels:
        def __init__(self, parent_class, method_name, *args):
            self.method_name = method_name
            self.parent_class = parent_class
            self._set_methods_names()
            if args:
                self.available_levels = args[0]

        def _set_methods_names(self):
            setattr(self, "off", self.set_level)
            setattr(self, "on", self.set_level)

        def set_level(self, domoticz_level, *_):
            list_idx = int(domoticz_level / 10)
            if list_idx < len(self.available_levels):
                return self.parent_class.set_param(self.method_name, self.available_levels[list_idx])
            else:
                pass
                return None, None

    TARGET_HUM = [0, 30, 35, 40, 45, 50, 55, 60, 65, 70]
    TARGET_TIMERS = [0, 1, 3, 5, 7, 9]
    FAN_SPED = [0, 1, 2, 3, 4, 5]

    command_dict = {
        'Power': (OnOff, []),
        'Automatic': (OnOff, []),
        'Boost': (OnOff, []),
        'SleepMode': (OnOff, []),
        'ChildLock': (OnOff, []),
        'TempUnit': (ZeroOne, ["celsius", "fahrenheit"]),  # 0 - celsius, 1 - fahrenheit
        'DisplayLeft': (ZeroOne, ["humidity", "temperature"]),  # 0 - humidity, 1 - temperature
        'DisplayRight': (ZeroOne, ["vlines", "square"]),  # 0 - vertical line, 1 - square
        'FanSpeed': (Levels, FAN_SPED),
        'TargetHum': (Levels, TARGET_HUM),
        'Timer': (Levels, TARGET_TIMERS),
        'SysLanguage': (Levels, [0, 1, 2, 3, 4, 5, 6, 7, 8]),
    }

    SysLang = {
        0: 'English',
        1: 'Chinese',
        2: 'English Kuubek XL-T',
        3: 'Deutsch(selected)/British',
        4: 'Deutsch(selected)/French',
        5: 'British(selected)/French',
        6: 'Chinese(selected)/British',
        7: 'Russian(Selected)/British',
        8: ['Polish(Selected)/British', ['CleanLanguage', 0, 6]]
    }

    def __init__(self, mac_address, host, port=48000, hash=0, app_name=''):
        self.header = f'"Header":{{"macAdress":"{mac_address}","DeviceType":2,' \
                      f'"Hash":"{hash}","DeviceName":"{app_name}"}}'
        self.host = host
        self.port = int(port)

    def send_command(self, message):
        local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            local_socket.settimeout(1)
            local_socket.connect((self.host, self.port))
        except Exception as e:
            Domoticz.Debug("1" + str(e))
        try:
            local_socket.settimeout(1)
            local_socket.sendall(message)
        except Exception as e:
            Domoticz.Debug("2" + str(e))
        try:
            local_socket.settimeout(1)
            received_data = local_socket.recv(1024).decode("utf-8")
        except Exception as e:
            received_data = ''
            Domoticz.Debug("3" + str(e))
        local_socket.close()
        return received_data

    def _prep_method(self, method, command_name='', value=''):
        method_string = self.METHODS[method]

        command_line = ''
        if method is 'set_opt':
            command_line = f'"Action":{{"{command_name}":{value}}},'

        command_line += self.header

        prepared_command = f"""{method_string}
                        Content-Length: {len(command_line)}
                        
                        {{{command_line}}}"""
        return textwrap.dedent(prepared_command).encode()

    def get_info(self):
        return self.send_command(self._prep_method('get_info'))

    def get_info_str(self):
        return self._prep_method('get_info')

    def set_param(self, command_name, value):
        # return self.send_command(self._prep_method('set_opt', command_name, value))
        return self._prep_method('set_opt', command_name, value)


def to_float(data: int, divider: float = 1.0) -> dict:
    converted = float(data / divider)
    return {'s_value': str(converted)}


def to_number(data: int, divider: float = 1.0) -> dict:
    converted = float(data / divider)
    return {'n_value': int(converted)}


def to_selector_switch(data: int, divider: float = 1.0) -> dict:
    converted = float(data/divider)
    return {'n_value': int(converted), 's_value': str(converted)}


def bool_to_number(data: int, mapping: list = None) -> dict:
    if mapping is None:
        mapping = [False, True]
    return {'n_value': mapping.index(data)}


def selector_switch_level_mapping(data: int, mapping: list) -> dict:
    level = mapping.index(data) * 10
    return {'n_value': int(level), 's_value': str(level)}


def to_alert(data: int, mapping: list) -> dict:
    return {'n_value': int(mapping[data][0]), 's_value': str(mapping[data][1])}


def humidity(data: int) -> dict:
    status = ''
    if 40 <= data <= 60:
        status = 1
    elif 30 <= data <= 70:
        status = 0
    elif data > 70:
        status = 3
    elif data < 40:
        status = 2
    return {'n_value': int(data), 's_value': str(status)}


class BasePlugin:
    def __init__(self):
        self.dev_list = []
        self.UNITS = {}
        self.UNITS_ID_KEYS = {}

        self.conn = None
        self.conn_write = None
        self.host = ''
        self.port = ''
        self.commandToSend = queue.Queue()

        self.Venta = None

    def prepare_devices_list(self):
        self.dev_list = [
            # Name, socket command, idx, data modification callback, Domoticz devices options, is writable
            [['Measure', 'Temperature'], [to_float], dict(TypeName="Temperature", Used=1)],
            [['Measure', 'Humidity'],   [humidity], dict(TypeName="Humidity", Used=1)],
            [['Measure', 'Dust'],       [to_float], dict(TypeName="Custom", Used=1, Options={"Custom": "1;µg/m³"})],
            [['Measure', 'FanRpm'],     [to_float], dict(TypeName="Custom", Used=1, Options={"Custom": "1;RPM"})],
            [['Measure', 'WaterLevel'], [to_alert, [(0, 'Power off/No container'),
                                                    (3, 'Low'),
                                                    (4, 'Empty'),
                                                    (2, 'Medium'),
                                                    (1, 'Full')]], dict(TypeName="Alert", Used=1)],

            # Writable
            [['Action', 'Automatic'],   [bool_to_number], dict(TypeName="Switch", Image=9, Used=1)],
            [['Action', 'ChildLock'],   [bool_to_number], dict(TypeName="Switch", Image=9, Used=1)],
            [['Action', 'Power'],       [bool_to_number], dict(TypeName="Switch", Image=9, Used=1)],
            [['Action', 'SleepMode'],   [bool_to_number], dict(TypeName="Switch", Image=9, Used=1)],
            [['Action', 'DisplayLeft'], [to_number], dict(TypeName="Switch", Image=9, Used=1)],
            [['Action', 'DisplayRight'], [to_number], dict(TypeName="Switch", Image=9, Used=1)],

            [['Action', 'TempUnit'],    [to_number], dict(TypeName="Switch", Image=9, Used=1)],

            [['Action', 'FanSpeed'],    [selector_switch_level_mapping, VentaAPI.FAN_SPED],
             dict(TypeName="Selector Switch", Image=7, Used=1,
                  Options={"LevelActions": "|"*(len(VentaAPI.FAN_SPED)-1),
                           "LevelNames": "|".join(str(x) for x in VentaAPI.FAN_SPED),
                           "LevelOffHidden": "true",
                           "SelectorStyle": "1"})],
            [['Action', 'TargetHum'],   [selector_switch_level_mapping, VentaAPI.TARGET_HUM],
             dict(TypeName="Selector Switch", Image=7, Used=1,
                  Options={"LevelActions": "|"*(len(VentaAPI.TARGET_HUM)-1),
                           "LevelNames": "%|".join(str(x) for x in VentaAPI.TARGET_HUM)+"%",
                           "LevelOffHidden": "false",
                           "SelectorStyle": "1"})],
            [['Action', 'Timer'],       [selector_switch_level_mapping, VentaAPI.TARGET_TIMERS],
             dict(TypeName="Selector Switch", Image=7, Used=1,
                  Options={"LevelActions": "|"*(len(VentaAPI.TARGET_TIMERS)-1),
                           "LevelNames": "h|".join(str(x) for x in VentaAPI.TARGET_TIMERS)+"h",
                           "LevelOffHidden": "false",
                           "SelectorStyle": "1"})],
        ]

        class Unit:
            def __init__(self, id, json_address, data_conversion, dev_params):
                self.id = id
                self.category = json_address[0]
                self.name = json_address[1]
                self.data_conversion, *self._args = data_conversion
                self.dev_params = dev_params

            def update_domoticz_dev(self, data):
                update_device(unit=self.id,
                              **self.data_conversion(data[self.category][self.name], *self._args))

        for dev_idx in range(len(self.dev_list)):
            tmp_unit = Unit(dev_idx+1, *self.dev_list[dev_idx])
            tmp_unit.dev_params.update(dict(Name=tmp_unit.name, Unit=tmp_unit.id))

            self.UNITS[tmp_unit.name] = tmp_unit
            self.UNITS_ID_KEYS[tmp_unit.id] = tmp_unit

    def create_devices(self):
        for unit in self.UNITS.values():
            if unit.id not in Devices:
                Domoticz.Device(**unit.dev_params).Create()

    def update_devices(self, data: str = ''):
        if data is '':
            return
        last_eol = data.rfind('\n')
        data = data[last_eol + 1:-1]
        parsed = json.loads(data)
        if len(parsed) > 0:
            def update_device_if_in_data(device, parsed):
                if device.category in parsed:
                    device.update_domoticz_dev(parsed)

            # Measure sensors do not work when power is off
            # Update power and use it's nValue to skip sensors update
            power_device = self.UNITS['Power']

            update_device_if_in_data(power_device, parsed)
            power_device_state = Devices[power_device.id].nValue
            fan_rpm_id = self.UNITS['FanRpm'].id

            for device in self.UNITS.values():
                if device.name == 'Power':
                    # Power is updated outside the for
                    continue
                if device.category == 'Measure' and device.id != fan_rpm_id and power_device_state == 0:
                    # Do not update Measure sensor when power is off
                    continue

                update_device_if_in_data(device, parsed)

    def onStart(self):
        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()

        self.prepare_devices_list()

        self.host = Parameters['Address']
        self.port = Parameters['Port']
        mac = Parameters['Mode1']
        hash = Parameters['Mode3']
        app_name = Parameters['Mode4']

        self.Venta = VentaAPI(mac, self.host, self.port, hash=hash, app_name=app_name)
        for method_name, val in VentaAPI.command_dict.items():
            setattr(VentaAPI, method_name, val[0](self.Venta, method_name, val[1]))

        Domoticz.Heartbeat(int(Parameters['Mode2']))

        self.create_devices()

        self.conn = Domoticz.Connection(Name="READ", Transport="TCP/IP", Protocol="None",
                                        Address=self.host, Port=self.port)
        self.conn.Connect()

    def onStop(self):
        if self.conn.Connected() or self.conn.Connecting():
            self.conn.Disconnect()
        Domoticz.Debug("onStop - Plugin is stopping.")

    def onDisconnect(self, Connection):
        Domoticz.Debug(f"onDisconnect called for Connection "
                       f"{Connection.Name} to: {Connection.Address}:{Connection.Port}")

    def onConnect(self, Connection, status, Description):
        Domoticz.Debug(f"onConnect called for Connection {Connection.Name} to: {Connection.Address}:{Connection.Port}")
        Domoticz.Debug(f"onConnect status: {str(status)}, Description: {str(Description)}")
        
        if not Connection.Connected():
            Domoticz.Debug(f"onConnect status: {str(status)}, Description: {str(Description)}")
            return
        
        if Connection.Name == "WRITE":
            while not self.commandToSend.empty():
                Connection.Send(self.commandToSend.get())
        elif Connection.Name == "READ":
            self.conn.Send(self.Venta.get_info_str())

    def onMessage(self, Connection, Data):
        Domoticz.Debug(f"onMessage called for connection {Connection.Name} to: {Connection.Address}:{Connection.Port}")
        self.update_devices(Data.decode())

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug(f"onCommand called for Unit: {str(Unit)}, Command {str(Command)}, Level: {str(Level)}")
        if Unit in self.UNITS_ID_KEYS:
            action = self.UNITS_ID_KEYS[Unit].name
            action_class = getattr(self.Venta, action)
            target_method = getattr(action_class, str(Command).lower().replace(" ", "_"))
            message = target_method(Level)

            self.commandToSend.put(message)
            self.conn_write = Domoticz.Connection(Name="WRITE", Transport="TCP/IP", Protocol="None",
                                       Address=self.host, Port=self.port)

            self.conn_write.Connect()

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called.")
        if self.conn.Connected():
            self.conn.Send(self.Venta.get_info_str())
        else:
            if not self.conn.Connecting():
                self.conn.Connect()

    def onTimeout(self, Connection):
        Domoticz.Debug(f"onTimeout called for connection to: {Connection.Address}: {Connection.Port}")
        if self.conn.Connected() or self.conn.Connecting():
            self.conn.Disconnect()


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def onTimeout(Connection):
    global _plugin
    _plugin.onTimeout(Connection)


def update_device(unit,
                  n_value=-1, s_value="", image_id=-1, sig_lvl=-1, bat_lvl=-1, opt=None, timed_out=-1, name="",
                  type_name="", type=-1, sub_type=-1, switch_type=-1, used=-1, descr="", color="", supp_trigg=-1):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if opt is None:
        opt = {}

    Domoticz.Debug(f"update_device unit: {str(unit)}")
    if unit not in Devices:
        global _plugin
        _plugin.create_devices()

    args = {}
    # Must always be passed for update
    if n_value != -1:
        args["nValue"] = n_value
    else:
        args["nValue"] = Devices[unit].nValue
    s_value = str(s_value)
    if len(s_value) > 0:
        args["sValue"] = s_value
    else:
        args["sValue"] = Devices[unit].sValue

    # Optionals
    if image_id != -1:
        args["Image"] = image_id
    if sig_lvl != -1:
        args["SignalLevel"] = sig_lvl
    if bat_lvl != -1:
        args["BatteryLevel"] = bat_lvl
    opt = str(opt)
    if len(opt) > 0:
        args["Options"] = opt
    if timed_out != -1:
        args["TimedOut"] = timed_out
    name = str(name)
    if len(name) > 0:
        args["Name"] = name
    type_name = str(type_name)
    if len(type_name) > 0:
        args["TypeName"] = type_name
    if type != -1:
        args["Type"] = type
    if sub_type != -1:
        args["Subtype"] = sub_type
    if switch_type != -1:
        args["Switchtype"] = switch_type
    if used != -1:
        args["Used"] = used
    descr = str(descr)
    if len(descr) > 0:
        args["Description"] = descr
    color = str(color)
    if len(color) > 0:
        args["Color"] = color
    if supp_trigg != -1:
        args["SuppressTriggers"] = supp_trigg
    Domoticz.Debug(f"Update with {str(args)}")
    Devices[unit].Update(**args)


# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug(f"'{x}':'{str(Parameters[x])}'")
    Domoticz.Debug(f"Device count: {str(len(Devices))}")
    for x in Devices:
        Domoticz.Debug(f"Device:           {str(x)} - {str(Devices[x])} ")
        Domoticz.Debug(f"Device ID:       '{str(Devices[x].ID)}'        ")
        Domoticz.Debug(f"Device Name:     '{Devices[x].Name}'           ")
        Domoticz.Debug(f"Device nValue:    {str(Devices[x].nValue)}     ")
        Domoticz.Debug(f"Device sValue:   '{Devices[x].sValue}'         ")
        Domoticz.Debug(f"Device LastLevel: {str(Devices[x].LastLevel)}  ")
    return
