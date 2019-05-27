#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import os
from raspiot.utils import InvalidParameter, MissingParameter
from raspiot.libs.commands.alsa import Alsa
from raspiot.libs.commands.lsmod import Lsmod
from raspiot.libs.configs.etcasoundconf import EtcAsoundConf
from raspiot.libs.drivers.audiodriver import AudioDriver
from raspiot.libs.internals.console import Console
from raspiot.libs.configs.configtxt import ConfigTxt
from raspiot.libs.configs.etcmodules import EtcModules

class Seeed2micAudioDriver(AudioDriver):
    """
    Audio driver for seeed-2mic-voicecard device

    Note:
        http://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/
    """

    CARD_NAME = u'seeed-2mic-voicecard'

    VOLUME_PLAYBACK_CONTROL = u'Playback'
    VOLUME_PLAYBACK_PATTERN = (u'Front Left', r'\[(\d*)%\]')
    VOLUME_CAPTURE_CONTROL = u'Capture'
    VOLUME_CAPTURE_PATTERN = (u'Front Left', r'\[(\d*)%\]')

    RESPEAKER_REPO = u'https://github.com/respeaker/seeed-voicecard.git'
    TMP_DIR = u'/tmp/respeaker'

    DRIVER_PATH = u'/boot/overlays/seeed-2mic-voicecard.dtbo'
    MODULE_NAMES = [
        u'snd-soc-ac108',
        u'snd-soc-seeed-voicecard',
        u'snd-soc-wm8960',
    ]
    PATHS = {
        u'etc': u'/etc/voicecard/',
        u'bin': u'/usr/bin/seeed-voicecard',
        u'service': u'/lib/systemd/system/seeed-voicecard.service'
    }

    def __init__(self, cleep_filesystem):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
        """
        #init
        AudioDriver.__init__(self, cleep_filesystem, u'Seeed Respeaker2mic', self.CARD_NAME)

        #members
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.alsa = Alsa(self.cleep_filesystem)
        self.lsmod = Lsmod()
        self.asoundconf = EtcAsoundConf(self.cleep_filesystem)
        self.configtxt = ConfigTxt(self.cleep_filesystem)
        self.etcmodules = EtcModules(self.cleep_filesystem)
        self.console = Console()
        self.__driver_task = None

    def _get_card_name(self):
        """
        Return card name

        Returns:
            string: card name
        """
        return self.CARD_NAME

    def _get_card_capabilities(self):
        """ 
        Return card capabilities

        Returns:
            tuple: card capabilities::

                (
                    bool: playback capability,
                    bool: capture capability
                )
        """
        return (True, True)

    def _get_repository(self):
        """
        Get respeaker repository
        """
        #make sure directory does not exist
        if os.path.exists(self.TMP_DIR):
            self.cleep_filesystem.rmdir(self.TMP_DIR)

        #get sources
        cmd = u'/usr/bin/git clone "%s" "%s" 2> /dev/null' % (self.RESPEAKER_REPO, self.TMP_DIR)
        self.logger.debug(u'Respeaker prepare driver cmd: %s' % cmd)
        res = self.console.command(cmd, timeout=120)
        if res[u'killed'] or not os.path.exists(self.TMP_DIR):
            self.logger.error(u'Error occured during git clone command: %s' % res)
            raise Exception(u'Unable to install or uninstall respeaker driver: respeaker repository seems not available.')
        if not os.path.exists(os.path.join(self.TMP_DIR, u'install.sh')) or not os.path.exists(os.path.join(self.TMP_DIR, u'uninstall.sh')):
            self.logger.error('Install.sh or uninstall.sh scripts do not exists.')
            raise Exception(u'Unable to install or uninstall respeaker driver: some scripts do not exist.')

    def __process_status_callback(self, stdout, stderr):
        """
        Called when running process received something on stdout/stderr

        Args:
            stdout (string): command stdout string
            stderr (string): command stderr string
        """
        #log for debug installation logs
        if stdout:
            self.logger.info(u'Driver process stdout: %s' % stdout)
        if stderr:
            self.logger.error(u'Driver process stderr: %s' % stderr)

    def __install_terminated_callback(self, return_code, killed):
        """
        Called when running process is terminated

        Args:
            return_code (string): command return code
            killed (bool): if True command was killed
        """
        self.logger.info('Respeaker driver process return code: %s (killed %s)' % (return_code, killed))

    def _install(self, params=None):
        """
        Install driver

        Args:
            callback (function): function called after installation
            params (dict): additional parameters

        Returns:
            bool: True if install succeed
        """
        #clone git repo
        self._get_repository()
        
        #build and install driver
        command = u'cd "%s"; ./install.sh 2mic' % self.TMP_DIR
        self.logger.debug('Respeaker driver install command: %s' % command)
        console = EndlessConsole()
        console.command(command, self.__process_status_callback, self.__install_terminated_callback)
        console.start()
        #make EndlessConsole blocking
        console.join()

        #clean everything
        if os.path.exists(self.TMP_DIR):
            self.cleep_filesystem.rmdir(self.TMP_DIR)

        #check install.sh return code
        if console.get_last_return_code()!=0:
            return False

        #disable seeed-voicecard systemd service because system is readonly cleep needs to handle its execution by itself
        cmd = u'/bin/systemctl disable seeed-voicecard.service'
        resp = self.console.command(cmd)
        self.logger.debug(u'Service "seeed-voicecard" disabling response: %s' % resp)
        cmd = u'/bin/systemctl stop seeed-voicecard.service'
        resp = self.console.command(cmd)
        self.logger.debug(u'Service "seeed-voicecard" stopping response: %s' % resp)

        #finalize installation fixing some mandatory features that may not have worked during install.sh script
        config = self.configtxt.enable_i2c() and self.configtxt.enable_i2s() and self.configtxt.enable_i2s_mmap() and self.configtxt.enable_spi()
        self.logger.debug(u'Config check %s' % config)
        module = all([self.etcmodules.enable_module(m) for m in self.MODULE_NAMES])
        self.logger.debug(u'Module check %s' % module)
        paths = all([os.path.exists(p) for p in self.PATHS.values()])
        self.logger.debug(u'Paths check %s' % paths)

        return True if config and module and paths else False

    def _uninstall(self, params=None):
        """
        Uninstall driver

        Args:
            callback (function): function called after uninstallation
            params (dict): additional parameters

        Raises:
            CommandError: if command failed
            Exception: if error occured during process
        """
        #first of all disable it
        self.disable()

        #clone git repo
        self._get_repository()
        
        #uninstall driver
        cmd = u'cd "%s"; ./uninstall.sh 2mic' % self.TMP_DIR
        console = Console()
        resp = console.command(cmd)
        self.logger.info(u'Uninstall command "%s" resp: %s' % (cmd, resp))

        #clean everything
        if os.path.exists(self.TMP_DIR):
            self.cleep_filesystem.rmdir(self.TMP_DIR)

        #make sure everything is disabled in /boot/config.txt
        config = self.configtxt.disable_i2c() and self.configtxt.disable_i2s() and self.configtxt.disable_i2s_mmap() and self.configtxt.disable_spi()
        self.logger.info(u'Config check %s' % config)

        #make sure all files are deleted
        if os.path.exists(self.PATHS[u'etc']):
            self.cleep_filesystem.rmdir(self.PATHS[u'etc'])
        if os.path.exists(self.PATHS[u'bin']):
            self.cleep_filesystem.rm(self.PATHS[u'bin'])
        if os.path.exists(self.PATHS[u'service']):
            self.cleep_filesystem.rm(self.PATHS[u'service'])

        #make sure all sound modules are disabled
        module = all([self.etcmodules.disable_module(m) for m in self.MODULE_NAMES])
        self.logger.info(u'Module check %s' % module)

        return True if config and module else False

    def is_installed(self):
        """
        Is driver installed

        Returns:
            bool: True if driver is installed
        """
        boot = self.configtxt.is_i2c_enabled() and self.configtxt.is_i2s_enabled() and self.configtxt.is_i2s_mmap_enabled() and self.configtxt.is_spi_enabled()
        modules =  all([self.etcmodules.is_module_enabled(module) for module in self.MODULE_NAMES])
        paths = all([os.path.exists(p) for p in self.PATHS.values()])
        self.logger.debug(u'is installed? boot=%s modules=%s paths=%s' % (boot, modules, paths))

        return boot and modules and paths

    def enable(self, params=None):
        """
        Enable driver

        Note:
            Enabling seeed-voicecard driver consists of running /usr/bin/seeed-voicecard binary
            which should be ran during system startup. But due to RO filesystem it can't create
            all it needs. So we need to enable it during cleep startup.

        Returns:
            bool: True if driver enabled
        """
        out = True

        #enable filesystem writings while executing seeed-voicecard script
        self.cleep_filesystem.enable_write(root=True, boot=False)

        try:
            #bypass /usr/bin/seeed-voicecard binary that is not reliable (sometimes i2cdetect does not work)
            #but execute the same commands below
            self.cleep_filesystem.rm(u'/etc/asound.conf')
            self.cleep_filesystem.rm(u'/var/lib/alsa/asound.state')
            if not self.cleep_filesystem.ln(u'/etc/voicecard/asound_2mic.conf', u'/etc/asound.conf'):
                raise Exception(u'Unable to create symlink to /etc/asound.conf')
            if not self.cleep_filesystem.ln(u'/etc/voicecard/wm8960_asound.state', u'/var/lib/alsa/asound.state'):
                raise Exception(u'Unable to create symlink to /var/lib/alsa/asound.state')
            if not self.alsa.amixer_control(Alsa.CSET, 3, 1):
                raise Exception(u'Error executing amixer control command')

            #patch asound_2mic.conf adding default ctl if necessary
            default_ctl = self.asoundconf.get_default_ctl_section()
            if default_ctl is None:
                self.logger.debug(u'Add missing CTL section in asound.conf')
                (card_id, device_id) = self._get_cardid_deviceid()
                self.asoundconf.add_default_ctl_section(card_id, device_id)

        except:
            self.logger.exception(u'Error while enabling driver:')
            out = False

        finally:
            #disable filesystem writings
            self.cleep_filesystem.disable_write(root=True, boot=False)

        return out

    def disable(self, params=None):
        """
        Disable driver

        Args:
            params (dict): additional parameters

        Returns:
            bool: True if driver disabled
        """
        #delete alsa conf
        self.asoundconf.delete()
        if os.path.exists('/var/lib/alsa/asound.state'):
            self.cleep_filesystem.rm('/var/lib/alsa/asound.state')
        
        return True

    def is_enabled(self):
        """
        Returns True if driver is enabled

        Returns:
            bool: True if enable
        """
        #check if alsa conf is sym linked to seeed files
        asoundconf = os.path.islink(u'/etc/asound.conf') and os.path.realpath(u'/etc/asound.conf')==u'/etc/voicecard/asound_2mic.conf'
        asoundstate = os.path.islink(u'/var/lib/alsa/asound.state') and os.path.realpath(u'/var/lib/alsa/asound.state')==u'/etc/voicecard/wm8960_asound.state'
        self.logger.debug(u'is enabled? asoundconf=%s asoundstate=%s' % (asoundconf, asoundstate))

        #check loaded system modules
        modules = True
        for module in self.MODULE_NAMES:
            if not self.lsmod.is_module_loaded(module):
                self.logger.debug(u'System module "%s" is not loaded' % module)
                modules = False

        return asoundconf and asoundstate and modules

    def get_volumes(self):
        """
        Get volumes

        Returns:
            dict: volumes level::

                {
                    playback (float): playback volume
                    capture (float): capture volume
                }

        """
        return {
            u'playback': self.alsa.get_volume(self.VOLUME_PLAYBACK_CONTROL, self.VOLUME_PLAYBACK_PATTERN),
            u'capture': self.alsa.get_volume(self.VOLUME_CAPTURE_CONTROL, self.VOLUME_CAPTURE_PATTERN)
        }

    def set_volumes(self, playback=None, capture=None):
        """
        Set volumes

        Args:
            playback (float): playback volume (None to disable update)
            capture (float): capture volume (None to disable update)

        Returns:
            dict: volumes level::

                {
                    playback (float): playback volume
                    capture (float): capture volume
                }

        """
        return {
            u'playback': self.alsa.set_volume(self.VOLUME_PLAYBACK_CONTROL, self.VOLUME_PLAYBACK_PATTERN, playback),
            u'capture': self.alsa.set_volume(self.VOLUME_CAPTURE_CONTROL, self.VOLUME_CAPTURE_PATTERN, capture)
        }

