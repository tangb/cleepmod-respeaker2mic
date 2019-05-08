/**
 * Respeaker2mic config directive
 * Handle respeaker2mic hat configuration
 */
var respeaker2micConfigDirective = function($rootScope, toast, respeaker2micService, raspiotService, $mdDialog, confirm) {

    var respeaker2micController = function()
    {
        var self = this;
        self.driverStatus = 'notinstalled';
        self.ledsProfiles = [];
        self.newActions = [];
        self.selectedLedsProfile = {
            name: null,
            id: null,
            actions: [],
            repeat: 0
        };

        self.actions = [
            {label:'Set LED1', value:1},
            {label:'Set LED2', value:2},
            {label:'Set LED3', value:3},
            {label:'Set all LEDs', value:4},
            {label:'Pause', value:5}
        ];
        self.colors = [
            {label:'White', value:'white'},
            {label:'Red', value:'red'},
            {label:'Green', value:'green'},
            {label:'Blue', value:'blue'},
            {label:'Yellow', value:'yellow'},
            {label:'Cyan', value:'cyan'},
            {label:'Magenta', value:'magenta'},
            {label:'Off', value:'black'}
        ];
        self.brightnesses = [
            {label:'Off', value:0},
            {label:'10%', value:10},
            {label:'20%', value:20},
            {label:'30%', value:30},
            {label:'40%', value:40},
            {label:'50%', value:50},
            {label:'60%', value:60},
            {label:'70%', value:70},
            {label:'80%', value:80},
            {label:'90%', value:90},
            {label:'Full brightness', value:100}
        ];
        self.repetitions = [
            {label:'No repetition', value:0},
            {label:'Undefinitely', value:99},
            {label:'Once', value:1},
            {label:'Twice', value:2},
            {label:'Thrice', value:3},
            {label:'Four times', value:4},
            {label:'Five times', value:5}
        ];

        self.newLedsProfileName = 'My profile';
        self.newLedsProfileAction = 1;
        self.newLedsProfileColor = 'white';
        self.newLedsProfileBrightness = 50;
        self.newLedsProfilePause = 250;
        self.newLedsProfileRepeat = 0;

        /**
         * Install driver
         */
        self.installDriver = function()
        {
            confirm.open('Install driver?', 'Installing this driver will allow you to use Respeaker hardware properly.<br>At end of installation, device will reboot automatically.<br><br><strong>The installation can last some minutes.</strong>', 'Install')
                .then(function() {
                    return respeaker2micService.installDriver();
                })
                .then(function() {
                    toast.info('Installing Respeaker driver...')
                });
        };

        /**
         * Uninstall driver
         */
        self.uninstallDriver = function()
        {
            confirm.open('Uninstall driver?', 'If you uninstall driver you won\'t be able to use Respeaker hardware properly.', 'Uninstall')
                .then(function() {
                    return respeaker2micService.uninstallDriver();
                })
                .then(function(config) {
                    self.setConfig(config)
                    toast.success('Respeaker driver uninstalled. Device will reboot in few seconds to finalize uninstallation.');
                });
        };

        /**
         * Add leds profile action
         */
        self.addLedsProfileAction = function()
        {
            //append new action
            self.selectedLedsProfile.actions.push({
                action: self.newLedsProfileAction,
                color: self.newLedsProfileColor,
                brightness: self.newLedsProfileBrightness,
                pause: self.newLedsProfilePause
            });
        };

        /**
         * Remove leds profile action
         */
        self.removeLedsProfileAction = function(index)
        {
            self.selectedLedsProfile.actions.splice(index, 1);
        };

        /**
         * Move left leds profile action
         */
        self.moveLeftLedsProfileAction = function(index)
        {
            if( index==0 )
                return;
            self.selectedLedsProfile.actions.splice(index-1, 0, self.selectedLedsProfile.actions.splice(index, 1)[0]);
        };

        /**
         * Move right leds profile action
         */
        self.moveRightLedsProfileAction = function(index)
        {
            if( index==self.selectedLedsProfile.actions.length-1 )
                return;
            self.selectedLedsProfile.actions.splice(index+1, 0, self.selectedLedsProfile.actions.splice(index, 1)[0]);
        };

        /**
         * Remove leds profile
         * @param profile: profile instance to remove
         */
        self.removeLedsProfile = function(profile)
        {
            respeaker2micService.removeLedsProfile(profile)
                .then(function(config) {
                    toast.success('Leds profile removed');
                    self.setConfig(config);
                });
        };

        /**
         * Add leds profile
         */
        self.addLedsProfile = function()
        {
            respeaker2micService.addLedsProfile(self.newLedsProfileName, self.newLedsProfileRepeat, self.selectedLedsProfile.actions)
                .then(function(config) {
                    toast.success('Leds profile added');
                    self.setConfig(config);
                });
        };

        /**
         * Remove leds profile
         */
        self.removeLedsProfile = function(profile)
        {
            confirm.open('Remove leds profile', null, 'Remove')
                .then(function() {
                    return respeaker2micService.removeLedsProfile(profile.uuid);
                })
                .then(function(config) {
                    toast.success('Leds profile removed');
                    self.setConfig(config);
                });
        };

        /**
         * Test leds profile playing it
         */
        self.testLedsProfile = function(profile)
        {
            respeaker2micService.testLedsProfile(profile.uuid)
                .then(function() {
                    toast.success('You should see leds flashing');
                });
        };
        
        /**
         * Set config
         */
        self.setConfig = function(config)
        {
            //set driver status
            if( config.driverprocessing )
                self.driverStatus = 'installing';
            else if( config.driverinstalled )
                self.driverStatus = 'installed';
            else
                self.driverStatus = 'notinstalled';

            //other values
            self.ledsProfiles = config.ledsprofiles;
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //get config
            raspiotService.getModuleConfig('respeaker2mic')
                .then(function(config) {
                    self.setConfig(config);
                });

            //add action button
            var actions = [{
                icon: 'plus',
                callback: self.openAddDialog,
                tooltip: 'Add LEDs profile'
            }]; 
            $rootScope.$broadcast('enableFab', actions);
        };


        /**
         * Cancel dialog (close modal and reset variables)
         */
        self.cancelDialog = function()
        {
            if( self.testing )
            {
                //test in progress, cancel action
                return;
            }

            $mdDialog.cancel();
        };

        /**
         * Valid dialog (only close modal)
         * Note: don't forget to reset variables !
         */
        self.validDialog = function() {
            if( self.testing )
            {
                //test in progress, cancel action
                return;
            }

            $mdDialog.hide();
        };

        /**
         * Open add led profile dialog
         */
        self.openAddDialog = function()
        {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'dialogCtl',
                templateUrl: 'addLedsProfileDialog.config.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                fullscreen: true
            }).then(function() {
                self.addLedsProfile();
            });
        };

    };

    var audioLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'respeaker2mic.config.html',
        replace: true,
        scope: true,
        controller: respeaker2micController,
        controllerAs: 'respeaker2micCtl',
        link: audioLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('respeaker2micConfigDirective', ['$rootScope', 'toastService', 'respeaker2micService', 'raspiotService', '$mdDialog', 'confirmService', respeaker2micConfigDirective])

