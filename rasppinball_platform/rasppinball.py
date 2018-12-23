"""raspPinball hardware platform"""

import sys
sys.path.insert(0, '/home/sysop/pinball/led2/python/build/lib.linux-armv7l-3.4')

import logging
import asyncio

# from mpf.devices.driver import ConfiguredHwDriver
from mpf.core.platform import LightsPlatform
from mpf.core.platform import SwitchPlatform, SwitchConfig, SwitchSettings
from mpf.core.platform import DriverPlatform, DriverConfig, DriverSettings

from rasppinball_platform.keypad import Keypad
from rasppinball_platform.neopixel import *  # don't find it on raspberry
# from neopixel import * # ok sur raspberry

from rasppinball_platform.driver import RASPDriver
from rasppinball_platform.switch import RASPSwitch
from rasppinball_platform.led import RASPLed
from rasppinball_platform.serial import RaspSerialCommunicator


class RasppinballHardwarePlatform(SwitchPlatform, DriverPlatform, LightsPlatform):
    """Platform class for the raspPinball hardware.

    Args:
        machine: The main ``MachineController`` instance.

    """

    def __init__(self, machine):
        """Initialise raspPinball platform."""
        # super(HardwarePlatform, self).__init__(machine)
        super().__init__(machine)
        self.log = logging.getLogger('RASPPINBALL')
        self.log.info("Configuring raspPinball hardware.")
        self.config = None # config not loaded yet
        self.strip = None
        self.switches = dict()
        self.drivers = dict()
        self.leds = dict()
        self.communicator = None
        self.init_done = False
        self.features['has_lights'] = True
        self.features['has_switches'] = True
        self.features['has_drivers'] = True
        self.features['tickless'] = False
        # self.features['hardware_sounds'] = False

        # fake keyboard:
        #  keypad
        self._kp = Keypad()
        self.key = None
        self.old_key = None

    def __repr__(self):
        """Return string representation."""
        return '<Platform.raspPinball>'


    @classmethod
    def get_config_spec(cls):
        return "rasppinball", """
    __valid_in__: machine
    debug:       single|bool|False
    serial_port: single|str|None
    serial_baud: single|int|115200
        """

    @asyncio.coroutine
    def initialize(self):
        """Initialise connections to raspPinball hardware."""
        self.log.info("Initialize raspPinball hardware.")

        # load config if setted
        if 'rasppinball' in self.machine.config:
            # raise AssertionError('Add `rasppinball:` to your machine config')
            self.config = self.machine.config_validator.validate_config(
                config_spec="rasppinball",
                source=self.machine.config['rasppinball']
            )

        # self.config = self.machine.config['rasppinball']
        # self.machine.config_validator.validate_config("rasppinball", self.config)
        #self.machine_type = (
        #    self.machine.config['hardware']['driverboards'].lower())

        # self._connect_to_hardware()


        #  leds
        self.init_strips()
        self.init_done = True
        self.log.debug("Initialize done.")

    def stop(self):
        #!!170723:add msg halt platform
        if self.communicator:
            self.communicator.msg_halt_platform()

    def init_strips(self):
        """read strips config and init objects"""
        #!!161126:VG:init_strips
        # read only one for now...
        #self.machine.config_validator.validate_config("rasp_strip_leds", rasp_strip_leds)
        #strip_config = self.config
        #self.strip = neopixel.Adafruit_NeoPixel(
        #    strip_config['count'], strip_config['pin'], strip_config['freq'], strip_config['dma'],
        #    strip_config['invert'], strip_config['brightness'])

        self.strip = Adafruit_NeoPixel(64, 10, 800000, 5, False, 255)
        #self.strip = neopixel.Adafruit_NeoPixel(64, 10, 800000, 5, False, 255)
        # Intialize the library (must be called once before other functions).
        self.strip.begin()
        #self.strips[strip_name] = self.strip
        self.strip.updated = False

    def update_kb(self):
        s = self._kp.getKeys()
        if s != self.old_key:
            # print("Keys:%s" % s)

            #   disable sw
            for num, sw in self.switches.items():
                if (num in self.old_key) and (not num in s):
                    # print ("%s OFF" % num)
                    self.machine.switch_controller.process_switch_by_num(sw.number, state=0, platform=self, logical=False)

            for num, sw in self.switches.items():
                if (num not in self.old_key) and (num in s):
                    # print ("%s ON" % num)
                    self.machine.switch_controller.process_switch_by_num(sw.number, state=1, platform=self, logical=False)

            self.old_key = s

    def tick(self):
        """check with tick..."""
        #!!181124:VG:Poll message from communicator

        #self.update_kb()

        #!!181125:VG:fade debug led
        dbg = self.strip.getPixelColor(0)
        dbg &= 0x3F3F3F
        self.strip.setPixelColor(0, dbg)

        if self.strip.updated:
            self.strip.updated = False
            self.strip.show()

        # check communicator as it might not been initialized yet
        if self.communicator:
            #  check if there is pending message to process
            while self.communicator.peek_msg():
                pass # unpack all message
            #  resent frame not acked by Arduino
            self.communicator.resent_frames()

    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Get initial hardware switch states."""
        # TODO: ask arduinball to refresh sw states (coroutine)
        # TODO: the fake kb management cause some clear sw...
        hw_states = dict()
        for number, sw in self.switches.items():
            hw_states[number] = sw.state
        return hw_states

    def _get_pulse_ms_value(self, coil):
        if coil.config['pulse_ms']:
            return coil.config['pulse_ms']
        else:
            # use mpf default_pulse_ms
            return self.machine.config['mpf']['default_pulse_ms']

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> RASPSwitch:
        """Configure a switch. """
        # self.log.debug("configure_switch(%s)" % number)
        switch = RASPSwitch(config, number)
        self.switches[number] = switch
        return switch

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> RASPDriver:
        """Configure a driver. """
        # self.log.debug("configure_driver(%s)" % number)
        driver = RASPDriver(config, number, self)
        self.drivers[number] = driver
        return driver

    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> RASPLed:
        """Subclass this method in a platform module to configure an LED. """
        self.log.debug("configure_led(%s)" % number)
        #strip = self.strips[0]
        strip = self.strip
        led = RASPLed(number, strip)
        self.leds[number] = led
        return led

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light number to a list of channels."""
        #  There is only one strip for now...
        if subtype in ("led") or not subtype:
            return [
                {
                    "number": str(number)
                }
            ]
        else:
            raise AssertionError("Unknown subtype {}".format(subtype))

    def light_sync(self):
        """Update lights synchonously."""
        if self.strip.updated:
            self.strip.updated = False
            self.strip.show()





    def clear_hw_rule(self, switch, coil):
        """Clear a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        """
        self.log.info("clear_hw_rule(coil=%s sw=%s)" %
                       (coil.hw_driver.number, switch.hw_switch.number))
        self.communicator.rule_clear(coil.hw_driver.number, switch.hw_switch.number)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse continues. Typically used for
        autofire coils such as pop bumpers.
        """
        self.log.info("set_pulse_on_hit_rule(coil=%s sw=%s)" %
                       (coil.hw_driver.number, enable_switch.hw_switch.number))
        self.communicator.rule_add(1, coil.hw_driver.number, enable_switch.hw_switch.number, 
                                   duration=self._get_pulse_ms_value(coil))

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse is canceled. Typically used on
        the main coil for dual coil flippers without eos switch.
        """
        self.log.info("set_pulse_on_hit_and_release_rule(coil=%s sw=%s)" %
                       (coil.hw_driver.number, enable_switch.hw_switch.number))
        self.communicator.rule_add(2, coil.hw_driver.number, enable_switch.hw_switch.number,
                                   duration=self._get_pulse_ms_value(coil))

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and enable and relase rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. Typically used for single coil flippers.
        """
        self.log.info("set_pulse_on_hit_and_enable_and_release_rule(coil=%s sw=%s)" %
                       (coil.hw_driver.number, enable_switch.hw_switch.number))
        self.communicator.rule_add(3, coil.hw_driver.number, enable_switch.hw_switch.number,
                                   duration=self._get_pulse_ms_value(coil))

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Set pulse on hit and enable and release and disable rule on driver.

    Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. When the second disable_switch is hit the pulse is canceled
        and the driver gets disabled. Typically used on the main coil for dual coil flippers with eos switch.
        """
        self.log.info("set_pulse_on_hit_and_enable_and_release_and_disable_rule(coil=%s sw=%s dis_sw=%s)" %
                       (coil.hw_driver.number, enable_switch.hw_switch.number, disable_switch.hw_switch.number))
        self.communicator.rule_add(4, coil.hw_driver.number, enable_switch.hw_switch.number, disable_sw_id=disable_switch.hw_switch.number,
                                   duration=self._get_pulse_ms_value(coil))

    def _connect_to_hardware(self):
        """Connect to each port from the config.

        This process will cause the connection threads to figure out which processor they've connected to
        and to register themselves.
        """
        # !!!TEMP:need to validate config...
        # if len(self.config['ports']) > 1:
        #     self.log.fatal("only one slave com port is supported")
        # if len(self.config['ports']) == 0:
        #     self.log.warning("no communication port setted!")
        #     return
        # port = self.config['ports'][0]
        # self.communicator = RaspSerialCommunicator(
        #     platform=self, port=port,
        #     baud=self.config['baud'])
        self.communicator = RaspSerialCommunicator(
            platform=self, port='COM6',
            # platform=self, port='/dev/ttyAMA0',
            baud=115200)
        self.communicator.msg_init_platform()

    def process_received_message(self, msg: str):
        """dispatch an incoming message

        Args:
            msg: messaged which was received
        """

        self.log.debug("process_received_message(%s)" % msg)
        if not self.init_done:
            return  # init incomplete, don't try to process anything...

        all = msg.split(":")
        if len(all) < 2:
            self.log.warning("Recv bad formated cmd", msg)
            return
        cmd, all_param = all[:2]
        params = all_param.split(";")

        #self.strip.setPixelColorRGB(0, 0, 0, 0)
        if cmd == "":
            pass

        elif cmd == "SWU":      # switch update
            try:
                sw_number = params[0]
                sw_state = int(params[1])
                sw = self.switches[sw_number]
                sw.state = sw_state
                self.machine.switch_controller.process_switch_obj(sw, sw.state, logical=False)
                # self.machine.switch_controller.process_switch_by_num(sw_number, state=sw_state, platform=self, logical=False)
                self.strip.setPixelColorRGB(0, 0, 0, 0xff)  # blue
            except ValueError:
                self.log.error("SWU:bad frame format (%s)" % msg)
            except IndexError:
                self.log.error("SWU:incomplete frame (%s)" % msg)
                return
            if not self.switches:
                self.log.error("SWU:switches not configured")
                return

        elif cmd == "DBG":      # debug message
            self.log.debug("RECV:%s" % msg)

        elif cmd == "INF":      # information message
            self.log.info("RECV:%s" % msg)
            self.strip.setPixelColorRGB(0, 0, 0xff, 0xff)  # magenta

        elif cmd == "WRN":  # warning message
            self.log.warning("RECV:%s" % msg)
            #self.strip.setPixelColorRGB(0, 0xc0, 0xff, 0)  # red light
            self.strip.setPixelColorRGB(0, 0xff, 0xff, 0)  # yellow

        elif cmd == "ERR":  # error message
            self.log.error("RECV:%s" % msg)
            self.strip.setPixelColorRGB(0, 0, 0xff, 0)     # red

        elif cmd == "TCK":  # arduino is alive !
            self.log.debug("TCK ok:%d" % int(params[0]))
            #self.strip.setPixelColorRGB(0, 0xff, 0xff, 0xff)  # white

        elif cmd == "ACK":  # ack of frame
            self.log.debug("ACK frame:%d  ok:%s" % (int(params[0]), params[1]))
            self.communicator.ack_frame(int(params[0]), params[1] == "OK")
            self.strip.setPixelColorRGB(0, 0xff, 0, 0)     # green

        else:
            self.log.warning("RECV:UNKNOWN FRAME: [%s]" % msg)

        self.strip.show()

        l = len(self.communicator.frames)
        #TODO: self.machine['frame_cnt'] = l
        if l:
            self.machine.events.post_async('raspberry_frame_count', frame_cnt=l, frames=self.communicator.frames)
   












